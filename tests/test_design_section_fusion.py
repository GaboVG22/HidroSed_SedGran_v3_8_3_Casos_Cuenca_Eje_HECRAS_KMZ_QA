import math
import pandas as pd

from modules.design_section_fusion import (
    DesignChannelSpec,
    apply_design_channel_to_section,
    apply_design_channel_to_reach,
    build_design_channel_points,
    resolve_bottom_elevation,
)


def _sample_data():
    sec = pd.DataFrame({
        "section_id": [1, 2],
        "pk_m": [0.0, 100.0],
        "cota_fondo_m": [98.0, 97.8],
    })
    rows = []
    for sid, pk, dz in [(1, 0.0, 0.0), (2, 100.0, -0.2)]:
        for x, z in [(-10, 105), (-5, 101), (0, 98 + dz), (5, 101), (10, 105)]:
            rows.append({"section_id": sid, "pk_m": pk, "offset_m": x, "z_m": z})
    return sec, pd.DataFrame(rows)


def test_build_trapezoid_points():
    spec = DesignChannelSpec(shape="Trapecial", bottom_width_m=4, depth_m=2, side_slope_left_hv=1.5, side_slope_right_hv=2.0, bottom_elevation_m=98)
    pts = build_design_channel_points(spec)
    assert pts["offset_m"].min() == -5.0
    assert pts["offset_m"].max() == 6.0
    assert pts["z_m"].min() == 98.0
    assert pts["z_m"].max() == 100.0


def test_rectangular_fusion_updates_profile_and_summary():
    sec, pts = _sample_data()
    original = pts[pts.section_id == 1].copy()
    bottom = resolve_bottom_elevation(original, "rebaje_relativo", value=0.5)
    spec = DesignChannelSpec(shape="Rectangular", bottom_width_m=4, depth_m=2, bottom_elevation_m=bottom, transition_width_m=1)
    sec2, pts2, summary, original_tagged = apply_design_channel_to_section(sec, pts, 1, spec)
    p1 = pts2[pts2.section_id == 1]
    assert len(p1) >= 6
    assert math.isclose(p1["z_m"].min(), 97.5, abs_tol=1e-6)
    assert sec2.loc[sec2.section_id == 1, "estado_revision"].iloc[0] == "Rellenada"
    assert summary.loc[0, "accion"] == "fusion_seccion_puntual"
    assert not original_tagged.empty
    assert set(pts2["section_id"].unique()) == {1, 2}


def test_reach_fusion_modifies_all_targets():
    sec, pts = _sample_data()
    spec = DesignChannelSpec(shape="Trapecial", bottom_width_m=3, depth_m=1.5, side_slope_left_hv=1, side_slope_right_hv=1, bottom_elevation_m=97.0, transition_width_m=1)
    sec2, pts2, summary, originals = apply_design_channel_to_reach(sec, pts, 0, 100, spec, bottom_elevation_mode="cota_absoluta")
    assert len(summary) == 2
    assert set(summary["accion"]) == {"fusion_tramo"}
    assert (sec2["estado_revision"] == "Rellenada").sum() == 2
    assert (pts2.groupby("section_id")["z_m"].min() <= 97.0).all()
    assert len(originals) == len(pts)
