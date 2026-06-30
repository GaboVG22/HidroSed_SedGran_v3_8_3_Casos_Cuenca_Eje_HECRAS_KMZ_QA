from __future__ import annotations

import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import pandas as pd
from shapely.geometry import LineString, Polygon, MultiPolygon


@dataclass
class HydrosedKmzPackage:
    kmz_bytes: bytes
    kml_bytes: bytes
    metadata: dict[str, Any]
    readme: str


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _parse_coords(text: str):
    coords = []
    for token in re.split(r'\s+', (text or '').strip()):
        if not token:
            continue
        parts = token.split(',')
        if len(parts) >= 2:
            try:
                coords.append((float(parts[0]), float(parts[1]), float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0))
            except Exception:
                continue
    return coords


def _kml_text(data: bytes | str | None) -> str:
    if data is None:
        return ''
    if isinstance(data, str):
        return data
    if data[:4] == b'PK\x03\x04':
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            kmls = [n for n in zf.namelist() if n.lower().endswith('.kml')]
            if not kmls:
                return ''
            return zf.read('doc.kml' if 'doc.kml' in kmls else kmls[0]).decode('utf-8', errors='ignore')
    return data.decode('utf-8', errors='ignore')


def _placemark_geometries_from_kml(kml: bytes | str | None, folder_name: str, style_url: str | None = None) -> list[str]:
    txt = _kml_text(kml)
    if not txt.strip():
        return []
    try:
        root = ET.fromstring(txt.encode('utf-8'))
    except Exception:
        return []
    placemarks = []
    for pm in root.iter():
        if _strip_ns(pm.tag) != 'Placemark':
            continue
        name = 'Elemento'
        for child in pm:
            if _strip_ns(child.tag) == 'name' and child.text:
                name = child.text
                break
        for geom in pm.iter():
            if _strip_ns(geom.tag) in {'Polygon', 'LineString', 'Point', 'MultiGeometry'}:
                geom_xml = ET.tostring(geom, encoding='unicode')
                # Remove namespace prefixes visually if ElementTree adds them.
                geom_xml = re.sub(r'ns\d+:', '', geom_xml).replace(' xmlns:ns0="http://www.opengis.net/kml/2.2"', '')
                su = f'<styleUrl>{style_url}</styleUrl>' if style_url else ''
                placemarks.append(f'<Placemark><name>{_xml_escape(name)}</name>{su}{geom_xml}</Placemark>')
                break
    return placemarks


def _xml_escape(s: Any) -> str:
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _line_kml(coords, name: str, style: str = '#axis') -> str:
    if not coords or len(coords) < 2:
        return ''
    txt = ' '.join(f'{float(x):.8f},{float(y):.8f},0' for x, y in coords)
    return f'<Placemark><name>{_xml_escape(name)}</name><styleUrl>{style}</styleUrl><LineString><tessellate>1</tessellate><coordinates>{txt}</coordinates></LineString></Placemark>'


def _point_kml(point: dict | tuple | None, name: str, style: str = '#point') -> str:
    if not point:
        return ''
    try:
        if isinstance(point, dict):
            lon = point.get('lon', point.get('x'))
            lat = point.get('lat', point.get('y'))
        else:
            lon, lat = point[:2]
        return f'<Placemark><name>{_xml_escape(name)}</name><styleUrl>{style}</styleUrl><Point><coordinates>{float(lon):.8f},{float(lat):.8f},0</coordinates></Point></Placemark>'
    except Exception:
        return ''


def _sections_kml(points_df: pd.DataFrame | None, name: str = 'Secciones transversales') -> list[str]:
    if points_df is None or getattr(points_df, 'empty', True):
        return []
    df = points_df.copy()
    # Exporta solo si hay coordenadas UTM o lon/lat. Para UTM se transforma desde EPSG:32719 por defecto.
    if {'Coord_X_UTM', 'Coord_Y_UTM'}.issubset(df.columns) and df['Coord_X_UTM'].notna().any() and df['Coord_Y_UTM'].notna().any():
        try:
            from pyproj import Transformer
            tr = Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True)
            x, y = tr.transform(pd.to_numeric(df['Coord_X_UTM'], errors='coerce').to_numpy(), pd.to_numeric(df['Coord_Y_UTM'], errors='coerce').to_numpy())
            df['_lon'], df['_lat'] = x, y
        except Exception:
            return []
    elif {'lon', 'lat'}.issubset(df.columns):
        df['_lon'], df['_lat'] = pd.to_numeric(df['lon'], errors='coerce'), pd.to_numeric(df['lat'], errors='coerce')
    else:
        return []
    sid_col = 'XS_ID' if 'XS_ID' in df.columns else 'section_id' if 'section_id' in df.columns else None
    if sid_col is None:
        return []
    out = []
    for sid, g in df.dropna(subset=['_lon', '_lat']).groupby(sid_col):
        coords = list(zip(g['_lon'].astype(float), g['_lat'].astype(float)))
        if len(coords) >= 2:
            out.append(_line_kml(coords, f'{name} {sid}', '#section'))
    return out


def _make_kmz(kml: bytes, readme: str, extra_files: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml)
        zf.writestr('README.txt', readme.encode('utf-8'))
        for n, b in (extra_files or {}).items():
            zf.writestr(n, b)
    return buf.getvalue()


def _document_kml(name: str, folders: list[tuple[str, list[str]]], metadata: dict[str, Any]) -> bytes:
    styles = '''
<Style id="basin"><LineStyle><color>ff0066ff</color><width>2.5</width></LineStyle><PolyStyle><color>330066ff</color></PolyStyle></Style>
<Style id="active"><LineStyle><color>ff00a5ff</color><width>3</width></LineStyle><PolyStyle><color>3300a5ff</color></PolyStyle></Style>
<Style id="axis"><LineStyle><color>ff00a5ff</color><width>3.5</width></LineStyle></Style>
<Style id="external_axis"><LineStyle><color>ff8a2be2</color><width>3.5</width></LineStyle></Style>
<Style id="contour"><LineStyle><color>ff222222</color><width>1</width></LineStyle></Style>
<Style id="section"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle></Style>
<Style id="point"><IconStyle><scale>1.0</scale><Icon><href>http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png</href></Icon></IconStyle></Style>
'''
    folder_txt = []
    for fname, items in folders:
        if not items:
            continue
        folder_txt.append(f'<Folder><name>{_xml_escape(fname)}</name>' + '\n'.join(items) + '</Folder>')
    meta_desc = _xml_escape(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>{_xml_escape(name)}</name>
{styles}
<Folder><name>Metadatos</name><Placemark><name>Metadatos proyecto</name><description><![CDATA[{meta_desc}]]></description><Point><coordinates>0,0,0</coordinates></Point></Placemark></Folder>
{''.join(folder_txt)}
</Document>
</kml>
'''
    return kml.encode('utf-8')


def build_axis_kmz_package(*, axis_coords=None, auto_axis_coords=None, control_point=None, outlet_point=None, abc_points: dict | None = None, case_key: str = '', case_title: str = '', missing: list[str] | None = None) -> HydrosedKmzPackage:
    axis = axis_coords if axis_coords and len(axis_coords) >= 2 else auto_axis_coords
    items = []
    if axis and len(axis) >= 2:
        items.append(_line_kml(axis, 'Eje cauce/modelación activo', '#axis'))
    cp_items = [_point_kml(control_point, 'Punto de control'), _point_kml(outlet_point, 'Punto de salida / punto ajustado')]
    for k, p in (abc_points or {}).items():
        cp_items.append(_point_kml(p, f'Punto {k}'))
    metadata = {'case_key': case_key, 'case_title': case_title, 'incluye_eje': bool(axis and len(axis) >= 2), 'missing': missing or []}
    folders = [('Eje de cauce de cuenca', items), ('Puntos de control y salida', [i for i in cp_items if i])]
    readme = 'Exportación eje_cauce_cuenca.kmz\n' + json.dumps(metadata, ensure_ascii=False, indent=2, default=str)
    kml = _document_kml('eje_cauce_cuenca HidroSed', folders, metadata)
    return HydrosedKmzPackage(_make_kmz(kml, readme), kml, metadata, readme)


def build_unified_kmz_package(*, basin_prelim_kml=None, basin_corrected_kml=None, basin_active_kml=None, contours_basin_kml=None, contours_axis_kml=None, axis_coords=None, external_axis_coords=None, sections_generated_df=None, sections_excel_df=None, control_point=None, outlet_point=None, abc_points: dict | None = None, metadata: dict | None = None) -> HydrosedKmzPackage:
    missing = []
    folders = []
    for label, kml, style in [
        ('Cuenca preliminar', basin_prelim_kml, '#basin'),
        ('Cuenca corregida', basin_corrected_kml, '#active'),
        ('Cuenca activa / validada', basin_active_kml, '#active'),
    ]:
        items = _placemark_geometries_from_kml(kml, label, style)
        if items:
            folders.append((label, items))
        else:
            missing.append(label)
    axis_items = []
    if axis_coords and len(axis_coords) >= 2:
        axis_items.append(_line_kml(axis_coords, 'Eje de cauce de la cuenca', '#axis'))
    else:
        missing.append('Eje de cauce de la cuenca')
    if external_axis_coords and len(external_axis_coords) >= 2:
        axis_items.append(_line_kml(external_axis_coords, 'Eje externo/marginal/alejado', '#external_axis'))
    folders.append(('Ejes', axis_items))
    cont_basin = _placemark_geometries_from_kml(contours_basin_kml, 'Curvas de nivel de cuenca', '#contour')
    if cont_basin:
        folders.append(('Curvas de nivel de la cuenca', cont_basin))
    else:
        missing.append('Curvas de nivel de cuenca')
    cont_axis = _placemark_geometries_from_kml(contours_axis_kml, 'Curvas de apoyo del eje', '#contour')
    if cont_axis:
        folders.append(('Curvas de apoyo del eje', cont_axis))
    else:
        missing.append('Curvas de apoyo del eje')
    gen_sections = _sections_kml(sections_generated_df, 'Sección generada')
    excel_sections = _sections_kml(sections_excel_df, 'Sección Excel HEC-RAS')
    if gen_sections:
        folders.append(('Secciones transversales generadas', gen_sections))
    else:
        missing.append('Secciones generadas georreferenciadas')
    if excel_sections:
        folders.append(('Secciones transversales cargadas desde Excel', excel_sections))
    else:
        missing.append('Secciones Excel georreferenciadas')
    point_items = [_point_kml(control_point, 'Punto de control'), _point_kml(outlet_point, 'Punto de salida / punto ajustado')]
    for k, p in (abc_points or {}).items():
        point_items.append(_point_kml(p, f'Punto {k}'))
    folders.append(('Puntos A-B-C / control', [p for p in point_items if p]))
    meta = dict(metadata or {})
    meta['missing'] = missing
    kml = _document_kml('cuenca_eje_curvas_unificado HidroSed', folders, meta)
    readme = 'Exportación unificada HidroSed\nElementos faltantes o no disponibles:\n' + '\n'.join(f'- {m}' for m in missing) + '\n\nMetadatos:\n' + json.dumps(meta, ensure_ascii=False, indent=2, default=str)
    return HydrosedKmzPackage(_make_kmz(kml, readme), kml, meta, readme)
