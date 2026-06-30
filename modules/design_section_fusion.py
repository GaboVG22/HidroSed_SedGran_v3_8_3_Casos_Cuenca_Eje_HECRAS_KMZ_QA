from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_SECTION_COLS = ["section_id", "pk_m"]
REQUIRED_POINT_COLS = ["section_id", "pk_m", "offset_m", "z_m"]


@dataclass(frozen=True)
class DesignChannelSpec:
    """Parámetros de una sección artificial que se inserta dentro de un perfil natural.

    side_slope_* se expresa como H:V. Para una sección rectangular se ignora y se
    modela con paredes casi verticales para que el motor hidráulico pueda integrar
    perímetro mojado sin offsets duplicados.
    """

    shape: str = "Trapecial"
    bottom_width_m: float = 3.0
    depth_m: float = 1.5
    side_slope_left_hv: float = 1.5
    side_slope_right_hv: float = 1.5
    bottom_elevation_m: float | None = None
    center_offset_m: float = 0.0
    transition_width_m: float = 2.0
    n_bottom_points: int = 3


def _ensure_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _sid_key(value) -> str:
    """Clave estable para comparar section_id aunque pandas lo lea como 1 o 1.0."""
    try:
        fv = float(value)
        if np.isfinite(fv) and abs(fv - round(fv)) < 1e-9:
            return str(int(round(fv)))
    except Exception:
        pass
    return str(value)


def _sid_mask(series: pd.Series, section_id) -> pd.Series:
    target = _sid_key(section_id)
    return series.map(_sid_key) == target


def _validate_inputs(sections_df: pd.DataFrame, points_df: pd.DataFrame) -> None:
    if sections_df is None or sections_df.empty:
        raise ValueError("No existen secciones para modificar.")
    if points_df is None or points_df.empty:
        raise ValueError("No existen puntos de sección para modificar.")
    missing_sec = [c for c in REQUIRED_SECTION_COLS if c not in sections_df.columns]
    missing_pts = [c for c in REQUIRED_POINT_COLS if c not in points_df.columns]
    if missing_sec:
        raise ValueError(f"Faltan columnas de secciones: {', '.join(missing_sec)}")
    if missing_pts:
        raise ValueError(f"Faltan columnas de puntos: {', '.join(missing_pts)}")


def _section_points(points_df: pd.DataFrame, section_id) -> pd.DataFrame:
    pts = points_df[_sid_mask(points_df["section_id"], section_id)].copy()
    if pts.empty:
        raise ValueError(f"La sección {section_id} no tiene puntos transversales.")
    pts = _ensure_numeric(pts, ["pk_m", "offset_m", "z_m"])
    pts = pts.dropna(subset=["offset_m", "z_m"]).sort_values("offset_m").reset_index(drop=True)
    if len(pts) < 2:
        raise ValueError(f"La sección {section_id} requiere al menos 2 puntos válidos.")
    if float(pts["offset_m"].max() - pts["offset_m"].min()) <= 0:
        raise ValueError(f"La sección {section_id} tiene ancho transversal nulo.")
    return pts


def _natural_z_at(pts: pd.DataFrame, x: float) -> float:
    xarr = pd.to_numeric(pts["offset_m"], errors="coerce").to_numpy(dtype=float)
    zarr = pd.to_numeric(pts["z_m"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(xarr) & np.isfinite(zarr)
    xarr = xarr[mask]
    zarr = zarr[mask]
    order = np.argsort(xarr)
    xarr = xarr[order]
    zarr = zarr[order]
    if len(xarr) == 0:
        return float("nan")
    if len(xarr) == 1:
        return float(zarr[0])
    return float(np.interp(float(x), xarr, zarr, left=zarr[0], right=zarr[-1]))


def resolve_bottom_elevation(
    pts: pd.DataFrame,
    mode: str,
    value: float | None = None,
    default_drop_m: float = 0.0,
) -> float:
    """Resuelve la cota de fondo artificial desde la sección natural.

    mode acepta: "minima_natural", "rebaje_relativo" o "cota_absoluta".
    """
    pts = _ensure_numeric(pts, ["z_m"])
    zmin = float(pts["z_m"].min())
    m = str(mode or "minima_natural").strip().lower()
    if m in {"minima", "minima_natural", "cota mínima natural", "usar cota mínima natural"}:
        return zmin
    if m in {"rebaje", "rebaje_relativo", "bajar fondo", "bajar el fondo"}:
        drop = float(default_drop_m if value is None else value)
        if not np.isfinite(drop):
            drop = 0.0
        return zmin - abs(drop)
    if m in {"absoluta", "cota_absoluta", "ingresar cota absoluta"}:
        if value is None or not np.isfinite(float(value)):
            raise ValueError("Debe ingresar una cota absoluta de fondo válida.")
        return float(value)
    raise ValueError(f"Modo de cota de fondo no reconocido: {mode}")


def build_design_channel_points(spec: DesignChannelSpec) -> pd.DataFrame:
    """Construye la polilínea transversal de la sección artificial."""
    shape = str(spec.shape or "Trapecial").strip().lower()
    b = float(spec.bottom_width_m)
    d = float(spec.depth_m)
    if not np.isfinite(b) or b <= 0:
        raise ValueError("El ancho basal/de fondo debe ser mayor que cero.")
    if not np.isfinite(d) or d <= 0:
        raise ValueError("La profundidad útil debe ser mayor que cero.")
    if spec.bottom_elevation_m is None or not np.isfinite(float(spec.bottom_elevation_m)):
        raise ValueError("La cota de fondo artificial no es válida.")

    zbed = float(spec.bottom_elevation_m)
    x0 = float(spec.center_offset_m or 0.0)
    ztop = zbed + d
    nb = int(max(2, spec.n_bottom_points))

    if shape.startswith("rect"):
        # Evita offsets idénticos para que la integración hidráulica considere
        # las paredes verticales como segmentos muy inclinados, no como dx=0.
        eps = max(1.0e-3, b * 1.0e-6)
        left_bottom = x0 - b / 2.0
        right_bottom = x0 + b / 2.0
        xs_bottom = np.linspace(left_bottom, right_bottom, nb)
        xs = [left_bottom - eps, *xs_bottom.tolist(), right_bottom + eps]
        zs = [ztop, *([zbed] * len(xs_bottom)), ztop]
        side_l = 0.0
        side_r = 0.0
        footprint_left = left_bottom - eps
        footprint_right = right_bottom + eps
    else:
        zl = float(spec.side_slope_left_hv)
        zr = float(spec.side_slope_right_hv)
        if not np.isfinite(zl) or zl < 0:
            raise ValueError("El talud izquierdo H:V no puede ser negativo.")
        if not np.isfinite(zr) or zr < 0:
            raise ValueError("El talud derecho H:V no puede ser negativo.")
        left_bottom = x0 - b / 2.0
        right_bottom = x0 + b / 2.0
        left_top = left_bottom - zl * d
        right_top = right_bottom + zr * d
        xs_bottom = np.linspace(left_bottom, right_bottom, nb)
        xs = [left_top, *xs_bottom.tolist(), right_top]
        zs = [ztop, *([zbed] * len(xs_bottom)), ztop]
        side_l = zl
        side_r = zr
        footprint_left = left_top
        footprint_right = right_top

    out = pd.DataFrame({"offset_m": xs, "z_m": zs})
    out["tipo_punto"] = "artificial_diseno"
    out["shape"] = "Rectangular" if shape.startswith("rect") else "Trapecial"
    out["bottom_width_m"] = b
    out["depth_m"] = d
    out["side_slope_left_hv"] = side_l
    out["side_slope_right_hv"] = side_r
    out["footprint_left_m"] = float(footprint_left)
    out["footprint_right_m"] = float(footprint_right)
    return out.sort_values("offset_m").reset_index(drop=True)


def _jitter_duplicate_offsets(df: pd.DataFrame, min_delta: float = 1.0e-5) -> pd.DataFrame:
    """Asegura offsets estrictamente crecientes para motores que integran segmentos."""
    out = df.sort_values("offset_m").reset_index(drop=True).copy()
    x = out["offset_m"].to_numpy(dtype=float)
    for i in range(1, len(x)):
        if not np.isfinite(x[i]):
            continue
        if x[i] <= x[i - 1]:
            x[i] = x[i - 1] + min_delta
    out["offset_m"] = x
    return out


def _base_point_row(template: pd.Series | None, section_id, pk_m: float, offset_m: float, z_m: float, origen: str) -> dict:
    row = {}
    if template is not None:
        for c, v in template.items():
            row[c] = v
    row["section_id"] = section_id
    row["pk_m"] = float(pk_m)
    row["offset_m"] = float(offset_m)
    row["z_m"] = float(z_m)
    row["origen"] = origen
    return row


def fuse_design_channel_into_section_points(
    section_points: pd.DataFrame,
    spec: DesignChannelSpec,
    section_id=None,
    pk_m: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inserta una sección rectangular/trapecial dentro de un perfil natural.

    Conserva las riberas naturales fuera de la huella artificial, reemplaza el
    tramo central por la geometría de diseño y agrega puntos de transición para
    evitar un corte brusco entre terreno y canal.

    Devuelve (puntos_fusionados, puntos_artificiales).
    """
    pts = section_points.copy()
    pts = _ensure_numeric(pts, ["pk_m", "offset_m", "z_m"])
    pts = pts.dropna(subset=["offset_m", "z_m"]).sort_values("offset_m").reset_index(drop=True)
    if pts.empty or len(pts) < 2:
        raise ValueError("La sección natural no tiene puntos suficientes para fusionar.")

    sid = section_id if section_id is not None else pts["section_id"].iloc[0] if "section_id" in pts.columns else 1
    if pk_m is None:
        if "pk_m" in pts.columns and pd.to_numeric(pts["pk_m"], errors="coerce").notna().any():
            pk = float(pd.to_numeric(pts["pk_m"], errors="coerce").dropna().iloc[0])
        else:
            pk = 0.0
    else:
        pk = float(pk_m)

    design = build_design_channel_points(spec)
    x_left = float(design["footprint_left_m"].iloc[0])
    x_right = float(design["footprint_right_m"].iloc[0])
    if x_left >= x_right:
        raise ValueError("La huella de la sección artificial no es válida.")

    x_min = float(pts["offset_m"].min())
    x_max = float(pts["offset_m"].max())
    if x_left <= x_min or x_right >= x_max:
        raise ValueError(
            "La sección artificial excede el ancho transversal disponible. "
            "Reduzca ancho/taludes/profundidad o modifique el desplazamiento respecto del eje."
        )

    trans = float(spec.transition_width_m or 0.0)
    if not np.isfinite(trans) or trans < 0:
        trans = 0.0
    # El ancho de transición no puede consumir toda la ribera disponible.
    trans_left = min(trans, max(0.0, x_left - x_min) * 0.90)
    trans_right = min(trans, max(0.0, x_max - x_right) * 0.90)
    x_tie_left = x_left - trans_left if trans_left > 0 else x_left
    x_tie_right = x_right + trans_right if trans_right > 0 else x_right

    outside = pts[(pts["offset_m"] < x_tie_left) | (pts["offset_m"] > x_tie_right)].copy()
    template = pts.iloc[0] if not pts.empty else None
    rows: list[dict] = []

    if x_tie_left > x_min:
        rows.append(_base_point_row(template, sid, pk, x_tie_left, _natural_z_at(pts, x_tie_left), "terreno_natural_transicion"))
    for _, r in design.iterrows():
        rows.append(_base_point_row(template, sid, pk, float(r["offset_m"]), float(r["z_m"]), "seccion_compuesta_sintetica_fusionada"))
    if x_tie_right < x_max:
        rows.append(_base_point_row(template, sid, pk, x_tie_right, _natural_z_at(pts, x_tie_right), "terreno_natural_transicion"))

    insert = pd.DataFrame(rows)
    merged = pd.concat([outside, insert], ignore_index=True, sort=False)
    merged["section_id"] = sid
    merged["pk_m"] = pk
    merged = _ensure_numeric(merged, ["pk_m", "offset_m", "z_m"])
    merged = merged.dropna(subset=["offset_m", "z_m"])
    merged = _jitter_duplicate_offsets(merged)
    merged["point_order"] = np.arange(1, len(merged) + 1)
    merged["geometria_compuesta"] = True
    merged["tipo_seccion_diseno"] = str(design["shape"].iloc[0])
    merged["ancho_fondo_diseno_m"] = float(spec.bottom_width_m)
    merged["profundidad_diseno_m"] = float(spec.depth_m)
    merged["cota_fondo_diseno_m"] = float(spec.bottom_elevation_m)
    merged["offset_centro_diseno_m"] = float(spec.center_offset_m)

    art = design.copy()
    art["section_id"] = sid
    art["pk_m"] = pk
    return merged.reset_index(drop=True), art.reset_index(drop=True)


def _update_section_row_with_points(row: pd.Series, pts_new: pd.DataFrame, spec: DesignChannelSpec, original_id) -> dict:
    out = row.to_dict()
    zmin = float(pts_new["z_m"].min())
    zmax = float(pts_new["z_m"].max())
    xmin = float(pts_new["offset_m"].min())
    xmax = float(pts_new["offset_m"].max())
    out["cota_fondo_m"] = zmin
    out["cota_min_m"] = zmin
    out["cota_max_m"] = zmax
    out["cota_borde_izq_m"] = float(pts_new.iloc[0]["z_m"])
    out["cota_borde_der_m"] = float(pts_new.iloc[-1]["z_m"])
    out["ancho_m"] = xmax - xmin
    out["width_m"] = xmax - xmin
    out["n_puntos_total"] = int(len(pts_new))
    out["seleccion_modelacion"] = True
    out["origen"] = "seccion_compuesta_sintetica_fusionada"
    out["estado_revision"] = "Rellenada"
    out["estado_modelacion"] = "fusionada_diseno"
    out["observacion_modelacion"] = (
        "Sección natural fusionada con canal rectangular/trapecial de diseño. "
        "Se conserva trazabilidad en puntos originales y resumen de fusión."
    )
    out["section_id_original_pre_fusion"] = original_id
    out["tipo_seccion_diseno"] = str(spec.shape)
    out["ancho_fondo_diseno_m"] = float(spec.bottom_width_m)
    out["profundidad_diseno_m"] = float(spec.depth_m)
    out["talud_izq_diseno_hv"] = float(spec.side_slope_left_hv)
    out["talud_der_diseno_hv"] = float(spec.side_slope_right_hv)
    out["cota_fondo_diseno_m"] = float(spec.bottom_elevation_m)
    out["offset_centro_diseno_m"] = float(spec.center_offset_m)
    return out


def apply_design_channel_to_section(
    sections_df: pd.DataFrame,
    points_df: pd.DataFrame,
    section_id,
    spec: DesignChannelSpec,
    keep_original_points: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aplica canal artificial a una sección puntual.

    Devuelve: secciones, puntos, resumen, puntos_originales_modificados.
    """
    _validate_inputs(sections_df, points_df)
    sec = _ensure_numeric(sections_df, ["pk_m"]).copy()
    pts = _ensure_numeric(points_df, ["pk_m", "offset_m", "z_m"]).copy()
    mask_sec = _sid_mask(sec["section_id"], section_id)
    if not mask_sec.any():
        raise ValueError(f"No existe la sección {section_id}.")
    sec_row = sec[mask_sec].iloc[0]
    pk = float(sec_row.get("pk_m", np.nan))
    if not np.isfinite(pk):
        pts_sid = _section_points(pts, section_id)
        pk = float(pts_sid["pk_m"].iloc[0]) if "pk_m" in pts_sid.columns else 0.0
    original_pts = _section_points(pts, section_id)
    fused_pts, art_pts = fuse_design_channel_into_section_points(original_pts, spec, section_id=section_id, pk_m=pk)

    new_sec_row = _update_section_row_with_points(sec_row, fused_pts, spec, original_id=sec_row.get("section_id_original", section_id))
    target_index = sec.index[mask_sec]
    if len(target_index) != 1:
        raise ValueError(f"La sección {section_id} no es única en la tabla de secciones.")
    ridx = target_index[0]
    for c, v in new_sec_row.items():
        if c not in sec.columns:
            sec[c] = np.nan
            if isinstance(v, str) or isinstance(v, bool):
                sec[c] = sec[c].astype(object)
        sec.at[ridx, c] = v

    pts_out = pts[~_sid_mask(pts["section_id"], section_id)].copy()
    if keep_original_points:
        original_tagged = original_pts.copy()
        original_tagged["section_id"] = section_id
        original_tagged["origen"] = "original_pre_fusion_no_modelacion"
        original_tagged["activo_modelacion"] = False
    else:
        original_tagged = original_pts.copy()
    fused_pts["activo_modelacion"] = True
    pts_new = pd.concat([pts_out, fused_pts], ignore_index=True, sort=False)
    pts_new = pts_new.sort_values(["pk_m", "section_id", "offset_m"]).reset_index(drop=True)

    resumen = pd.DataFrame([{
        "section_id": section_id,
        "pk_m": pk,
        "accion": "fusion_seccion_puntual",
        "tipo_seccion_diseno": str(spec.shape),
        "ancho_fondo_diseno_m": float(spec.bottom_width_m),
        "profundidad_diseno_m": float(spec.depth_m),
        "talud_izq_hv": float(spec.side_slope_left_hv),
        "talud_der_hv": float(spec.side_slope_right_hv),
        "cota_fondo_diseno_m": float(spec.bottom_elevation_m),
        "offset_centro_diseno_m": float(spec.center_offset_m),
        "n_puntos_originales": int(len(original_pts)),
        "n_puntos_fusionados": int(len(fused_pts)),
        "cota_min_antes_m": float(original_pts["z_m"].min()),
        "cota_min_despues_m": float(fused_pts["z_m"].min()),
        "cota_max_antes_m": float(original_pts["z_m"].max()),
        "cota_max_despues_m": float(fused_pts["z_m"].max()),
    }])
    return sec.reset_index(drop=True), pts_new, resumen, original_tagged.reset_index(drop=True)


def apply_design_channel_to_reach(
    sections_df: pd.DataFrame,
    points_df: pd.DataFrame,
    pk_start_m: float,
    pk_end_m: float,
    spec: DesignChannelSpec,
    bottom_elevation_mode: str = "por_seccion",
    bottom_elevation_value: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aplica la misma geometría de canal a todas las secciones dentro de un tramo.

    bottom_elevation_mode acepta:
    - "por_seccion" / "minima_natural": usa la cota mínima natural local.
    - "rebaje_relativo": usa mínimo natural local menos bottom_elevation_value.
    - "cota_absoluta" / "as_spec": usa spec.bottom_elevation_m para todo el tramo.
    """
    _validate_inputs(sections_df, points_df)
    sec = _ensure_numeric(sections_df, ["pk_m"]).copy().sort_values("pk_m").reset_index(drop=True)
    pk_ini = float(min(pk_start_m, pk_end_m))
    pk_fin = float(max(pk_start_m, pk_end_m))
    if not np.isfinite(pk_ini) or not np.isfinite(pk_fin) or pk_fin < pk_ini:
        raise ValueError("El tramo de fusión no es válido.")
    targets = sec[(sec["pk_m"] >= pk_ini) & (sec["pk_m"] <= pk_fin)].copy()
    if targets.empty:
        raise ValueError("No hay secciones dentro del tramo seleccionado.")

    sec_current = sections_df.copy()
    pts_current = points_df.copy()
    summaries: list[pd.DataFrame] = []
    originals: list[pd.DataFrame] = []
    for _, row in targets.iterrows():
        sid = row["section_id"]
        pts_sid = _section_points(pts_current, sid)
        mode = str(bottom_elevation_mode or "por_seccion").strip().lower()
        if mode in {"por_seccion", "local", "minima_local", "minima_natural", "cota mínima natural"}:
            local_bottom = float(pts_sid["z_m"].min())
        elif mode in {"rebaje", "rebaje_relativo", "bajar fondo", "bajar el fondo"}:
            drop = 0.0 if bottom_elevation_value is None else abs(float(bottom_elevation_value))
            local_bottom = float(pts_sid["z_m"].min()) - drop
        elif mode in {"absoluta", "cota_absoluta", "as_spec", "cota absoluta"}:
            if spec.bottom_elevation_m is None or not np.isfinite(float(spec.bottom_elevation_m)):
                raise ValueError("Para aplicar cota absoluta en tramo debe ingresar una cota de fondo válida.")
            local_bottom = float(spec.bottom_elevation_m)
        else:
            if spec.bottom_elevation_m is None:
                local_bottom = float(pts_sid["z_m"].min())
            else:
                local_bottom = float(spec.bottom_elevation_m)
        local_spec = replace(spec, bottom_elevation_m=local_bottom)
        sec_current, pts_current, summary, original = apply_design_channel_to_section(
            sec_current,
            pts_current,
            sid,
            local_spec,
            keep_original_points=False,
        )
        summary["accion"] = "fusion_tramo"
        summary["pk_ini_tramo_m"] = pk_ini
        summary["pk_fin_tramo_m"] = pk_fin
        summaries.append(summary)
        originals.append(original)

    return (
        sec_current.reset_index(drop=True),
        pts_current.reset_index(drop=True),
        pd.concat(summaries, ignore_index=True, sort=False) if summaries else pd.DataFrame(),
        pd.concat(originals, ignore_index=True, sort=False) if originals else pd.DataFrame(),
    )
