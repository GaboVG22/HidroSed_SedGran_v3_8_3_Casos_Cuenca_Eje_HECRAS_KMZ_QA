from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import io
import json
import math
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import transform as shp_transform, unary_union


@dataclass
class BasinPolygonPackage:
    polygon_wgs84: Polygon | MultiPolygon
    kml_bytes: bytes
    kmz_bytes: bytes
    metrics: dict[str, Any]
    source: str


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _parse_coords_text(text: str):
    coords = []
    for token in (text or '').replace('\n', ' ').replace('\t', ' ').split():
        parts = token.split(',')
        if len(parts) >= 2:
            try:
                coords.append((float(parts[0]), float(parts[1])))
            except Exception:
                continue
    return coords


def _read_kmz_or_kml(data: bytes, filename: str = '') -> str:
    name = (filename or '').lower()
    if name.endswith('.kmz') or data[:4] == b'PK\x03\x04':
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            kml_names = [n for n in zf.namelist() if n.lower().endswith('.kml')]
            if not kml_names:
                raise ValueError('El KMZ no contiene archivo KML.')
            # Prefer doc.kml, otherwise first KML.
            chosen = 'doc.kml' if 'doc.kml' in kml_names else kml_names[0]
            return zf.read(chosen).decode('utf-8', errors='ignore')
    return data.decode('utf-8', errors='ignore')


def _polygons_from_kml_text(kml_text: str):
    root = ET.fromstring(kml_text.encode('utf-8'))
    polygons = []
    for poly_elem in root.iter():
        if _strip_ns(poly_elem.tag) != 'Polygon':
            continue
        outer = None
        holes = []
        for ring in poly_elem.iter():
            if _strip_ns(ring.tag) not in {'outerBoundaryIs', 'innerBoundaryIs'}:
                continue
            coords_text = None
            for child in ring.iter():
                if _strip_ns(child.tag) == 'coordinates':
                    coords_text = child.text or ''
                    break
            coords = _parse_coords_text(coords_text or '')
            if len(coords) >= 4:
                if _strip_ns(ring.tag) == 'outerBoundaryIs':
                    outer = coords
                else:
                    holes.append(coords)
        if outer:
            try:
                p = Polygon(outer, holes)
                if not p.is_valid:
                    p = p.buffer(0)
                if not p.is_empty and p.area > 0:
                    polygons.append(p)
            except Exception:
                continue
    if not polygons:
        raise ValueError('No se encontró polígono válido en el archivo KML/KMZ.')
    geom = unary_union(polygons)
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom


def _polygon_from_geojson(data: bytes):
    obj = json.loads(data.decode('utf-8', errors='ignore'))
    geoms = []
    if obj.get('type') == 'FeatureCollection':
        for f in obj.get('features', []):
            g = f.get('geometry')
            if g:
                geoms.append(shape(g))
    elif obj.get('type') == 'Feature':
        geoms.append(shape(obj.get('geometry')))
    else:
        geoms.append(shape(obj))
    polys = [g for g in geoms if g is not None and not g.is_empty and g.geom_type in {'Polygon', 'MultiPolygon'}]
    if not polys:
        raise ValueError('No se encontró polígono válido en GeoJSON.')
    geom = unary_union(polys)
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom


def _polygon_from_shp_zip(data: bytes):
    try:
        import fiona  # type: ignore
    except Exception as exc:
        raise RuntimeError('La lectura SHP requiere fiona/geopandas. Use KMZ/KML o GeoJSON, o instale fiona.') from exc
    tmp = None
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(td)
        shp_files = list(Path(td).rglob('*.shp'))
        if not shp_files:
            raise ValueError('El ZIP no contiene archivo .shp.')
        geoms = []
        with fiona.open(str(shp_files[0])) as src:
            crs = src.crs_wkt or src.crs
            for feat in src:
                geoms.append(shape(feat['geometry']))
        geom = unary_union([g for g in geoms if g and not g.is_empty])
        # Fiona entrega geometría en CRS fuente. Si hay CRS, transformar a WGS84.
        try:
            from pyproj import CRS, Transformer
            src_crs = CRS.from_user_input(crs)
            if src_crs.to_epsg() != 4326:
                tr = Transformer.from_crs(src_crs, 'EPSG:4326', always_xy=True)
                geom = shp_transform(lambda x, y, z=None: tr.transform(x, y), geom)
        except Exception:
            pass
        if not geom.is_valid:
            geom = geom.buffer(0)
        return geom


def polygon_from_uploaded_bytes(data: bytes, filename: str = ''):
    name = (filename or '').lower()
    if name.endswith(('.kml', '.kmz')) or data[:4] == b'PK\x03\x04':
        # ZIP can also be SHP. Try KMZ first only when KML exists.
        if data[:4] == b'PK\x03\x04':
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    names = [n.lower() for n in zf.namelist()]
                    if any(n.endswith('.kml') for n in names):
                        return _polygons_from_kml_text(_read_kmz_or_kml(data, filename))
                    if any(n.endswith('.shp') for n in names):
                        return _polygon_from_shp_zip(data)
            except zipfile.BadZipFile:
                pass
        return _polygons_from_kml_text(_read_kmz_or_kml(data, filename))
    if name.endswith(('.geojson', '.json')):
        return _polygon_from_geojson(data)
    if name.endswith('.zip'):
        return _polygon_from_shp_zip(data)
    # Fallback: try KML text then GeoJSON.
    try:
        return _polygons_from_kml_text(data.decode('utf-8', errors='ignore'))
    except Exception:
        return _polygon_from_geojson(data)


def _utm_crs_for_geom(poly_wgs):
    from pyproj import CRS
    c = poly_wgs.centroid
    zone = int((float(c.x) + 180) // 6) + 1
    epsg = 32700 + zone if float(c.y) < 0 else 32600 + zone
    return CRS.from_epsg(epsg)


def basin_metrics_from_polygon(poly_wgs) -> dict[str, Any]:
    from pyproj import Transformer
    crs_m = _utm_crs_for_geom(poly_wgs)
    tr = Transformer.from_crs('EPSG:4326', crs_m, always_xy=True)
    poly_m = shp_transform(lambda x, y, z=None: tr.transform(x, y), poly_wgs)
    area_km2 = float(poly_m.area / 1_000_000.0)
    perimeter_km = float(poly_m.length / 1000.0)
    bounds = tuple(float(v) for v in poly_wgs.bounds)
    return {
        'area_km2': area_km2,
        'area_ha': area_km2 * 100.0,
        'perimetro_km': perimeter_km,
        'epsg_morfometria': int(crs_m.to_epsg()),
        'centroide_lon': float(poly_wgs.centroid.x),
        'centroide_lat': float(poly_wgs.centroid.y),
        'bounds_wgs84': bounds,
        'estado_validacion': 'CORREGIDA_USUARIO',
        'cuenca_validada': True,
        'fuente_cuenca': 'poligono_corregido_usuario',
    }


def _polygon_to_kml_geometry(poly_wgs):
    def polygon_kml(p: Polygon):
        coords = ' '.join(f'{x:.8f},{y:.8f},0' for x, y in list(p.exterior.coords))
        holes = ''
        for ring in p.interiors:
            icoords = ' '.join(f'{x:.8f},{y:.8f},0' for x, y in list(ring.coords))
            holes += f'<innerBoundaryIs><LinearRing><coordinates>{icoords}</coordinates></LinearRing></innerBoundaryIs>'
        return f'<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs>{holes}</Polygon>'
    if isinstance(poly_wgs, MultiPolygon):
        return '<MultiGeometry>' + ''.join(polygon_kml(p) for p in poly_wgs.geoms if not p.is_empty) + '</MultiGeometry>'
    return polygon_kml(poly_wgs)


def kml_for_basin_polygon(poly_wgs, name: str = 'Cuenca corregida HidroSed', description: str = '') -> bytes:
    geom_kml = _polygon_to_kml_geometry(poly_wgs)
    desc = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>{name}</name>
<Style id="active_basin"><LineStyle><color>ff00a5ff</color><width>2.5</width></LineStyle><PolyStyle><color>3300a5ff</color></PolyStyle></Style>
<Placemark><name>{name}</name><description>{desc}</description><styleUrl>#active_basin</styleUrl>{geom_kml}</Placemark>
</Document>
</kml>
'''
    return kml.encode('utf-8')


def kmz_from_kml(kml_bytes: bytes, readme: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml_bytes)
        if readme:
            zf.writestr('README.txt', readme.encode('utf-8'))
    return buf.getvalue()


def package_corrected_basin(data: bytes, filename: str = '', source: str = 'usuario') -> BasinPolygonPackage:
    poly = polygon_from_uploaded_bytes(data, filename)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError('El polígono corregido está vacío.')
    metrics = basin_metrics_from_polygon(poly)
    desc = f"Fuente: {source}. Área: {metrics['area_km2']:.6f} km². EPSG cálculo: {metrics['epsg_morfometria']}"
    kml = kml_for_basin_polygon(poly, name='Cuenca corregida / activa HidroSed', description=desc)
    kmz = kmz_from_kml(kml, readme='Cuenca corregida cargada por el usuario y usada como cuenca activa en HidroSed.')
    return BasinPolygonPackage(poly, kml, kmz, metrics, source)


def compare_basin_areas(preliminary_metrics: dict | None, corrected_metrics: dict | None, threshold_pct: float = 5.0) -> dict[str, Any]:
    pre = float((preliminary_metrics or {}).get('area_km2') or 0.0)
    cor = float((corrected_metrics or {}).get('area_km2') or 0.0)
    diff = cor - pre
    pct = (diff / pre * 100.0) if pre > 0 else None
    significant = bool(pct is not None and abs(pct) >= float(threshold_pct))
    return {
        'area_preliminar_km2': pre,
        'area_corregida_km2': cor,
        'diferencia_km2': diff,
        'diferencia_pct': pct,
        'umbral_pct': float(threshold_pct),
        'diferencia_significativa': significant,
        'estado': 'Corregida' if cor > 0 else 'Preliminar',
    }


def area_comparison_dataframe(comp: dict[str, Any]) -> Any:
    import pandas as pd
    return pd.DataFrame([
        {'Variable': 'Área cuenca preliminar km²', 'Valor': comp.get('area_preliminar_km2')},
        {'Variable': 'Área cuenca corregida km²', 'Valor': comp.get('area_corregida_km2')},
        {'Variable': 'Diferencia km²', 'Valor': comp.get('diferencia_km2')},
        {'Variable': 'Diferencia %', 'Valor': comp.get('diferencia_pct')},
        {'Variable': 'Estado', 'Valor': comp.get('estado')},
    ])
