from modules.basin_contours_export import build_basin_axis_kmz, build_basin_contours_kmz

BASIN_KML = b'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>cuenca</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
0,0,0 1,0,0 1,1,0 0,1,0 0,0,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</Document></kml>'''

CONTOURS_KML = b'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Curva 100</name><LineString><coordinates>0.1,0.1,0 0.9,0.9,0</coordinates></LineString></Placemark>
</Document></kml>'''


def test_build_basin_axis_exports_axis_placemark():
    out = build_basin_axis_kmz(BASIN_KML, [(0.2, 0.1), (0.4, 0.5), (0.8, 0.9)])
    assert out.kmz_bytes.startswith(b"PK")
    assert b"Eje del cauce" in out.kml_bytes
    assert out.metadata["incluye_eje"] is True
    assert out.metadata["puntos_eje"] == 3


def test_build_basin_contours_can_include_axis_in_unified_kml():
    out = build_basin_contours_kmz(BASIN_KML, CONTOURS_KML, clip_to_basin=True, axis_line_coords=[(0.2, 0.1), (0.8, 0.9)])
    assert b"Cuenca delimitada" in out.kml_bytes
    assert b"Curvas de nivel" in out.kml_bytes
    assert b"Eje del cauce" in out.kml_bytes
    assert out.metadata["incluye_eje"] is True
