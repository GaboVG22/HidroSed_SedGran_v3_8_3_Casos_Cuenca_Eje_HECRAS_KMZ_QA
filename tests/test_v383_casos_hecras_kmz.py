from io import BytesIO
import zipfile

from modules.application_cases import application_cases, topo_support_status
from modules.corrected_basin_io import package_corrected_basin, compare_basin_areas
from modules.hecras_sections_io import hecras_template_bytes, read_hecras_sections_excel, SHEET_NAME
from modules.hydrosed_kmz_export import build_axis_kmz_package, build_unified_kmz_package
from modules.axis_contours_export import build_axis_contours_kmz


def simple_basin_kml():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>cuenca</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
-71.0,-30.0,0 -70.99,-30.0,0 -70.99,-29.99,0 -71.0,-29.99,0 -71.0,-30.0,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>'''


def simple_contours_kml():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>100</name><LineString><coordinates>-71.001,-29.995,0 -70.989,-29.995,0</coordinates></LineString></Placemark>
<Placemark><name>110</name><LineString><coordinates>-71.001,-29.990,0 -70.989,-29.990,0</coordinates></LineString></Placemark>
</Document></kml>'''


def test_application_cases_four_and_alerts():
    cases = application_cases()
    assert len(cases) == 4
    assert any('marginal desde salida' in c.title for c in cases.values())
    status = topo_support_status('case_4_basin_external_axis', False, False)
    assert status['required'] is True
    assert status['ok'] is False


def test_corrected_basin_package_and_compare():
    pkg = package_corrected_basin(simple_basin_kml(), 'cuenca.kml')
    assert pkg.metrics['area_km2'] > 0
    comp = compare_basin_areas({'area_km2': pkg.metrics['area_km2'] * 0.5}, pkg.metrics, threshold_pct=5)
    assert comp['diferencia_significativa'] is True


def test_hecras_template_and_validation():
    xlsx = hecras_template_bytes()
    assert len(xlsx) > 1000
    res = read_hecras_sections_excel(BytesIO(xlsx))
    assert res.ok is True
    assert not res.sections_df.empty
    assert not res.points_df.empty
    assert SHEET_NAME == 'SECCIONES_HECRAS'


def test_axis_kmz_no_axis_does_not_fail():
    pkg = build_axis_kmz_package(
        axis_coords=[],
        control_point={'lon': -71.0, 'lat': -30.0},
        outlet_point={'lon': -70.999, 'lat': -29.999},
        case_key='case_1_basin_internal_axis',
        case_title='Caso 1',
        missing=['Eje'],
    )
    assert pkg.kmz_bytes.startswith(b'PK')
    with zipfile.ZipFile(BytesIO(pkg.kmz_bytes)) as zf:
        assert 'README.txt' in zf.namelist()
        kml = zf.read('doc.kml').decode('utf-8')
        assert 'Punto de control' in kml


def test_unified_kmz_partial_state_no_fail():
    pkg = build_unified_kmz_package(
        basin_active_kml=simple_basin_kml(),
        axis_coords=[],
        contours_basin_kml=None,
        control_point={'lon': -71.0, 'lat': -30.0},
        metadata={'case_key': 'case_3_basin_marginal_axis'},
    )
    assert pkg.kmz_bytes.startswith(b'PK')
    assert 'Curvas de nivel de cuenca' in pkg.readme


def test_axis_contours_buffer_clip():
    axis = [(-71.0, -30.0), (-70.99, -29.99)]
    out = build_axis_contours_kmz(simple_contours_kml(), axis, buffer_m=1000)
    assert out.metadata['curvas_exportadas'] >= 1
    assert out.kmz_bytes.startswith(b'PK')
