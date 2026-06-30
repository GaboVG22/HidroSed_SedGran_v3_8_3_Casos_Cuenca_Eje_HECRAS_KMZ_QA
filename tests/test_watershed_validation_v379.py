import numpy as np

from modules.watershed_morphometry import _coverage_stats, _validate_basin_candidate


def test_coverage_stats_detects_border_truncation():
    valid = np.ones((8, 8), dtype=bool)
    basin = np.zeros((8, 8), dtype=bool)
    basin[0:4, 2:5] = True
    stats = _coverage_stats(basin, valid)
    assert stats["touches_dem_border"] is True
    assert stats["border_touch_cells"] > 0


def test_coverage_stats_detects_nodata_contact():
    valid = np.ones((8, 8), dtype=bool)
    valid[4, 4] = False
    basin = np.zeros((8, 8), dtype=bool)
    basin[2:5, 2:4] = True
    stats = _coverage_stats(basin, valid)
    assert stats["touches_nodata"] is True
    assert stats["nodata_adjacent_cells"] > 0


def test_validation_blocks_truncated_basin():
    valid = np.ones((10, 10), dtype=bool)
    basin = np.zeros((10, 10), dtype=bool)
    basin[0:5, 3:7] = True
    acc = np.ones((10, 10), dtype=float)
    acc[4, 5] = 100.0
    qa = _validate_basin_candidate(
        basin=basin,
        valid=valid,
        area_km2=0.02,
        expected_area_km2=None,
        max_area_km2=1.0,
        r0=4,
        c0=4,
        r1=4,
        c1=5,
        acc=acc,
        snapped_dist_m=10.0,
        snap_radius_m=100.0,
        cell_m=10.0,
        decim=1,
    )
    assert qa["cuenca_validada"] is False
    assert qa["controles_minimos"]["cuenca_no_toca_borde_dem"] is False
    assert any("borde del DEM" in d["mensaje"] for d in qa["diagnostico_tecnico"])


def test_validation_accepts_complete_candidate():
    valid = np.ones((20, 20), dtype=bool)
    basin = np.zeros((20, 20), dtype=bool)
    basin[6:14, 7:15] = True
    acc = np.ones((20, 20), dtype=float)
    acc[12, 12] = 250.0
    qa = _validate_basin_candidate(
        basin=basin,
        valid=valid,
        area_km2=0.064,
        expected_area_km2=0.06,
        max_area_km2=1.0,
        r0=12,
        c0=11,
        r1=12,
        c1=12,
        acc=acc,
        snapped_dist_m=10.0,
        snap_radius_m=100.0,
        cell_m=10.0,
        decim=1,
    )
    assert qa["cuenca_validada"] is True
    assert qa["controles_minimos"]["cuenca_no_toca_borde_dem"] is True
    assert qa["controles_minimos"]["cuenca_no_toca_nodata"] is True

from modules.watershed_morphometry import _compose_portal_basin, _upstream_mask


def test_portal_union_recovers_parallel_outlet_subbasin():
    valid = np.ones((14, 22), dtype=bool)
    ncols = valid.shape[1]
    dst = np.full(valid.size, -1, dtype=np.int64)
    outlet_a = (11, 8)
    outlet_b = (11, 12)
    # Dos subcuencas paralelas que descargan muy cerca en un abanico.
    left_cells = [(r, c) for r in range(2, 12) for c in range(3, 9)]
    right_cells = [(r, c) for r in range(2, 12) for c in range(12, 18)]
    for r, c in left_cells:
        if (r, c) != outlet_a:
            dst[r*ncols + c] = outlet_a[0]*ncols + outlet_a[1]
    for r, c in right_cells:
        if (r, c) != outlet_b:
            dst[r*ncols + c] = outlet_b[0]*ncols + outlet_b[1]
    acc = np.ones(valid.shape, dtype=float)
    acc[outlet_a] = 120.0
    acc[outlet_b] = 115.0
    primary = _upstream_mask(dst, valid, outlet_a[0]*ncols + outlet_a[1])
    assert int(primary.sum()) < 80

    union, info = _compose_portal_basin(
        dst, valid, acc,
        row=11, col=10,
        primary_row=outlet_a[0], primary_col=outlet_a[1],
        primary_basin=primary,
        portal_radius_cells=6,
        dx=10.0, dy=10.0,
        expected_area_km2=None,
        max_area_km2=1.0,
        selection_mode="area_controlled",
    )
    assert int(union.sum()) > int(primary.sum()) * 1.8
    assert info["portal_total_outlets"] >= 2
    assert info["portal_factor_incremento_area"] > 1.8
