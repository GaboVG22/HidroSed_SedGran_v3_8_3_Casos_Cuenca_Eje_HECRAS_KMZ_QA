
from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import numpy as np

import pandas as pd
import streamlit as st
from shapely.geometry import LineString

from modules.kmz_utils import read_kml, parse_first_point, parse_lines, line_to_shapely_wgs84
from modules.opentopo_engine import bbox_from_margin, bbox_area_km2, build_url, download_dem
from modules.opentopo_tiled_download import download_dem_normal_or_tiled, recommended_tiling
from modules.dem_sources import (
    dem_source_registry, dem_source_table, copernicus_tiles_for_bbox,
    download_copernicus_public_dem, download_url_bytes,
)
from modules.application_cases import (
    application_cases, case_labels, case_key_from_label, get_application_case,
    cases_dataframe, topo_support_status, output_plan_for_case, case_image_path,
)
from modules.dem_processing import generate_contours
from modules.tiled_contours import generate_tiled_contours_from_dem, split_bbox_km2_strategy
from modules.topography_support import read_kmz_kml_bytes, parse_topographic_contours, improve_section_points_with_topo
from modules.section_qaqc import select_and_fill_sections, section_report_summary
from modules.visual_3d_hydraulic import create_3d_profile_figure, create_section_selection_3d_figure, figure_to_html_bytes, VIEW_CAMERAS_3D, apply_3d_view
from modules.watershed_morphometry import delineate_basin, metrics_dataframe
from modules.axis_sections import generate_preliminary_axis, export_axis_kmz, generate_cross_sections, sections_excel_bytes
from modules.hydrology_methods import DEFAULT_T, rational_method, dga_ac_series, combine_design_flows, time_concentration_kirpich
from modules.sediment_scour import hydraulic_and_sediment
from modules.hydraulic_hecras_like import hecras_like_steady_profile, sediment_from_hecras_profile
from modules.hydraulic_advanced_qaqc import (
    enhance_hydraulic_profile, sediment_transport_advanced, manning_sensitivity,
    hydraulic_qa, monte_carlo_uncertainty, confidence_report
)
from modules.cartographic_output import make_cartographic_sheet
from modules.roughness_engine import ROUGHNESS_TABLE, COWAN_FACTORS, suggested_roughness, compose_roughness_manual, cowan_n, table_n, roughness_confidence
from modules.synthetic_trapezoid_sections import generate_trapezoid_reach_sections, trapezoid_capacity_table
from modules.granulometry_kmz import read_kmz_or_kml_to_text, parse_granulometry_points, normalize_granulometry_table, validate_granulometry, assign_granulometry_to_sections
from modules.hydrologic_transfer_dual import transfer_flow_area_altitude_distance, rank_hydrometric_stations
from modules.supreme_dashboard import CSS, kpi_html, global_confidence_report
from modules.maestra_ui import (
    MAESTRA_CSS, workflow_html, dashboard_header_html, kpi_cards_html,
    transport_kpis, transport_longitudinal_figure, capacity_by_return_period_figure,
    representative_reach_table, scour_kpis, footer_html, select_return_period, format_pk,
)
from modules.basin_contours_export import build_basin_contours_kmz, build_basin_axis_kmz
from modules.corrected_basin_io import package_corrected_basin, compare_basin_areas, area_comparison_dataframe
from modules.auto_axis_dem import generate_main_thalweg_axis_from_dem
from modules.hecras_sections_io import hecras_template_bytes, read_hecras_sections_excel
from modules.hydrosed_kmz_export import build_axis_kmz_package, build_unified_kmz_package
from modules.project_diagnostics import build_project_diagnostics, diagnostics_to_txt
from modules.axis_contours_export import build_axis_contours_kmz
from modules.hydrology_advanced import build_hydrology, adopt_flows as adopt_flows_advanced, PERIODS as HYDRO_PERIODS
from modules.sediment_dynamic import classify_sediment_zones, summarize_zones
from modules.isoyetas_engine import read_kmz_kml_to_text as read_isoyetas_kmz_kml, parse_isoyetas_kml, estimate_p24_from_isoyetas, isoyeta_inventory
from modules.data_catalog_engine import load_catalog, rank_stations_by_point, validation_station_isoyeta
from modules.normativa_hidrosed import normative_hydraulic_hydrology_check, normative_confidence_score
from modules.hydrology_normative_v35 import run_normative_hydrology
from modules.corrective_actions_v36 import (
    load_regional_coefficients,
    flow_annual_maxima_frequency,
    fill_pluviometric_gaps,
    station_isoyeta_semiphore,
    calibrate_manning_from_observed,
    sediment_applicability_ranges,
    generate_calculation_memory_text,
    unit_tests_v36,
)
from modules.granulometry_engine import (
    DEFAULT_PROFILES_MM, default_profiles_dataframe, profile_to_characteristics,
    extract_granulometry_from_excel, characteristic_table, method_diameter_table,
    profile_curve_dataframe, confidence_label
)
from modules.sections_v13_core import (
    read_kml_or_kmz as v13_read_kml_or_kmz, extract_lines_from_kml as v13_extract_lines_from_kml,
    make_transformers as v13_make_transformers, utm_epsg_from_datum as v13_utm_epsg_from_datum,
    get_lines_dataframe as v13_get_lines_dataframe, project_geom as v13_project_geom,
    generate_chainages as v13_generate_chainages, build_sections as v13_build_sections,
    sections_to_dataframe as v13_sections_to_dataframe, sample_profiles as v13_sample_profiles,
    sample_longitudinal_axis_profile as v13_sample_longitudinal_axis_profile,
    estimated_longitudinal_from_sections as v13_estimated_longitudinal_from_sections,
    evaluate_section_quality as v13_evaluate_section_quality,
    evaluate_modelable_sections as v13_evaluate_modelable_sections,
    build_longitudinal_modelacion as v13_build_longitudinal_modelacion,
    filter_sections_for_modelacion as v13_filter_sections_for_modelacion,
    filter_selected_profile_points as v13_filter_selected_profile_points,
    make_kmz_modelacion as v13_make_kmz_modelacion,
    make_zip_download as v13_make_zip_download,
)
from modules.section_improvement import compute_section_relief_stats, generate_intermediate_sections
from modules.design_section_fusion import (
    DesignChannelSpec, resolve_bottom_elevation, fuse_design_channel_into_section_points,
    apply_design_channel_to_section, apply_design_channel_to_reach,
)
from modules.hydraulic_visuals import detect_overflow_sections, create_hydraulic_longitudinal_figure, summarize_overflow_sections
from modules.axis_thalweg_qaqc import verify_and_snap_axis_to_section_minima, summarize_axis_thalweg_qa
from modules.hydrology_general import (
    DEFAULT_PERIODS as AUDIT_PERIODS,
    morphometry_table, tc_methods, select_tc_value, idf_from_p24_duration,
    rational_method_design, verni_king_modified, dga_ac_design, scs_cn_runoff,
    adopt_design_flows,
)
from modules.boundary_conditions import downstream_scenarios, audit_downstream_influence
from modules.scour_protection import general_scour_methods, local_scour_preliminary, protection_design_preliminary
from modules.external_audit_score import audit_external_report, technical_score, excel_bytes, technical_markdown_report, docx_report_bytes, pdf_report_bytes

st.set_page_config(page_title="HidroSed Maestra Integrada · v3.8.3", page_icon="🌊", layout="wide")

st.markdown(CSS + MAESTRA_CSS, unsafe_allow_html=True)

OUT = Path("outputs")
OUT.mkdir(exist_ok=True)

if "project_id" not in st.session_state:
    st.session_state["project_id"] = str(int(time.time()))
PROJECT = OUT / st.session_state["project_id"]
PROJECT.mkdir(parents=True, exist_ok=True)


def has(key: str) -> bool:
    v = st.session_state.get(key)
    if v is None:
        return False
    if hasattr(v, "empty"):
        return not v.empty
    if isinstance(v, (str, bytes, list, tuple, dict)):
        return len(v) > 0
    return True


def _axis_line_coords(axis_obj):
    """Normaliza el eje de cauce a lista de coordenadas.

    Corrige el caso en que el eje preliminar queda guardado como objeto
    Shapely LineString. Streamlit intentaba evaluar len(LineString) y
    generaba TypeError al mostrar el eje activo.
    """
    if axis_obj is None:
        return []
    if hasattr(axis_obj, "coords"):
        try:
            return [(float(c[0]), float(c[1])) for c in list(axis_obj.coords)]
        except Exception:
            return []
    if isinstance(axis_obj, dict) and "coordinates" in axis_obj:
        axis_obj = axis_obj.get("coordinates")
    try:
        coords = []
        for c in list(axis_obj):
            if len(c) >= 2:
                coords.append((float(c[0]), float(c[1])))
        return coords
    except Exception:
        return []


def _axis_line_point_count(axis_obj) -> int:
    return len(_axis_line_coords(axis_obj))


def _axis_line_as_linestring(axis_obj) -> LineString:
    coords = _axis_line_coords(axis_obj)
    if len(coords) < 2:
        raise ValueError("El eje de cauce activo no contiene al menos dos coordenadas válidas.")
    return LineString(coords)


def badge(key, label):
    if has(key):
        st.sidebar.success(f"✓ {label}")
    else:
        st.sidebar.warning(f"○ {label}")


def save_bytes(name: str, data: bytes) -> Path:
    path = PROJECT / name
    path.write_bytes(data)
    return path


def periods_from_text(txt: str):
    vals = set(DEFAULT_T)
    if txt.strip():
        for t in txt.replace(";", ",").split(","):
            try:
                vals.add(float(t.strip()))
            except Exception:
                pass
    return sorted(vals)


def _current_case_key() -> str:
    return st.session_state.get("application_case_key", "case_1_basin_internal_axis")


def _render_case_selector(compact: bool = False):
    """Muestra selector de caso y ficha desplegable sin sobrecargar la pantalla."""
    labels = case_labels()
    current_key = _current_case_key()
    current_case = get_application_case(current_key)
    current_label = f"{current_case.short_name} · {current_case.title}"
    index = labels.index(current_label) if current_label in labels else 0
    selected_label = st.selectbox(
        "Caso tipo de modelación cuenca–eje",
        labels,
        index=index,
        help="Define cómo se relaciona la cuenca aportante con el eje hidráulico de modelación.",
        key="application_case_label",
    )
    selected_key = case_key_from_label(selected_label)
    st.session_state["application_case_key"] = selected_key
    case = get_application_case(selected_key)
    topo_status = topo_support_status(
        selected_key,
        has_topo_support=has("topo_support_df"),
        has_generated_contours=has("contours_kmz") or has("contours_kml"),
    )

    badge_text = "Curvas de respaldo obligatorias" if case.topo_required else "Curvas recomendadas"
    if compact:
        st.caption(f"{case.short_name}: {case.title} · {badge_text}")
    else:
        c1, c2, c3 = st.columns([1.5, 1.1, 1.1])
        c1.metric("Caso activo", case.short_name)
        c2.metric("Respaldo topo", "Obligatorio" if case.topo_required else "Recomendado")
        c3.metric("Nivel alerta", case.alert_level.upper())

    if topo_status["level"] == "error":
        st.error(topo_status["message"])
    elif topo_status["level"] == "warning":
        st.warning(topo_status["message"])
    elif topo_status["level"] == "success":
        st.success(topo_status["message"])
    else:
        st.info(topo_status["message"])

    with st.expander("Ver ficha técnica del caso, requisitos y salidas", expanded=False):
        st.markdown(f"**{case.short_name} · {case.title}**")
        st.write(case.description)
        st.markdown(f"**Uso hidráulico:** {case.hydraulic_use}")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Insumos mínimos**")
            for item in case.required_inputs:
                st.write(f"- {item}")
            st.markdown("**Insumos opcionales**")
            for item in case.optional_inputs:
                st.write(f"- {item}")
        with cc2:
            st.markdown("**Controles QA principales**")
            for item in case.qa_focus:
                st.write(f"- {item}")
            st.markdown("**Salidas recomendadas**")
            for item in output_plan_for_case(case.key):
                st.write(f"- {item}")
        img = case_image_path(case.key, Path(__file__).parent / "assets")
        if img.exists():
            st.image(str(img), caption=f"Imagen referencial · {case.short_name}", use_container_width=True)
        st.dataframe(cases_dataframe(), use_container_width=True, hide_index=True)

    return case, topo_status


def _render_topo_requirement_alert(location: str = ""):
    case = get_application_case(_current_case_key())
    status = topo_support_status(
        case.key,
        has_topo_support=has("topo_support_df"),
        has_generated_contours=has("contours_kmz") or has("contours_kml"),
    )
    prefix = f"{location}: " if location else ""
    msg = prefix + status["message"]
    if not status["ok"]:
        if status["level"] == "error":
            st.error(msg)
        else:
            st.warning(msg)
    elif case.topo_required:
        st.success(msg)
    return status


def _set_active_basin(kind: str, kml: bytes, kmz: bytes, metrics: dict):
    """Centraliza la cuenca que usan las etapas posteriores.

    Mantiene compatibilidad con claves antiguas basin_kml/basin_kmz, pero agrega
    trazabilidad: preliminar, validada, corregida y activa.
    """
    st.session_state["basin_active_kml"] = kml
    st.session_state["basin_active_kmz"] = kmz
    st.session_state["basin_active_metrics"] = dict(metrics or {})
    st.session_state["cuenca_activa_tipo"] = kind
    st.session_state["basin_kml"] = kml
    st.session_state["basin_kmz"] = kmz
    st.session_state["basin_metrics"] = dict(metrics or {})
    try:
        st.session_state["basin_metrics_df"] = metrics_dataframe(metrics)
    except Exception:
        pass


def _active_basin_kml():
    return st.session_state.get("basin_active_kml") or st.session_state.get("basin_kml")


def _active_basin_kmz():
    return st.session_state.get("basin_active_kmz") or st.session_state.get("basin_kmz")


def _active_basin_metrics():
    return st.session_state.get("basin_active_metrics") or st.session_state.get("basin_metrics") or {}


def _outlet_point_from_metrics(metrics: dict | None = None):
    m = metrics or _active_basin_metrics()
    lon = m.get("punto_ajustado_lon") or m.get("centroide_lon")
    lat = m.get("punto_ajustado_lat") or m.get("centroide_lat")
    if lon is None or lat is None:
        return None
    try:
        return {"lon": float(lon), "lat": float(lat)}
    except Exception:
        return None


def _ensure_axis_available(silent: bool = False):
    """Usa eje manual si existe; si no, intenta eje automático por DEM.

    Nunca lanza error hacia la interfaz: devuelve lista vacía y deja diagnóstico.
    """
    manual = _axis_line_coords(st.session_state.get("axis_line"))
    if len(manual) >= 2:
        return manual, "manual_kmz"
    auto = _axis_line_coords(st.session_state.get("axis_auto_coords"))
    if len(auto) >= 2:
        return auto, "automatico_dem_thalweg"
    if has("dem_path") and has("control_point"):
        try:
            cp = st.session_state["control_point"]
            metrics = _active_basin_metrics()
            outlet = _outlet_point_from_metrics(metrics) or {"lon": cp["lon"], "lat": cp["lat"]}
            res = generate_main_thalweg_axis_from_dem(
                st.session_state["dem_path"],
                outlet_lon=float(outlet["lon"]),
                outlet_lat=float(outlet["lat"]),
                snap_radius_m=float(metrics.get("radio_ajuste_m", st.session_state.get("snap_default_m", 500)) or 500),
                max_cells=2_500_000,
                max_length_km=float(st.session_state.get("axis_auto_max_length_km", 30.0)),
            )
            st.session_state["axis_auto_coords"] = res.coords_wgs84
            st.session_state["axis_auto_meta"] = res.metadata
            if not silent:
                st.success(f"Eje automático DEM generado · {len(res.coords_wgs84)} puntos.")
            return res.coords_wgs84, "automatico_dem_thalweg"
        except Exception as exc:
            st.session_state["axis_auto_error"] = str(exc)
            if not silent:
                st.warning(f"No se pudo generar eje automático DEM. Se exportarán los elementos disponibles. Detalle: {exc}")
    return [], "sin_eje"


def _current_topo_backing_exists() -> bool:
    return bool(
        has("topo_support_df") or has("contours_kml") or has("basin_contours_kml") or
        has("axis_contours_kml") or has("hecras_sections_points") or has("section_points_df")
    )


def _render_topo_strong_warning_if_needed(location: str = ""):
    case = get_application_case(_current_case_key())
    if case.topo_required:
        st.warning(
            "Alerta topográfica: este caso requiere topografía de respaldo para el eje externo, marginal o alejado. "
            "Debe existir DEM, curvas de nivel, nube de puntos, secciones levantadas o topografía suficiente en el corredor del eje "
            "antes de generar secciones, perfiles hidráulicos o modelación."
        )
        if not _current_topo_backing_exists():
            st.error(
                "Advertencia: el eje seleccionado está fuera o parcialmente fuera de la cuenca. La modelación requiere respaldo topográfico del tramo hidráulico. "
                "Los resultados pueden no ser válidos si no se cargan curvas, DEM o secciones."
            )


def _render_hidrosed_kmz_export_panel():
    st.subheader("Exportación KMZ HidroSed")
    st.caption("Para evitar desorden, la salida principal se concentra en dos archivos KMZ. Los elementos faltantes quedan documentados dentro del README del KMZ.")
    case = get_application_case(_current_case_key())
    axis_coords, axis_src = _ensure_axis_available(silent=True)
    control_point = st.session_state.get("control_point")
    outlet_point = _outlet_point_from_metrics()
    missing = []
    if not axis_coords:
        missing.append("Eje de cauce manual o automático")
    if not _active_basin_kml():
        missing.append("Cuenca activa")
    if not has("contours_kml") and not has("basin_contours_kml"):
        missing.append("Curvas de nivel")
    metadata = {
        "version": "v3.8.3",
        "caso_tipo": case.title,
        "caso_key": case.key,
        "cuenca_activa_tipo": st.session_state.get("cuenca_activa_tipo", "sin_cuenca_activa"),
        "axis_source": axis_src,
        "area_cuenca_activa_km2": _active_basin_metrics().get("area_km2"),
        "crs_recomendado_chile": "WGS84 / UTM 19S / EPSG:32719",
    }
    try:
        eje_pkg = build_axis_kmz_package(
            axis_coords=axis_coords,
            auto_axis_coords=st.session_state.get("axis_auto_coords"),
            control_point=control_point,
            outlet_point=outlet_point,
            abc_points=st.session_state.get("abc_points", {}),
            case_key=case.key,
            case_title=case.title,
            missing=missing,
        )
        st.session_state["export_axis_hidrosed_kmz"] = eje_pkg.kmz_bytes
        st.session_state["export_axis_hidrosed_kml"] = eje_pkg.kml_bytes
        st.session_state["export_axis_hidrosed_meta"] = eje_pkg.metadata
    except Exception as exc:
        st.warning(f"No se pudo preparar eje_cauce_cuenca.kmz: {exc}")
    try:
        unified = build_unified_kmz_package(
            basin_prelim_kml=st.session_state.get("basin_preliminar_kml") or st.session_state.get("basin_candidate_kml"),
            basin_corrected_kml=st.session_state.get("basin_corregida_kml"),
            basin_active_kml=_active_basin_kml(),
            contours_basin_kml=st.session_state.get("basin_contours_kml") or st.session_state.get("contours_kml"),
            contours_axis_kml=st.session_state.get("axis_contours_kml") or st.session_state.get("contours_kml"),
            axis_coords=axis_coords,
            external_axis_coords=st.session_state.get("external_axis_line"),
            sections_generated_df=st.session_state.get("section_points_df"),
            sections_excel_df=st.session_state.get("hecras_sections_points"),
            control_point=control_point,
            outlet_point=outlet_point,
            abc_points=st.session_state.get("abc_points", {}),
            metadata=metadata,
        )
        st.session_state["export_unified_hidrosed_kmz"] = unified.kmz_bytes
        st.session_state["export_unified_hidrosed_kml"] = unified.kml_bytes
        st.session_state["export_unified_hidrosed_meta"] = unified.metadata
    except Exception as exc:
        st.warning(f"No se pudo preparar cuenca_eje_curvas_unificado.kmz: {exc}")
    c1, c2 = st.columns(2)
    if has("export_axis_hidrosed_kmz"):
        c1.download_button(
            "Descargar eje_cauce_cuenca.kmz",
            st.session_state["export_axis_hidrosed_kmz"],
            file_name="eje_cauce_cuenca.kmz",
            mime="application/vnd.google-earth.kmz",
        )
    else:
        c1.info("eje_cauce_cuenca.kmz no preparado aún.")
    if has("export_unified_hidrosed_kmz"):
        c2.download_button(
            "Descargar cuenca_eje_curvas_unificado.kmz",
            st.session_state["export_unified_hidrosed_kmz"],
            file_name="cuenca_eje_curvas_unificado.kmz",
            mime="application/vnd.google-earth.kmz",
        )
    else:
        c2.info("cuenca_eje_curvas_unificado.kmz no preparado aún.")
    with st.expander("Ver metadatos y elementos faltantes del KMZ unificado", expanded=False):
        st.json(st.session_state.get("export_unified_hidrosed_meta", metadata))


def _render_diagnostics_panel():
    case = get_application_case(_current_case_key())
    df = build_project_diagnostics(st.session_state, f"{case.short_name} · {case.title}")
    st.dataframe(df, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    c1.download_button("Descargar diagnóstico TXT", diagnostics_to_txt(df), file_name="diagnostico_tecnico_hidrosed.txt", mime="text/plain")
    c2.download_button("Descargar diagnóstico CSV", df.to_csv(index=False).encode("utf-8"), file_name="diagnostico_tecnico_hidrosed.csv", mime="text/csv")


def _hs_section_points(points_df: pd.DataFrame, section_id) -> pd.DataFrame:
    if points_df is None or points_df.empty or "section_id" not in points_df.columns:
        return pd.DataFrame()
    df = points_df[points_df["section_id"].astype(str) == str(section_id)].copy()
    if df.empty:
        return df
    if "offset_m" not in df.columns:
        # Compatibilidad con otros nombres de abscisa transversal.
        for c in ["estacion_m", "station_m", "offset", "abscisa_m"]:
            if c in df.columns:
                df["offset_m"] = pd.to_numeric(df[c], errors="coerce")
                break
    if "z_m" not in df.columns:
        for c in ["cota_m", "elevacion_m", "elevation_m", "z"]:
            if c in df.columns:
                df["z_m"] = pd.to_numeric(df[c], errors="coerce")
                break
    df["offset_m"] = pd.to_numeric(df.get("offset_m"), errors="coerce")
    df["z_m"] = pd.to_numeric(df.get("z_m"), errors="coerce")
    return df.dropna(subset=["offset_m", "z_m"]).sort_values("offset_m")


def _hs_row_by_section(df: pd.DataFrame, section_id, T=None) -> pd.Series:
    if df is None or df.empty or "section_id" not in df.columns:
        return pd.Series(dtype=object)
    dd = df[df["section_id"].astype(str) == str(section_id)].copy()
    if T is not None and "T_anios" in dd.columns:
        dd = dd[pd.to_numeric(dd["T_anios"], errors="coerce") == float(T)]
    if dd.empty:
        return pd.Series(dtype=object)
    return dd.iloc[0]


def _hs_section_review_figure(section_id, T, points_df, hydraulic_df=None, sediment_df=None):
    import plotly.graph_objects as go
    pts = _hs_section_points(points_df, section_id)
    if pts.empty:
        raise ValueError("No hay puntos transversales válidos para esta sección.")
    x = pts["offset_m"].astype(float)
    z = pts["z_m"].astype(float)
    hrow = _hs_row_by_section(hydraulic_df, section_id, T)
    srow = _hs_row_by_section(sediment_df, section_id, T)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=z, mode="lines+markers", name="Terreno natural",
        line=dict(color="#6b4f2a", width=3), marker=dict(size=4),
        hovertemplate="Offset %{x:.2f} m<br>Cota %{y:.2f} m<extra></extra>",
    ))

    if not hrow.empty and "cota_agua_m" in hrow and pd.notna(hrow.get("cota_agua_m")):
        wse = float(hrow.get("cota_agua_m"))
        wet = pts[z <= wse].copy()
        if len(wet) >= 2:
            fig.add_trace(go.Scatter(
                x=wet["offset_m"], y=[wse]*len(wet), mode="lines",
                name="Lámina de agua", line=dict(color="#1d4ed8", width=4, dash="dash")
            ))
            fig.add_trace(go.Scatter(
                x=list(wet["offset_m"]) + list(wet["offset_m"])[::-1],
                y=[wse]*len(wet) + list(wet["z_m"])[::-1],
                fill="toself", mode="none", name="Área mojada",
                fillcolor="rgba(37,99,235,0.25)",
            ))

    if not srow.empty:
        zsc = srow.get("cota_fondo_socavado_m", np.nan)
        scour_total = srow.get("socavacion_total_prelim_m", srow.get("socavacion_general_m", np.nan))
        if pd.notna(zsc) or pd.notna(scour_total):
            if pd.isna(zsc):
                zsc = float(z.min()) - float(scour_total)
            center = float(x.iloc[(np.abs(x)).argmin()]) if len(x) else 0.0
            width = max(float(x.max()-x.min())*0.22, 3.0)
            xs = np.linspace(center-width/2, center+width/2, 16)
            base = np.interp(xs, x, z)
            fig.add_trace(go.Scatter(
                x=list(xs)+list(xs)[::-1], y=list(base)+[float(zsc)]*len(xs),
                fill="toself", mode="none", name="Zona de socavación",
                fillcolor="rgba(220,38,38,0.38)",
            ))
            fig.add_trace(go.Scatter(
                x=xs, y=[float(zsc)]*len(xs), mode="lines",
                name="Fondo socavado", line=dict(color="#dc2626", width=4)
            ))
        depo = srow.get("depositacion_m", np.nan)
        if pd.notna(depo) and float(depo) > 0:
            right = pts[pts["offset_m"] >= 0].copy()
            if len(right) >= 2:
                ydep = right["z_m"].astype(float) + float(depo)
                fig.add_trace(go.Scatter(
                    x=list(right["offset_m"]) + list(right["offset_m"])[::-1],
                    y=list(ydep) + list(right["z_m"])[::-1],
                    fill="toself", mode="none", name="Área de depositación",
                    fillcolor="rgba(22,163,74,0.35)",
                ))

    # Estética ejecutiva tipo tablero HidroSed Maestra.
    if not hrow.empty and "cota_agua_m" in hrow and pd.notna(hrow.get("cota_agua_m")):
        try:
            wse = float(hrow.get("cota_agua_m"))
            fig.add_annotation(
                x=float(x.mean()), y=wse,
                text=f"Lámina de agua<br>{wse:.2f} m",
                showarrow=False,
                yshift=16,
                font=dict(color="#1d4ed8", size=12),
                bgcolor="rgba(255,255,255,0.70)",
            )
        except Exception:
            pass
    if not srow.empty and "socavacion_general_m" in srow and pd.notna(srow.get("socavacion_general_m")):
        try:
            sc = float(srow.get("socavacion_general_m"))
            fig.add_annotation(
                x=float(x.max()), y=float(z.min() - sc/2),
                text=f"{sc:.2f} m<br>Socavación general",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-55,
                font=dict(color="#dc2626", size=12),
                arrowcolor="#dc2626",
                bgcolor="rgba(255,255,255,0.80)",
            )
        except Exception:
            pass
    fig.update_layout(
        title=f"Sección transversal – {section_id}",
        xaxis_title="Estación (m)",
        yaxis_title="Cota (m)",
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=.5),
        margin=dict(l=45, r=20, t=55, b=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        font=dict(family="Inter, Arial, sans-serif", color="#1f2937"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5eaf3", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5eaf3", zeroline=False)
    return fig


def _hs_section_summary_table(section_id, T, hydraulic_df=None, sediment_df=None, qa_df=None, sensitivity_df=None) -> pd.DataFrame:
    rows = []
    h = _hs_row_by_section(hydraulic_df, section_id, T)
    s = _hs_row_by_section(sediment_df, section_id, T)
    q = _hs_row_by_section(qa_df, section_id, None)
    m = _hs_row_by_section(sensitivity_df, section_id, T)
    fields = [
        ("Q_m3s", "Caudal [m³/s]", h),
        ("cota_agua_m", "Cota agua [m]", h),
        ("tirante_max_m", "Tirante [m]", h),
        ("velocidad_m_s", "Velocidad [m/s]", h),
        ("Froude", "Froude [-]", h),
        ("energia_especifica_m", "Energía específica [m]", h),
        ("tirante_normal_manning_m", "yn [m]", h),
        ("calado_critico_m", "yc [m]", h),
        ("cota_normal_manning_m", "Cota yn [m]", h),
        ("cota_ribera_izq_m", "Cota ribera izq. [m]", h),
        ("cota_ribera_der_m", "Cota ribera der. [m]", h),
        ("margen_desborde", "Desborde", h),
        ("altura_desborde_max_m", "Altura desborde máx. [m]", h),
        ("radio_hidraulico_m", "Radio hidráulico [m]", h),
        ("Shields", "Shields [-]", s),
        ("Qb_MPM_m3_s", "Fondo MPM [m³/s]", s),
        ("Qs_EH_total_m3_s", "Total Engelund-Hansen [m³/s]", s),
        ("socavacion_general_m", "Socavación general [m]", s),
        ("socavacion_local_prelim_m", "Socavación local prelim. [m]", s),
        ("socavacion_total_prelim_m", "Socavación total prelim. [m]", s),
        ("depositacion_m", "Depositación [m]", s),
        ("delta_wse_max_m", "Sensibilidad Manning ΔWSE [m]", m),
        ("orientacion_eje_detectada", "Orientación eje detectada", h),
        ("control_tirante_irreal", "Control tirante irreal aplicado", h),
        ("wse_original_m", "Cota agua original antes QA [m]", h),
        ("criterio_control_tirante", "Criterio control tirante", h),
        ("warnings", "Advertencias QA", q),
    ]
    for key, label, row in fields:
        if row is not None and not row.empty and key in row and pd.notna(row.get(key)):
            val = row.get(key)
            if isinstance(val, (float, int, np.floating)):
                val = f"{float(val):.4g}"
            rows.append({"variable": label, "valor": val})
    return pd.DataFrame(rows)


_workflow_steps = [
    (1, "Proyecto", has("control_point")),
    (2, "DEM / Curvas", has("dem_path") or has("contours_kmz")),
    (3, "Eje del cauce", has("axis_line")),
    (4, "Generación de secciones", has("sections_df")),
    (5, "Revisión de secciones", has("sections_qaqc_df") or has("section_points_df")),
    (6, "Transferencia a HidroSed", has("section_points_df")),
    (7, "Hidrología", has("hydrology_done") or has("q_design")),
    (8, "Hidráulica", has("hydraulic_profile_df")),
    (9, "Sedimentos y socavación", has("sediment_df")),
    (10, "Modelo 3D", has("profile_3d_html")),
    (11, "Transporte de sedimentos", has("sediment_df")),
    (12, "Informe final", has("cartographic_png") or has("external_audit_report")),
]
st.sidebar.markdown(
    workflow_html(
        _workflow_steps,
        active=11 if has("sediment_df") else 5 if has("sections_df") else None,
        project_name=st.session_state.get("project_name", "Río_San_Antonio"),
        project_id=f"PRJ-{st.session_state.get('project_id','')}"
    ),
    unsafe_allow_html=True,
)
with st.sidebar.expander("Estado técnico detallado", expanded=False):
    for k, label in [
        ("control_point", "Punto control"),
        ("axis_line", "Eje cauce"),
        ("topo_support_df", "Curvas apoyo topo"),
        ("dem_path", "DEM"),
        ("basin_metrics", "Cuenca/morfometría"),
        ("contours_kmz", "Curvas"),
        ("sections_df", "Secciones"),
        ("hydrology_done", "Hidrología"),
        ("q_design", "Caudales"),
        ("hydraulic_profile_df", "Perfil tipo HEC-RAS"),
        ("sediment_df", "Socavación/sedimentos"),
        ("profile_3d_html", "Perfil 3D hidráulico"),
        ("cartographic_png", "Lámina cartográfica"),
    ]:
        badge(k, label)

st.markdown(
    dashboard_header_html(
        "HidroSed Maestra Integrada · v3.8.3",
        "Formato visual tipo tablero profesional: DEM multifuente, casos de aplicación, secciones compuestas y QA estricto de punto de control, cauce DEM y cuenca no truncada."
    ),
    unsafe_allow_html=True,
)
st.markdown("<span class='hm-chip'>HEC-RAS 1D enhanced</span><span class='hm-chip'>Hidrología DGA/MC</span><span class='hm-chip'>Rugosidad Cowan/Strickler</span><span class='hm-chip'>Secciones compuestas</span><span class='hm-chip'>Granulometría KMZ/Excel</span>", unsafe_allow_html=True)

st.info(
    "Secuencia oficial: 1 Entrada → 2 DEM → 3 Cuenca/Morfometría → 4 Curvas/Eje → "
    "5 Secciones → 6 Hidrología → 7 Caudales → 8 Hidráulica/Sedimentos → 9 Exportación → 10 Modo Supremo QA/Rugosidad. "
    "Modo recomendado: cuencas hasta 10.000 km² con DEM COP30 y controles QA."
)

tabs = st.tabs([
    "1 · Entrada",
    "2 · DEM multifuente",
    "3 · Cuenca y morfometría",
    "4 · Curvas y eje",
    "5 · Secciones",
    "6 · Hidrología",
    "7 · Caudales",
    "8 · Socavación y sedimentos",
    "9 · Cartografía y exportar",
    "10 · Supremo QA/Rugosidad/Trapezoidal",
    "11 · Auditoría general",
])

with tabs[0]:
    st.header("1 · Entrada geométrica")
    c1, c2 = st.columns(2)
    with c1:
        point_file = st.file_uploader("KMZ/KML con punto de control", type=["kmz", "kml"], key="point_file")
        if point_file and st.button("Leer punto de control"):
            try:
                kml = read_kml(point_file)
                cp = parse_first_point(kml)
                st.session_state["control_point"] = {"lat": cp.lat, "lon": cp.lon, "name": cp.name}
                st.success(f"Punto leído: {cp.name} · lat {cp.lat:.8f}, lon {cp.lon:.8f}")
            except Exception as exc:
                st.error(str(exc))
    with c2:
        axis_file = st.file_uploader("KMZ/KML eje de cauce opcional", type=["kmz", "kml"], key="axis_file")
        if axis_file and st.button("Leer eje de cauce"):
            try:
                kml = read_kml(axis_file)
                lines = parse_lines(kml)
                if not lines:
                    raise ValueError("No se encontró LineString válido para eje de cauce.")
                line = line_to_shapely_wgs84(lines[0])
                st.session_state["axis_line"] = list(line.coords)
                st.session_state["axis_source"] = "manual_kmz"
                st.success(f"Eje leído: {lines[0].name} · puntos {_axis_line_point_count(st.session_state.get('axis_line'))}")
            except Exception as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Caso de aplicación y relación cuenca–eje")
    _render_case_selector(compact=False)
    _render_topo_strong_warning_if_needed("Entrada")

    st.divider()
    st.subheader("Curvas de nivel de apoyo topográfico opcionales")
    st.caption("Este archivo es 100% opcional. Si no se carga, si falla la lectura o si no contiene cotas válidas, la app continúa usando solo el DEM.")
    topo_file = st.file_uploader(
        "KMZ/KML con curvas de nivel topográficas de apoyo",
        type=["kmz", "kml"],
        key="topo_support_file",
        help="Archivo opcional. Mejora cotas de secciones si las curvas contienen cota en nombre, ExtendedData o coordenada Z.",
    )

    if not topo_file and "topo_support_df" not in st.session_state:
        st.info("Sin curvas de apoyo topográfico: el proceso continuará normalmente con el DEM.")

    if topo_file and st.button("Leer curvas topográficas de apoyo"):
        try:
            topo_kml = read_kmz_kml_bytes(topo_file)
            topo_df = parse_topographic_contours(topo_kml)

            if topo_df is None or topo_df.empty:
                st.session_state.pop("topo_support_df", None)
                st.warning("El archivo fue leído, pero no se detectaron curvas útiles. Se continuará solo con DEM.")
            elif "z_m" not in topo_df.columns or topo_df["z_m"].notna().sum() == 0:
                st.session_state.pop("topo_support_df", None)
                st.warning("El archivo no contiene cotas reconocibles. Se continuará solo con DEM.")
            else:
                st.session_state["topo_support_df"] = topo_df
                st.success(f"Curvas de apoyo leídas: {topo_df['contour_id'].nunique()} curvas · {len(topo_df)} vértices · {topo_df['z_m'].notna().sum()} cotas válidas.")
        except Exception as exc:
            st.session_state.pop("topo_support_df", None)
            st.warning(f"No fue posible usar las curvas topográficas de apoyo. El proceso continuará solo con DEM. Detalle: {exc}")

    if has("topo_support_df"):
        topo_ok = st.session_state["topo_support_df"]
        st.caption("Muestra de curvas topográficas de apoyo cargadas")
        st.dataframe(topo_ok.head(100), use_container_width=True)
        if st.button("Quitar curvas de apoyo y continuar solo con DEM"):
            st.session_state.pop("topo_support_df", None)
            st.success("Curvas de apoyo removidas. La app continuará solo con DEM.")

    if has("control_point"):
        st.subheader("Punto de control activo")
        st.json(st.session_state["control_point"])
    if has("axis_line"):
        st.subheader("Eje de cauce activo")
        st.write(f"Puntos del eje: {_axis_line_point_count(st.session_state.get('axis_line'))}")

with tabs[1]:
    st.header("2 · DEM multifuente / OpenTopography / Copernicus / DEM manual")

    if not has("control_point"):
        st.warning("Primero ingresa el KMZ/KML con punto de control.")
    else:
        cp = st.session_state["control_point"]

        st.markdown(
            "<div class='hs-info'><b>Mejora v3.1.4:</b> este módulo usa la lógica de la app demcop30_streamlit: "
            "el Área bbox es la ventana rectangular del DEM, no la superficie real de la cuenca. "
            "Seleccione un preajuste según el tamaño esperado para evitar descargas excesivas.</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            source_registry = dem_source_registry()
            source_labels = [
                source_registry["opentopography"].label,
                source_registry["copernicus_public_cog"].label,
                source_registry["direct_geotiff_url"].label,
                source_registry["manual_geotiff"].label,
                source_registry["nasa_earthdata"].label,
                source_registry["usgs_earthexplorer"].label,
                source_registry["asf_vertex_alos"].label,
            ]
            source_label_to_key = {v.label: k for k, v in source_registry.items()}
            dem_source_label = st.selectbox(
                "Fuente DEM",
                source_labels,
                index=0,
                help="Si OpenTopography falla, use Copernicus público, URL directa o cargue un DEM manual."
            )
            dem_source_key = source_label_to_key[dem_source_label]
            dem_source_info = source_registry[dem_source_key]
            st.session_state["dem_source_selected"] = dem_source_key
            st.caption(f"Autenticación: {dem_source_info.auth_type}")
            if dem_source_info.requires_login and not dem_source_info.direct_in_app:
                st.info(
                    "Esta fuente usa portal con cuenta/sesión. HidroSed la opera en modo asistido: "
                    "descargue el GeoTIFF fuera de la app con el bbox mostrado y cárguelo abajo como DEM manual."
                )

            api_key = ""
            dem_type = "COP30"
            direct_dem_url = ""
            direct_dem_token = ""
            if dem_source_key == "opentopography":
                api_key = st.text_input("API Key OpenTopography", type="password", key="api_key_manual")
                dem_type = st.selectbox("Producto OpenTopography", ["COP30", "NASADEM", "SRTMGL1", "SRTMGL3"], index=0)
            elif dem_source_key == "copernicus_public_cog":
                dem_type = "COPERNICUS_GLO30_PUBLIC_COG"
                st.success("Copernicus DEM público: no requiere API Key en este modo COG público.")
            elif dem_source_key == "direct_geotiff_url":
                dem_type = "URL_DIRECTA_GEOTIFF"
                direct_dem_url = st.text_input("URL directa GeoTIFF/COG", key="direct_dem_url")
                direct_dem_token = st.text_input(
                    "Token Bearer opcional",
                    type="password",
                    key="direct_dem_token",
                    help="Use solo si la URL directa exige token. No sirve para portales con login interactivo."
                )
            else:
                dem_type = "DEM_MANUAL_ASISTIDO"

            dem_manual_file = st.file_uploader(
                "DEM GeoTIFF manual opcional",
                type=["tif", "tiff"],
                help="Use esta vía si ya descargó el DEM desde Earthdata, USGS, ASF, IDE Chile, QGIS u otra plataforma."
            )
            if dem_manual_file and st.button("Usar DEM manual GeoTIFF"):
                try:
                    dem_bytes = dem_manual_file.getvalue()
                    dem_path = save_bytes("dem_manual_geotiff.tif", dem_bytes)
                    st.session_state["dem_path"] = str(dem_path)
                    st.session_state["dem_bytes"] = dem_bytes
                    st.session_state["dem_bbox"] = None
                    st.session_state["dem_source"] = "DEM manual GeoTIFF"
                    st.session_state["dem_download_meta"] = {
                        "source": "DEM manual GeoTIFF",
                        "bytes": len(dem_bytes),
                        "note": "Archivo cargado por usuario; no se aplicó descarga externa desde HidroSed.",
                    }
                    st.success(f"DEM manual activo: {len(dem_bytes)/(1024*1024):.2f} MB")
                except Exception as exc:
                    st.error(f"No se pudo cargar DEM manual: {exc}")

            with st.expander("Ver matriz de fuentes DEM y autenticación"):
                src_df = pd.DataFrame(dem_source_table())[
                    ["label", "product", "resolution", "auth_type", "direct_in_app", "recommended_use"]
                ]
                src_df = src_df.rename(columns={
                    "label": "Fuente",
                    "product": "Producto",
                    "resolution": "Resolución",
                    "auth_type": "Autenticación",
                    "direct_in_app": "Descarga directa en app",
                    "recommended_use": "Uso recomendado",
                })
                st.dataframe(src_df, use_container_width=True, hide_index=True)

        with c2:
            bbox_profile = st.selectbox(
                "Tamaño esperado de la cuenca",
                [
                    "Quebrada pequeña ≤ 50 km²",
                    "Cuenca pequeña 50–500 km²",
                    "Cuenca mediana 500–2.000 km²",
                    "Cuenca grande > 2.000 km²",
                    "Manual"
                ],
                index=0,
                help="Este preajuste controla la ventana DEM. No limita el cálculo hidráulico posterior."
            )

            profile_defaults = {
                "Quebrada pequeña ≤ 50 km²": {"margin_km": 7.5, "margin_deg": 0.06, "bbox_max": 500.0, "expected": 20.0, "basin_max": 80.0, "snap": 250},
                "Cuenca pequeña 50–500 km²": {"margin_km": 15.0, "margin_deg": 0.12, "bbox_max": 2500.0, "expected": 150.0, "basin_max": 750.0, "snap": 500},
                "Cuenca mediana 500–2.000 km²": {"margin_km": 30.0, "margin_deg": 0.25, "bbox_max": 10000.0, "expected": 1000.0, "basin_max": 3000.0, "snap": 1000},
                "Cuenca grande > 2.000 km²": {"margin_km": 60.0, "margin_deg": 0.50, "bbox_max": 40000.0, "expected": 5000.0, "basin_max": 15000.0, "snap": 1500},
                "Manual": {"margin_km": 10.0, "margin_deg": 0.08, "bbox_max": 1000.0, "expected": 50.0, "basin_max": 200.0, "snap": 250},
            }
            prof = profile_defaults[bbox_profile]
            margin_unit = st.radio("Unidad margen", ["km", "grados"], horizontal=True)
            default_margin = prof["margin_km"] if margin_unit == "km" else prof["margin_deg"]
            margin = st.number_input(
                "Margen desde punto",
                min_value=0.001,
                value=float(default_margin),
                step=1.0 if margin_unit == "km" else 0.01,
                format="%.3f" if margin_unit == "grados" else "%.1f",
                help="El margen se aplica hacia norte, sur, este y oeste. Aumente solo si la cuenca toca el borde del DEM."
            )

            st.session_state["bbox_profile"] = bbox_profile
            st.session_state["expected_basin_default"] = float(prof["expected"])
            st.session_state["max_basin_default"] = float(prof["basin_max"])
            st.session_state["snap_default_m"] = int(prof["snap"])

        with c3:
            area_limit = st.number_input(
                "Límite técnico bbox [km²]",
                min_value=1.0,
                value=float(prof["bbox_max"]),
                step=100.0 if prof["bbox_max"] <= 2500 else 1000.0,
                help="Control de seguridad para evitar descargas demasiado grandes. El bbox no es el área de cuenca."
            )
            expected_for_warning = st.number_input(
                "Área real esperada referencial [km²]",
                min_value=0.0,
                value=float(prof["expected"]),
                step=10.0 if prof["expected"] >= 100 else 5.0,
                help="Solo se usa para advertir si el bbox es desproporcionado."
            )
            st.session_state["expected_basin_default"] = float(expected_for_warning)

        bbox = bbox_from_margin(cp["lat"], cp["lon"], margin, margin_unit)
        area = bbox_area_km2(bbox)
        st.session_state["bbox_area_km2"] = float(area)

        k1, k2, k3 = st.columns(3)
        k1.metric("Área bbox aprox.", f"{area:,.1f} km²")
        k2.metric("Margen", f"{margin:g} {margin_unit}")
        k3.metric("Preajuste", bbox_profile)
        st.caption("El Área bbox aprox. corresponde a la ventana rectangular de descarga del DEM. No corresponde al área real de la cuenca.")

        if expected_for_warning and expected_for_warning > 0:
            ratio_bbox = area / expected_for_warning
            if ratio_bbox > 100:
                st.error(
                    f"El bbox es {ratio_bbox:,.0f} veces mayor que el área referencial. "
                    "Reduzca margen o use un preajuste menor. Un bbox excesivo hace más lenta la app y puede inducir ajustes erróneos."
                )
            elif ratio_bbox > 25:
                st.warning(
                    f"El bbox es {ratio_bbox:,.0f} veces mayor que el área referencial. "
                    "Puede funcionar, pero probablemente es más grande de lo necesario."
                )

        rec = recommended_tiling(area)
        st.caption(f"Recomendación descarga DEM: {rec['mode']} · {rec['rows']} x {rec['cols']} teselas")

        if area > area_limit:
            st.error("El bbox supera el límite técnico definido. Reduce margen, cambia preajuste o aumenta el límite bajo tu responsabilidad.")
        elif area < max(10.0, expected_for_warning*1.2 if expected_for_warning else 10.0):
            st.warning("El bbox podría ser demasiado pequeño para contener toda la cuenca. Si la cuenca toca el borde del DEM, aumente el margen gradualmente.")
        else:
            st.success("Bounding box válido para construir la solicitud.")

        st.subheader("Bounding box calculado")
        bbox_cols = st.columns(5)
        bbox_cols[0].metric("south", f"{bbox['south']:.6f}")
        bbox_cols[1].metric("north", f"{bbox['north']:.6f}")
        bbox_cols[2].metric("west", f"{bbox['west']:.6f}")
        bbox_cols[3].metric("east", f"{bbox['east']:.6f}")
        bbox_cols[4].metric("Área aprox.", f"{area:,.0f} km²")

        st.subheader("Solicitud DEM")
        if dem_source_key == "opentopography":
            st.code(build_url(dem_type, bbox, "API_KEY_OCULTA"), language="text")
        elif dem_source_key == "copernicus_public_cog":
            cop_tiles = copernicus_tiles_for_bbox(bbox)
            st.info(f"Copernicus usará {len(cop_tiles)} tesela(s) pública(s) 1°x1° y las recortará al bbox.")
            st.code("\n".join(t["url"] for t in cop_tiles[:8]), language="text")
            if len(cop_tiles) > 8:
                st.caption(f"Se muestran 8 de {len(cop_tiles)} URLs.")
        elif dem_source_key == "direct_geotiff_url":
            st.code(direct_dem_url or "Ingrese una URL directa GeoTIFF/COG.", language="text")
        else:
            st.warning("Fuente asistida: use el bbox anterior para descargar fuera de HidroSed y luego cargue el GeoTIFF manual.")

        st.subheader("Modo de descarga DEM")
        d1, d2, d3 = st.columns(3)
        with d1:
            download_mode = st.selectbox(
                "Descarga DEM",
                ["Auto", "Normal", "Por partes"],
                index=0,
                disabled=dem_source_key not in ["opentopography"],
                help="OpenTopography permite modo normal o por partes. Copernicus público usa teselas 1°x1° automáticamente."
            )
        with d2:
            tile_rows_dem = st.selectbox(
                "Filas DEM",
                [1, 2, 3, 4, 5, 6, 8],
                index=[1,2,3,4,5,6,8].index(rec["rows"]) if rec["rows"] in [1,2,3,4,5,6,8] else 1,
                disabled=dem_source_key not in ["opentopography"],
            )
        with d3:
            tile_cols_dem = st.selectbox(
                "Columnas DEM",
                [1, 2, 3, 4, 5, 6, 8],
                index=[1,2,3,4,5,6,8].index(rec["cols"]) if rec["cols"] in [1,2,3,4,5,6,8] else 1,
                disabled=dem_source_key not in ["opentopography"],
            )

        can_download_direct = dem_source_key in ["opentopography", "copernicus_public_cog", "direct_geotiff_url"]
        if not can_download_direct:
            st.info("Esta fuente queda en modo asistido. HidroSed no solicita contraseñas de portales externos; cargue el DEM manual una vez descargado.")

        if area <= area_limit and can_download_direct:
            if st.button("Obtener DEM GeoTIFF", type="primary"):
                try:
                    progress = st.progress(0.0)
                    status = st.empty()

                    def cb(msg, frac):
                        status.info(msg)
                        progress.progress(min(max(float(frac), 0.0), 1.0))

                    if dem_source_key == "opentopography":
                        result = download_dem_normal_or_tiled(
                            dem_type,
                            bbox,
                            api_key,
                            mode=download_mode,
                            rows=int(tile_rows_dem),
                            cols=int(tile_cols_dem),
                            progress_callback=cb,
                        )
                        source_name = "OpenTopography"
                        file_stub = f"dem_{dem_type}_opentopography"
                    elif dem_source_key == "copernicus_public_cog":
                        result = download_copernicus_public_dem(bbox, progress_callback=cb, crop_to_bbox=True)
                        source_name = "Copernicus DEM GLO-30 público COG"
                        file_stub = "dem_copernicus_glo30_public_cog"
                    elif dem_source_key == "direct_geotiff_url":
                        cb("Descargando DEM desde URL directa...", 0.2)
                        dem_bytes_direct = download_url_bytes(direct_dem_url, token=direct_dem_token)
                        result = type("DirectDEMResult", (), {
                            "dem_bytes": dem_bytes_direct,
                            "metadata": {
                                "source": "URL directa GeoTIFF/COG",
                                "url": direct_dem_url,
                                "bytes": len(dem_bytes_direct),
                                "bbox_reference": bbox,
                            }
                        })()
                        cb("DEM URL directa listo.", 1.0)
                        source_name = "URL directa GeoTIFF/COG"
                        file_stub = "dem_url_directa"
                    else:
                        raise RuntimeError("Fuente DEM no soportada para descarga directa.")

                    dem_bytes = result.dem_bytes
                    dem_path = save_bytes(f"{file_stub}_unificado.tif", dem_bytes)
                    st.session_state["dem_path"] = str(dem_path)
                    st.session_state["dem_bytes"] = dem_bytes
                    st.session_state["dem_bbox"] = bbox
                    st.session_state["dem_source"] = source_name
                    st.session_state["dem_download_meta"] = result.metadata
                    progress.progress(1.0)
                    status.success("DEM listo para delimitación, curvas y secciones.")
                    st.success(f"DEM descargado/unificado: {len(dem_bytes)/(1024*1024):.2f} MB")
                except Exception as exc:
                    st.error(str(exc))

        if has("dem_download_meta"):
            st.subheader("Metadata descarga DEM")
            st.json(st.session_state["dem_download_meta"])

        if has("dem_bytes"):
            st.download_button("Descargar DEM", st.session_state["dem_bytes"], file_name="dem_hidrosed_unificado.tif", mime="image/tiff")


with tabs[2]:
    st.header("3 · Delimitar cuenca y calcular parámetros morfológicos")
    if not has("dem_path") or not has("control_point"):
        st.warning("Necesitas DEM descargado y punto de control.")
    else:
        cp = st.session_state["control_point"]
        st.markdown(
            "<div class='hs-info'><b>QA cuenca v3.8.3:</b> además del ajuste puntual al cauce DEM, la app puede usar "
            "un <b>cierre compuesto de salida</b> para abanicos aluviales o cauces divididos. Esto evita que se entregue solo media cuenca "
            "cuando varios hilos drenan al mismo punto de control.</div>",
            unsafe_allow_html=True,
        )
        with st.expander("Caso activo y criterios de validación de cuenca", expanded=False):
            case = get_application_case(_current_case_key())
            st.write(f"**{case.short_name} · {case.title}**")
            st.write(case.description)
            for item in case.qa_focus:
                st.write(f"- {item}")
            _render_topo_requirement_alert("Validación de cuenca")

        c1, c2, c3, c4 = st.columns(4)
        default_expected_area = float(st.session_state.get("expected_basin_default", 20.0))
        default_basin_limit = float(st.session_state.get("max_basin_default", max(default_expected_area*4, 80.0)))
        default_snap = int(st.session_state.get("snap_default_m", 250))
        snap_options = [50, 100, 250, 500, 1000, 1500, 2500, 5000]
        default_snap_index = snap_options.index(default_snap) if default_snap in snap_options else 2

        with c1:
            selection_mode = st.selectbox(
                "Modo ajuste punto",
                ["area_controlled", "closest", "max_acc"],
                index=0,
                format_func=lambda x: {
                    "area_controlled": "Controlado por área (recomendado)",
                    "closest": "Celda cercana",
                    "max_acc": "Máxima acumulación (antiguo)"
                }[x],
            )
            snap_radius = st.selectbox("Radio ajuste punto al cauce [m]", snap_options, index=default_snap_index)
        with c2:
            expected_area = st.number_input("Área esperada aprox. [km²]", min_value=0.0, value=default_expected_area, step=max(5.0, default_expected_area/20.0))
            basin_area_limit = st.number_input("Área máxima permitida [km²]", min_value=1.0, value=default_basin_limit, step=max(10.0, default_basin_limit/20.0))
        with c3:
            basin_max_cells = st.selectbox("Máx. celdas delimitación", [500_000, 1_000_000, 1_500_000, 2_500_000, 4_000_000, 6_000_000], index=3, format_func=lambda x: f"{x:,}".replace(",", "."))
        with c4:
            simplify_basin = st.selectbox("Simplificación polígono [m]", [0, 20, 30, 50, 80, 120, 200], index=3)

        c5, c6 = st.columns(2)
        with c5:
            outlet_closure_mode = st.selectbox(
                "Cierre de salida",
                ["auto_portal", "portal_union", "single"],
                index=0,
                format_func=lambda x: {
                    "auto_portal": "Automático: puntual + portal si falta cuenca",
                    "portal_union": "Portal compuesto forzado",
                    "single": "Solo outlet puntual"
                }[x],
                help="Use portal compuesto cuando el DEM genera hilos paralelos en abanicos aluviales, caminos o cauces poco incisos y la cuenca queda partida.",
            )
        with c6:
            portal_radius = st.selectbox(
                "Radio portal compuesto [m]",
                [250, 500, 750, 1000, 1500, 2000, 3000, 5000],
                index=3,
                help="Radio adicional para buscar hilos de salida que pertenezcan al mismo exutorio. Para el caso de media cuenca, pruebe 1000 a 3000 m.",
            )

        st.info(
            "QA v3.8.3 activo: la app corrige el punto al cauce DEM, evalúa candidatos, descarta cuencas truncadas por borde/NoData "
            "y ahora puede cerrar la salida como portal compuesto para no perder subcuencas laterales del mismo exutorio."
        )

        if st.button("Delimitar, corregir punto y validar cuenca", type="primary"):
            # Elimina una cuenca oficial anterior antes de una nueva corrida. Si la nueva
            # corrida falla QA, no quedará disponible para cálculos posteriores.
            for _k in [
                "basin_kmz", "basin_kml", "basin_preview", "basin_metrics", "basin_metrics_df",
                "basin_contours_kmz", "basin_contours_kml", "basin_contours_preview"
            ]:
                st.session_state.pop(_k, None)
            try:
                result = delineate_basin(
                    st.session_state["dem_path"],
                    outlet_lon=float(cp["lon"]),
                    outlet_lat=float(cp["lat"]),
                    snap_radius_m=float(snap_radius),
                    max_cells=int(basin_max_cells),
                    simplify_m=float(simplify_basin),
                    expected_area_km2=float(expected_area) if expected_area > 0 else None,
                    max_area_km2=float(basin_area_limit) if basin_area_limit > 0 else None,
                    selection_mode=str(selection_mode),
                    outlet_closure_mode=str(outlet_closure_mode),
                    portal_radius_m=float(portal_radius),
                )
                st.session_state["basin_candidate_kmz"] = result.kmz_bytes
                st.session_state["basin_candidate_kml"] = result.kml_bytes
                st.session_state["basin_candidate_preview"] = result.preview_png
                st.session_state["basin_candidate_metrics"] = result.metrics
                st.session_state["basin_candidate_metrics_df"] = metrics_dataframe(result.metrics)
                # Estados solicitados: la cuenca preliminar siempre queda disponible para revisión externa.
                st.session_state["basin_preliminar_kmz"] = result.kmz_bytes
                st.session_state["basin_preliminar_kml"] = result.kml_bytes
                st.session_state["basin_preliminar_metrics"] = result.metrics
                st.session_state["cuenca_preliminar"] = True
                save_bytes("cuenca_preliminar_revision.kmz", result.kmz_bytes)
                save_bytes("cuenca_preliminar_revision.kml", result.kml_bytes)

                if bool(result.metrics.get("cuenca_validada")):
                    _set_active_basin("cuenca_validada", result.kml_bytes, result.kmz_bytes, result.metrics)
                    st.session_state["basin_preview"] = result.preview_png
                    st.session_state["cuenca_validada"] = True
                    save_bytes("cuenca_delimitada_validada.kmz", result.kmz_bytes)
                    save_bytes("cuenca_delimitada_validada.kml", result.kml_bytes)
                    if result.preview_png:
                        save_bytes("preview_cuenca_validada.png", result.preview_png)
                    st.success("Cuenca VALIDADA: punto corregido al cauce DEM y controles mínimos aprobados. Esta cuenca queda como cuenca_activa.")
                else:
                    st.error("Cuenca NO VALIDADA: se muestra diagnóstico y se permite descargar como preliminar para revisión, pero no queda como cuenca oficial activa.")
            except Exception as exc:
                st.error(str(exc))

        m = st.session_state.get("basin_candidate_metrics") or st.session_state.get("basin_metrics")
        if isinstance(m, dict) and m:
            df_metrics = st.session_state.get("basin_candidate_metrics_df") if has("basin_candidate_metrics_df") else st.session_state.get("basin_metrics_df")
            preview_key = "basin_candidate_preview" if has("basin_candidate_preview") else "basin_preview"
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Área", f"{m['area_km2']:.3f} km²")
            c2.metric("Perímetro", f"{m['perimetro_km']:.3f} km")
            c3.metric("Kc", f"{m['coef_compacidad_kc']:.3f}")
            c4.metric("Ajuste punto", f"{float(m.get('distancia_ajuste_m', 0)):.1f} m")
            c5.metric("Estado QA", str(m.get("estado_validacion", "NO_VALIDADA")))

            if bool(m.get("cuenca_validada")):
                st.success("QA cuenca: VALIDADA. La cuenca quedó habilitada para curvas, eje, morfometría e hidrología.")
            else:
                st.error("QA cuenca: NO VALIDADA. No se usará en etapas posteriores hasta corregir DEM/punto/radio.")

            diag = m.get("diagnostico_tecnico") or []
            if isinstance(diag, list) and diag:
                st.subheader("Diagnóstico técnico de delineación")
                diag_df = pd.DataFrame(diag)
                st.dataframe(diag_df, use_container_width=True)
            if m.get("acciones_recomendadas"):
                st.warning("Acciones recomendadas:")
                for a in m.get("acciones_recomendadas", []):
                    st.write(f"- {a}")
            if m.get("advertencias"):
                with st.expander("Advertencias QA", expanded=False):
                    for a in m["advertencias"]:
                        st.write(f"- {a}")

            if df_metrics is not None:
                st.dataframe(df_metrics, use_container_width=True)
            if isinstance(m.get("candidatos_salida_top"), list) and m.get("candidatos_salida_top"):
                with st.expander("QA ajuste del punto: candidatos evaluados", expanded=False):
                    st.dataframe(pd.DataFrame(m["candidatos_salida_top"]), use_container_width=True)
            if isinstance(m.get("portal_outlets_adicionales"), list) and m.get("portal_outlets_adicionales"):
                with st.expander("QA cierre compuesto: outlets adicionales incorporados", expanded=True):
                    st.dataframe(pd.DataFrame(m["portal_outlets_adicionales"]), use_container_width=True)
            if has(preview_key):
                st.image(st.session_state[preview_key], caption="Candidato de cuenca y acumulación de flujo", use_container_width=True)

            st.subheader("Revisión y corrección de cuenca antes de curvas")
            st.caption("Revise la cuenca preliminar en Google Earth/GIS. Si está incompleta o desplazada, cargue una cuenca corregida. La cuenca_corregida tiene prioridad como cuenca_activa.")
            if has("basin_preliminar_kmz") and has("basin_preliminar_kml"):
                p1, p2 = st.columns(2)
                p1.download_button("Descargar cuenca PRELIMINAR KMZ", st.session_state["basin_preliminar_kmz"], file_name="cuenca_preliminar_revision.kmz", mime="application/vnd.google-earth.kmz")
                p2.download_button("Descargar cuenca PRELIMINAR KML", st.session_state["basin_preliminar_kml"], file_name="cuenca_preliminar_revision.kml", mime="application/vnd.google-earth.kml+xml")
            if bool(m.get("cuenca_validada")) and has("basin_kmz") and has("basin_kml"):
                d1, d2 = st.columns(2)
                d1.download_button("Descargar cuenca VALIDADA KMZ", st.session_state["basin_kmz"], file_name="cuenca_delimitada_validada.kmz", mime="application/vnd.google-earth.kmz")
                d2.download_button("Descargar cuenca VALIDADA KML", st.session_state["basin_kml"], file_name="cuenca_delimitada_validada.kml", mime="application/vnd.google-earth.kml+xml")
            else:
                st.info("La cuenca preliminar se puede descargar para revisión, pero solo una cuenca VALIDADA o CORREGIDA queda como cuenca_activa.")

        st.divider()
        st.subheader("Cargar cuenca corregida / validada por el usuario")
        with st.expander("Corrección manual de área de cuenca", expanded=False):
            st.caption("Formatos: KMZ, KML, GeoJSON o ZIP SHP. Esta cuenca reemplaza a la preliminar para área, curvas, hidrología y KMZ posteriores.")
            corrected_file = st.file_uploader("Cuenca corregida KMZ/KML/SHP/GeoJSON", type=["kmz", "kml", "geojson", "json", "zip"], key="corrected_basin_file")
            threshold_pct = st.number_input("Umbral alerta diferencia de área [%]", min_value=0.1, max_value=100.0, value=5.0, step=0.5)
            if corrected_file is not None and st.button("Validar y usar cuenca corregida como cuenca activa"):
                try:
                    pkg = package_corrected_basin(corrected_file.getvalue(), corrected_file.name, source="usuario")
                    st.session_state["basin_corregida_kml"] = pkg.kml_bytes
                    st.session_state["basin_corregida_kmz"] = pkg.kmz_bytes
                    st.session_state["basin_corregida_metrics"] = pkg.metrics
                    st.session_state["cuenca_corregida"] = True
                    _set_active_basin("cuenca_corregida", pkg.kml_bytes, pkg.kmz_bytes, pkg.metrics)
                    comp = compare_basin_areas(st.session_state.get("basin_preliminar_metrics") or st.session_state.get("basin_candidate_metrics"), pkg.metrics, threshold_pct=threshold_pct)
                    st.session_state["basin_area_comparison"] = comp
                    save_bytes("cuenca_corregida_activa.kmz", pkg.kmz_bytes)
                    save_bytes("cuenca_corregida_activa.kml", pkg.kml_bytes)
                    st.success("Cuenca corregida cargada, validada geométricamente y definida como cuenca_activa.")
                except Exception as exc:
                    st.error(f"No fue posible cargar la cuenca corregida: {exc}")
            if has("basin_area_comparison"):
                comp = st.session_state["basin_area_comparison"]
                st.dataframe(area_comparison_dataframe(comp), use_container_width=True, hide_index=True)
                if comp.get("diferencia_significativa"):
                    st.warning("Atención: la cuenca corregida difiere significativamente de la cuenca preliminar. Verifique punto de control, proyección y divisorias topográficas.")
            if has("basin_corregida_kmz"):
                d1, d2 = st.columns(2)
                d1.download_button("Descargar cuenca CORREGIDA activa KMZ", st.session_state["basin_corregida_kmz"], file_name="cuenca_corregida_activa.kmz", mime="application/vnd.google-earth.kmz")
                d2.download_button("Descargar cuenca CORREGIDA activa KML", st.session_state["basin_corregida_kml"], file_name="cuenca_corregida_activa.kml", mime="application/vnd.google-earth.kml+xml")

        with st.expander("Estado interno de cuenca", expanded=False):
            st.write({
                "cuenca_preliminar": has("basin_preliminar_kml"),
                "cuenca_validada": bool(st.session_state.get("cuenca_validada")),
                "cuenca_corregida": bool(st.session_state.get("cuenca_corregida")),
                "cuenca_activa": st.session_state.get("cuenca_activa_tipo", "sin_cuenca_activa"),
            })


with tabs[3]:
    st.header("4 · Curvas de nivel, modo por teselas y eje de cauce")
    with st.expander("Caso activo y respaldo topográfico requerido", expanded=False):
        case = get_application_case(_current_case_key())
        st.write(f"**{case.short_name} · {case.title}**")
        st.write(case.description)
        _render_topo_requirement_alert("Curvas/eje")
        _render_topo_strong_warning_if_needed("Curvas/eje")
        img = case_image_path(case.key, Path(__file__).parent / "assets")
        if img.exists():
            st.image(str(img), caption=f"Referencia {case.short_name}", use_container_width=True)
    if not has("dem_path"):
        st.warning("Primero descarga el DEM.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            interval = st.selectbox("Distancia entre curvas [m]", [1, 2, 5, 10, 20, 25, 50, 100, 200], index=0)
            st.caption("Mínimo: 1 m. Para cuencas cercanas a 10.000 km², 1 m puede generar KMZ muy pesado si el relieve es alto.")
        with c2:
            contour_mode = st.selectbox("Modo curvas", ["Automático", "Normal", "Por teselas y unificado"], index=0)
        with c3:
            max_levels = st.selectbox("Máx. niveles cota", [1000, 3000, 5000, 10000, 20000, 30000], index=4)

        bbox_area_ref = float(st.session_state.get("bbox_area_km2", 0) or 0)
        strategy = split_bbox_km2_strategy(bbox_area_ref)
        st.caption(f"Estrategia sugerida: {strategy['tile_rows']} x {strategy['tile_cols']} teselas · {strategy['nota']}")

        c4, c5, c6 = st.columns(3)
        with c4:
            max_cells = st.selectbox("Máx. celdas curvas normal", [1_000_000, 2_500_000, 4_000_000, 6_000_000, 10_000_000, 20_000_000], index=3, format_func=lambda x: f"{x:,}".replace(",", "."))
        with c5:
            tile_rows = st.selectbox("Filas teselas", [2, 3, 4, 5, 6, 8, 10], index=[2,3,4,5,6,8,10].index(strategy["tile_rows"]) if strategy["tile_rows"] in [2,3,4,5,6,8,10] else 3)
        with c6:
            tile_cols = st.selectbox("Columnas teselas", [2, 3, 4, 5, 6, 8, 10], index=[2,3,4,5,6,8,10].index(strategy["tile_cols"]) if strategy["tile_cols"] in [2,3,4,5,6,8,10] else 3)

        use_tiled = contour_mode == "Por teselas y unificado" or (contour_mode == "Automático" and bbox_area_ref >= 10000)

        if use_tiled:
            st.info("Modo por teselas activo: el DEM se procesa por partes y las curvas se unifican en un solo KMZ/KML.")
        else:
            st.info("Modo normal activo: el DEM se procesa como una sola unidad.")

        if st.button("Generar curvas KMZ/KML", type="primary"):
            try:
                if use_tiled:
                    out = generate_tiled_contours_from_dem(
                        st.session_state["dem_path"],
                        interval_m=float(interval),
                        tile_rows=int(tile_rows),
                        tile_cols=int(tile_cols),
                        max_levels=int(max_levels),
                        index_interval_m=max(float(interval) * 10.0, 10.0),
                    )
                else:
                    out = generate_contours(
                        st.session_state["dem_path"],
                        interval_m=float(interval),
                        max_cells=int(max_cells),
                        max_levels=int(max_levels),
                    )
                st.session_state["contours_kmz"] = out.kmz_bytes
                st.session_state["contours_kml"] = out.kml_bytes
                st.session_state["contours_preview"] = out.preview_png
                st.session_state["contours_meta"] = out.metadata
                save_bytes("curvas_nivel_unificadas.kmz", out.kmz_bytes)
                save_bytes("curvas_nivel_unificadas.kml", out.kml_bytes)
                if out.preview_png:
                    save_bytes("preview_curvas.png", out.preview_png)
                st.success("Curvas generadas correctamente.")
            except Exception as exc:
                st.error(str(exc))

        if has("contours_meta"):
            st.json(st.session_state["contours_meta"])
        if has("contours_preview"):
            st.image(st.session_state["contours_preview"], caption="Vista previa curvas/DEM", use_container_width=True)
        if has("contours_kmz"):
            with st.expander("Descargas avanzadas de curvas generales", expanded=False):
                c1, c2 = st.columns(2)
                c1.download_button("Descargar curvas KMZ unificadas", st.session_state["contours_kmz"], file_name="curvas_nivel_unificadas.kmz", mime="application/vnd.google-earth.kmz")
                c2.download_button("Descargar curvas KML unificadas", st.session_state["contours_kml"], file_name="curvas_nivel_unificadas.kml", mime="application/vnd.google-earth.kml+xml")

        if has("contours_kml"):
            st.divider()
            st.subheader("Curvas de nivel de apoyo del eje")
            st.caption("Genera curvas dentro de un corredor/buffer alrededor del eje. Recomendado u obligatorio para casos 2, 3 y 4.")
            axis_buffer = st.selectbox("Ancho de corredor/buffer eje [m]", [50, 100, 200, 300, 500, 750, 1000, 1500, 2000], index=4)
            if st.button("Generar curvas de apoyo del eje"):
                axis_coords, axis_src = _ensure_axis_available(silent=False)
                if not axis_coords:
                    st.error("No existe eje manual ni automático para generar corredor de curvas.")
                else:
                    try:
                        ac = build_axis_contours_kmz(st.session_state["contours_kml"], axis_coords, buffer_m=float(axis_buffer))
                        st.session_state["axis_contours_kmz"] = ac.kmz_bytes
                        st.session_state["axis_contours_kml"] = ac.kml_bytes
                        st.session_state["axis_contours_meta"] = ac.metadata
                        save_bytes("curvas_apoyo_eje.kmz", ac.kmz_bytes)
                        save_bytes("curvas_apoyo_eje.kml", ac.kml_bytes)
                        st.success(f"Curvas de apoyo del eje generadas desde {axis_src}: {ac.metadata.get('curvas_exportadas')} curvas.")
                    except Exception as exc:
                        st.error(str(exc))
            if has("axis_contours_meta"):
                with st.expander("Metadatos curvas de apoyo del eje", expanded=False):
                    st.json(st.session_state["axis_contours_meta"])
            if has("axis_contours_kmz"):
                with st.expander("Descarga avanzada curvas de apoyo del eje", expanded=False):
                    st.download_button("Descargar curvas_apoyo_eje.kmz", st.session_state["axis_contours_kmz"], file_name="curvas_apoyo_eje.kmz", mime="application/vnd.google-earth.kmz")

        if _active_basin_kml():
            st.divider()
            st.subheader("Cuenca + eje del cauce")
            st.caption("Si no existe eje manual, HidroSed intenta generar un eje automático DEM. Si no es posible, la exportación no falla y documenta el faltante.")
            if st.button("Preparar eje_cauce_cuenca.kmz", type="secondary"):
                axis_coords, axis_src = _ensure_axis_available(silent=False)
                try:
                    pkg = build_axis_kmz_package(
                        axis_coords=axis_coords,
                        auto_axis_coords=st.session_state.get("axis_auto_coords"),
                        control_point=st.session_state.get("control_point"),
                        outlet_point=_outlet_point_from_metrics(),
                        abc_points=st.session_state.get("abc_points", {}),
                        case_key=_current_case_key(),
                        case_title=get_application_case(_current_case_key()).title,
                        missing=[] if axis_coords else ["Eje de cauce manual o automático"],
                    )
                    st.session_state["export_axis_hidrosed_kmz"] = pkg.kmz_bytes
                    st.session_state["export_axis_hidrosed_kml"] = pkg.kml_bytes
                    st.session_state["export_axis_hidrosed_meta"] = pkg.metadata
                    st.success(f"eje_cauce_cuenca.kmz preparado. Fuente eje: {axis_src}.")
                except Exception as exc:
                    st.error(str(exc))

        if has("export_axis_hidrosed_meta"):
            with st.expander("Metadatos eje_cauce_cuenca.kmz", expanded=False):
                st.json(st.session_state["export_axis_hidrosed_meta"])
        if has("export_axis_hidrosed_kmz"):
            st.download_button("Descargar eje_cauce_cuenca.kmz", st.session_state["export_axis_hidrosed_kmz"], file_name="eje_cauce_cuenca.kmz", mime="application/vnd.google-earth.kmz")

        if _active_basin_kml() and has("contours_kml"):
            st.divider()
            st.subheader("Cuenca + eje + curvas de nivel")
            st.caption("Salida unificada usando siempre cuenca_activa. Si no hay eje, se exporta cuenca + curvas y se registra el faltante en README.")
            clip_basin_curves = st.checkbox("Recortar curvas al polígono de cuenca", value=True)
            if st.button("Generar KMZ cuenca + eje + curvas", type="secondary"):
                try:
                    bc = build_basin_contours_kmz(
                        _active_basin_kml(),
                        st.session_state["contours_kml"],
                        clip_to_basin=bool(clip_basin_curves),
                        axis_line_coords=_axis_line_coords(st.session_state.get("axis_line")) if has("axis_line") else None,
                    )
                    st.session_state["basin_contours_kmz"] = bc.kmz_bytes
                    st.session_state["basin_contours_kml"] = bc.kml_bytes
                    st.session_state["basin_contours_preview"] = bc.preview_png
                    st.session_state["basin_contours_meta"] = bc.metadata
                    save_bytes("cuenca_eje_curvas_nivel.kmz", bc.kmz_bytes)
                    save_bytes("cuenca_eje_curvas_nivel.kml", bc.kml_bytes)
                    if bc.preview_png:
                        save_bytes("preview_cuenca_eje_curvas.png", bc.preview_png)
                    st.success("KMZ cuenca + eje + curvas generado correctamente.")
                except Exception as exc:
                    st.error(str(exc))

        if has("basin_contours_meta"):
            st.json(st.session_state["basin_contours_meta"])
        if has("basin_contours_preview"):
            st.image(st.session_state["basin_contours_preview"], caption="Vista previa cuenca + curvas de nivel", use_container_width=True)
        if has("basin_contours_kmz"):
            c1, c2 = st.columns(2)
            c1.download_button("Descargar KMZ cuenca + eje + curvas", st.session_state["basin_contours_kmz"], file_name="cuenca_eje_curvas_nivel.kmz", mime="application/vnd.google-earth.kmz")
            c2.download_button("Descargar KML cuenca + eje + curvas", st.session_state["basin_contours_kml"], file_name="cuenca_eje_curvas_nivel.kml", mime="application/vnd.google-earth.kml+xml")

        st.divider()
        st.subheader("Eje de cauce")
        if has("axis_line"):
            st.success("Eje de cauce cargado desde KMZ/KML.")
        else:
            st.warning("No hay eje cargado. Se puede generar un eje preliminar para continuar.")
            c1, c2 = st.columns(2)
            with c1:
                axis_len = st.number_input("Longitud eje preliminar [km]", min_value=0.1, value=5.0, step=0.5)
            with c2:
                az = st.number_input("Azimut eje preliminar [°]", min_value=0.0, max_value=360.0, value=0.0, step=5.0)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Generar eje preliminar"):
                    from modules.axis_sections import generate_preliminary_axis
                    cp = st.session_state["control_point"]
                    line = generate_preliminary_axis(cp["lon"], cp["lat"], length_km=axis_len, azimuth_deg=az)
                    st.session_state["axis_line"] = _axis_line_coords(line)
                    st.session_state["axis_source"] = "automatico_preliminar"
                    st.success(f"Eje preliminar generado · puntos {_axis_line_point_count(st.session_state.get('axis_line'))}.")
            with b2:
                if st.button("Generar eje automático desde DEM/thalweg"):
                    coords, src = _ensure_axis_available(silent=False)
                    if coords:
                        st.session_state["axis_line"] = coords
                        st.session_state["axis_source"] = src
                        st.success(f"Eje automático activo · {len(coords)} puntos · fuente {src}.")

with tabs[4]:
    st.header("5 · Secciones transversales · Motor v13 UTM19S 3D")
    st.markdown("""
Esta etapa usa como motor principal la lógica de **app_secciones_kmz_v13_fix_km_final_utm19s_3d**: eje + curvas de nivel KMZ/KML, cálculo métrico en UTM, generación de secciones, muestreo por intersección con curvas, QA de secciones modelables y exportables.
""")
    with st.expander("Validación del caso antes de generar secciones", expanded=False):
        case = get_application_case(_current_case_key())
        st.write(f"**{case.short_name} · {case.title}**")
        st.write(case.hydraulic_use)
        _render_topo_requirement_alert("Secciones")
        _render_topo_strong_warning_if_needed("Secciones")
        st.markdown("**Salidas esperadas para este caso:**")
        for item in output_plan_for_case(case.key):
            st.write(f"- {item}")

    st.subheader("Secciones tipo HEC-RAS desde Excel")
    with st.expander("Cargar / validar secciones Excel HEC-RAS", expanded=False):
        st.caption("Use la hoja SECCIONES_HECRAS. Las secciones Excel pueden reemplazar o complementar las generadas desde DEM/curvas.")
        st.download_button(
            "Descargar plantilla Formato_Carga_Secciones_HECRAS_HidroSed.xlsx",
            hecras_template_bytes(),
            file_name="Formato_Carga_Secciones_HECRAS_HidroSed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        hec_file = st.file_uploader("Cargar Excel secciones tipo HEC-RAS", type=["xlsx"], key="hecras_sections_upload")
        if hec_file is not None and st.button("Validar secciones Excel HEC-RAS"):
            res = read_hecras_sections_excel(hec_file)
            st.session_state["hecras_sections_errors"] = res.errors_df
            st.session_state["hecras_sections_summary"] = res.summary_df
            if res.ok:
                st.session_state["hecras_sections_points"] = res.points_df
                st.session_state["hecras_sections_df"] = res.sections_df
                st.success(f"Excel válido: {len(res.sections_df)} secciones · {len(res.points_df)} puntos.")
            else:
                st.error("El Excel tiene errores. Revise la tabla de validación.")
        if has("hecras_sections_errors") and not st.session_state["hecras_sections_errors"].empty:
            st.dataframe(st.session_state["hecras_sections_errors"], use_container_width=True, hide_index=True)
        if has("hecras_sections_summary"):
            st.dataframe(st.session_state["hecras_sections_summary"], use_container_width=True, hide_index=True)
        if has("hecras_sections_points"):
            ids = sorted(st.session_state["hecras_sections_points"]["section_id"].astype(str).unique().tolist())
            sel = st.selectbox("Ver sección Excel", ids, key="hecras_section_view")
            try:
                fig = _hs_section_review_figure(sel, None, st.session_state["hecras_sections_points"])
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.warning(f"No se pudo graficar la sección: {exc}")

    st.subheader("Fuente de secciones para modelación")
    section_source = st.selectbox(
        "Fuente de secciones para modelación",
        [
            "secciones generadas automáticamente desde DEM",
            "secciones cargadas desde Excel",
            "combinación validada de ambas",
            "solo secciones aceptadas manualmente",
        ],
        index=0,
        key="section_source_for_modeling",
    )
    if section_source == "secciones cargadas desde Excel":
        if has("hecras_sections_points") and has("hecras_sections_df"):
            excel_sec = st.session_state["hecras_sections_df"].copy()
            excel_pts = st.session_state["hecras_sections_points"].copy()
            # Formato interno mínimo compatible con hidráulica HidroSed.
            excel_sec["section_id_original"] = excel_sec["XS_ID"].astype(str)
            id_map_excel = {sid: i + 1 for i, sid in enumerate(excel_sec["section_id_original"].tolist())}
            excel_sec["section_id"] = excel_sec["section_id_original"].map(id_map_excel).astype(int)
            excel_sec["pk_m"] = pd.to_numeric(excel_sec.get("Chainage_m"), errors="coerce")
            excel_sec["cota_fondo_m"] = pd.to_numeric(excel_sec.get("cota_min_m"), errors="coerce")
            excel_sec["cota_borde_izq_m"] = pd.to_numeric(excel_sec.get("cota_max_m"), errors="coerce")
            excel_sec["cota_borde_der_m"] = pd.to_numeric(excel_sec.get("cota_max_m"), errors="coerce")
            excel_pts["section_id_original"] = excel_pts["section_id"].astype(str)
            excel_pts["section_id"] = excel_pts["section_id_original"].map(id_map_excel).astype(int)
            excel_pts["pk_m"] = pd.to_numeric(excel_pts.get("Chainage_m"), errors="coerce")
            excel_pts["offset_m"] = pd.to_numeric(excel_pts.get("Station_m"), errors="coerce")
            excel_pts["z_m"] = pd.to_numeric(excel_pts.get("Elevation_m"), errors="coerce")
            st.session_state["sections_df"] = excel_sec
            st.session_state["section_points_df"] = excel_pts
            st.session_state["sections_mode"] = "excel_hecras_hidrosed"
            st.success("Secciones Excel HEC-RAS definidas como geometría activa para modelación.")
        else:
            st.warning("Seleccione esta opción solo después de cargar y validar el Excel HEC-RAS.")

    section_engine = st.radio(
        "Motor de secciones",
        ["Motor v13 KMZ/curvas/eje UTM19S 3D", "Motor DEM actual"],
        index=0,
        horizontal=True,
    )

    if section_engine.startswith("Motor v13"):
        v13_file = st.file_uploader(
            "KMZ/KML con eje del cauce y curvas de nivel",
            type=["kmz", "kml"],
            key="v13_sections_kmz",
            help="Puede ser el KMZ generado por la App A: cuenca + curvas + eje, o un KMZ con eje y curvas topográficas.",
        )
        st.subheader("Sistema métrico")
        cr1, cr2, cr3 = st.columns(3)
        with cr1:
            datum_key = st.selectbox("Datum", ["WGS84", "SIRGAS2000", "PSAD56", "SAD69"], index=0)
        with cr2:
            utm_zone = st.selectbox("Huso UTM", [17, 18, 19, 20, 21], index=2)
        with cr3:
            hemisphere = st.selectbox("Hemisferio", ["S", "N"], index=0)
        try:
            metric_epsg = v13_utm_epsg_from_datum(datum_key, int(utm_zone), hemisphere)
        except Exception as epsg_exc:
            st.warning(str(epsg_exc))
            metric_epsg = "EPSG:32719"
        st.info(f"CRS activo: {metric_epsg}")

        if v13_file:
            try:
                fwd, inv = v13_make_transformers(metric_epsg)
                kml_text = v13_read_kml_or_kmz(v13_file, v13_file.name)
                lines = v13_extract_lines_from_kml(kml_text)
                if not lines:
                    st.warning("No se encontraron líneas tipo LineString en el KMZ/KML.")
                else:
                    lines_df = v13_get_lines_dataframe(lines, fwd)
                    st.subheader("Elementos lineales detectados")
                    st.dataframe(lines_df, use_container_width=True, hide_index=True)

                    line_options = [f"{r.fid} | {r.name} | L={r.largo_m:,.1f} m" for _, r in lines_df.iterrows()]
                    axis_opt = st.selectbox("Seleccionar eje del cauce", line_options)
                    axis_fid = axis_opt.split("|")[0].strip()
                    axis_feature = next(f for f in lines if f.fid == axis_fid)
                    axis_metric = v13_project_geom(axis_feature.geometry_wgs84, fwd)

                    filter_regex = st.text_input("Filtro opcional para curvas por nombre", value="", help="Ejemplo: curva|contour|cota. Vacío: todas excepto eje.")
                    candidate_contours = [f for f in lines if f.fid != axis_fid]
                    if filter_regex.strip():
                        try:
                            rx = re.compile(filter_regex, re.IGNORECASE)
                            candidate_contours = [f for f in candidate_contours if rx.search(f.name)]
                        except re.error:
                            st.warning("Filtro regex inválido; se usan todas las líneas excepto eje.")

                    contour_rows = []
                    contours_metric = []
                    for f in candidate_contours:
                        z = f.z_candidate
                        contour_rows.append({"fid": f.fid, "name": f.name, "z_m": z, "largo_m": round(v13_project_geom(f.geometry_wgs84, fwd).length, 2)})
                    contour_df = pd.DataFrame(contour_rows)
                    st.subheader("Curvas candidatas")
                    contour_df = st.data_editor(contour_df, use_container_width=True, hide_index=True, num_rows="fixed")
                    valid_curves = contour_df[pd.to_numeric(contour_df["z_m"], errors="coerce").notna()].copy()
                    for _, rr in valid_curves.iterrows():
                        f = next(feat for feat in candidate_contours if feat.fid == rr["fid"])
                        contours_metric.append((f.fid, float(rr["z_m"]), v13_project_geom(f.geometry_wgs84, fwd)))

                    st.subheader("Parámetros de secciones")
                    p1, p2, p3, p4 = st.columns(4)
                    with p1:
                        km_start = st.number_input("Km inicial", value=0.0, step=0.1)
                        km_end = st.number_input("Km final", value=float(axis_metric.length/1000.0), step=0.1)
                    with p2:
                        standard_spacing = st.number_input("Espaciamiento base [m]", min_value=1.0, value=100.0, step=10.0)
                        width_m = st.number_input("Ancho sección [m]", min_value=5.0, value=80.0, step=10.0)
                    with p3:
                        dense_start = st.number_input("Densificar desde km", value=0.0, step=0.1)
                        dense_end = st.number_input("Densificar hasta km", value=0.0, step=0.1)
                    with p4:
                        dense_count = st.number_input("N° secciones densificadas", min_value=0, value=0, step=1)
                        min_points_each_bank = st.number_input("Mín. puntos por ribera", min_value=1, value=2, step=1)

                    if st.button("Generar secciones v13 + QA", type="primary"):
                        if not contours_metric:
                            st.error("No hay curvas con cota válida para generar perfiles.")
                        else:
                            dense_s = float(dense_start) if dense_count > 0 else None
                            dense_e = float(dense_end) if dense_count > 0 else None
                            chainages = v13_generate_chainages(axis_metric.length, float(km_start), float(km_end), float(standard_spacing), dense_s, dense_e, int(dense_count), include_ends=True)
                            sections = v13_build_sections(axis_metric, chainages, float(width_m))
                            sections_table = v13_sections_to_dataframe(sections, inv)
                            profile_points, profile_summary = v13_sample_profiles(sections, contours_metric, inv)
                            longitudinal_axis = v13_sample_longitudinal_axis_profile(axis_metric, contours_metric, inv)
                            longitudinal_est = v13_estimated_longitudinal_from_sections(profile_summary)
                            section_quality = v13_evaluate_section_quality(sections, profile_points, profile_summary)
                            modelable = v13_evaluate_modelable_sections(sections, profile_points, profile_summary, section_quality=section_quality, min_points_each_bank=int(min_points_each_bank), min_total_points=4, require_axis_elevation=True)
                            longitudinal_model = v13_build_longitudinal_modelacion(profile_summary, modelable, longitudinal_axis)
                            selected_sections = v13_filter_sections_for_modelacion(sections, modelable)
                            selected_points = v13_filter_selected_profile_points(profile_points, modelable)

                            # Conversión al formato interno HidroSed para hidráulica conectada.
                            if selected_sections:
                                sec_base = v13_sections_to_dataframe(selected_sections, inv)
                            else:
                                sec_base = sections_table.copy()
                            summary_base = profile_summary.copy()
                            sec_internal = sec_base.merge(summary_base[["section_id", "cota_min_m", "cota_max_m", "cota_eje_estimada_m"]], on="section_id", how="left") if not summary_base.empty else sec_base.copy()
                            sec_internal["section_id_original"] = sec_internal["section_id"].astype(str)
                            id_map = {sid: i+1 for i, sid in enumerate(sec_internal["section_id_original"].tolist())}
                            sec_internal["section_id"] = sec_internal["section_id_original"].map(id_map).astype(int)
                            sec_internal["pk_m"] = pd.to_numeric(sec_internal["chainage_m"], errors="coerce")
                            sec_internal["cota_fondo_m"] = pd.to_numeric(sec_internal.get("cota_min_m"), errors="coerce")
                            sec_internal["cota_borde_izq_m"] = pd.to_numeric(sec_internal.get("cota_max_m"), errors="coerce")
                            sec_internal["cota_borde_der_m"] = pd.to_numeric(sec_internal.get("cota_max_m"), errors="coerce")
                            sec_internal["lon_eje"] = sec_internal.get("eje_lon")
                            sec_internal["lat_eje"] = sec_internal.get("eje_lat")

                            pts_source = selected_points if not selected_points.empty else profile_points
                            pts_internal = pts_source.copy()
                            pts_internal["section_id_original"] = pts_internal["section_id"].astype(str)
                            pts_internal = pts_internal[pts_internal["section_id_original"].isin(id_map.keys())].copy()
                            pts_internal["section_id"] = pts_internal["section_id_original"].map(id_map).astype(int)
                            pts_internal["pk_m"] = pd.to_numeric(pts_internal["chainage_m"], errors="coerce")
                            pts_internal["z_m"] = pd.to_numeric(pts_internal["elevacion_m"], errors="coerce")
                            pts_internal["offset_m"] = pd.to_numeric(pts_internal["offset_m"], errors="coerce")
                            # QA eje-thalweg: verifica si el offset 0 coincide con la menor cota.
                            sec_internal, pts_internal, axis_thalweg_qa, _axis_thalweg_auto = verify_and_snap_axis_to_section_minima(
                                sec_internal,
                                pts_internal,
                                axis_source=st.session_state.get("axis_source", "manual_v13_kmz"),
                                tolerance_m=0.50,
                                update_axis_if_auto=True,
                            )
                            st.session_state["axis_thalweg_qa_df"] = axis_thalweg_qa
                            st.session_state["axis_thalweg_qa_summary"] = summarize_axis_thalweg_qa(axis_thalweg_qa)
                            if _axis_thalweg_auto:
                                st.session_state["axis_line"] = _axis_thalweg_auto
                                st.session_state["axis_source"] = "automatico_recentrado_thalweg"
                            # Asegura al menos 3 puntos por sección para hidráulica; si hay menos, queda QA visible.

                            st.session_state["sections_df"] = sec_internal
                            st.session_state["section_points_df"] = pts_internal
                            st.session_state["sections_mode"] = "v13_kmz_utm19s_3d"
                            st.session_state["sections_v13_raw_df"] = sections_table
                            st.session_state["sections_v13_profile_summary"] = profile_summary
                            st.session_state["sections_v13_quality_df"] = section_quality
                            st.session_state["sections_v13_modelable_df"] = modelable
                            st.session_state["sections_v13_longitudinal_modelacion"] = longitudinal_model
                            st.session_state["axis_metric_length_m"] = float(axis_metric.length)

                            try:
                                kmz_model = v13_make_kmz_modelacion(selected_sections if selected_sections else sections, selected_points if not selected_points.empty else profile_points, longitudinal_model, inv)
                                st.session_state["sections_v13_modelacion_kmz"] = kmz_model
                            except Exception:
                                pass
                            try:
                                zip_bytes = v13_make_zip_download(sections, profile_points, profile_summary, longitudinal_axis, longitudinal_est, axis_metric, contours_metric, inv, metric_epsg=metric_epsg, section_quality=section_quality, modelable_sections=modelable, selected_profile_points=selected_points, longitudinal_modelacion=longitudinal_model)
                                st.session_state["sections_v13_zip"] = zip_bytes
                            except Exception:
                                pass
                            st.success(f"Motor v13: secciones generadas {len(sec_internal)} · puntos útiles {len(pts_internal)} · modelables {int(modelable.get('seleccionada_modelacion', pd.Series(dtype=bool)).sum()) if not modelable.empty else 0}")

                    if has("sections_df") and st.session_state.get("sections_mode") == "v13_kmz_utm19s_3d":
                        st.subheader("Ventana de revisión de secciones seleccionadas")

                        sec_view = st.session_state["sections_df"].copy()
                        model_df = st.session_state.get("sections_v13_modelable_df", pd.DataFrame())
                        if model_df is not None and not model_df.empty and "section_id" in model_df.columns:
                            tmp = model_df.copy()
                            tmp["section_id_original"] = tmp["section_id"].astype(str)
                            if "section_id_original" in sec_view.columns:
                                sec_view = sec_view.merge(
                                    tmp[[c for c in [
                                        "section_id_original", "seleccion_modelacion", "estado_modelacion",
                                        "observacion_modelacion", "n_puntos_izquierda", "n_puntos_derecha", "n_puntos_total"
                                    ] if c in tmp.columns]],
                                    on="section_id_original",
                                    how="left",
                                )

                        def _estado_revision(row):
                            sel = bool(row.get("seleccion_modelacion", True)) if not pd.isna(row.get("seleccion_modelacion", True)) else True
                            origen = str(row.get("origen", "")).lower()
                            estado = str(row.get("estado_modelacion", "")).lower()
                            if not sel or "carga" in estado or "descart" in estado or "elimin" in estado:
                                return "Eliminada / revisar"
                            if "rell" in origen or "interpol" in origen or "fallback" in origen or "sint" in origen or "rell" in estado:
                                return "Rellenada"
                            return "Aceptada"

                        sec_view["estado_revision"] = sec_view.apply(_estado_revision, axis=1)
                        st.session_state["sections_review_df"] = sec_view

                        rv1, rv2, rv3, rv4 = st.columns(4)
                        rv1.metric("Aceptadas", int((sec_view["estado_revision"] == "Aceptada").sum()))
                        rv2.metric("Rellenadas", int((sec_view["estado_revision"] == "Rellenada").sum()))
                        rv3.metric("Eliminadas/revisar", int((sec_view["estado_revision"] == "Eliminada / revisar").sum()))
                        rv4.metric("Total", len(sec_view))

                        show_states = st.multiselect(
                            "Mostrar estados en la ventana",
                            ["Aceptada", "Rellenada", "Eliminada / revisar"],
                            default=["Aceptada", "Rellenada", "Eliminada / revisar"],
                            key="section_review_state_filter",
                        )
                        sec_filtered = sec_view[sec_view["estado_revision"].isin(show_states)].copy()
                        st.dataframe(sec_filtered, use_container_width=True)

                        if has("axis_thalweg_qa_df"):
                            st.subheader("QA eje de cauce vs cota mínima de sección")
                            axis_sum = st.session_state.get("axis_thalweg_qa_summary", {})
                            qa1, qa2, qa3, qa4 = st.columns(4)
                            qa1.metric("Secciones verificadas", axis_sum.get("n_secciones", 0))
                            qa2.metric("Recentradas al thalweg", axis_sum.get("n_corregidas", 0))
                            qa3.metric("Revisar", axis_sum.get("n_revisar", 0))
                            try:
                                qa4.metric("Desfase máx.", f"{float(axis_sum.get('desfase_max_m', float('nan'))):.2f} m")
                            except Exception:
                                qa4.metric("Desfase máx.", "NA")
                            st.caption("Criterio: el eje hidráulico local debe quedar en offset 0 coincidiendo con el punto de menor cota de cada sección. Si el eje fue automático, se recenteriza; si fue manual, se informa para revisión.")
                            st.dataframe(st.session_state["axis_thalweg_qa_df"], use_container_width=True, hide_index=True)

                        st.subheader("QA geométrico adicional · secciones aplanadas / cambios de dirección")
                        try:
                            flat_df = compute_section_relief_stats(sec_view, st.session_state.get("section_points_df"))
                            st.session_state["section_flat_stats_df"] = flat_df
                            if not flat_df.empty:
                                flat_bad = flat_df[flat_df["sospecha_aplanamiento"].fillna(False)].copy()
                                f1, f2, f3 = st.columns(3)
                                f1.metric("Sospechosas por aplanamiento", int(len(flat_bad)))
                                f2.metric("Relieve mediano", f"{float(flat_df['relieve_m'].median()):.2f} m" if flat_df['relieve_m'].notna().any() else "NA")
                                f3.metric("Puntos medianos", f"{int(flat_df['n_puntos'].median())}" if flat_df['n_puntos'].notna().any() else "NA")
                                if not flat_bad.empty:
                                    st.warning("Se detectaron secciones sospechosas por relieve anómalo, pocos puntos o posible cambio de dirección.")
                                    st.dataframe(flat_bad, use_container_width=True, hide_index=True)
                                else:
                                    st.success("No se detectaron secciones aplanadas relevantes con el criterio automático actual.")
                        except Exception as exc:
                            st.info(f"No fue posible calcular el QA geométrico adicional: {exc}")

                        st.subheader("Corrección semiautomática de tramo · generar secciones intermedias")
                        st.caption("Uso recomendado: después de revisar el perfil longitudinal 3D, seleccione el tramo con secciones aplanadas y genere una transición gradual entre secciones ancla aguas arriba y aguas abajo.")
                        if not sec_view.empty and has("section_points_df"):
                            pk_min_sec = float(pd.to_numeric(sec_view["pk_m"], errors="coerce").min())
                            pk_max_sec = float(pd.to_numeric(sec_view["pk_m"], errors="coerce").max())
                            gi1, gi2, gi3, gi4 = st.columns(4)
                            with gi1:
                                tramo_ini_km = st.number_input("Tramo a mejorar desde PK [km]", min_value=pk_min_sec/1000.0, max_value=pk_max_sec/1000.0, value=float(pk_min_sec/1000.0), step=0.05, key="interp_ini_km")
                            with gi2:
                                tramo_fin_km = st.number_input("Hasta PK [km]", min_value=pk_min_sec/1000.0, max_value=pk_max_sec/1000.0, value=float(min(pk_max_sec, pk_min_sec + 500.0)/1000.0), step=0.05, key="interp_fin_km")
                            with gi3:
                                n_interp = st.number_input("N° secciones intermedias", min_value=1, value=max(1, int(((min(pk_max_sec, pk_min_sec + 500.0) - pk_min_sec) / max(1.0, sec_view["pk_m"].diff().median() if sec_view["pk_m"].diff().notna().any() else 100.0)))), step=1, key="interp_n_sections")
                            with gi4:
                                st.caption("Las secciones originales dentro del tramo seleccionado serán reemplazadas por una transición interpolada y quedarán marcadas como 'Rellenada'.")
                                if st.button("Generar secciones intermedias", key="btn_generate_intermediate_sections"):
                                    try:
                                        new_sec, new_pts, interp_summary = generate_intermediate_sections(
                                            st.session_state["sections_df"],
                                            st.session_state["section_points_df"],
                                            pk_start_m=float(tramo_ini_km) * 1000.0,
                                            pk_end_m=float(tramo_fin_km) * 1000.0,
                                            n_sections=int(n_interp),
                                        )
                                        st.session_state["sections_df"] = new_sec
                                        st.session_state["section_points_df"] = new_pts
                                        st.session_state["sections_review_df"] = new_sec.copy()
                                        st.session_state["sections_interpolation_summary_df"] = interp_summary
                                        # Limpia resultados hidráulicos porque cambió la geometría.
                                        for _k in [
                                            "hydraulic_profile_base_df", "hydraulic_profile_df", "hydraulic_df",
                                            "sediment_df", "sediment_zone_summary_df", "qa_hidraulica_df",
                                            "sensibilidad_manning_df", "incertidumbre_mc_df", "confianza_v6_df",
                                            "profile_3d_fig", "profile_3d_html", "hydraulic_longitudinal_fig",
                                            "overflow_sections_df"
                                        ]:
                                            st.session_state.pop(_k, None)
                                        st.success("Tramo corregido: se generaron secciones intermedias y se limpió la hidráulica previa para recalcular con la nueva geometría.")
                                    except Exception as exc:
                                        st.error(f"No se pudo generar el tramo interpolado: {exc}")
                            if has("sections_interpolation_summary_df"):
                                st.dataframe(st.session_state["sections_interpolation_summary_df"], use_container_width=True, hide_index=True)

                        st.subheader("Editor de sección compuesta · insertar canal rectangular/trapecial")
                        st.caption(
                            "Permite fusionar una geometría artificial dentro de la sección natural: conserva riberas, reemplaza el tramo central, "
                            "marca trazabilidad y limpia resultados hidráulicos previos para recalcular."
                        )
                        if not sec_view.empty and has("section_points_df"):
                            try:
                                sec_design_view = sec_view.copy()
                                sec_design_view["pk_m"] = pd.to_numeric(sec_design_view["pk_m"], errors="coerce")
                                sec_design_view = sec_design_view.dropna(subset=["pk_m"]).sort_values("pk_m")
                                design_ids = sec_design_view["section_id"].astype(str).tolist()
                                if design_ids:
                                    ed0, ed1, ed2, ed3 = st.columns([1.1, 1.1, 1.1, 1.1])
                                    with ed0:
                                        design_scope = st.radio(
                                            "Aplicación",
                                            ["Sección puntual", "Tramo de PK"],
                                            horizontal=True,
                                            key="design_fusion_scope",
                                        )
                                    with ed1:
                                        design_shape = st.selectbox("Tipo", ["Trapecial", "Rectangular"], key="design_fusion_shape")
                                    with ed2:
                                        bottom_width_design = st.number_input(
                                            "Ancho basal/fondo [m]",
                                            min_value=0.10,
                                            value=3.00,
                                            step=0.25,
                                            key="design_fusion_bottom_width",
                                        )
                                    with ed3:
                                        depth_design = st.number_input(
                                            "Profundidad útil [m]",
                                            min_value=0.10,
                                            value=1.50,
                                            step=0.10,
                                            key="design_fusion_depth",
                                        )

                                    ed4, ed5, ed6, ed7 = st.columns(4)
                                    with ed4:
                                        talud_izq = st.number_input(
                                            "Talud izquierdo H:V",
                                            min_value=0.0,
                                            value=1.50,
                                            step=0.25,
                                            disabled=(design_shape == "Rectangular"),
                                            key="design_fusion_talud_izq",
                                        )
                                    with ed5:
                                        talud_der = st.number_input(
                                            "Talud derecho H:V",
                                            min_value=0.0,
                                            value=1.50,
                                            step=0.25,
                                            disabled=(design_shape == "Rectangular"),
                                            key="design_fusion_talud_der",
                                        )
                                    with ed6:
                                        center_offset_design = st.number_input(
                                            "Desplazamiento eje [m]",
                                            value=0.00,
                                            step=0.25,
                                            key="design_fusion_center_offset",
                                            help="0 ubica la sección artificial centrada en el thalweg/eje hidráulico local.",
                                        )
                                    with ed7:
                                        transition_width_design = st.number_input(
                                            "Transición lateral [m]",
                                            min_value=0.00,
                                            value=2.00,
                                            step=0.25,
                                            key="design_fusion_transition_width",
                                            help="Ancho para suavizar la unión entre ribera natural y geometría artificial.",
                                        )

                                    if design_scope == "Sección puntual":
                                        eds1, eds2, eds3 = st.columns([1.1, 1.5, 1.2])
                                        with eds1:
                                            sid_design = st.selectbox("Sección a intervenir", design_ids, key="design_fusion_sid")
                                        sec_row_design = sec_design_view[sec_design_view["section_id"].astype(str) == str(sid_design)].iloc[0]
                                        pts_design_base = _hs_section_points(st.session_state["section_points_df"], sid_design)
                                        local_min_design = float(pd.to_numeric(pts_design_base["z_m"], errors="coerce").min()) if not pts_design_base.empty else float(sec_row_design.get("cota_fondo_m", 0.0))
                                        with eds2:
                                            cota_mode_label = st.selectbox(
                                                "Cota de fondo artificial",
                                                ["Usar cota mínima natural", "Rebajar desde mínima natural", "Ingresar cota absoluta"],
                                                key="design_fusion_bottom_mode_single",
                                            )
                                        with eds3:
                                            if cota_mode_label == "Rebajar desde mínima natural":
                                                bottom_value_design = st.number_input("Rebaje [m]", min_value=0.0, value=0.50, step=0.10, key="design_fusion_bottom_drop_single")
                                                bottom_mode_internal = "rebaje_relativo"
                                            elif cota_mode_label == "Ingresar cota absoluta":
                                                bottom_value_design = st.number_input("Cota fondo [m]", value=float(local_min_design), step=0.10, key="design_fusion_bottom_abs_single")
                                                bottom_mode_internal = "cota_absoluta"
                                            else:
                                                bottom_value_design = 0.0
                                                bottom_mode_internal = "minima_natural"
                                                st.metric("Cota mínima local", f"{local_min_design:.2f} m")

                                        try:
                                            bottom_elev_design = resolve_bottom_elevation(pts_design_base, bottom_mode_internal, value=float(bottom_value_design))
                                            spec_preview = DesignChannelSpec(
                                                shape=str(design_shape),
                                                bottom_width_m=float(bottom_width_design),
                                                depth_m=float(depth_design),
                                                side_slope_left_hv=float(talud_izq),
                                                side_slope_right_hv=float(talud_der),
                                                bottom_elevation_m=float(bottom_elev_design),
                                                center_offset_m=float(center_offset_design),
                                                transition_width_m=float(transition_width_design),
                                                n_bottom_points=5,
                                            )
                                            fused_preview, _art_preview = fuse_design_channel_into_section_points(
                                                pts_design_base,
                                                spec_preview,
                                                section_id=sid_design,
                                                pk_m=float(sec_row_design.get("pk_m", 0.0)),
                                            )
                                            import plotly.graph_objects as go
                                            fig_fusion = go.Figure()
                                            fig_fusion.add_trace(go.Scatter(
                                                x=pts_design_base["offset_m"], y=pts_design_base["z_m"],
                                                mode="lines+markers", name="Antes · natural"
                                            ))
                                            fig_fusion.add_trace(go.Scatter(
                                                x=fused_preview["offset_m"], y=fused_preview["z_m"],
                                                mode="lines+markers", name="Después · compuesta"
                                            ))
                                            fig_fusion.update_layout(
                                                title=f"Vista previa fusión sección {sid_design} · PK {float(sec_row_design.get('pk_m', 0.0))/1000:.3f} km",
                                                xaxis_title="Offset transversal [m]",
                                                yaxis_title="Cota [m]",
                                                height=430,
                                            )
                                            st.plotly_chart(fig_fusion, use_container_width=True)
                                            fp1, fp2, fp3, fp4 = st.columns(4)
                                            fp1.metric("Cota fondo diseño", f"{bottom_elev_design:.2f} m")
                                            fp2.metric("Puntos antes", int(len(pts_design_base)))
                                            fp3.metric("Puntos después", int(len(fused_preview)))
                                            fp4.metric("Huella artificial", f"{float(_art_preview['footprint_right_m'].iloc[0] - _art_preview['footprint_left_m'].iloc[0]):.2f} m")
                                            if st.button("Aplicar fusión a sección seleccionada", type="primary", key="btn_apply_design_fusion_single"):
                                                if "sections_df_original_pre_design" not in st.session_state:
                                                    st.session_state["sections_df_original_pre_design"] = st.session_state["sections_df"].copy()
                                                if "section_points_df_original_pre_design" not in st.session_state:
                                                    st.session_state["section_points_df_original_pre_design"] = st.session_state["section_points_df"].copy()
                                                new_sec, new_pts, fusion_summary, original_pts_fusion = apply_design_channel_to_section(
                                                    st.session_state["sections_df"],
                                                    st.session_state["section_points_df"],
                                                    sid_design,
                                                    spec_preview,
                                                )
                                                st.session_state["sections_df"] = new_sec
                                                st.session_state["section_points_df"] = new_pts
                                                st.session_state["sections_review_df"] = new_sec.copy()
                                                st.session_state["section_design_fusion_summary_df"] = fusion_summary
                                                st.session_state["section_design_fusion_original_points_df"] = original_pts_fusion
                                                st.session_state["sections_mode"] = "v13_kmz_utm19s_3d"
                                                for _k in [
                                                    "hydraulic_profile_base_df", "hydraulic_profile_df", "hydraulic_df",
                                                    "sediment_df", "sediment_zone_summary_df", "qa_hidraulica_df",
                                                    "sensibilidad_manning_df", "incertidumbre_mc_df", "confianza_v6_df",
                                                    "profile_3d_fig", "profile_3d_html", "hydraulic_longitudinal_fig",
                                                    "overflow_sections_df", "sections_preview_3d_fig", "sections_preview_3d_html",
                                                ]:
                                                    st.session_state.pop(_k, None)
                                                st.success("Sección compuesta aplicada. Recalcule hidráulica/sedimentos con la nueva geometría.")
                                        except Exception as exc:
                                            st.warning(f"No se pudo previsualizar/aplicar la fusión: {exc}")
                                    else:
                                        pk_min_design = float(sec_design_view["pk_m"].min())
                                        pk_max_design = float(sec_design_view["pk_m"].max())
                                        edt1, edt2, edt3 = st.columns(3)
                                        with edt1:
                                            design_pk_ini = st.number_input(
                                                "Desde PK [km]",
                                                min_value=pk_min_design/1000.0,
                                                max_value=pk_max_design/1000.0,
                                                value=pk_min_design/1000.0,
                                                step=0.05,
                                                key="design_fusion_pk_ini",
                                            )
                                        with edt2:
                                            design_pk_fin = st.number_input(
                                                "Hasta PK [km]",
                                                min_value=pk_min_design/1000.0,
                                                max_value=pk_max_design/1000.0,
                                                value=min(pk_max_design, pk_min_design + 500.0)/1000.0,
                                                step=0.05,
                                                key="design_fusion_pk_fin",
                                            )
                                        with edt3:
                                            cota_mode_reach_label = st.selectbox(
                                                "Cota de fondo en tramo",
                                                ["Mínima natural por sección", "Rebaje relativo por sección", "Cota absoluta única"],
                                                key="design_fusion_bottom_mode_reach",
                                            )
                                        edr1, edr2 = st.columns([1, 2])
                                        with edr1:
                                            if cota_mode_reach_label == "Rebaje relativo por sección":
                                                bottom_reach_value = st.number_input("Rebaje local [m]", min_value=0.0, value=0.50, step=0.10, key="design_fusion_bottom_drop_reach")
                                                bottom_mode_reach = "rebaje_relativo"
                                                bottom_abs_reach = None
                                            elif cota_mode_reach_label == "Cota absoluta única":
                                                bottom_abs_reach = st.number_input("Cota absoluta [m]", value=float(pd.to_numeric(st.session_state["section_points_df"]["z_m"], errors="coerce").min()), step=0.10, key="design_fusion_bottom_abs_reach")
                                                bottom_reach_value = None
                                                bottom_mode_reach = "cota_absoluta"
                                            else:
                                                bottom_reach_value = None
                                                bottom_abs_reach = None
                                                bottom_mode_reach = "minima_natural"
                                                st.caption("Usa el mínimo natural de cada sección dentro del tramo.")
                                        with edr2:
                                            n_targets_design = int(((sec_design_view["pk_m"] >= float(design_pk_ini)*1000.0) & (sec_design_view["pk_m"] <= float(design_pk_fin)*1000.0)).sum())
                                            st.info(f"Secciones a fusionar en tramo: {n_targets_design}")

                                        spec_reach = DesignChannelSpec(
                                            shape=str(design_shape),
                                            bottom_width_m=float(bottom_width_design),
                                            depth_m=float(depth_design),
                                            side_slope_left_hv=float(talud_izq),
                                            side_slope_right_hv=float(talud_der),
                                            bottom_elevation_m=(float(bottom_abs_reach) if bottom_abs_reach is not None else None),
                                            center_offset_m=float(center_offset_design),
                                            transition_width_m=float(transition_width_design),
                                            n_bottom_points=5,
                                        )
                                        if st.button("Aplicar fusión al tramo seleccionado", type="primary", key="btn_apply_design_fusion_reach"):
                                            try:
                                                if n_targets_design <= 0:
                                                    raise ValueError("No hay secciones dentro del tramo seleccionado.")
                                                if "sections_df_original_pre_design" not in st.session_state:
                                                    st.session_state["sections_df_original_pre_design"] = st.session_state["sections_df"].copy()
                                                if "section_points_df_original_pre_design" not in st.session_state:
                                                    st.session_state["section_points_df_original_pre_design"] = st.session_state["section_points_df"].copy()
                                                new_sec, new_pts, fusion_summary, original_pts_fusion = apply_design_channel_to_reach(
                                                    st.session_state["sections_df"],
                                                    st.session_state["section_points_df"],
                                                    pk_start_m=float(design_pk_ini) * 1000.0,
                                                    pk_end_m=float(design_pk_fin) * 1000.0,
                                                    spec=spec_reach,
                                                    bottom_elevation_mode=bottom_mode_reach,
                                                    bottom_elevation_value=bottom_reach_value,
                                                )
                                                st.session_state["sections_df"] = new_sec
                                                st.session_state["section_points_df"] = new_pts
                                                st.session_state["sections_review_df"] = new_sec.copy()
                                                st.session_state["section_design_fusion_summary_df"] = fusion_summary
                                                st.session_state["section_design_fusion_original_points_df"] = original_pts_fusion
                                                for _k in [
                                                    "hydraulic_profile_base_df", "hydraulic_profile_df", "hydraulic_df",
                                                    "sediment_df", "sediment_zone_summary_df", "qa_hidraulica_df",
                                                    "sensibilidad_manning_df", "incertidumbre_mc_df", "confianza_v6_df",
                                                    "profile_3d_fig", "profile_3d_html", "hydraulic_longitudinal_fig",
                                                    "overflow_sections_df", "sections_preview_3d_fig", "sections_preview_3d_html",
                                                ]:
                                                    st.session_state.pop(_k, None)
                                                st.success(f"Fusión aplicada al tramo. Secciones modificadas: {len(fusion_summary)}. Recalcule hidráulica/sedimentos.")
                                            except Exception as exc:
                                                st.error(f"No se pudo aplicar la fusión al tramo: {exc}")

                                    if has("section_design_fusion_summary_df"):
                                        st.subheader("Resumen de fusiones aplicadas")
                                        st.dataframe(st.session_state["section_design_fusion_summary_df"], use_container_width=True, hide_index=True)
                                        st.download_button(
                                            "Descargar resumen fusión CSV",
                                            st.session_state["section_design_fusion_summary_df"].to_csv(index=False).encode("utf-8"),
                                            file_name="resumen_fusion_secciones_compuestas.csv",
                                            mime="text/csv",
                                        )
                                    if has("sections_df_original_pre_design") and has("section_points_df_original_pre_design"):
                                        st.caption("Trazabilidad activa: se conservó una copia interna de secciones y puntos antes de la primera fusión de diseño.")
                            except Exception as exc:
                                st.info(f"Editor de sección compuesta no disponible en este estado: {exc}")

                        st.subheader("Ventana 2D de sección seleccionada · dimensiones y PK")
                        if not sec_filtered.empty and has("section_points_df"):
                            sec_ids_2d = sec_filtered["section_id"].astype(str).tolist()
                            sc1, sc2 = st.columns([1, 2])
                            with sc1:
                                sid_2d = st.selectbox("Sección para visualizar", sec_ids_2d, key="sid_2d_sections_tab")
                            with sc2:
                                st.caption("La sección se muestra en plano coordenado offset–cota. Debe verse como perfil transversal real, no como línea plana.")
                            try:
                                pts_2d = _hs_section_points(st.session_state["section_points_df"], sid_2d)
                                sec_row_2d = sec_filtered[sec_filtered["section_id"].astype(str) == str(sid_2d)].iloc[0]
                                if pts_2d.empty:
                                    st.warning("Esta sección no tiene puntos topográficos asociados. Revise curvas de apoyo o generación v13.")
                                else:
                                    fig_2d = _hs_section_review_figure(
                                        sid_2d,
                                        None,
                                        st.session_state.get("section_points_df"),
                                        hydraulic_df=None,
                                        sediment_df=None,
                                    )
                                    fig_2d.update_layout(
                                        title=f"Sección {sid_2d} · PK {float(sec_row_2d.get('pk_m', 0.0))/1000:.3f} km · perfil geométrico",
                                        height=520,
                                    )
                                    st.plotly_chart(fig_2d, use_container_width=True)

                                    dims_2d = pd.DataFrame([{
                                        "section_id": sid_2d,
                                        "PK_m": float(sec_row_2d.get("pk_m", np.nan)),
                                        "PK_km": float(sec_row_2d.get("pk_m", np.nan)) / 1000.0,
                                        "n_puntos": int(len(pts_2d)),
                                        "offset_min_m": float(pts_2d["offset_m"].min()),
                                        "offset_max_m": float(pts_2d["offset_m"].max()),
                                        "ancho_m": float(pts_2d["offset_m"].max() - pts_2d["offset_m"].min()),
                                        "cota_min_m": float(pts_2d["z_m"].min()),
                                        "cota_max_m": float(pts_2d["z_m"].max()),
                                        "profundidad_geometrica_m": float(pts_2d["z_m"].max() - pts_2d["z_m"].min()),
                                        "estado_revision": str(sec_row_2d.get("estado_revision", "")),
                                    }])
                                    st.dataframe(dims_2d, use_container_width=True, hide_index=True)
                            except Exception as exc:
                                st.warning(f"No se pudo visualizar sección 2D: {exc}")

                        st.subheader("Puntos de perfil v13")
                        st.dataframe(st.session_state["section_points_df"].head(500), use_container_width=True)

                        if has("sections_v13_modelable_df"):
                            st.subheader("QA de secciones modelables")
                            st.dataframe(st.session_state["sections_v13_modelable_df"], use_container_width=True)

                        st.subheader("Perfil longitudinal 3D previo · secciones seleccionadas")
                        pr1, pr2, pr3, pr4, pr5 = st.columns(5)
                        with pr1:
                            prev_vex = st.slider("Exageración vertical previa", min_value=0.5, max_value=10.0, value=1.5, step=0.5, key="prev_sections_vex")
                        with pr2:
                            prev_show_ok = st.checkbox("Ver aceptadas", value=True, key="prev_show_ok")
                        with pr3:
                            prev_show_fill = st.checkbox("Ver rellenadas", value=True, key="prev_show_fill")
                        with pr4:
                            prev_show_bad = st.checkbox("Ver eliminadas", value=True, key="prev_show_bad")
                        with pr5:
                            prev_view = st.selectbox("Vista inicial", list(VIEW_CAMERAS_3D.keys()), index=list(VIEW_CAMERAS_3D.keys()).index("Isométrica"), key="prev_view_3d")

                        if st.button("Generar perfil previo de secciones", type="secondary"):
                            try:
                                fig_prev = create_section_selection_3d_figure(
                                    st.session_state["sections_review_df"],
                                    st.session_state.get("section_points_df"),
                                    modelable_df=st.session_state.get("sections_v13_modelable_df"),
                                    vertical_exaggeration=float(prev_vex),
                                    show_accepted=bool(prev_show_ok),
                                    show_filled=bool(prev_show_fill),
                                    show_removed=bool(prev_show_bad),
                                    initial_view=str(prev_view),
                                )
                                st.session_state["sections_preview_3d_fig"] = fig_prev
                                st.session_state["sections_preview_3d_html"] = figure_to_html_bytes(fig_prev)
                                st.success("Perfil previo 3D de secciones generado.")
                            except Exception as exc:
                                st.error(f"No se pudo generar perfil previo: {exc}")

                        if has("sections_preview_3d_fig"):
                            st.plotly_chart(st.session_state["sections_preview_3d_fig"], use_container_width=True)
                            if has("sections_preview_3d_html"):
                                st.download_button(
                                    "Descargar perfil previo 3D HTML",
                                    st.session_state["sections_preview_3d_html"],
                                    file_name="perfil_previo_secciones_3d.html",
                                    mime="text/html",
                                )

                        if has("sections_v13_modelacion_kmz"):
                            st.download_button("Descargar KMZ modelación v13", st.session_state["sections_v13_modelacion_kmz"], file_name="secciones_modelacion_v13.kmz", mime="application/vnd.google-earth.kmz")
                        if has("sections_v13_zip"):
                            st.download_button("Descargar ZIP completo v13", st.session_state["sections_v13_zip"], file_name="salida_secciones_v13_hidrosed.zip", mime="application/zip")
            except Exception as exc:
                st.error(f"Error en motor v13 de secciones: {exc}")
        else:
            st.info("Carga un KMZ/KML con eje y curvas para usar el motor v13.")

    else:
        st.info("Motor DEM actual disponible como respaldo. Para esta versión se recomienda el motor v13 KMZ/curvas/eje.")
        if not has("axis_line") or not has("dem_path"):
            st.warning("Necesitas DEM y eje de cauce.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                spacing = st.number_input("Espaciamiento secciones [m]", min_value=5.0, value=100.0, step=10.0)
            with c2:
                width = st.number_input("Ancho sección [m]", min_value=5.0, value=80.0, step=10.0)
            with c3:
                pts_side = st.number_input("Puntos por lado", min_value=2, value=10, step=1)
            if st.button("Generar secciones desde eje + DEM", type="primary"):
                try:
                    line = _axis_line_as_linestring(st.session_state.get("axis_line"))
                    sec_raw, pts_raw = generate_cross_sections(line, st.session_state["dem_path"], spacing_m=float(spacing), width_m=float(width), points_each_side=int(pts_side))
                    sec_raw, pts_raw, axis_thalweg_qa, axis_thalweg_auto = verify_and_snap_axis_to_section_minima(
                        sec_raw,
                        pts_raw,
                        axis_source=st.session_state.get("axis_source", "manual_o_dem"),
                        tolerance_m=0.50,
                        update_axis_if_auto=True,
                    )
                    st.session_state["axis_thalweg_qa_df"] = axis_thalweg_qa
                    st.session_state["axis_thalweg_qa_summary"] = summarize_axis_thalweg_qa(axis_thalweg_qa)
                    if axis_thalweg_auto:
                        st.session_state["axis_line"] = axis_thalweg_auto
                        st.session_state["axis_source"] = "automatico_recentrado_thalweg"
                    st.session_state["sections_df"] = sec_raw
                    st.session_state["section_points_df"] = pts_raw
                    st.session_state["sections_mode"] = "dem_actual"
                    resumen_eje = st.session_state.get("axis_thalweg_qa_summary", {})
                    st.success(f"Secciones DEM generadas: {len(sec_raw)} · eje-thalweg corregido en {resumen_eje.get('n_corregidas', 0)} secciones.")
                except Exception as exc:
                    st.error(str(exc))


with tabs[5]:
    st.header("6 · Hidrología reforzada · metodología y caudales")

    with st.expander("Base histórica DGA/Sedimentos precargada", expanded=False):
        cat_pre = load_catalog()
        if cat_pre.empty:
            st.warning("No se encontró catálogo precargado.")
        else:
            st.dataframe(cat_pre, use_container_width=True, hide_index=True)
            st.caption("La base se mantiene comprimida para no sobrecargar la aplicación. Se consulta por demanda para ranking de estaciones y trazabilidad.")
            if has("control_point"):
                cp_rank = st.session_state["control_point"]
                dataset_rank = st.selectbox(
                    "Ranking de estaciones cercanas",
                    ["precipitacion_max_24h", "precipitacion_diaria", "caudal_diario", "caudal_medio_mensual", "sedimento_rutinario", "sedimento_integrado"],
                    index=0,
                    key="dataset_rank_preloaded",
                )
                if st.button("Calcular ranking preliminar de estaciones", key="btn_rank_preloaded"):
                    try:
                        rank_df = rank_stations_by_point(dataset_rank, float(cp_rank["lat"]), float(cp_rank["lon"]))
                        st.session_state["ranking_estaciones_df"] = rank_df
                        st.success(f"Ranking calculado para {dataset_rank}.")
                    except Exception as exc:
                        st.error(f"No se pudo calcular ranking: {exc}")
                if has("ranking_estaciones_df"):
                    st.dataframe(st.session_state["ranking_estaciones_df"].head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Ingrese punto de control para ranking por distancia.")


    with st.expander("Acciones correctivas prioritarias v3.6", expanded=False):
        st.caption("Cierra las brechas de auditoría: frecuencia real, relleno pluviométrico, estación-isoyeta, coeficientes regionales, pruebas unitarias y memoria de cálculo.")
        corr_tabs = st.tabs([
            "Coeficientes",
            "Frecuencia Q(T)",
            "Relleno P24",
            "Estación vs isoyeta",
            "Pruebas",
        ])

        with corr_tabs[0]:
            coeff_df_v36 = load_regional_coefficients()
            st.session_state["regional_coeffs_v36"] = coeff_df_v36
            st.dataframe(coeff_df_v36, use_container_width=True, hide_index=True)
            st.caption("Archivo editable incluido: data/regional_coeffs_hidrologia_v36.csv")

        with corr_tabs[1]:
            st.caption("Conecta caudales diarios reales con frecuencia de máximos anuales. Si se adopta, puede reemplazar o contrastar Q(T) normativa.")
            fc1, fc2, fc3 = st.columns([1, 1, 1])
            with fc1:
                flow_station_code = st.text_input("Código estación fluviométrica", value="", key="flow_station_code_v36")
            with fc2:
                usar_frecuencia_qt = st.checkbox("Usar Q(T) frecuencia si es válida", value=False, key="usar_frecuencia_qt_v36")
            with fc3:
                st.write("")
                st.write("")
                btn_flow_freq = st.button("Calcular frecuencia real Q(T)", key="btn_flow_freq_v36")
            if btn_flow_freq and flow_station_code.strip():
                try:
                    fr = flow_annual_maxima_frequency(flow_station_code.strip(), periods=periods)
                    st.session_state["flow_frequency_v36"] = fr
                    if fr["ok"]:
                        st.success("Frecuencia de caudales máximos diarios conectada.")
                    else:
                        st.warning("No se pudo obtener frecuencia adoptable para la estación.")
                except Exception as exc:
                    st.error(f"Error frecuencia Q(T): {exc}")
            if has("flow_frequency_v36"):
                fr = st.session_state["flow_frequency_v36"]
                st.dataframe(fr.get("report", pd.DataFrame()), use_container_width=True, hide_index=True)
                st.dataframe(fr.get("frequency", pd.DataFrame()), use_container_width=True, hide_index=True)
                st.dataframe(fr.get("annual_max", pd.DataFrame()).head(100), use_container_width=True, hide_index=True)
                if usar_frecuencia_qt and fr.get("ok") and not fr.get("frequency", pd.DataFrame()).empty:
                    qfreq = fr["frequency"][["T_anios", "Q_m3s", "metodo"]].copy()
                    st.session_state["q_design"] = qfreq
                    st.info("Q(T) de frecuencia real quedó conectado como caudal de diseño para hidráulica posterior.")

        with corr_tabs[2]:
            st.caption("Relleno de lagunas anuales P24: regresión lineal si hay traslape suficiente y buen R²; razón normal si no.")
            rg1, rg2, rg3 = st.columns([1, 1, 1])
            with rg1:
                primary_code = st.text_input("Estación principal P24", value="", key="primary_p24_v36")
            with rg2:
                secondary_code = st.text_input("Estación secundaria P24", value="", key="secondary_p24_v36")
            with rg3:
                st.write("")
                st.write("")
                btn_fill = st.button("Rellenar lagunas P24", key="btn_fill_p24_v36")
            if btn_fill and primary_code.strip() and secondary_code.strip():
                try:
                    fill = fill_pluviometric_gaps(primary_code.strip(), secondary_code.strip())
                    st.session_state["pluvio_fill_v36"] = fill
                    if fill["ok"]:
                        st.success("Relleno pluviométrico generado.")
                    else:
                        st.warning("No se pudo rellenar: revise códigos y traslape.")
                except Exception as exc:
                    st.error(f"Error relleno pluviométrico: {exc}")
            if has("pluvio_fill_v36"):
                fill = st.session_state["pluvio_fill_v36"]
                st.dataframe(fill.get("report", pd.DataFrame()), use_container_width=True, hide_index=True)
                st.dataframe(fill.get("filled", pd.DataFrame()).head(200), use_container_width=True, hide_index=True)

        with corr_tabs[3]:
            st.caption("Validación automática P24 estación vs P24 isoyeta: verde ≤20%, amarillo 20–35%, rojo >35%.")
            vi1, vi2, vi3 = st.columns([1, 1, 1])
            with vi1:
                station_iso_code = st.text_input("Código estación P24", value="", key="station_iso_code_v36")
            with vi2:
                p24_iso_for_validation = st.number_input(
                    "P24,10 isoyeta [mm]",
                    min_value=0.0,
                    value=float(st.session_state.get("p24_10_adoptada_mm", 80.7)),
                    step=1.0,
                    key="p24_iso_validate_v36",
                )
            with vi3:
                st.write("")
                st.write("")
                btn_iso_val = st.button("Validar estación-isoyeta", key="btn_iso_val_v36")
            if btn_iso_val and station_iso_code.strip():
                try:
                    val = station_isoyeta_semiphore(station_iso_code.strip(), float(p24_iso_for_validation))
                    st.session_state["station_isoyeta_validation_v36"] = val
                    if val["ok"]:
                        sem = val["validation"].iloc[0]["semaforo"]
                        if sem == "verde":
                            st.success("Estación e isoyeta consistentes.")
                        elif sem == "amarillo":
                            st.warning("Diferencia intermedia estación-isoyeta.")
                        else:
                            st.error("Inconsistencia fuerte estación-isoyeta; usar criterio conservador.")
                    else:
                        st.warning("No se pudo validar estación-isoyeta.")
                except Exception as exc:
                    st.error(f"Error validación estación-isoyeta: {exc}")
            if has("station_isoyeta_validation_v36"):
                val = st.session_state["station_isoyeta_validation_v36"]
                st.dataframe(val.get("validation", pd.DataFrame()), use_container_width=True, hide_index=True)
                if val.get("ok") and not val.get("validation", pd.DataFrame()).empty:
                    pcons = float(val["validation"].iloc[0]["P24_adoptada_conservadora_mm"])
                    if st.button("Adoptar P24 conservadora estación/isoyeta", key="btn_adopt_p24_cons_v36"):
                        st.session_state["p24_10_adoptada_mm"] = pcons
                        st.session_state["p24_10_fuente"] = "Validación estación-isoyeta conservadora"
                        st.session_state["p24_10_observacion"] = f"P24 adoptada conservadora={pcons:.2f} mm"
                        st.success(f"P24 conservadora adoptada: {pcons:.2f} mm")

        with corr_tabs[4]:
            if st.button("Ejecutar pruebas unitarias v3.6", key="btn_unit_tests_v36"):
                try:
                    tests = unit_tests_v36()
                    st.session_state["unit_tests_v36_df"] = tests
                    st.success("Pruebas unitarias ejecutadas.")
                except Exception as exc:
                    st.error(f"Error pruebas unitarias: {exc}")
            if has("unit_tests_v36_df"):
                st.dataframe(st.session_state["unit_tests_v36_df"], use_container_width=True, hide_index=True)


    basin_m = st.session_state.get("basin_metrics", {})
    area_default = float(basin_m.get("area_km2", st.session_state.get("expected_basin_default", 10.0)) or 10.0)
    length_default = float(basin_m.get("bbox_largo_km", 5.0) or 5.0)
    dz_default = float(basin_m.get("desnivel_m", 0.0) or 0.0)

    st.markdown("""
Este módulo aplica el núcleo HidroSed de hidrología: morfometría, selección metodológica, tiempos de concentración, IDF sintética desde P24, DGA‑AC/regional, racional modificado y transferencia hidrológica si existe estación de referencia.

**Mejora v3.2:** la P24 puede obtenerse desde isoyetas KMZ precargadas o cargadas por el usuario. El valor manual queda como respaldo preliminar.
""")

    st.subheader("Fuente de precipitación máxima diaria P24")
    iso1, iso2, iso3 = st.columns([1.2, 1.2, 1.0])
    with iso1:
        p24_source = st.selectbox(
            "Fuente P24",
            ["Isoyetas KMZ precargadas", "Cargar isoyetas KMZ/KML", "Manual de respaldo"],
            index=0,
            help="Priorice isoyetas o fuente pluviométrica trazable. Manual solo como respaldo preliminar."
        )
    with iso2:
        uploaded_isoyetas = st.file_uploader(
            "Isoyetas KMZ/KML opcional",
            type=["kmz", "kml"],
            disabled=p24_source != "Cargar isoyetas KMZ/KML",
            key="isoyetas_upload_v32"
        )
    with iso3:
        n_nearest_iso = st.selectbox("N° isoyetas IDW", [1, 2, 3, 4, 5], index=2)

    p24_auto = None
    p24_obs = "P24 manual de respaldo."
    p24_method = "manual"
    iso_detail_df = pd.DataFrame()

    try:
        iso_text = None
        if p24_source == "Isoyetas KMZ precargadas":
            if ISOYETAS_DEFAULT_PATH.exists():
                iso_text = read_isoyetas_kmz_kml(ISOYETAS_DEFAULT_PATH)
            else:
                st.warning("No se encontró data/isoyetas/Precipitaciones_Maximas_Diarias.kmz dentro de la app.")
        elif p24_source == "Cargar isoyetas KMZ/KML" and uploaded_isoyetas is not None:
            iso_text = read_isoyetas_kmz_kml(uploaded_isoyetas)

        if iso_text:
            isodf = parse_isoyetas_kml(iso_text)
            st.session_state["isoyetas_df"] = isodf
            if not isodf.empty and has("control_point"):
                cp_iso = st.session_state["control_point"]
                est = estimate_p24_from_isoyetas(
                    isodf,
                    lon=float(cp_iso["lon"]),
                    lat=float(cp_iso["lat"]),
                    basin_kml=st.session_state.get("basin_kml"),
                    n_nearest=int(n_nearest_iso),
                )
                if est.get("ok"):
                    p24_auto = float(est["P24_mm"])
                    p24_method = est.get("metodo", "isoyetas")
                    p24_obs = est.get("mensaje", "P24 estimada desde isoyetas.")
                    iso_detail_df = est.get("detalle_df", pd.DataFrame())
                    st.success(f"P24 estimada desde isoyetas: {p24_auto:.2f} mm · {p24_method}")
                else:
                    st.warning(est.get("mensaje", "No se pudo estimar P24 desde isoyetas."))
            if not isodf.empty:
                with st.expander("Inventario y trazabilidad de isoyetas", expanded=False):
                    st.dataframe(isoyeta_inventory(isodf), use_container_width=True)
                    st.dataframe(isodf.drop(columns=["geometry_wkt"], errors="ignore").head(300), use_container_width=True)
                    if not iso_detail_df.empty:
                        st.subheader("Isopletas usadas para P24")
                        st.dataframe(iso_detail_df, use_container_width=True)
                    st.subheader("Visualización simple de isoyetas")
                    try:
                        from shapely import wkt as shapely_wkt
                        import plotly.graph_objects as go
                        fig_iso = go.Figure()
                        for _, rr in isodf.head(500).iterrows():
                            geom = shapely_wkt.loads(rr["geometry_wkt"])
                            geoms = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
                            for gg in geoms:
                                if hasattr(gg, "exterior"):
                                    xs, ys = gg.exterior.xy
                                elif hasattr(gg, "xy"):
                                    xs, ys = gg.xy
                                else:
                                    continue
                                fig_iso.add_trace(go.Scatter(
                                    x=list(xs), y=list(ys), mode="lines",
                                    name=f'P24 {rr["P24_mm"]:.1f} mm',
                                    line=dict(width=1),
                                    showlegend=False,
                                    hovertemplate=f'P24={rr["P24_mm"]:.1f} mm<br>{rr.get("nombre","")}<extra></extra>',
                                ))
                        if has("control_point"):
                            cpv = st.session_state["control_point"]
                            fig_iso.add_trace(go.Scatter(x=[cpv["lon"]], y=[cpv["lat"]], mode="markers", marker=dict(size=10), name="Punto control"))
                        fig_iso.update_layout(height=480, xaxis_title="Longitud", yaxis_title="Latitud", title="Capa visual de isoyetas Pmáx diaria")
                        st.plotly_chart(fig_iso, use_container_width=True)
                    except Exception as exc:
                        st.warning(f"No se pudo graficar isoyetas: {exc}")
        elif p24_source != "Manual de respaldo":
            st.info("Cargue isoyetas o use las precargadas para estimar P24 automáticamente.")
    except Exception as exc:
        st.warning(f"No se pudo procesar isoyetas. Se mantiene P24 manual. Detalle: {exc}")

    p24_default_value = float(p24_auto) if p24_auto is not None else float(st.session_state.get("p24_10_adoptada_mm", 80.7))
    st.session_state["p24_10_adoptada_mm"] = p24_default_value
    st.session_state["p24_10_fuente"] = p24_source if p24_auto is not None else "Manual de respaldo"
    st.session_state["p24_10_metodo"] = p24_method
    st.session_state["p24_10_observacion"] = p24_obs

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        area_km2 = st.number_input("Área cuenca [km²]", min_value=0.001, value=area_default, step=max(0.5, area_default/100))
        C = st.number_input("Coeficiente escorrentía C", min_value=0.01, max_value=1.0, value=0.45, step=0.05)
    with c2:
        length_km = st.number_input("Longitud cauce [km]", min_value=0.001, value=length_default, step=0.5)
        slope = st.number_input("Pendiente media [m/m]", min_value=0.00001, value=0.01, step=0.001, format="%.5f")
    with c3:
        p24_10 = st.number_input("P24,10 [mm]", min_value=0.0, value=float(p24_default_value), step=1.0, help="Valor adoptado para P24,10. Si proviene de isoyetas, queda con trazabilidad en la matriz normativa.")
        alpha = st.number_input("Factor alfa DGA-AC", min_value=0.1, value=2.14, step=0.01)
    with c4:
        basin_regime = st.selectbox("Régimen", ["pluvial", "nivo-pluvial", "mixto / árido"], index=0)
        periods_txt = st.text_input("Periodos T", value="2,5,10,25,50,100,200")

    periods = periods_from_text(periods_txt)

    st.subheader("Control normativo DGA / Manual de Carreteras / IDF")
    norm_a, norm_b, norm_c, norm_d = st.columns(4)
    with norm_a:
        activar_normativa_v35 = st.checkbox("Activar hidrología normativa v3.5", value=True)
    with norm_b:
        regla_adopcion_v35 = st.selectbox("Adopción caudal", ["envolvente_maxima", "mediana_adoptable", "promedio_adoptable"], index=0)
    with norm_c:
        pma_mm_v35 = st.number_input("P media anual/PMA [mm]", min_value=0.0, value=float(max(p24_10*3.5, p24_10)), step=10.0)
    with norm_d:
        area_nival_v35 = st.number_input("Área nival [km²]", min_value=0.0, value=float(area_km2 if "nivo" in basin_regime else 0.0), step=1.0)

    st.subheader("Transferencia hidrológica opcional")
    t1, t2, t3, t4, t5 = st.columns(5)
    with t1:
        use_transfer = st.checkbox("Usar estación de referencia", value=False)
    with t2:
        station_area = st.number_input("Área estación [km²]", min_value=0.0, value=max(area_km2, 1.0), step=10.0)
    with t3:
        station_q100 = st.number_input("Q100 estación [m³/s]", min_value=0.0, value=0.0, step=10.0)
    with t4:
        b_exp = st.number_input("Exponente b", min_value=0.30, max_value=1.20, value=0.75, step=0.05)
    with t5:
        f_alt = st.number_input("Factor altitud", min_value=0.10, max_value=3.00, value=1.00, step=0.05)
        f_dist = st.number_input("Factor similitud", min_value=0.10, max_value=3.00, value=1.00, step=0.05)

    if st.button("Calcular hidrología reforzada", type="primary"):
        try:
            tc_df, hydro_all, rec_df, uncertainty_df = build_hydrology(
                area_km2=float(area_km2),
                length_km=float(length_km),
                slope=float(slope),
                C=float(C),
                p24_10=float(p24_10),
                alpha=float(alpha),
                periods=periods,
                include_transfer=bool(use_transfer and station_area > 0 and station_q100 > 0),
                station_area=float(station_area),
                station_q100=float(station_q100),
                b_exp=float(b_exp),
                f_alt=float(f_alt),
                f_dist=float(f_dist),
                dz_m=dz_default,
                basin_regime=basin_regime,
            )
            st.session_state["tc_methods_df"] = tc_df
            st.session_state["hydrology_all_methods"] = hydro_all
            st.session_state["hydrology_methods_recommendation"] = rec_df
            st.session_state["hydrology_uncertainty_df"] = uncertainty_df
            st.session_state["hydrology_inputs"] = {
                "area_km2": area_km2, "C": C, "length_km": length_km, "slope": slope,
                "p24_10": p24_10, "alpha": alpha, "regimen": basin_regime,
                "transferencia": bool(use_transfer), "station_area": station_area, "station_q100": station_q100,
                "p24_fuente": st.session_state.get("p24_10_fuente", "Manual de respaldo"),
                "p24_metodo": st.session_state.get("p24_10_metodo", "manual"),
                "p24_observacion": st.session_state.get("p24_10_observacion", ""),
            }
            st.session_state["normativa_hidrosed_df"] = normative_hydraulic_hydrology_check({
                "p24_trazable": st.session_state.get("p24_10_fuente") != "Manual de respaldo",
                "p24_observacion": st.session_state.get("p24_10_observacion", ""),
                "idf_tc": True,
                "metodos_comparados": True,
                "geometria_hidraulica": has("sections_df") or has("basin_metrics"),
                "hecras_like": has("hydraulic_profile_df"),
                "granulometria_real": str(st.session_state.get("granulometry_metrics", {}).get("fuente", "")).lower() == "excel_usuario",
            })
            st.session_state["normativa_hidrosed_score"] = normative_confidence_score(st.session_state["normativa_hidrosed_df"])

            if bool(activar_normativa_v35):
                norm_v35 = run_normative_hydrology(
                    area_km2=float(area_km2),
                    length_km=float(length_km),
                    slope=float(slope),
                    C=float(C),
                    p24_10=float(p24_10),
                    alpha=float(alpha),
                    periods=periods,
                    regime=basin_regime,
                    pma_mm=float(pma_mm_v35),
                    nival_area_km2=float(area_nival_v35) if float(area_nival_v35) > 0 else None,
                    adoption_rule=str(regla_adopcion_v35),
                )
                st.session_state["hydrology_normative_v35"] = norm_v35
                st.session_state["hydrology_normative_methods_v35"] = norm_v35["metodos_normativos"]
                st.session_state["idf_normativa_v35"] = norm_v35["idf_normativa"]
                st.session_state["pmax_123_v35"] = norm_v35["pmax_123"]
                st.session_state["hidrogramas_v35"] = norm_v35["hidrogramas"]
                st.session_state["caudales_minimos_v35"] = norm_v35["caudales_minimos"]
                st.session_state["qa_hidrologia_v35"] = norm_v35["qa_hidrologia"]
                st.session_state["cumplimiento_hidrologia_v35"] = norm_v35["cumplimiento"]
                # La hidráulica posterior usará la adopción normativa v3.5.
                st.session_state["q_design"] = norm_v35["caudales_adoptados"]
            st.session_state["hydrology_done"] = True
            st.success("Hidrología reforzada calculada con control normativo v3.5.")
        except Exception as exc:
            st.error(str(exc))

    if has("tc_methods_df"):
        k1, k2, k3 = st.columns(3)
        tc_med = pd.to_numeric(st.session_state["tc_methods_df"].get("tc_adoptado_h"), errors="coerce").dropna()
        k1.metric("Tc adoptado", f"{float(tc_med.iloc[0]):.2f} h" if len(tc_med) else "N/D")
        k2.metric("Métodos hidrológicos", len(st.session_state.get("hydrology_all_methods", [])))
        k3.metric("Periodos", len(periods))
        st.subheader("Tiempos de concentración")
        st.dataframe(st.session_state["tc_methods_df"], use_container_width=True)
        st.subheader("Recomendación metodológica")
        st.dataframe(st.session_state["hydrology_methods_recommendation"], use_container_width=True)
        st.subheader("Caudales por método")
        st.dataframe(st.session_state["hydrology_all_methods"], use_container_width=True)
        st.subheader("Incertidumbre entre métodos")
        st.dataframe(st.session_state["hydrology_uncertainty_df"], use_container_width=True)
        try:
            import plotly.express as px
            fig = px.line(st.session_state["hydrology_all_methods"], x="T_anios", y="Q_m3s", color="metodo", markers=True, title="Comparación de caudales por metodología")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        if has("hydrology_normative_v35"):
            st.subheader("Hidrología normativa v3.5 · Manual DGA + Manual de Carreteras + IDF + Pmáx 1-2-3 días")
            norm_tabs = st.tabs(["Cumplimiento", "Métodos", "IDF", "P24/P48/P72", "Hidrogramas", "Q mínimos", "QA"])
            with norm_tabs[0]:
                st.dataframe(st.session_state["cumplimiento_hidrologia_v35"], use_container_width=True, hide_index=True)
                try:
                    st.metric("Puntaje hidrología normativa", f"{float(st.session_state['cumplimiento_hidrologia_v35'].iloc[0]['puntaje_hidrologia_normativa_1_10']):.1f}/10")
                except Exception:
                    pass
            with norm_tabs[1]:
                st.dataframe(st.session_state["hydrology_normative_methods_v35"], use_container_width=True, hide_index=True)
                st.caption("DGA-AC pluvial se valida automáticamente para 20–10.000 km²; racional queda con advertencias fuera de cuencas pequeñas.")
            with norm_tabs[2]:
                st.dataframe(st.session_state["idf_normativa_v35"], use_container_width=True, hide_index=True)
            with norm_tabs[3]:
                st.dataframe(st.session_state["pmax_123_v35"], use_container_width=True, hide_index=True)
            with norm_tabs[4]:
                st.dataframe(st.session_state["hidrogramas_v35"], use_container_width=True, hide_index=True)
            with norm_tabs[5]:
                st.dataframe(st.session_state["caudales_minimos_v35"], use_container_width=True, hide_index=True)
            with norm_tabs[6]:
                st.dataframe(st.session_state["qa_hidrologia_v35"], use_container_width=True, hide_index=True)

        st.subheader("Trazabilidad P24 e isoyetas")
        trace_df = pd.DataFrame([{
            "P24_adoptada_mm": st.session_state.get("hydrology_inputs", {}).get("p24_10"),
            "fuente": st.session_state.get("hydrology_inputs", {}).get("p24_fuente"),
            "metodo": st.session_state.get("hydrology_inputs", {}).get("p24_metodo"),
            "observacion": st.session_state.get("hydrology_inputs", {}).get("p24_observacion"),
        }])
        st.dataframe(trace_df, use_container_width=True, hide_index=True)

        if has("normativa_hidrosed_df"):
            st.subheader("Matriz normativa HidroSed · Manual de Carreteras / DGA / HEC-RAS / Sedimentos")
            score_norm = float(st.session_state.get("normativa_hidrosed_score", 0.0) or 0.0)
            st.metric("Confianza normativa-hidrológica", f"{score_norm:.1f}/10")
            st.dataframe(st.session_state["normativa_hidrosed_df"], use_container_width=True, hide_index=True)


with tabs[6]:
    st.header("7 · Cálculo y adopción de caudales")
    if not has("hydrology_done"):
        st.warning("Primero calcula hidrología reforzada.")
    else:
        mode = st.selectbox("Criterio de adopción", ["envolvente_maxima", "mediana_metodos", "promedio_metodos"], index=0)
        st.caption("Para diseño conservador se recomienda envolvente máxima; para diagnóstico se puede comparar mediana/promedio.")
        if st.button("Adoptar caudales", type="primary"):
            q = adopt_flows_advanced(st.session_state.get("hydrology_all_methods"), mode=mode)
            st.session_state["q_design"] = q
            st.session_state["q_adoption_mode"] = mode
            st.success("Caudales adoptados.")
        if has("q_design"):
            st.dataframe(st.session_state["q_design"], use_container_width=True)
            try:
                import plotly.express as px
                fig = px.bar(st.session_state["q_design"], x="T_anios", y="Q_m3s", title=f"Caudales adoptados · {st.session_state.get('q_adoption_mode','')}")
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
            st.download_button("Descargar caudales adoptados CSV", st.session_state["q_design"].to_csv(index=False).encode("utf-8"), file_name="caudales_adoptados_hidrosed.csv", mime="text/csv")


with tabs[7]:
    st.header("8 · Hidráulica 1D tipo HEC-RAS, socavación y transporte")
    st.markdown(
        """
Este módulo usa las secciones transversales generadas desde el DEM y las resuelve como **sistema conectado**.

La lógica es tipo HEC‑RAS 1D permanente simplificado:

```text
Secciones ordenadas por PK
↓
Condición de borde aguas abajo
↓
Balance de energía entre secciones
↓
Pérdidas por fricción
↓
Pérdidas locales por contracción/expansión
↓
Perfil de cota de agua por periodo de retorno
↓
Shields / MPM / socavación preliminar
```
"""
    )

    st.markdown(
        """
        <div class="hs-info">
        <b>Relación con Manual de Carreteras:</b> el módulo queda alineado como cálculo hidráulico preliminar para revisión de cauces,
        secciones, rugosidad, velocidades, Froude, esfuerzo cortante, transporte y socavación. Para diseño definitivo debe contrastarse
        con el Manual de Carreteras vigente, criterios DOH/DGA, verificación topográfica, granulometría real, obras existentes,
        condiciones de borde y, cuando corresponda, modelación HEC-RAS oficial calibrada.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not has("sections_df") or not has("section_points_df") or not has("q_design"):
        st.warning("Necesitas secciones transversales completas y caudales adoptados.")
    else:
        st.subheader("Parámetros de modelación hidráulica conectada")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            S = st.number_input(
                "Pendiente energía/fricción inicial",
                min_value=0.00001,
                value=float(st.session_state.get("hydrology_inputs", {}).get("slope", 0.01)),
                step=0.001,
                format="%.5f",
            )
        with c2:
            n_default_sup = float(st.session_state.get("n_manning_adoptado", 0.035) or 0.035)
            n = st.number_input("Manning n", min_value=0.010, value=n_default_sup, step=0.005, format="%.3f")
        with c3:
            contr = st.number_input("Coef. contracción", min_value=0.0, max_value=1.0, value=0.10, step=0.05)
        with c4:
            expan = st.number_input("Coef. expansión", min_value=0.0, max_value=1.0, value=0.30, step=0.05)

        with st.expander("Granulometría para sedimentos y socavación", expanded=True):
            st.caption("Seleccione una granulometría tipo o cargue Excel/CSV real. La app calcula D16, D30, D35, D50, D60, D65, D84, D90 y Dm para las metodologías internas.")
            g1, g2, g3 = st.columns([1.1, 1.1, 1.0])
            with g1:
                gran_mode = st.radio(
                    "Fuente granulométrica",
                    ["Perfil tipo por defecto", "Excel/CSV granulometría real"],
                    horizontal=False,
                    key="gran_mode_sedgran_v316",
                )
                profile_name = st.selectbox(
                    "Perfil tipo",
                    list(DEFAULT_PROFILES_MM.keys()),
                    index=3,
                    disabled=gran_mode != "Perfil tipo por defecto",
                    key="gran_profile_name_v316",
                )
            with g2:
                gran_excel = st.file_uploader(
                    "Cargar Excel/CSV granulometría",
                    type=["xlsx", "xls", "csv"],
                    disabled=gran_mode != "Excel/CSV granulometría real",
                    help="Puede contener diámetros D16/D50/D84/etc. o curva por tamiz con abertura_mm y porcentaje_pasa.",
                    key="gran_excel_v316",
                )
                use_default_if_fail = st.checkbox("Usar perfil tipo si Excel falla", value=True, key="gran_fallback_v316")
            with g3:
                st.dataframe(default_profiles_dataframe()[["perfil", "material", "D50_mm", "D84_mm", "D90_mm"]], use_container_width=True, hide_index=True)

            gran_metrics = None
            gran_samples = pd.DataFrame()
            gran_diag = []

            if gran_mode == "Excel/CSV granulometría real" and gran_excel is not None:
                try:
                    gran_result = extract_granulometry_from_excel(gran_excel)
                    if gran_result["ok"]:
                        gran_metrics = gran_result["characteristics"]
                        gran_samples = gran_result["samples"]
                        gran_diag = gran_result["diagnostics"]
                        st.success("Granulometría real leída desde Excel/CSV.")
                    else:
                        gran_diag = gran_result.get("diagnostics", [])
                        if use_default_if_fail:
                            gran_metrics = profile_to_characteristics(profile_name)
                            st.warning("No se detectó granulometría válida en Excel/CSV. Se usará perfil tipo.")
                        else:
                            st.error("No se detectó granulometría válida en Excel/CSV.")
                except Exception as exc:
                    gran_diag = [str(exc)]
                    if use_default_if_fail:
                        gran_metrics = profile_to_characteristics(profile_name)
                        st.warning(f"Error leyendo Excel/CSV. Se usará perfil tipo. Detalle: {exc}")
                    else:
                        st.error(str(exc))
            else:
                gran_metrics = profile_to_characteristics(profile_name)

            st.session_state["granulometry_metrics"] = gran_metrics
            st.session_state["granulometry_samples_df"] = gran_samples
            st.session_state["granulometry_method_table_df"] = method_diameter_table(gran_metrics)
            st.session_state["granulometry_characteristic_df"] = characteristic_table(gran_metrics)
            st.session_state["granulometry_curve_df"] = profile_curve_dataframe(gran_metrics)

            d50_default = float(gran_metrics.get("D50_m", 0.045) or 0.045)
            d90_default = float(gran_metrics.get("D90_m", 0.20) or 0.20)

            gg1, gg2, gg3, gg4 = st.columns(4)
            gg1.metric("Perfil / fuente", str(gran_metrics.get("perfil", "granulometría")))
            gg2.metric("D50", f"{gran_metrics.get('D50_mm', float('nan')):.2f} mm")
            gg3.metric("D84", f"{gran_metrics.get('D84_mm', float('nan')):.2f} mm")
            gg4.metric("Confianza", confidence_label(gran_metrics))

            gran_tab1, gran_tab2, gran_tab3, gran_tab4 = st.tabs([
                "Diámetros",
                "Metodologías",
                "Curva granulométrica",
                "Muestras Excel/CSV",
            ])

            with gran_tab1:
                st.dataframe(
                    st.session_state["granulometry_characteristic_df"],
                    use_container_width=True,
                    hide_index=True,
                )

            with gran_tab2:
                st.dataframe(
                    st.session_state["granulometry_method_table_df"],
                    use_container_width=True,
                    hide_index=True,
                )

            with gran_tab3:
                if gran_diag:
                    st.info(" | ".join(gran_diag))
                try:
                    import plotly.express as px
                    curve_df = st.session_state["granulometry_curve_df"]
                    if not curve_df.empty:
                        fig_gr = px.line(
                            curve_df,
                            x="diametro_mm",
                            y="porcentaje_pasa",
                            markers=True,
                            title="Curva granulométrica adoptada",
                            labels={"diametro_mm": "Diámetro [mm]", "porcentaje_pasa": "% que pasa"},
                        )
                        fig_gr.update_xaxes(type="log")
                        st.plotly_chart(fig_gr, use_container_width=True)
                    else:
                        st.info("No hay curva granulométrica disponible.")
                except Exception as exc:
                    st.warning(f"No se pudo graficar curva granulométrica: {exc}")

            with gran_tab4:
                if not gran_samples.empty:
                    st.dataframe(gran_samples, use_container_width=True)
                else:
                    st.info("No se cargaron muestras Excel/CSV. Se usa el perfil tipo seleccionado.")

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            boundary = st.selectbox("Condición aguas abajo", ["tirante_normal", "cota_conocida"], index=0)
        with c6:
            ds_wse = st.number_input("Cota agua aguas abajo [m]", value=0.0, step=0.5, help="Solo se usa si seleccionas cota_conocida.")
        with c7:
            d50 = st.number_input("D50 adoptado [m]", min_value=0.00001, value=d50_default, step=max(d50_default/10, 0.0001), format="%.5f")
        with c8:
            d90 = st.number_input("D90 adoptado [m]", min_value=0.00001, value=d90_default, step=max(d90_default/10, 0.0001), format="%.5f")

        a1, a2, a3, a4 = st.columns(4)
        with a1:
            temp_c = st.number_input("Temperatura agua [°C]", min_value=0.0, max_value=35.0, value=15.0, step=1.0, help="Se usa para densidad del agua en Shields y transporte.")
        with a2:
            d75 = st.number_input("D75 adoptado [m]", min_value=0.00001, value=float(st.session_state.get("granulometry_metrics", {}).get("D75_m", d50_default*1.8) or d50_default*1.8), step=max(d50_default/10, 0.0001), format="%.5f")
        with a3:
            mc_iter = st.selectbox("Monte Carlo iteraciones", [0, 50, 100, 200, 500], index=2, help="0 desactiva incertidumbre Monte Carlo.")
        with a4:
            calibracion_obs = st.file_uploader("Cotas observadas CSV/XLSX opcional", type=["csv", "xlsx", "xls"], help="Opcional: columnas section_id, T_anios, cota_observada_m.")

        if st.button("Calcular perfil hidráulico conectado tipo HEC-RAS", type="primary"):
            try:
                profile_base = hecras_like_steady_profile(
                    st.session_state["sections_df"],
                    st.session_state["section_points_df"],
                    st.session_state["q_design"],
                    n_manning=float(n),
                    downstream_mode=boundary,
                    downstream_wse=float(ds_wse) if boundary == "cota_conocida" else None,
                    slope_energy=float(S),
                    contraction_coeff=float(contr),
                    expansion_coeff=float(expan),
                    alpha=1.0,
                )
                sens_manning = manning_sensitivity(
                    st.session_state["sections_df"],
                    st.session_state["section_points_df"],
                    profile_base,
                    n_manning=float(n),
                    slope_energy=float(S),
                )
                profile = enhance_hydraulic_profile(
                    profile_base,
                    st.session_state["sections_df"],
                    st.session_state["section_points_df"],
                    n_manning=float(n),
                    slope_energy=float(S),
                    manning_sensitivity_df=sens_manning,
                )
                profile = detect_overflow_sections(profile, st.session_state["section_points_df"])
                profile["pendiente_energia"] = float(S)
                overflow_df = summarize_overflow_sections(profile)
                sed_adv = sediment_transport_advanced(
                    profile,
                    d50_m=float(d50),
                    d75_m=float(d75),
                    d90_m=float(d90),
                    slope_energy=float(S),
                    temp_c=float(temp_c),
                )
                zones = classify_sediment_zones(sed_adv)
                zone_summary = summarize_zones(zones)
                qa_hid = hydraulic_qa(
                    st.session_state["sections_df"],
                    st.session_state["section_points_df"],
                    profile,
                    n_manning=float(n),
                    slope_energy=float(S),
                )
                mc_df = monte_carlo_uncertainty(
                    profile,
                    d50_m=float(d50),
                    n_manning=float(n),
                    slope_energy=float(S),
                    n_iter=int(mc_iter),
                ) if int(mc_iter) > 0 else pd.DataFrame()
                conf_df = confidence_report(profile, zones if not zones.empty else sed_adv, qa_hid, sens_manning, mc_df)
                st.session_state["hydraulic_profile_base_df"] = profile_base
                st.session_state["hydraulic_profile_df"] = profile
                st.session_state["hydraulic_df"] = profile
                st.session_state["overflow_sections_df"] = overflow_df
                st.session_state["sediment_df"] = zones if not zones.empty else sed_adv
                st.session_state["sediment_zone_summary_df"] = zone_summary
                st.session_state["qa_hidraulica_df"] = qa_hid
                st.session_state["sensibilidad_manning_df"] = sens_manning
                st.session_state["incertidumbre_mc_df"] = mc_df
                # Acción correctiva 4: calibración automática de Manning con cotas observadas.
                if calibracion_obs is not None:
                    try:
                        if calibracion_obs.name.lower().endswith(".csv"):
                            obs_df = pd.read_csv(calibracion_obs)
                        else:
                            obs_df = pd.read_excel(calibracion_obs)
                        cal = calibrate_manning_from_observed(profile, obs_df)
                        st.session_state["calibracion_v6_df"] = cal.get("calibration", pd.DataFrame())
                        st.session_state["calibracion_v6_reporte_df"] = cal.get("report", pd.DataFrame())
                    except Exception as exc:
                        st.session_state["calibracion_v6_reporte_df"] = pd.DataFrame([{"estado":"error", "detalle":str(exc)}])

                # Acción correctiva 5: rangos de aplicación sedimentológica.
                try:
                    st.session_state["sediment_applicability_v36_df"] = sediment_applicability_ranges(st.session_state["sediment_df"])
                except Exception:
                    st.session_state["sediment_applicability_v36_df"] = pd.DataFrame()

                st.session_state["confianza_v6_df"] = conf_df
                st.session_state["hecras_like_inputs"] = {
                    "modelo": "1D permanente tipo HEC-RAS simplificado",
                    "n_manning": float(n),
                    "pendiente_energia": float(S),
                    "coef_contraccion": float(contr),
                    "coef_expansion": float(expan),
                    "condicion_aguas_abajo": boundary,
                    "cota_aguas_abajo": float(ds_wse) if boundary == "cota_conocida" else None,
                    "orientacion_hidraulica": "auto_by_bed_slope",
                    "D50_m": float(d50),
                    "D84_m": float(st.session_state.get("granulometry_metrics", {}).get("D84_m", float("nan"))),
                    "D90_m": float(d90),
                    "D75_m": float(d75),
                    "temperatura_agua_C": float(temp_c),
                    "monte_carlo_iter": int(mc_iter),
                    "granulometria_fuente": st.session_state.get("granulometry_metrics", {}).get("fuente", "sin_dato"),
                    "granulometria_perfil": st.session_state.get("granulometry_metrics", {}).get("perfil", "sin_dato"),
                    "granulometria_confianza": st.session_state.get("granulometry_metrics", {}).get("confianza_granulometria", None),
                }
                n_fallback = int(profile.get("geometria_fallback", pd.Series(dtype=bool)).fillna(False).sum()) if not profile.empty else 0
                n_tirante_qa = int(profile.get("control_tirante_irreal", pd.Series(dtype=bool)).fillna(False).sum()) if not profile.empty else 0
                n_overflow = int(profile.get("desborde_bool", pd.Series(dtype=bool)).fillna(False).sum()) if not profile.empty and "desborde_bool" in profile.columns else 0
                orient_msg = str(profile.get("orientacion_eje_detectada", pd.Series(["sin_dato"])).dropna().iloc[0]) if not profile.empty and "orientacion_eje_detectada" in profile.columns else "sin_dato"
                if n_fallback > 0:
                    st.warning(
                        f"Perfil hidráulico calculado con {n_fallback} registros usando sección sintética fallback. "
                        "El cálculo continúa, pero esas secciones deben revisarse topográficamente."
                    )
                if n_tirante_qa > 0:
                    st.warning(
                        f"QA hidráulica aplicó control de tirante irreal en {n_tirante_qa} registros. "
                        "Causa probable: eje KMZ dibujado en sentido aguas abajo→aguas arriba, sección transversal insuficiente o condición de borde excesiva. "
                        "Revise las columnas orientacion_eje_detectada, wse_original_m y criterio_control_tirante."
                    )
                if n_overflow > 0:
                    st.warning(f"Se detectaron {n_overflow} registros/secciones con desborde. Revise el panel de secciones con desborde y el perfil longitudinal hidráulico.")
                if n_fallback == 0 and n_tirante_qa == 0:
                    st.success(f"Perfil hidráulico conectado calculado con secciones reales + normativa. Orientación: {orient_msg}.")
            except Exception as exc:
                st.error(str(exc))

        # Panel ejecutivo con formato HidroSed Maestra Integrada.
        if has("sediment_df"):
            st.markdown(
                dashboard_header_html(
                    "Transporte de sedimentos",
                    "Resultados del transporte de sedimentos en el cauce para las condiciones hidráulicas simuladas."
                ),
                unsafe_allow_html=True,
            )
            sed_dash = st.session_state.get("sediment_df")
            hyd_dash = st.session_state.get("hydraulic_profile_df")
            T_dash = select_return_period(sed_dash, preferred=100.0)
            if sed_dash is not None and not sed_dash.empty and "T_anios" in sed_dash.columns:
                T_vals_dash = sorted(pd.to_numeric(sed_dash["T_anios"], errors="coerce").dropna().astype(int).unique().tolist())
                if T_vals_dash:
                    T_dash = st.selectbox(
                        "Periodo de retorno del panel ejecutivo",
                        T_vals_dash,
                        index=min(len(T_vals_dash)-1, T_vals_dash.index(100) if 100 in T_vals_dash else len(T_vals_dash)-1),
                        key="T_maestra_transport_dash",
                    )
            st.markdown(
                kpi_cards_html(transport_kpis(sed_dash, hyd_dash, st.session_state.get("sections_df"), T_dash)),
                unsafe_allow_html=True,
            )
            dash_left, dash_right = st.columns([3.2, 1.0])
            with dash_left:
                st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Perfil longitudinal – Tendencia de erosión/deposición</div>", unsafe_allow_html=True)
                st.plotly_chart(
                    transport_longitudinal_figure(sed_dash, hyd_dash, st.session_state.get("sections_df"), T_dash),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
            with dash_right:
                st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Opciones de visualización</div>", unsafe_allow_html=True)
                st.selectbox("Variable", ["Tendencia de erosión/deposición", "Capacidad de transporte", "Socavación general"], key="maestra_transport_var")
                st.selectbox("Escala vertical", ["Cota del terreno", "Cota de agua", "Fondo socavado"], key="maestra_transport_scale")
                st.markdown("""
                <div style='font-size:.80rem; color:#334155; line-height:1.8'>
                  <b>Tendencia</b><br>
                  <span style='background:#fee2e2; padding:2px 8px; border-radius:7px'>Erosión</span><br>
                  <span style='background:#fef3c7; padding:2px 8px; border-radius:7px'>Equilibrio</span><br>
                  <span style='background:#dcfce7; padding:2px 8px; border-radius:7px'>Deposición</span>
                </div>
                """, unsafe_allow_html=True)
                st.slider("Umbral gráfico", min_value=-0.10, max_value=0.10, value=0.00, step=0.01, key="maestra_transport_threshold")
                st.markdown("</div>", unsafe_allow_html=True)
            cap_col, table_col = st.columns([1.15, 2.15])
            with cap_col:
                st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Capacidad de transporte por periodo de retorno (Q)</div>", unsafe_allow_html=True)
                st.plotly_chart(capacity_by_return_period_figure(sed_dash, st.session_state.get("q_design")), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with table_col:
                st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Resultados por tramo representativo</div>", unsafe_allow_html=True)
                reach_tbl = representative_reach_table(sed_dash, T_dash, n_bins=6)
                if not reach_tbl.empty:
                    st.dataframe(reach_tbl, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay datos suficientes para construir la tabla representativa.")
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(footer_html(modelo="Meyer-Peter & Müller / Shields / HidroSed", src="WGS 84 / UTM", unidades="SI"), unsafe_allow_html=True)
            st.divider()

        if has("hydraulic_profile_df") and has("section_points_df"):
            sec_ids_dash = []
            if has("sections_df") and "section_id" in st.session_state["sections_df"].columns:
                sec_ids_dash = st.session_state["sections_df"]["section_id"].astype(str).tolist()
            elif "section_id" in st.session_state["section_points_df"].columns:
                sec_ids_dash = sorted(st.session_state["section_points_df"]["section_id"].astype(str).unique().tolist())
            if sec_ids_dash:
                st.markdown(
                    dashboard_header_html(
                        "Resultados de socavación",
                        "Visualización de socavación general y local para la sección seleccionada."
                    ),
                    unsafe_allow_html=True,
                )
                rs1, rs2, rs3 = st.columns([1, 1, 2])
                with rs1:
                    sid_scour_dash = st.selectbox("Sección evaluada", sec_ids_dash, index=len(sec_ids_dash)-1, key="sid_scour_maestra_dash")
                with rs2:
                    T_opts_scour_dash = []
                    if has("sediment_df") and "T_anios" in st.session_state["sediment_df"].columns:
                        T_opts_scour_dash = sorted(pd.to_numeric(st.session_state["sediment_df"]["T_anios"], errors="coerce").dropna().astype(int).unique().tolist())
                    T_opts_scour_dash = T_opts_scour_dash or [100]
                    T_scour_dash = st.selectbox(
                        "Periodo de retorno",
                        T_opts_scour_dash,
                        index=min(len(T_opts_scour_dash)-1, T_opts_scour_dash.index(100) if 100 in T_opts_scour_dash else len(T_opts_scour_dash)-1),
                        key="T_scour_maestra_dash",
                    )
                with rs3:
                    st.markdown("<div style='padding-top:1.8rem; color:#64748b'>Vista: sección actual · comparar con adyacentes desde la ventana experta inferior.</div>", unsafe_allow_html=True)
                st.markdown(
                    kpi_cards_html(scour_kpis(sid_scour_dash, T_scour_dash, st.session_state.get("hydraulic_profile_df"), st.session_state.get("sediment_df"))),
                    unsafe_allow_html=True,
                )
                sc_left, sc_right = st.columns([2.55, 1.15])
                with sc_left:
                    st.markdown(f"<div class='hm-panel'><div class='hm-panel-title'>Sección transversal – {sid_scour_dash}</div>", unsafe_allow_html=True)
                    try:
                        fig_sc_dash = _hs_section_review_figure(
                            sid_scour_dash,
                            T_scour_dash,
                            st.session_state.get("section_points_df"),
                            hydraulic_df=st.session_state.get("hydraulic_profile_df"),
                            sediment_df=st.session_state.get("sediment_df"),
                        )
                        st.plotly_chart(fig_sc_dash, use_container_width=True)
                    except Exception as exc:
                        st.info(f"No fue posible generar la sección ejecutiva: {exc}")
                    st.markdown("</div>", unsafe_allow_html=True)
                with sc_right:
                    st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Resumen por sección</div>", unsafe_allow_html=True)
                    sec_summary_dash = _hs_section_summary_table(
                        sid_scour_dash,
                        T_scour_dash,
                        hydraulic_df=st.session_state.get("hydraulic_profile_df"),
                        sediment_df=st.session_state.get("sediment_df"),
                        qa_df=st.session_state.get("qa_hidraulica_df"),
                        sensitivity_df=st.session_state.get("sensibilidad_manning_df"),
                    )
                    if not sec_summary_dash.empty:
                        st.dataframe(sec_summary_dash.head(12), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin resumen disponible para la sección seleccionada.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("<div class='hm-panel'><div class='hm-panel-title'>Perfil del cauce</div>", unsafe_allow_html=True)
                    try:
                        st.plotly_chart(
                            transport_longitudinal_figure(st.session_state.get("sediment_df"), st.session_state.get("hydraulic_profile_df"), st.session_state.get("sections_df"), T_scour_dash),
                            use_container_width=True,
                        )
                    except Exception:
                        st.info("Perfil longitudinal no disponible.")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(footer_html(modelo="HEC-RAS 1D simplificado + socavación preliminar", src="WGS 84 / UTM", unidades="metros"), unsafe_allow_html=True)
                st.divider()

        if has("hydraulic_profile_df"):
            st.subheader("Perfil hidráulico conectado")
            st.dataframe(st.session_state["hydraulic_profile_df"], use_container_width=True)
            if "geometria_status" in st.session_state["hydraulic_profile_df"].columns:
                qa_geom = st.session_state["hydraulic_profile_df"].groupby("geometria_status").size().reset_index(name="registros")
                st.caption("QA geometría de secciones usada en el cálculo")
                st.dataframe(qa_geom, use_container_width=True, hide_index=True)

            st.subheader("Plantilla hidráulica tipo HEC-RAS por sección")
            hprof = st.session_state["hydraulic_profile_df"].copy()
            hec_cols = [c for c in [
                "section_id", "pk_m", "T_anios", "Q_m3s", "cota_fondo_m", "cota_agua_m",
                "tirante_max_m", "tirante_normal_manning_m", "calado_critico_m", "velocidad_m_s",
                "Froude", "energia_especifica_m", "energia_m", "area_m2", "radio_hidraulico_m",
                "margen_desborde", "altura_desborde_max_m"
            ] if c in hprof.columns]
            if hec_cols:
                st.dataframe(hprof[hec_cols], use_container_width=True)

            st.subheader("Perfil longitudinal hidráulico")
            hg1, hg2, hg3 = st.columns([1.2, 1.2, 1.0])
            with hg1:
                T_opts_long = sorted(pd.to_numeric(hprof["T_anios"], errors="coerce").dropna().astype(int).unique().tolist()) if "T_anios" in hprof.columns else [100]
                T_long = st.selectbox("Periodo de retorno para perfil hidráulico", T_opts_long, index=min(len(T_opts_long)-1, T_opts_long.index(100) if 100 in T_opts_long else len(T_opts_long)-1), key="T_long_hydraulic")
            with hg2:
                mode_long = st.selectbox(
                    "Fenómeno hidráulico a mostrar",
                    ["Lámina de agua y desborde", "yn / yc / energía", "Velocidad / Froude", "Tensión de corte / energía"],
                    index=0,
                    key="mode_long_hydraulic",
                )
            with hg3:
                vertical_ref = st.selectbox("Escala vertical", ["Cota del terreno", "Cota de agua"], index=0, key="vertical_ref_hydraulic")
            try:
                fig_hlong = create_hydraulic_longitudinal_figure(hprof, T_select=T_long, variable_mode=mode_long, vertical_reference=vertical_ref)
                st.session_state["hydraulic_longitudinal_fig"] = fig_hlong
                st.plotly_chart(fig_hlong, use_container_width=True)
            except Exception as exc:
                st.info(f"No fue posible graficar el perfil longitudinal hidráulico: {exc}")

            if has("overflow_sections_df") and not st.session_state["overflow_sections_df"].empty:
                st.subheader("Secciones y tramos con desborde")
                st.dataframe(st.session_state["overflow_sections_df"], use_container_width=True, hide_index=True)
            else:
                st.info("No se detectaron secciones con desborde para los resultados actuales.")

            qa_tabs = st.tabs(["QA hidráulica", "Sensibilidad Manning ±20%", "Incertidumbre MC", "Confianza"])
            with qa_tabs[0]:
                if has("qa_hidraulica_df"):
                    st.dataframe(st.session_state["qa_hidraulica_df"], use_container_width=True, hide_index=True)
            with qa_tabs[1]:
                if has("sensibilidad_manning_df"):
                    st.dataframe(st.session_state["sensibilidad_manning_df"], use_container_width=True, hide_index=True)
            with qa_tabs[2]:
                if has("incertidumbre_mc_df") and not st.session_state["incertidumbre_mc_df"].empty:
                    st.dataframe(st.session_state["incertidumbre_mc_df"], use_container_width=True, hide_index=True)
                else:
                    st.info("Monte Carlo desactivado o sin resultados.")
            with qa_tabs[3]:
                if has("confianza_v6_df"):
                    st.dataframe(st.session_state["confianza_v6_df"], use_container_width=True, hide_index=True)
                    try:
                        st.metric("Confianza técnica hidráulica-sedimentológica", f"{float(st.session_state['confianza_v6_df'].iloc[0]['puntaje_confianza_1_10']):.1f}/10")
                    except Exception:
                        pass

            corr_h_tabs = st.tabs(["Calibración Manning", "Rangos sedimentos"])
            with corr_h_tabs[0]:
                if has("calibracion_v6_reporte_df"):
                    st.dataframe(st.session_state["calibracion_v6_reporte_df"], use_container_width=True, hide_index=True)
                if has("calibracion_v6_df"):
                    st.dataframe(st.session_state["calibracion_v6_df"], use_container_width=True, hide_index=True)
                else:
                    st.info("Cargue cotas observadas en el módulo hidráulico para calibrar Manning.")
            with corr_h_tabs[1]:
                if has("sediment_applicability_v36_df"):
                    st.dataframe(st.session_state["sediment_applicability_v36_df"], use_container_width=True, hide_index=True)
                else:
                    st.info("Los rangos sedimentológicos se generan junto con el cálculo hidráulico/sedimentos.")

            try:
                import plotly.express as px
                prof = st.session_state["hydraulic_profile_df"]
                fig = px.line(
                    prof,
                    x="pk_m",
                    y="cota_agua_m",
                    color="T_anios",
                    markers=True,
                    title="Perfil de cota de agua por periodo de retorno",
                    labels={"pk_m": "PK [m]", "cota_agua_m": "Cota agua [m]"},
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

            st.download_button(
                "Descargar perfil hidráulico CSV",
                st.session_state["hydraulic_profile_df"].to_csv(index=False).encode("utf-8"),
                file_name="perfil_hidraulico_tipo_hecras.csv",
                mime="text/csv",
            )

        if has("sediment_df"):
            st.subheader("Transporte, socavación, erosión y depositación")
            sed_view = st.session_state["sediment_df"]
            st.dataframe(sed_view, use_container_width=True)
            if has("sediment_zone_summary_df"):
                st.subheader("Resumen de zonas críticas")
                st.dataframe(st.session_state["sediment_zone_summary_df"], use_container_width=True)
            try:
                import plotly.express as px
                if {"pk_m", "socavacion_general_m", "T_anios", "zona_hidrosed"}.issubset(sed_view.columns):
                    fig_scour = px.scatter(
                        sed_view,
                        x="pk_m",
                        y="socavacion_general_m",
                        color="zona_hidrosed",
                        size="indice_riesgo_sedimento" if "indice_riesgo_sedimento" in sed_view.columns else None,
                        facet_col="T_anios" if sed_view["T_anios"].nunique() <= 4 else None,
                        title="Zonas de socavación, transporte y depositación por PK",
                    )
                    st.plotly_chart(fig_scour, use_container_width=True)
                if {"pk_m", "Qs_total_m3_s", "T_anios", "tendencia_sedimentaria"}.issubset(sed_view.columns):
                    fig_qs = px.line(
                        sed_view,
                        x="pk_m",
                        y="Qs_total_m3_s",
                        color="T_anios",
                        line_group="tendencia_sedimentaria",
                        title="Transporte de sedimentos longitudinal",
                    )
                    st.plotly_chart(fig_qs, use_container_width=True)
            except Exception:
                pass
            st.download_button(
                "Descargar socavación/sedimentos CSV",
                st.session_state["sediment_df"].to_csv(index=False).encode("utf-8"),
                file_name="socavacion_sedimentos.csv",
                mime="text/csv",
            )

        st.divider()
        st.subheader("Ventana experta de sección seleccionada")
        st.caption("Revisión individual: sección transversal, lámina de agua, área mojada, socavación, depositación, hidráulica, sedimentos y QA.")

        if has("section_points_df") and (has("hydraulic_profile_df") or has("sediment_df")):
            sec_ids_review = []
            if has("sections_df") and "section_id" in st.session_state["sections_df"].columns:
                sec_ids_review = st.session_state["sections_df"]["section_id"].astype(str).tolist()
            elif "section_id" in st.session_state["section_points_df"].columns:
                sec_ids_review = sorted(st.session_state["section_points_df"]["section_id"].astype(str).unique().tolist())
            T_opts_review = []
            for _dfkey in ["hydraulic_profile_df", "sediment_df"]:
                _df = st.session_state.get(_dfkey, pd.DataFrame())
                if hasattr(_df, "empty") and not _df.empty and "T_anios" in _df.columns:
                    T_opts_review += pd.to_numeric(_df["T_anios"], errors="coerce").dropna().astype(int).unique().tolist()
            T_opts_review = sorted(set(T_opts_review)) or [100]
            overflow_only_ids = []
            if has("overflow_sections_df") and not st.session_state["overflow_sections_df"].empty:
                overflow_only_ids = st.session_state["overflow_sections_df"]["section_id"].astype(str).unique().tolist()

            rw0, rw1, rw2, rw3 = st.columns([1.1, 1.0, 1.0, 2.0])
            with rw0:
                only_overflow = st.checkbox("Solo secciones con desborde", value=False, key="only_overflow_review")
                if only_overflow and overflow_only_ids:
                    sec_ids_review = [sid for sid in sec_ids_review if sid in overflow_only_ids]
                elif only_overflow and not overflow_only_ids:
                    st.info("No hay desbordes detectados para filtrar.")
            if not sec_ids_review:
                st.info("No hay secciones disponibles para la revisión con el filtro actual.")
            else:
                with rw1:
                    sid_review = st.selectbox("Sección a revisar", sec_ids_review, key="sid_review_v37")
                with rw2:
                    T_review = st.selectbox("Periodo retorno", T_opts_review, index=min(len(T_opts_review)-1, T_opts_review.index(100) if 100 in T_opts_review else len(T_opts_review)-1), key="T_review_v37")
                with rw3:
                    st.info("Azul: agua · Rojo: socavación · Verde: depositación · Café: terreno natural")

                try:
                    fig_section = _hs_section_review_figure(
                        sid_review,
                        T_review,
                        st.session_state.get("section_points_df"),
                        hydraulic_df=st.session_state.get("hydraulic_profile_df"),
                        sediment_df=st.session_state.get("sediment_df"),
                    )
                    st.plotly_chart(fig_section, use_container_width=True)
                    summary_section = _hs_section_summary_table(
                        sid_review,
                        T_review,
                        hydraulic_df=st.session_state.get("hydraulic_profile_df"),
                        sediment_df=st.session_state.get("sediment_df"),
                        qa_df=st.session_state.get("qa_hidraulica_df"),
                        sensitivity_df=st.session_state.get("sensibilidad_manning_df"),
                    )
                    csum1, csum2 = st.columns([1, 1])
                    with csum1:
                        st.dataframe(summary_section, use_container_width=True, hide_index=True)
                    with csum2:
                        if has("sediment_applicability_v36_df"):
                            app_sed = st.session_state["sediment_applicability_v36_df"]
                            if "section_id" in app_sed.columns:
                                app_sed = app_sed[app_sed["section_id"].astype(str) == str(sid_review)]
                            st.dataframe(app_sed, use_container_width=True, hide_index=True)
                        else:
                            st.info("No hay tabla de rangos sedimentológicos para esta sección.")
                except Exception as exc:
                    st.warning(f"No se pudo generar la revisión de sección: {exc}")
        else:
            st.info("Calcule primero el perfil hidráulico/sedimentos para activar esta ventana.")

        st.divider()
        st.subheader("Perfil longitudinal 3D con secciones y fenómenos hidráulicos")
        if has("sections_df") and has("section_points_df"):
            v1, v2, v3, v4, v5 = st.columns(5)
            with v1:
                vex = st.slider("Exageración vertical", min_value=0.5, max_value=10.0, value=1.5, step=0.5)
            with v2:
                show_water = st.checkbox("Mostrar lámina de agua", value=True)
            with v3:
                show_scour = st.checkbox("Mostrar socavación", value=True)
            with v4:
                show_depo = st.checkbox("Mostrar depositación", value=True)
            with v5:
                view_3d = st.selectbox(
                    "Vista inicial 3D",
                    list(VIEW_CAMERAS_3D.keys()),
                    index=list(VIEW_CAMERAS_3D.keys()).index("Isométrica"),
                    help="La vista fija solo define la cámara inicial; la rotación libre sigue activa."
                )

            if st.button("Generar perfil longitudinal 3D", type="primary"):
                try:
                    fig3d = create_3d_profile_figure(
                        st.session_state["sections_df"],
                        st.session_state["section_points_df"],
                        hydraulic_df=st.session_state.get("hydraulic_profile_df"),
                        sediment_df=st.session_state.get("sediment_df"),
                        vertical_exaggeration=float(vex),
                        show_water=bool(show_water),
                        show_scour=bool(show_scour),
                        show_deposition=bool(show_depo),
                        initial_view=str(view_3d),
                    )
                    st.session_state["profile_3d_fig"] = fig3d
                    html3d = figure_to_html_bytes(fig3d)
                    st.session_state["profile_3d_html"] = html3d
                    save_bytes("perfil_longitudinal_3d_hidrosed.html", html3d)
                    st.success("Perfil 3D generado.")
                except Exception as exc:
                    st.error(str(exc))

            if has("profile_3d_fig"):
                st.caption("Controles de vista fija: planta/superior, lateral, aguas arriba, aguas abajo e isométrica. La rotación libre interactiva se mantiene.")
                view_cols = st.columns(6)
                for i, vname in enumerate(["Planta / superior", "Lateral", "Aguas arriba", "Aguas abajo", "Isométrica", "Rotación libre"]):
                    if view_cols[i].button(vname, key=f"btn_view_{vname}"):
                        st.session_state["profile_3d_fig"] = apply_3d_view(st.session_state["profile_3d_fig"], vname)
                        st.session_state["profile_3d_html"] = figure_to_html_bytes(st.session_state["profile_3d_fig"])
                st.plotly_chart(st.session_state["profile_3d_fig"], use_container_width=True)
            if has("profile_3d_html"):
                st.download_button(
                    "Descargar perfil 3D HTML",
                    st.session_state["profile_3d_html"],
                    file_name="perfil_longitudinal_3d_hidrosed.html",
                    mime="text/html",
                )
        else:
            st.info("Genera primero las secciones transversales.")



        st.divider()
        st.subheader("Galería técnica de referencia visual")
        st.caption("Imágenes de referencia incorporadas para orientar la lectura de secciones, socavación, transporte y plataforma.")
        img_cols = st.columns(2)
        with img_cols[0]:
            st.image("assets/dashboard_maestra_transporte_sedimentos.png", caption="Referencia aplicada: dashboard de transporte de sedimentos", use_container_width=True)
        with img_cols[1]:
            st.image("assets/dashboard_maestra_resultados_socavacion.png", caption="Referencia aplicada: resultados de socavación", use_container_width=True)
        with img_cols[0]:
            st.image("assets/visualizacion_3d_de_cauce_y_secciones.png", caption="Referencia: visualización 3D de cauce y secciones", use_container_width=True)
        with img_cols[1]:
            st.image("assets/HidroSed_Plataforma_Visual.png", caption="Referencia: plataforma visual HidroSed", use_container_width=True)

        st.warning(
            "Nota técnica: este motor aplica flujo permanente 1D con balance de energía, "
            "pero no reemplaza una modelación HEC‑RAS oficial calibrada. Para diseño final se deben revisar "
            "condiciones de borde, coeficientes, régimen, puentes/alcantarillas, llanuras de inundación y calibración."
        )

with tabs[8]:
    st.header("9 · Lámina cartográfica y exportación final")

    st.subheader("Lámina cartográfica preliminar")
    if not has("dem_path"):
        st.warning("Para generar la lámina necesitas al menos DEM. Para mejor salida agrega cuenca, curvas, eje y morfometría.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            map_title = st.text_input("Título de lámina", value="HidroSed · Delimitación de cuenca y curvas de nivel")
        with c2:
            map_contour_interval = st.selectbox("Curvas visibles en lámina [m]", [1, 2, 5, 10, 20, 25, 50, 100, 200], index=3)

        if st.button("Generar lámina cartográfica PNG", type="primary"):
            try:
                png = make_cartographic_sheet(
                    st.session_state["dem_path"],
                    basin_kml_bytes=_active_basin_kml(),
                    axis_line=_ensure_axis_available(silent=True)[0],
                    control_point=st.session_state.get("control_point"),
                    metrics=_active_basin_metrics(),
                    title=map_title,
                    contour_interval=float(map_contour_interval),
                )
                st.session_state["cartographic_png"] = png
                save_bytes("lamina_cartografica.png", png)
                st.success("Lámina cartográfica generada.")
            except Exception as exc:
                st.error(str(exc))

        if has("cartographic_png"):
            st.image(st.session_state["cartographic_png"], caption="Lámina cartográfica preliminar", use_container_width=True)
            st.download_button("Descargar lámina PNG", st.session_state["cartographic_png"], file_name="lamina_cartografica_hidrosed.png", mime="image/png")

    st.divider()
    _render_hidrosed_kmz_export_panel()

    st.divider()
    st.subheader("Diagnóstico técnico del proyecto")
    with st.expander("Ver diagnóstico técnico y trazabilidad", expanded=False):
        _render_diagnostics_panel()

    st.divider()
    st.subheader("Descargas técnicas avanzadas / opcionales")
    st.caption("La descarga principal recomendada es la Exportación KMZ HidroSed de dos archivos. Estas salidas se mantienen por compatibilidad con versiones anteriores.")
    if has("profile_3d_html"):
        st.download_button(
            "Descargar perfil longitudinal 3D HTML",
            st.session_state["profile_3d_html"],
            file_name="perfil_longitudinal_3d_hidrosed.html",
            mime="text/html",
        )


    if has("basin_metrics_df"):
        st.download_button(
            "Descargar morfometría CSV",
            st.session_state["basin_metrics_df"].to_csv(index=False).encode("utf-8"),
            file_name="morfometria_cuenca.csv",
            mime="text/csv",
        )
    if has("basin_kmz"):
        st.download_button("Descargar cuenca delimitada KMZ", st.session_state["basin_kmz"], file_name="cuenca_delimitada.kmz", mime="application/vnd.google-earth.kmz")
    if has("basin_metrics"):
        st.download_button("Descargar morfometría JSON", json.dumps(st.session_state["basin_metrics"], ensure_ascii=False, indent=2).encode("utf-8"), file_name="morfometria_cuenca.json", mime="application/json")
    if has("section_qc_report_df"):
        st.download_button(
            "Descargar QA secciones CSV",
            st.session_state["section_qc_report_df"].to_csv(index=False).encode("utf-8"),
            file_name="qa_secciones.csv",
            mime="text/csv",
        )
    if has("topo_support_report_df"):
        st.download_button(
            "Descargar apoyo topográfico CSV",
            st.session_state["topo_support_report_df"].to_csv(index=False).encode("utf-8"),
            file_name="apoyo_topografico_secciones.csv",
            mime="text/csv",
        )
    if has("sections_df") and has("section_points_df"):
        xlsx = sections_excel_bytes(
            st.session_state["sections_df"],
            st.session_state["section_points_df"],
            st.session_state.get("q_design"),
            st.session_state.get("hydraulic_df"),
            st.session_state.get("sediment_df"),
        )
        st.download_button("Descargar Excel maestro", xlsx, file_name="HidroSed_Resultados_Maestros.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Excel avanzado v6: agrega confianza, sensibilidad, incertidumbre y QA hidráulica.
        if has("hydraulic_profile_df") or has("qa_hidraulica_df"):
            adv_buf = io.BytesIO()
            with pd.ExcelWriter(adv_buf, engine="xlsxwriter") as writer:
                if has("sections_df"):
                    st.session_state["sections_df"].to_excel(writer, sheet_name="Secciones", index=False)
                if has("section_points_df"):
                    st.session_state["section_points_df"].head(200000).to_excel(writer, sheet_name="Puntos_seccion", index=False)
                if has("hydraulic_profile_df"):
                    st.session_state["hydraulic_profile_df"].to_excel(writer, sheet_name="Perfil_HECRAS_v6", index=False)
                if has("sediment_df"):
                    st.session_state["sediment_df"].to_excel(writer, sheet_name="Sedimentos_v6", index=False)
                if has("qa_hidraulica_df"):
                    st.session_state["qa_hidraulica_df"].to_excel(writer, sheet_name="QA_Hidraulica_v6", index=False)
                if has("sensibilidad_manning_df"):
                    st.session_state["sensibilidad_manning_df"].to_excel(writer, sheet_name="Sensibilidad_Manning", index=False)
                if has("incertidumbre_mc_df"):
                    st.session_state["incertidumbre_mc_df"].to_excel(writer, sheet_name="Incertidumbre_MC_v6", index=False)
                if has("confianza_v6_df"):
                    st.session_state["confianza_v6_df"].to_excel(writer, sheet_name="Confianza_v6", index=False)
                if has("normativa_hidrosed_df"):
                    st.session_state["normativa_hidrosed_df"].to_excel(writer, sheet_name="Normativa", index=False)
                if has("hydrology_all_methods"):
                    st.session_state["hydrology_all_methods"].to_excel(writer, sheet_name="Hidrologia_metodos", index=False)
                if has("hydrology_normative_methods_v35"):
                    st.session_state["hydrology_normative_methods_v35"].to_excel(writer, sheet_name="Hidrologia_DGA_MC_v35", index=False)
                if has("idf_normativa_v35"):
                    st.session_state["idf_normativa_v35"].to_excel(writer, sheet_name="IDF_v35", index=False)
                if has("pmax_123_v35"):
                    st.session_state["pmax_123_v35"].to_excel(writer, sheet_name="Pmax123_v35", index=False)
                if has("hidrogramas_v35"):
                    st.session_state["hidrogramas_v35"].to_excel(writer, sheet_name="Hidrogramas_v35", index=False)
                if has("caudales_minimos_v35"):
                    st.session_state["caudales_minimos_v35"].to_excel(writer, sheet_name="Caudales_minimos_v35", index=False)
                if has("qa_hidrologia_v35"):
                    st.session_state["qa_hidrologia_v35"].to_excel(writer, sheet_name="QA_Hidrologia_v35", index=False)
                if has("cumplimiento_hidrologia_v35"):
                    st.session_state["cumplimiento_hidrologia_v35"].to_excel(writer, sheet_name="Cumplimiento_Hidro_v35", index=False)
                if has("flow_frequency_v36"):
                    st.session_state["flow_frequency_v36"].get("frequency", pd.DataFrame()).to_excel(writer, sheet_name="Frecuencia_QT_v36", index=False)
                    st.session_state["flow_frequency_v36"].get("annual_max", pd.DataFrame()).to_excel(writer, sheet_name="MaxAnuales_Q_v36", index=False)
                if has("pluvio_fill_v36"):
                    st.session_state["pluvio_fill_v36"].get("report", pd.DataFrame()).to_excel(writer, sheet_name="Relleno_P24_reporte", index=False)
                    st.session_state["pluvio_fill_v36"].get("filled", pd.DataFrame()).to_excel(writer, sheet_name="Relleno_P24_serie", index=False)
                if has("station_isoyeta_validation_v36"):
                    st.session_state["station_isoyeta_validation_v36"].get("validation", pd.DataFrame()).to_excel(writer, sheet_name="Estacion_Isoyeta_v36", index=False)
                if has("calibracion_v6_df"):
                    st.session_state["calibracion_v6_df"].to_excel(writer, sheet_name="Calibracion_v6", index=False)
                if has("sediment_applicability_v36_df"):
                    st.session_state["sediment_applicability_v36_df"].to_excel(writer, sheet_name="Rangos_Sedimentos_v36", index=False)
                if has("unit_tests_v36_df"):
                    st.session_state["unit_tests_v36_df"].to_excel(writer, sheet_name="Pruebas_v36", index=False)
                if has("regional_coeffs_v36"):
                    st.session_state["regional_coeffs_v36"].to_excel(writer, sheet_name="Coef_Regionales_v36", index=False)
            st.download_button(
                "Descargar Excel avanzado HEC-RAS/QA v6",
                adv_buf.getvalue(),
                file_name="HidroSed_HECRAS_QA_v6.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        memoria_txt = generate_calculation_memory_text({
            "fuentes": {
                "P24": st.session_state.get("p24_10_fuente", "sin_dato"),
                "Isoyetas": "data/isoyetas/Precipitaciones_Maximas_Diarias.kmz",
                "Base DGA": "data/preloaded/*.zip",
            },
            "parametros": {
                "hidrologia": st.session_state.get("hydrology_inputs", {}),
                "hidraulica": st.session_state.get("hecras_like_inputs", {}),
            },
            "qa": {
                "normativa": st.session_state.get("normativa_hidrosed_score", "sin_dato"),
                "confianza_hidraulica": st.session_state.get("confianza_v6_df", pd.DataFrame()).to_dict("records") if has("confianza_v6_df") else "sin_dato",
            },
            "dictamen": "Memoria automática generada por HidroSed SedGran v3.7.3 Correctivas. Debe revisarse y firmarse por profesional responsable.",
        })
        st.download_button(
            "Descargar memoria de cálculo automática TXT",
            memoria_txt.encode("utf-8"),
            file_name="Memoria_Calculo_HidroSed_v36.txt",
            mime="text/plain",
        )
    if has("contours_kmz"):
        st.download_button("Descargar curvas KMZ", st.session_state["contours_kmz"], file_name="curvas_nivel.kmz")
    if has("axis_kmz_path"):
        p = Path(st.session_state["axis_kmz_path"])
        if p.exists():
            st.download_button("Descargar eje KMZ", p.read_bytes(), file_name="eje_cauce.kmz")
    if has("dem_bytes"):
        st.download_button("Descargar DEM GeoTIFF", st.session_state["dem_bytes"], file_name="dem_hidrosed.tif", mime="image/tiff")

    resumen = {
        "control_point": st.session_state.get("control_point"),
        "basin_metrics": st.session_state.get("basin_metrics"),
        "hydrology_inputs": st.session_state.get("hydrology_inputs"),
        "n_sections": int(len(st.session_state["sections_df"])) if has("sections_df") else 0,
        "n_design_flows": int(len(st.session_state["q_design"])) if has("q_design") else 0,
    }
    st.download_button(
        "Descargar resumen maestro JSON",
        json.dumps(resumen, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="resumen_maestro_hidrosed.json",
        mime="application/json",
    )

    st.info("Versión SedGran v3.4: flujo maestro completo configurado para cuencas hasta 10.000 km², curvas mínimo 1 m y perfil hidráulico conectado. Para diseño final se recomienda validar eje, cuenca, secciones y parámetros con antecedentes topográficos/hidrométricos oficiales.")



with tabs[9]:
    st.header("10 · Modo Supremo: rugosidad, granulometría, sección trapezoidal y QA")

    st.subheader("Control normativo y trazabilidad técnica")
    st.caption("Matriz automática basada en los insumos disponibles: isoyetas/P24, métodos hidrológicos, geometría, hidráulica, granulometría y sedimentos.")
    if has("normativa_hidrosed_df"):
        st.metric("Puntaje normativo", f"{float(st.session_state.get('normativa_hidrosed_score', 0.0)):.1f}/10")
        st.dataframe(st.session_state["normativa_hidrosed_df"], use_container_width=True, hide_index=True)
    else:
        st.info("La matriz normativa se genera al calcular la hidrología reforzada. Si se usan isoyetas, la P24 queda con trazabilidad.")

    st.markdown(
        """
Este módulo permite avanzar incluso cuando la topografía no entrega secciones suficientes. La app separa claramente resultados **reales/topográficos** de resultados **estimados**.

```text
rugosidad manual / tabla / Cowan / Strickler
↓
sección real o sección trapezoidal estimada
↓
granulometría georreferenciada KMZ
↓
transferencia hidrológica dual
↓
semáforo de confianza
```
"""
    )

    st.subheader("A · Rugosidad avanzada del cauce")
    r1, r2, r3 = st.columns(3)
    with r1:
        rough_mode = st.selectbox("Modo rugosidad", ["manual", "tabla", "cowan", "granulometria/strickler"], index=2)
    with r2:
        cat = st.selectbox("Tipo de cauce", list(ROUGHNESS_TABLE["categoria"]), index=list(ROUGHNESS_TABLE["categoria"]).index("grava_media"))
    with r3:
        has_cal = st.checkbox("Existe calibración nivel/caudal", value=False)

    if rough_mode == "manual":
        a,b,c = st.columns(3)
        with a: n_left = st.number_input("n margen izquierda", min_value=0.010, max_value=0.200, value=0.045, step=0.005, format="%.3f")
        with b: n_ch = st.number_input("n cauce principal", min_value=0.010, max_value=0.200, value=0.038, step=0.005, format="%.3f")
        with c: n_right = st.number_input("n margen derecha", min_value=0.010, max_value=0.200, value=0.045, step=0.005, format="%.3f")
        rough_df = compose_roughness_manual(n_left, n_ch, n_right)
        n_adopt = float(n_ch)
        conf_n = roughness_confidence("manual", has("granulometry_assigned_df"), has_cal, zones=3)
    elif rough_mode == "tabla":
        rough_df = pd.DataFrame([table_n(cat)])
        n_adopt = float(rough_df["n_manning"].iloc[0])
        conf_n = roughness_confidence("tabla", has("granulometry_assigned_df"), has_cal, zones=1)
    elif rough_mode == "cowan":
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        with c1: material = st.selectbox("Material", list(COWAN_FACTORS["n0_material"].keys()), index=3)
        with c2: irr = st.selectbox("Irregularidad", list(COWAN_FACTORS["n1_irregularidad"].keys()), index=2)
        with c3: varsec = st.selectbox("Variación sección", list(COWAN_FACTORS["n2_variacion_seccion"].keys()), index=1)
        with c4: obs = st.selectbox("Obstrucciones", list(COWAN_FACTORS["n3_obstrucciones"].keys()), index=1)
        with c5: veg = st.selectbox("Vegetación", list(COWAN_FACTORS["n4_vegetacion"].keys()), index=1)
        with c6: sinu = st.selectbox("Sinuosidad", list(COWAN_FACTORS["m_sinuosidad"].keys()), index=1)
        rough_df = pd.DataFrame([cowan_n(material, irr, varsec, obs, veg, sinu)])
        n_adopt = float(rough_df["n_manning"].iloc[0])
        conf_n = roughness_confidence("cowan", has("granulometry_assigned_df"), has_cal, zones=3)
    else:
        d50_auto = 0.045
        d84_auto = 0.090
        if has("granulometry_assigned_df") and "D50_m" in st.session_state["granulometry_assigned_df"].columns:
            d50_auto = float(pd.to_numeric(st.session_state["granulometry_assigned_df"]["D50_m"], errors="coerce").median())
        if has("granulometry_assigned_df") and "D84_m" in st.session_state["granulometry_assigned_df"].columns:
            d84_auto = float(pd.to_numeric(st.session_state["granulometry_assigned_df"]["D84_m"], errors="coerce").median())
        rough_df = suggested_roughness(cat, d50_m=d50_auto, d84_m=d84_auto)
        n_adopt = float(rough_df["n_adoptado_recomendado"].dropna().iloc[0])
        conf_n = roughness_confidence("cowan", True, has_cal, zones=3)

    if st.button("Adoptar rugosidad", type="primary"):
        st.session_state["roughness_df"] = rough_df
        st.session_state["n_manning_adoptado"] = n_adopt
        st.session_state["roughness_confidence"] = conf_n
        st.success(f"Rugosidad adoptada n = {n_adopt:.3f} · confianza {conf_n['confianza_rugosidad']}/10")
    st.dataframe(rough_df, use_container_width=True)
    st.json(conf_n)

    st.divider()
    st.subheader("B · Granulometría georreferenciada con KMZ")
    g1, g2 = st.columns(2)
    with g1:
        gran_file = st.file_uploader("Tabla granulométrica CSV/XLSX", type=["csv", "xlsx"], key="gran_table")
    with g2:
        gran_kmz = st.file_uploader("KMZ/KML puntos de muestras", type=["kmz", "kml"], key="gran_kmz")
    if st.button("Leer y validar granulometría"):
        try:
            if gran_file is None:
                raise ValueError("Debes cargar una tabla granulométrica.")
            if gran_file.name.lower().endswith(".csv"):
                gdf = pd.read_csv(gran_file)
            else:
                gdf = pd.read_excel(gran_file)
            gdf = normalize_granulometry_table(gdf)
            if gran_kmz is not None:
                kmltxt = read_kmz_or_kml_to_text(gran_kmz)
                pts = parse_granulometry_points(kmltxt)
                gdf = gdf.merge(pts, on="id_muestra", how="left")
            val = validate_granulometry(gdf)
            st.session_state["granulometry_df"] = gdf
            st.session_state["granulometry_validation_df"] = val
            if has("sections_df"):
                assigned = assign_granulometry_to_sections(st.session_state["sections_df"], gdf)
                st.session_state["granulometry_assigned_df"] = assigned
            st.success("Granulometría leída, validada y asignada por sección si existen secciones.")
        except Exception as exc:
            st.error(str(exc))
    if has("granulometry_df"):
        st.dataframe(st.session_state["granulometry_df"], use_container_width=True)
    if has("granulometry_validation_df"):
        st.dataframe(st.session_state["granulometry_validation_df"], use_container_width=True)
    if has("granulometry_assigned_df"):
        st.subheader("Granulometría asignada por sección")
        st.dataframe(st.session_state["granulometry_assigned_df"], use_container_width=True)

    st.divider()
    st.subheader("C · Sección trapezoidal estimada de respaldo")
    st.caption("Usar cuando no existan suficientes secciones reales + normativa. El informe debe marcar estos cálculos como preliminares/estimativos.")
    t1,t2,t3,t4 = st.columns(4)
    with t1:
        btm = st.number_input("Ancho fondo [m]", min_value=0.1, value=6.0, step=0.5)
        reach_len = st.number_input("Longitud tramo [m]", min_value=10.0, value=1000.0, step=100.0)
    with t2:
        dep = st.number_input("Profundidad geométrica [m]", min_value=0.1, value=2.0, step=0.2)
        sep = st.number_input("Separación secciones [m]", min_value=5.0, value=100.0, step=10.0)
    with t3:
        zl = st.number_input("Talud izquierdo H:V", min_value=0.0, value=1.5, step=0.25)
        zr = st.number_input("Talud derecho H:V", min_value=0.0, value=1.5, step=0.25)
    with t4:
        slp = st.number_input("Pendiente longitudinal [m/m]", min_value=0.00001, value=float(st.session_state.get("hydrology_inputs", {}).get("slope", 0.008)), step=0.001, format="%.5f")
        z0 = st.number_input("Cota fondo inicial [m]", value=100.0, step=1.0)
    if st.button("Generar secciones trapezoidales estimadas", type="primary"):
        sec_syn, pts_syn = generate_trapezoid_reach_sections(reach_len, sep, btm, dep, zl, zr, slp, z0_m=z0)
        st.session_state["sections_df"] = sec_syn
        st.session_state["section_points_df"] = pts_syn
        st.session_state["sections_mode"] = "trapezoidal_estimado"
        st.success(f"Secciones trapezoidales generadas: {len(sec_syn)}. El cálculo queda marcado como preliminar estimativo.")
    if has("q_design"):
        qvals = list(pd.to_numeric(st.session_state["q_design"]["Q_m3s"], errors="coerce").dropna())
        if qvals:
            cap = trapezoid_capacity_table(qvals, btm, dep, zl, zr, slp, float(st.session_state.get("n_manning_adoptado", 0.040)))
            st.subheader("Capacidad hidráulica trapezoidal preliminar")
            st.dataframe(cap, use_container_width=True)

    st.divider()
    st.subheader("D · Transferencia hidrológica dual área-altitud-distancia")
    h1,h2,h3,h4 = st.columns(4)
    with h1:
        q_est = st.number_input("Q estación [m³/s]", min_value=0.0, value=10.0, step=1.0)
        a_punto = st.number_input("Área punto [km²]", min_value=0.001, value=float(st.session_state.get("basin_metrics", {}).get("area_km2", 50.0) or 50.0), step=1.0)
    with h2:
        a_est = st.number_input("Área estación [km²]", min_value=0.001, value=60.0, step=1.0, help="Si se calculó desde DEM, ingrese aquí el área obtenida.")
        b_exp = st.number_input("Exponente área b", min_value=0.30, max_value=1.20, value=0.75, step=0.05)
    with h3:
        alt_p = st.number_input("Altitud punto [m]", value=500.0, step=50.0)
        alt_e = st.number_input("Altitud estación [m]", value=450.0, step=50.0)
    with h4:
        dist_km = st.number_input("Distancia estación-punto [km]", min_value=0.0, value=20.0, step=5.0)
    if st.button("Calcular transferencia hidrológica"):
        tr = transfer_flow_area_altitude_distance(q_est, a_punto, a_est, alt_p, alt_e, dist_km, b_exp)
        st.session_state["hydrologic_transfer"] = tr
        st.success(f"Q transferido = {tr.get('Q_transferido_m3s', float('nan')):.2f} m³/s · confianza {tr.get('confianza_transferencia', 0)}/10")
    if has("hydrologic_transfer"):
        st.json(st.session_state["hydrologic_transfer"])

    st.divider()
    st.subheader("E · Semáforo maestro de confianza")
    scores = {
        "DEM / descarga": 8.8 if has("dem_path") else 6.5,
        "Cuenca / morfometría": 8.9 if has("basin_metrics") else 6.0,
        "Curvas / eje": 8.8 if has("contours_kmz") and has("axis_line") else 6.5,
        "Secciones": 8.8 if has("sections_df") and st.session_state.get("sections_mode") != "trapezoidal_estimado" else (7.4 if has("sections_df") else 5.5),
        "Hidrología normativa": 8.9 if has("hydrology_done") else 6.0,
        "Rugosidad": float(st.session_state.get("roughness_confidence", {}).get("confianza_rugosidad", 6.0)),
        "Granulometría": 9.0 if has("granulometry_assigned_df") else 6.5,
        "Hidráulica 1D": 8.8 if has("hydraulic_profile_df") else 6.0,
        "Sedimentos / socavación": 8.8 if has("sediment_df") and has("granulometry_assigned_df") else (7.2 if has("sediment_df") else 5.5),
    }
    conf_df = global_confidence_report(scores)
    st.dataframe(conf_df, use_container_width=True)
    st.session_state["confidence_report_df"] = conf_df
    st.markdown(
        """
<div class='hs-alert'><b>Advertencia técnica:</b> cuando se usen secciones trapezoidales estimadas, los resultados permiten avanzar con prefactibilidad o estimación preliminar, pero no reemplazan levantamiento topográfico ni calibración hidráulica de diseño.</div>
""",
        unsafe_allow_html=True,
    )

with tabs[10]:
    st.header("11 · Auditoría general hidráulica, hidrológica y sedimentológica")
    st.markdown(
        """
Este módulo v3.7.6 convierte HidroSed en una plataforma reutilizable para revisar proyectos de puentes, defensas fluviales, quebradas, canales naturales, ríos, esteros, desembocaduras, humedales, alcantarillas, cajones y obras de protección. Permite comparar métodos, auditar coherencia técnica y emitir una nota objetiva de 0 a 10.
"""
    )
    audit_tabs = st.tabs([
        "Morfometría y Tc",
        "IDF regional",
        "Caudales y adopción",
        "Aguas abajo / marea",
        "Socavación / protección",
        "Auditoría externa / nota",
        "Exportar auditoría",
    ])

    with audit_tabs[0]:
        st.subheader("Morfometría de cuenca y tiempo de concentración")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            A_aud = st.number_input("Área de cuenca [km²]", min_value=0.001, value=float(st.session_state.get("basin_metrics", {}).get("area_km2", 25.0) or 25.0), step=1.0, key="aud_A")
            L_aud = st.number_input("Longitud cauce principal [km]", min_value=0.001, value=float(st.session_state.get("basin_metrics", {}).get("main_length_km", 8.0) or 8.0), step=0.5, key="aud_L")
        with m2:
            zmax_aud = st.number_input("Altitud máxima [m]", value=900.0, step=10.0, key="aud_zmax")
            zmin_aud = st.number_input("Altitud mínima [m]", value=300.0, step=10.0, key="aud_zmin")
        with m3:
            per_aud = st.number_input("Perímetro cuenca [km]", min_value=0.0, value=30.0, step=1.0, key="aud_per")
            drain_aud = st.number_input("Longitud red drenaje [km]", min_value=0.0, value=15.0, step=1.0, key="aud_drain")
        with m4:
            reg_aud = st.selectbox("Régimen hidrológico", ["pluvial", "nival", "nivo-pluvial", "mixto/otro"], index=0, key="aud_reg")
            tc_manual = st.number_input("Tc manual justificado [h]", min_value=0.0, value=0.0, step=0.1, key="aud_tc_manual")
        use1, use2, use3, use4, use5 = st.columns(5)
        with use1:
            urbano = st.number_input("Urbano [%]", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="aud_urb")
        with use2:
            rural = st.number_input("Rural [%]", min_value=0.0, max_value=100.0, value=20.0, step=5.0, key="aud_rur")
        with use3:
            agricola = st.number_input("Agrícola [%]", min_value=0.0, max_value=100.0, value=20.0, step=5.0, key="aud_agr")
        with use4:
            forestal = st.number_input("Forestal [%]", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="aud_for")
        with use5:
            natural = st.number_input("Natural [%]", min_value=0.0, max_value=100.0, value=60.0, step=5.0, key="aud_nat")
        tc_methods_list = ["California Highways / Manual de Carreteras", "Kirpich", "Témez", "Giandotti", "Ventura", "Bransby-Williams", "Promedio de métodos", "Mediana de métodos", "Valor manual justificado"]
        rector_tc = st.selectbox("Método rector de Tc", tc_methods_list, index=7, key="aud_tc_rector")
        if st.button("Calcular morfometría y comparar Tc", type="primary", key="btn_aud_morph_tc"):
            morph = morphometry_table(A_aud, L_aud, zmax_aud, zmin_aud, per_aud, drain_aud, urbano, rural, agricola, forestal, natural, reg_aud)
            tcdf = tc_methods(L_aud, zmax_aud - zmin_aud, A_aud, user_tc_h=(tc_manual if tc_manual > 0 else None), rector_method=rector_tc)
            tc_val, tc_name = select_tc_value(tcdf, rector_tc)
            st.session_state["aud_morphometry_df"] = morph
            st.session_state["aud_tc_methods_df"] = tcdf
            st.session_state["aud_tc_h"] = tc_val
            st.session_state["aud_tc_method"] = tc_name
            st.success(f"Tc rector: {tc_name} = {tc_val:.3f} h")
        if has("aud_morphometry_df"):
            st.dataframe(st.session_state["aud_morphometry_df"], use_container_width=True, hide_index=True)
        if has("aud_tc_methods_df"):
            st.dataframe(st.session_state["aud_tc_methods_df"], use_container_width=True, hide_index=True)

    with audit_tabs[1]:
        st.subheader("Curvas IDF regionales editables")
        st.caption("Ingrese P24(T) y coeficientes de duración Cd(t). La intensidad se calcula como i(T,t)=P24(T)·Cd(t)/t.")
        default_p24 = pd.DataFrame({"T_anios": AUDIT_PERIODS, "P24_mm": [35, 48, 60, 75, 88, 102, 118]})
        default_cd = pd.DataFrame({"duracion_h": [0.25, 0.5, 1, 2, 3, 6, 12, 24], "Cd": [0.22, 0.32, 0.42, 0.55, 0.63, 0.75, 0.88, 1.00]})
        idf_c1, idf_c2 = st.columns(2)
        with idf_c1:
            p24_edit = st.data_editor(st.session_state.get("aud_p24_table", default_p24), use_container_width=True, num_rows="dynamic", key="aud_p24_edit")
        with idf_c2:
            cd_edit = st.data_editor(st.session_state.get("aud_cd_table", default_cd), use_container_width=True, num_rows="dynamic", key="aud_cd_edit")
        durations_text = st.text_input("Duraciones IDF [h] separadas por coma", value="0.25,0.5,1,2,3,6,12,24", key="aud_durations")
        periods_text = st.text_input("Períodos de retorno [años] separados por coma", value="2,5,10,25,50,100,200", key="aud_periods")
        if st.button("Calcular curvas IDF", type="primary", key="btn_aud_idf"):
            try:
                periods = [float(x.strip()) for x in periods_text.split(",") if x.strip()]
                durations = [float(x.strip()) for x in durations_text.split(",") if x.strip()]
                idfdf = idf_from_p24_duration(p24_edit, cd_edit, periods=periods, durations_h=durations)
                st.session_state["aud_p24_table"] = p24_edit
                st.session_state["aud_cd_table"] = cd_edit
                st.session_state["aud_idf_df"] = idfdf
                st.success("IDF calculada.")
            except Exception as exc:
                st.error(f"No se pudo calcular IDF: {exc}")
        if has("aud_idf_df"):
            st.dataframe(st.session_state["aud_idf_df"], use_container_width=True, hide_index=True)
            try:
                import plotly.express as px
                fig_idf = px.line(st.session_state["aud_idf_df"], x="duracion_h", y="intensidad_mm_h", color="T_anios", markers=True, title="Curvas IDF regionales editables")
                fig_idf.update_xaxes(type="log")
                st.plotly_chart(fig_idf, use_container_width=True)
            except Exception as exc:
                st.info(f"No se pudo graficar IDF: {exc}")

    with audit_tabs[2]:
        st.subheader("Caudales de diseño, comparación y adopción")
        if not has("aud_idf_df"):
            st.info("Calcule primero la IDF regional o use valores por defecto desde la pestaña IDF.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            c_base = st.number_input("Coeficiente C racional", min_value=0.0, max_value=1.5, value=0.35, step=0.05, key="aud_cbase")
            use_scs = st.checkbox("Incluir SCS-CN preliminar", value=False, key="aud_use_scs")
        with c2:
            c10_vk = st.number_input("C10 Verni-King", min_value=0.01, value=1.0, step=0.05, key="aud_c10_vk")
            audit_p24_const = st.checkbox("Auditar P24 constante Verni-King", value=False, key="aud_p24_const_chk")
        with c3:
            p24_const = st.number_input("P24 constante auditoría [mm]", min_value=0.0, value=60.0, step=5.0, key="aud_p24_const")
            q10_dga = st.number_input("Q10 DGA-AC [m³/s]", min_value=0.0, value=10.0, step=1.0, key="aud_q10_dga")
        with c4:
            alpha_dga = st.number_input("α instantáneo DGA-AC", min_value=0.1, value=1.25, step=0.05, key="aud_alpha_dga")
            cn_scs = st.number_input("CN SCS", min_value=30.0, max_value=100.0, value=75.0, step=1.0, key="aud_cn")
        crit_adopt = st.selectbox("Criterio de adopción", ["Mediana", "Promedio", "Máximo", "Racional", "Verni-King Modificado", "DGA-AC", "Ponderación técnica", "Manual"], index=0, key="aud_crit_adopt")
        declared_crit = st.text_input("Criterio declarado en informe/proyecto", value=crit_adopt, key="aud_declared_crit")
        if st.button("Calcular métodos y auditar adopción", type="primary", key="btn_aud_flows"):
            try:
                idfdf = st.session_state.get("aud_idf_df")
                if idfdf is None or idfdf.empty:
                    idfdf = idf_from_p24_duration(default_p24, default_cd, periods=AUDIT_PERIODS, durations_h=[0.25,0.5,1,2,3,6,12,24])
                    st.session_state["aud_idf_df"] = idfdf
                    st.session_state["aud_p24_table"] = default_p24
                tc_use = float(st.session_state.get("aud_tc_h", 1.0) or 1.0)
                periods = sorted(pd.to_numeric(idfdf["T_anios"], errors="coerce").dropna().unique().tolist())
                rat = rational_method_design(A_aud, idfdf, tc_use, c_base, periods=periods)
                vk = verni_king_modified(A_aud, st.session_state.get("aud_p24_table", default_p24), c10=c10_vk, periods=periods, p24_constant_mm=p24_const, audit_constant=audit_p24_const)
                dga = dga_ac_design(q10_dga, alpha_dga, periods=periods)
                method_tables = [rat, vk, dga]
                if use_scs:
                    method_tables.append(scs_cn_runoff(A_aud, st.session_state.get("aud_p24_table", default_p24), cn_scs, periods=periods))
                crit_map = {"Racional": "Racional", "Verni-King Modificado": "Verni-King Modificado", "DGA-AC": "DGA-AC"}
                crit_use = crit_map.get(crit_adopt, crit_adopt)
                adoption = adopt_design_flows(method_tables, criterion=crit_use, declared_criterion=declared_crit, required_periods=periods)
                st.session_state["aud_rational_df"] = rat
                st.session_state["aud_verni_king_df"] = vk
                st.session_state["aud_dga_ac_df"] = dga
                st.session_state["aud_adoption_df"] = adoption
                # Permite usar estos caudales en la hidráulica existente.
                qdes = adoption[["T_anios", "Adoptado"]].rename(columns={"Adoptado": "Q_m3s"}).dropna()
                st.session_state["aud_q_design"] = qdes
                st.success("Caudales calculados y auditados.")
            except Exception as exc:
                st.error(f"No se pudo calcular caudales: {exc}")
        if has("aud_rational_df"):
            st.markdown("**Método racional**")
            st.dataframe(st.session_state["aud_rational_df"], use_container_width=True, hide_index=True)
        if has("aud_verni_king_df"):
            st.markdown("**Verni-King Modificado**")
            st.dataframe(st.session_state["aud_verni_king_df"], use_container_width=True, hide_index=True)
        if has("aud_dga_ac_df"):
            st.markdown("**DGA-AC**")
            st.dataframe(st.session_state["aud_dga_ac_df"], use_container_width=True, hide_index=True)
        if has("aud_adoption_df"):
            st.markdown("**Tabla comparativa y caudal adoptado**")
            st.dataframe(st.session_state["aud_adoption_df"], use_container_width=True, hide_index=True)
            if st.button("Usar caudal adoptado en módulo hidráulico principal", key="btn_use_aud_q"):
                st.session_state["q_design"] = st.session_state["aud_q_design"]
                st.success("Caudales adoptados transferidos a q_design del flujo principal.")

    with audit_tabs[3]:
        st.subheader("Condición aguas abajo, marea, humedal y barra litoral")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            base_level = st.number_input("Cota base aguas abajo [m]", value=0.0, step=0.5, key="aud_base_level")
            nmm = st.number_input("Nivel medio mar [m]", value=0.0, step=0.1, key="aud_nmm")
        with b2:
            pleamar = st.number_input("Pleamar máxima [m]", value=1.2, step=0.1, key="aud_pleamar")
            tide_design = st.number_input("Pleamar diseño [m]", value=1.5, step=0.1, key="aud_tide_design")
        with b3:
            surge = st.number_input("Marejada [m]", value=0.3, step=0.1, key="aud_surge")
            setup = st.number_input("Sobre-elevación meteorológica [m]", value=0.2, step=0.1, key="aud_setup")
        with b4:
            wetland = st.number_input("Nivel humedal/laguna [m]", value=0.8, step=0.1, key="aud_wetland")
            bar = st.number_input("Cota barra litoral [m]", value=1.0, step=0.1, key="aud_bar")
        influence_len = st.number_input("Longitud de propagación a revisar [m]", min_value=10.0, value=1000.0, step=100.0, key="aud_infl_len")
        if st.button("Generar escenarios aguas abajo", type="primary", key="btn_aud_boundary"):
            scen = downstream_scenarios(base_level, nmm, pleamar, tide_design, surge, setup, wetland, bar)
            st.session_state["aud_boundary_scenarios_df"] = scen
            if has("hydraulic_profile_df"):
                st.session_state["aud_boundary_audit_df"] = audit_downstream_influence(st.session_state["hydraulic_profile_df"], scen, influence_len)
            st.success("Escenarios generados.")
        if has("aud_boundary_scenarios_df"):
            st.dataframe(st.session_state["aud_boundary_scenarios_df"], use_container_width=True, hide_index=True)
        if has("aud_boundary_audit_df"):
            st.markdown("**Screening de influencia sobre perfil hidráulico existente**")
            st.dataframe(st.session_state["aud_boundary_audit_df"], use_container_width=True, hide_index=True)
        else:
            st.info("Calcule antes el perfil hidráulico principal si desea estimar secciones afectadas por el control aguas abajo.")

    with audit_tabs[4]:
        st.subheader("Socavación general/local y diseño preliminar de protección fluvial")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            d50_sc = st.number_input("D50 [m]", min_value=0.00001, value=0.05, step=0.01, key="aud_d50_sc")
            d90_sc = st.number_input("D90 [m]", min_value=0.00001, value=0.15, step=0.01, key="aud_d90_sc")
        with s2:
            obra_tipo = st.selectbox("Tipo obra local", ["pila", "estribo", "contracción", "alcantarilla/cajón", "defensa fluvial"], index=0, key="aud_local_type")
            ancho_obra = st.number_input("Ancho efectivo obra [m]", min_value=0.01, value=1.0, step=0.1, key="aud_width_obra")
        with s3:
            ang_ataque = st.number_input("Ángulo ataque [°]", min_value=0.0, max_value=90.0, value=0.0, step=5.0, key="aud_angle")
            fund_level = st.number_input("Cota fundación [m]", value=0.0, step=0.5, key="aud_found")
        with s4:
            v_prot = st.number_input("Velocidad diseño protección [m/s]", min_value=0.0, value=3.0, step=0.2, key="aud_vprot")
            tau_prot = st.number_input("Tensión corte diseño [Pa]", min_value=0.0, value=40.0, step=5.0, key="aud_tauprot")
        if st.button("Calcular socavación/protección", type="primary", key="btn_aud_scour"):
            if has("hydraulic_profile_df"):
                hprof = st.session_state["hydraulic_profile_df"].copy()
                hprof["pendiente_energia"] = hprof.get("pendiente_energia", st.session_state.get("hecras_like_inputs", {}).get("pendiente_energia", 0.01))
                scour_df = general_scour_methods(hprof, d50_sc, d90_sc)
                row0 = hprof.iloc[0].to_dict()
            else:
                row0 = {"tirante_max_m": 2.0, "velocidad_m_s": v_prot, "Froude": 0.7, "cota_fondo_m": fund_level + 1.0, "radio_hidraulico_m": 1.5, "pendiente_energia": 0.01}
                scour_df = general_scour_methods(pd.DataFrame([row0]), d50_sc, d90_sc)
            local = pd.DataFrame([local_scour_preliminary(row0, obra_tipo, ancho_obra, ang_ataque, foundation_level_m=fund_level)])
            prot = protection_design_preliminary(v_prot, tau_prot)
            st.session_state["aud_scour_general_df"] = scour_df
            st.session_state["aud_scour_local_df"] = local
            st.session_state["aud_protection_df"] = prot
            st.success("Socavación y protección preliminar calculadas.")
        if has("aud_scour_general_df"):
            st.markdown("**Socavación general comparada**")
            st.dataframe(st.session_state["aud_scour_general_df"], use_container_width=True, hide_index=True)
        if has("aud_scour_local_df"):
            st.markdown("**Socavación local preliminar**")
            st.dataframe(st.session_state["aud_scour_local_df"], use_container_width=True, hide_index=True)
        if has("aud_protection_df"):
            st.markdown("**Predimensionamiento de protección fluvial**")
            st.dataframe(st.session_state["aud_protection_df"], use_container_width=True, hide_index=True)

    with audit_tabs[5]:
        st.subheader("Auditoría de informe externo y nota técnica 0 a 10")
        st.caption("Active los antecedentes que el informe externo sí contiene. Las ausencias generan observaciones y afectan la nota.")
        ck1, ck2, ck3 = st.columns(3)
        with ck1:
            f_datos = st.checkbox("Datos de cuenca completos", value=has("aud_morphometry_df"), key="aud_f_datos")
            f_idf = st.checkbox("IDF / P24 trazable", value=has("aud_idf_df"), key="aud_f_idf")
            f_tc = st.checkbox("Tiempo de concentración justificado", value=has("aud_tc_methods_df"), key="aud_f_tc")
            f_qmeth = st.checkbox("Caudales por métodos", value=has("aud_adoption_df"), key="aud_f_qmeth")
        with ck2:
            f_qadopt = st.checkbox("Caudal adoptado consistente", value=has("aud_adoption_df"), key="aud_f_qadopt")
            f_hyd = st.checkbox("Modelación hidráulica", value=has("hydraulic_profile_df"), key="aud_f_hyd")
            f_bound = st.checkbox("Condición aguas abajo", value=has("aud_boundary_scenarios_df"), key="aud_f_bound")
            f_sed = st.checkbox("Sedimentos y socavación", value=has("aud_scour_general_df") or has("sediment_df"), key="aud_f_sed")
        with ck3:
            f_prot = st.checkbox("Protección fluvial", value=has("aud_protection_df"), key="aud_f_prot")
            f_trace = st.checkbox("Trazabilidad completa", value=False, key="aud_f_trace")
            err_units = st.checkbox("Existen errores de unidades", value=False, key="aud_err_units")
            bridge_no_local = st.checkbox("Puente sin socavación local", value=False, key="aud_bridge_no_local")
        cprom = st.checkbox("Declara promedio pero adopta máximo", value=False, key="aud_cprom")
        p24const_flag = st.checkbox("Usa P24 constante en Verni-King", value=bool(audit_p24_const if 'audit_p24_const' in locals() else False), key="aud_p24const_flag")
        threshold = st.number_input("Umbral aprobación [0-10]", min_value=0.0, max_value=10.0, value=8.7, step=0.1, key="aud_threshold")
        if st.button("Ejecutar auditoría y nota", type="primary", key="btn_aud_score"):
            data = {
                "datos_cuenca": f_datos,
                "idf": f_idf,
                "tiempo_concentracion": f_tc,
                "caudales_metodos": f_qmeth,
                "caudal_adoptado": f_qadopt,
                "hidraulica": f_hyd,
                "condicion_aguas_abajo": f_bound,
                "sedimentos_socavacion": f_sed,
                "proteccion_fluvial": f_prot,
                "trazabilidad": f_trace,
                "criterio_promedio": cprom,
                "adopta_maximo": cprom,
                "p24_constante_verni_king": p24const_flag,
                "errores_unidades": err_units,
                "puente_sin_socavacion_local": bridge_no_local,
            }
            audit_df = audit_external_report(data)
            score_df = technical_score(audit_df, threshold=threshold)
            st.session_state["aud_external_audit_df"] = audit_df
            st.session_state["aud_score_df"] = score_df
            st.success("Auditoría ejecutada.")
        if has("aud_external_audit_df"):
            st.dataframe(st.session_state["aud_external_audit_df"], use_container_width=True, hide_index=True)
        if has("aud_score_df"):
            summ = st.session_state["aud_score_df"][st.session_state["aud_score_df"].get("tipo", "") == "resumen"]
            if not summ.empty:
                sr = summ.iloc[0]
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Nota global", f"{float(sr.get('nota_global', 0)):.1f}/10")
                sc2.metric("Estado", str(sr.get("estado_final", "")))
                sc3.metric("Supera umbral", "Sí" if bool(sr.get("supera_umbral", False)) else "No")
            st.dataframe(st.session_state["aud_score_df"], use_container_width=True, hide_index=True)

    with audit_tabs[6]:
        st.subheader("Exportables de auditoría general")
        sheets = {
            "morfometria": st.session_state.get("aud_morphometry_df", pd.DataFrame()),
            "tiempo_concentracion": st.session_state.get("aud_tc_methods_df", pd.DataFrame()),
            "idf": st.session_state.get("aud_idf_df", pd.DataFrame()),
            "racional": st.session_state.get("aud_rational_df", pd.DataFrame()),
            "verni_king": st.session_state.get("aud_verni_king_df", pd.DataFrame()),
            "dga_ac": st.session_state.get("aud_dga_ac_df", pd.DataFrame()),
            "adopcion": st.session_state.get("aud_adoption_df", pd.DataFrame()),
            "aguas_abajo": st.session_state.get("aud_boundary_scenarios_df", pd.DataFrame()),
            "socavacion_general": st.session_state.get("aud_scour_general_df", pd.DataFrame()),
            "socavacion_local": st.session_state.get("aud_scour_local_df", pd.DataFrame()),
            "proteccion": st.session_state.get("aud_protection_df", pd.DataFrame()),
            "auditoria_externa": st.session_state.get("aud_external_audit_df", pd.DataFrame()),
            "nota": st.session_state.get("aud_score_df", pd.DataFrame()),
        }
        try:
            xb = excel_bytes(sheets)
            st.download_button("Descargar auditoría general Excel", xb, file_name="auditoria_general_hidrosed_v376.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as exc:
            st.info(f"Excel no disponible: {exc}")
        md = technical_markdown_report(
            "Informe de Auditoría General HidroSed Maestra Integrada v3.8.3",
            st.session_state.get("aud_external_audit_df", pd.DataFrame()),
            st.session_state.get("aud_score_df", pd.DataFrame()),
            st.session_state.get("aud_adoption_df", pd.DataFrame()),
        )
        st.download_button("Descargar informe técnico Markdown", md.encode("utf-8"), file_name="informe_auditoria_general_hidrosed_v376.md", mime="text/markdown")
        try:
            docxb = docx_report_bytes("Informe de Auditoría General HidroSed Maestra Integrada v3.8.3", st.session_state.get("aud_external_audit_df", pd.DataFrame()), st.session_state.get("aud_score_df", pd.DataFrame()), st.session_state.get("aud_adoption_df", pd.DataFrame()))
            st.download_button("Descargar informe Word DOCX", docxb, file_name="informe_auditoria_general_hidrosed_v376.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as exc:
            st.info(f"Exportación DOCX no disponible hasta instalar python-docx: {exc}")
        try:
            pdfb = pdf_report_bytes("Informe de Auditoría General HidroSed Maestra Integrada v3.8.3", st.session_state.get("aud_external_audit_df", pd.DataFrame()), st.session_state.get("aud_score_df", pd.DataFrame()), st.session_state.get("aud_adoption_df", pd.DataFrame()))
            st.download_button("Descargar informe PDF", pdfb, file_name="informe_auditoria_general_hidrosed_v376.pdf", mime="application/pdf")
        except Exception as exc:
            st.info(f"Exportación PDF no disponible hasta instalar reportlab: {exc}")
        st.code(md[:3000] + ("\n..." if len(md) > 3000 else ""), language="markdown")
