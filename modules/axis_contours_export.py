from __future__ import annotations

from dataclasses import dataclass
import io
import zipfile
from typing import Any

from shapely.geometry import LineString, MultiLineString
from shapely.ops import transform as shp_transform

from modules.basin_contours_export import _line_records_from_kml, _normalise_axis_coords


@dataclass
class AxisContoursOutput:
    kmz_bytes: bytes
    kml_bytes: bytes
    metadata: dict[str, Any]


def _utm_for_lonlat(lon: float, lat: float):
    from pyproj import CRS
    zone = int((lon + 180) // 6) + 1
    epsg = 32700 + zone if lat < 0 else 32600 + zone
    return CRS.from_epsg(epsg)


def build_axis_contours_kmz(contours_kml, axis_line_coords, buffer_m: float = 300.0) -> AxisContoursOutput:
    axis = _normalise_axis_coords(axis_line_coords)
    if len(axis) < 2:
        raise ValueError('Se requiere eje con al menos dos puntos para generar curvas de apoyo del eje.')
    records = _line_records_from_kml(contours_kml)
    if not records:
        raise ValueError('No se encontraron curvas en el KML de entrada.')
    lon = sum(x for x, y in axis) / len(axis)
    lat = sum(y for x, y in axis) / len(axis)
    crs_m = _utm_for_lonlat(lon, lat)
    from pyproj import Transformer
    fwd = Transformer.from_crs('EPSG:4326', crs_m, always_xy=True)
    inv = Transformer.from_crs(crs_m, 'EPSG:4326', always_xy=True)
    axis_m = shp_transform(lambda x, y, z=None: fwd.transform(x, y), LineString(axis))
    corridor = axis_m.buffer(float(buffer_m), cap_style=2, join_style=2)
    clipped = []
    for rec in records:
        line = LineString(rec['coords'])
        line_m = shp_transform(lambda x, y, z=None: fwd.transform(x, y), line)
        inter = line_m.intersection(corridor)
        if inter.is_empty:
            continue
        geoms = [inter] if isinstance(inter, LineString) else list(inter.geoms) if hasattr(inter, 'geoms') else []
        for g in geoms:
            if isinstance(g, LineString) and len(g.coords) >= 2:
                g_wgs = shp_transform(lambda x, y, z=None: inv.transform(x, y), g)
                clipped.append({'name': rec.get('name'), 'level': rec.get('level'), 'coords': list(g_wgs.coords)})
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n',
        '<name>Curvas de apoyo del eje HidroSed</name>\n',
        '<Style id="axis"><LineStyle><color>ff00a5ff</color><width>3</width></LineStyle></Style>\n',
        '<Style id="contour"><LineStyle><color>ff222222</color><width>1</width></LineStyle></Style>\n',
        '<Folder><name>Eje</name>',
        '<Placemark><name>Eje de modelación</name><styleUrl>#axis</styleUrl><LineString><tessellate>1</tessellate><coordinates>',
        ' '.join(f'{x:.8f},{y:.8f},0' for x, y in axis),
        '</coordinates></LineString></Placemark></Folder>\n',
        '<Folder><name>Curvas de nivel en corredor del eje</name>\n'
    ]
    for i, rec in enumerate(clipped, start=1):
        name = rec.get('name') or f'Curva eje {i}'
        coord_txt = ' '.join(f'{x:.8f},{y:.8f},0' for x, y in rec['coords'])
        parts.append(f'<Placemark><name>{name}</name><styleUrl>#contour</styleUrl><LineString><tessellate>1</tessellate><coordinates>{coord_txt}</coordinates></LineString></Placemark>\n')
    parts.append('</Folder></Document></kml>')
    kml = ''.join(parts).encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml)
        zf.writestr('README.txt', f'Curvas de apoyo del eje. Buffer {float(buffer_m):.2f} m. Curvas exportadas: {len(clipped)}')
    return AxisContoursOutput(buf.getvalue(), kml, {'buffer_m': float(buffer_m), 'curvas_entrada': len(records), 'curvas_exportadas': len(clipped), 'epsg_trabajo': int(crs_m.to_epsg())})
