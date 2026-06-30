
from __future__ import annotations

import numpy as np
import pandas as pd


def _to_float(v, default=np.nan):
    try:
        x = float(v)
        return x if np.isfinite(x) else default
    except Exception:
        return default


def verify_and_snap_axis_to_section_minima(
    sections_df: pd.DataFrame,
    points_df: pd.DataFrame,
    axis_source: str = "manual",
    tolerance_m: float = 0.50,
    update_axis_if_auto: bool = True,
):
    """Verifica y corrige la coincidencia eje-thalweg en secciones.

    Objetivo:
    - Detectar si el offset 0 de cada sección coincide con la cota mínima.
    - Si el eje fue generado automáticamente, recentrar la sección para que
      el punto de menor cota quede en offset 0.
    - Si existen lon/lat del punto mínimo, reconstruir el eje automático como
      una polilínea que sigue los puntos más bajos de las secciones.

    Devuelve:
    (sections_corr, points_corr, qa_report, axis_coords_auto)
    """
    if sections_df is None or sections_df.empty or points_df is None or points_df.empty:
        return sections_df, points_df, pd.DataFrame(), None

    sec = sections_df.copy()
    pts = points_df.copy()
    if "section_id" not in sec.columns or "section_id" not in pts.columns:
        return sec, pts, pd.DataFrame(), None

    for c in ["pk_m", "offset_m", "z_m", "lon", "lat", "x_utm", "y_utm"]:
        if c in pts.columns:
            pts[c] = pd.to_numeric(pts[c], errors="coerce")
    for c in ["pk_m", "cota_fondo_m", "lon_eje", "lat_eje", "x_utm_eje", "y_utm_eje"]:
        if c in sec.columns:
            sec[c] = pd.to_numeric(sec[c], errors="coerce")

    axis_source_l = str(axis_source or "").lower()
    is_auto = any(k in axis_source_l for k in ["auto", "preliminar", "automatico"])
    do_snap = bool(is_auto and update_axis_if_auto)

    if "offset_original_m" not in pts.columns:
        pts["offset_original_m"] = pts.get("offset_m", np.nan)

    report_rows = []
    axis_coords = []

    for sid_str in sec["section_id"].astype(str).tolist():
        idx_sec = sec.index[sec["section_id"].astype(str) == sid_str]
        if len(idx_sec) == 0:
            continue
        i_sec = idx_sec[0]
        pidx = pts.index[pts["section_id"].astype(str) == sid_str].tolist()
        if not pidx:
            report_rows.append({
                "section_id": sec.at[i_sec, "section_id"],
                "pk_m": sec.at[i_sec, "pk_m"] if "pk_m" in sec.columns else np.nan,
                "axis_source": axis_source,
                "estado": "SIN_PUNTOS",
                "offset_minimo_original_m": np.nan,
                "desfase_eje_thalweg_m": np.nan,
                "correccion_aplicada": False,
                "observacion": "La sección no tiene puntos topográficos para verificar eje-thalweg.",
            })
            continue

        g = pts.loc[pidx].copy()
        g = g[np.isfinite(g["z_m"]) & np.isfinite(g["offset_m"])]
        if g.empty:
            report_rows.append({
                "section_id": sec.at[i_sec, "section_id"],
                "pk_m": sec.at[i_sec, "pk_m"] if "pk_m" in sec.columns else np.nan,
                "axis_source": axis_source,
                "estado": "SIN_COTAS_VALIDAS",
                "offset_minimo_original_m": np.nan,
                "desfase_eje_thalweg_m": np.nan,
                "correccion_aplicada": False,
                "observacion": "La sección no tiene cotas válidas.",
            })
            continue

        zmin = float(g["z_m"].min())
        # Si hay varios mínimos, elegir el mínimo más cercano al eje actual.
        cand = g[np.isclose(g["z_m"], zmin, rtol=0, atol=1e-6)].copy()
        if cand.empty:
            min_row = g.loc[g["z_m"].idxmin()]
        else:
            min_row = cand.loc[cand["offset_m"].abs().idxmin()]
        off_min = float(min_row["offset_m"])
        desfase = abs(off_min)
        coincide = bool(desfase <= float(tolerance_m))
        apply_corr = bool(do_snap and not coincide)

        if apply_corr:
            pts.loc[pidx, "offset_m"] = pd.to_numeric(pts.loc[pidx, "offset_m"], errors="coerce") - off_min

        # Actualizar resumen de sección al punto mínimo detectado.
        sec.at[i_sec, "cota_fondo_m"] = zmin
        sec.at[i_sec, "cota_eje_minima_m"] = zmin
        sec.at[i_sec, "offset_minimo_original_m"] = off_min
        sec.at[i_sec, "desfase_eje_thalweg_m"] = desfase
        sec.at[i_sec, "eje_coincide_cota_minima"] = True if (coincide or apply_corr) else False
        sec.at[i_sec, "eje_recentrado_al_thalweg"] = apply_corr
        sec.at[i_sec, "axis_source_qaqc"] = axis_source
        sec.at[i_sec, "criterio_eje_thalweg"] = (
            "eje_automatico_recentrado_al_punto_mas_bajo"
            if apply_corr else
            ("eje_coincide_con_punto_mas_bajo" if coincide else "eje_manual_no_coincide_revisar")
        )

        # Si el eje es automático, usar coordenadas del punto mínimo como
        # eje hidráulico local. Si el eje es manual, solo se informa la diferencia.
        if do_snap and "lon" in g.columns and "lat" in g.columns:
            lon_min = _to_float(min_row.get("lon"))
            lat_min = _to_float(min_row.get("lat"))
            if np.isfinite(lon_min) and np.isfinite(lat_min):
                sec.at[i_sec, "lon_eje"] = lon_min
                sec.at[i_sec, "lat_eje"] = lat_min
                axis_coords.append((float(sec.at[i_sec, "pk_m"]) if "pk_m" in sec.columns else len(axis_coords), lon_min, lat_min))
        if do_snap and "x_utm" in g.columns and "y_utm" in g.columns:
            x_min = _to_float(min_row.get("x_utm"))
            y_min = _to_float(min_row.get("y_utm"))
            if np.isfinite(x_min) and np.isfinite(y_min):
                sec.at[i_sec, "x_utm_eje"] = x_min
                sec.at[i_sec, "y_utm_eje"] = y_min

        report_rows.append({
            "section_id": sec.at[i_sec, "section_id"],
            "pk_m": sec.at[i_sec, "pk_m"] if "pk_m" in sec.columns else np.nan,
            "axis_source": axis_source,
            "estado": "OK_CORREGIDO" if apply_corr else ("OK" if coincide else "REVISAR"),
            "cota_minima_m": zmin,
            "offset_minimo_original_m": off_min,
            "desfase_eje_thalweg_m": desfase,
            "tolerancia_m": float(tolerance_m),
            "correccion_aplicada": apply_corr,
            "observacion": (
                "Eje automático recentrado: el offset 0 ahora coincide con la cota más baja de la sección."
                if apply_corr else
                ("El eje coincide con la cota más baja dentro de la tolerancia." if coincide else
                 "El eje no coincide con la cota mínima; al ser manual no se corrige automáticamente.")
            ),
        })

    qa = pd.DataFrame(report_rows)
    axis_line = None
    if do_snap and axis_coords:
        axis_coords = sorted(axis_coords, key=lambda t: t[0])
        # quitar duplicados consecutivos
        coords = []
        for _, lon, lat in axis_coords:
            if not coords or (abs(coords[-1][0] - lon) > 1e-12 or abs(coords[-1][1] - lat) > 1e-12):
                coords.append((lon, lat))
        if len(coords) >= 2:
            axis_line = coords

    return sec, pts, qa, axis_line


def summarize_axis_thalweg_qa(qa_df: pd.DataFrame) -> dict:
    if qa_df is None or qa_df.empty:
        return {"estado": "SIN_DATOS", "n_secciones": 0}
    n = int(len(qa_df))
    n_corr = int(pd.Series(qa_df.get("correccion_aplicada", False)).fillna(False).sum())
    n_rev = int((qa_df.get("estado", pd.Series([], dtype=str)).astype(str) == "REVISAR").sum()) if "estado" in qa_df else 0
    max_desfase = float(pd.to_numeric(qa_df.get("desfase_eje_thalweg_m"), errors="coerce").max()) if "desfase_eje_thalweg_m" in qa_df else np.nan
    return {
        "estado": "OK" if n_rev == 0 else "REVISAR",
        "n_secciones": n,
        "n_corregidas": n_corr,
        "n_revisar": n_rev,
        "desfase_max_m": max_desfase,
    }
