from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_SECTION_COLS = ["section_id", "pk_m"]
REQUIRED_POINT_COLS = ["section_id", "pk_m", "offset_m", "z_m"]


def _ensure_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _section_points(points_df: pd.DataFrame, section_id) -> pd.DataFrame:
    if points_df is None or points_df.empty or "section_id" not in points_df.columns:
        return pd.DataFrame()
    pts = points_df[points_df["section_id"].astype(str) == str(section_id)].copy()
    if pts.empty:
        return pts
    pts = _ensure_numeric(pts, ["pk_m", "offset_m", "z_m"])
    return pts.dropna(subset=["offset_m", "z_m"]).sort_values("offset_m")


def compute_section_relief_stats(sections_df: pd.DataFrame, points_df: pd.DataFrame) -> pd.DataFrame:
    if sections_df is None or sections_df.empty:
        return pd.DataFrame()
    sec = sections_df.copy()
    sec = _ensure_numeric(sec, ["pk_m"])
    rows = []
    for _, row in sec.sort_values("pk_m").iterrows():
        sid = row.get("section_id")
        pts = _section_points(points_df, sid)
        if pts.empty:
            relief = np.nan
            width = np.nan
            npts = 0
            zstd = np.nan
            flatness = np.nan
        else:
            relief = float(pts["z_m"].max() - pts["z_m"].min())
            width = float(pts["offset_m"].max() - pts["offset_m"].min())
            npts = int(len(pts))
            zstd = float(pts["z_m"].std(ddof=0)) if len(pts) > 1 else 0.0
            flatness = float(relief / max(width, 1e-6)) if np.isfinite(width) else np.nan
        rows.append({
            "section_id": sid,
            "pk_m": row.get("pk_m", np.nan),
            "n_puntos": npts,
            "relieve_m": relief,
            "ancho_m": width,
            "desv_z_m": zstd,
            "indice_relieve_por_ancho": flatness,
        })
    out = pd.DataFrame(rows).sort_values("pk_m").reset_index(drop=True)
    if out.empty:
        return out
    out["relieve_vecinos_mediana_m"] = out["relieve_m"].rolling(3, center=True, min_periods=1).median()
    out["ratio_relieve_vecinos"] = out["relieve_m"] / out["relieve_vecinos_mediana_m"].replace(0, np.nan)
    out["sospecha_aplanamiento"] = (
        (out["ratio_relieve_vecinos"].fillna(1.0) < 0.60)
        | (out["n_puntos"].fillna(0) < 4)
        | (out["indice_relieve_por_ancho"].fillna(1.0) < 0.01)
    )
    out["observacion_aplanamiento"] = np.where(
        out["sospecha_aplanamiento"],
        "Sección sospechosa por relieve bajo / pocos puntos / posible cambio de dirección.",
        "OK",
    )
    return out


def _resample_profile_normalized(pts: pd.DataFrame, n_samples: int = 21):
    pts = pts.sort_values("offset_m").copy()
    x = pd.to_numeric(pts["offset_m"], errors="coerce").to_numpy(dtype=float)
    z = pd.to_numeric(pts["z_m"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(z)
    x = x[mask]
    z = z[mask]
    if len(x) < 2:
        raise ValueError("La sección no tiene puntos suficientes para interpolar.")
    width = float(np.max(x) - np.min(x))
    if not np.isfinite(width) or width <= 0:
        width = 1.0
    eta = (x - np.min(x)) / width * 2.0 - 1.0
    eta_grid = np.linspace(-1.0, 1.0, int(max(n_samples, 5)))
    z_grid = np.interp(eta_grid, eta, z)
    zmin = float(np.min(z_grid))
    return eta_grid, z_grid, zmin, width


def _interpolate_section_row(anchor_a: pd.Series, anchor_b: pd.Series, pk_new: float, ratio: float) -> dict:
    new_row = {}
    numeric_pref = [
        "pk_m", "chainage_m", "cota_fondo_m", "cota_borde_izq_m", "cota_borde_der_m",
        "cota_min_m", "cota_max_m", "cota_eje_estimada_m", "ancho_m", "width_m",
        "lon_eje", "lat_eje", "eje_lon", "eje_lat", "km_eje"
    ]
    common = set(anchor_a.index).intersection(anchor_b.index)
    for c in common:
        va, vb = anchor_a.get(c), anchor_b.get(c)
        if c in numeric_pref:
            try:
                va = float(va)
                vb = float(vb)
                new_row[c] = va + ratio * (vb - va)
            except Exception:
                if pd.notna(va):
                    new_row[c] = va
                elif pd.notna(vb):
                    new_row[c] = vb
        else:
            new_row[c] = va if pd.notna(va) else vb
    new_row["pk_m"] = float(pk_new)
    if "chainage_m" in common:
        new_row["chainage_m"] = float(pk_new)
    if "km_eje" in common:
        new_row["km_eje"] = float(pk_new) / 1000.0
    new_row["origen"] = "interpolada_auto_tramo"
    new_row["estado_revision"] = "Rellenada"
    new_row["estado_modelacion"] = "interpolada_auto_tramo"
    new_row["observacion_modelacion"] = "Sección generada automáticamente para suavizar tramo con cambio de dirección / aplanamiento."
    return new_row


def generate_intermediate_sections(
    sections_df: pd.DataFrame,
    points_df: pd.DataFrame,
    pk_start_m: float,
    pk_end_m: float,
    n_sections: int | None = None,
    n_profile_points: int = 21,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Genera secciones interpoladas en un tramo seleccionado.

    Devuelve (sections_new, points_new, resumen).
    """
    if sections_df is None or sections_df.empty:
        raise ValueError("No existen secciones para mejorar.")
    if points_df is None or points_df.empty:
        raise ValueError("No existen puntos de sección para mejorar.")
    sec = sections_df.copy()
    pts = points_df.copy()
    sec = _ensure_numeric(sec, ["pk_m"])
    pts = _ensure_numeric(pts, ["pk_m", "offset_m", "z_m"])
    sec = sec.sort_values("pk_m").reset_index(drop=True)

    pk_ini = float(min(pk_start_m, pk_end_m))
    pk_fin = float(max(pk_start_m, pk_end_m))
    if not np.isfinite(pk_ini) or not np.isfinite(pk_fin) or pk_fin <= pk_ini:
        raise ValueError("El tramo seleccionado no es válido.")

    in_range = (sec["pk_m"] >= pk_ini) & (sec["pk_m"] <= pk_fin)
    target = sec[in_range].copy()
    if target.empty:
        raise ValueError("No hay secciones dentro del tramo seleccionado.")

    idx_first = target.index.min()
    idx_last = target.index.max()
    idx_a = max(idx_first - 1, 0)
    idx_b = min(idx_last + 1, len(sec) - 1)
    anchor_a = sec.iloc[idx_a]
    anchor_b = sec.iloc[idx_b]
    if idx_a == idx_b:
        if idx_first != idx_last:
            anchor_a = sec.iloc[idx_first]
            anchor_b = sec.iloc[idx_last]
        else:
            raise ValueError("Se requieren al menos dos secciones ancla para interpolar el tramo.")

    pts_a = _section_points(pts, anchor_a["section_id"])
    pts_b = _section_points(pts, anchor_b["section_id"])
    if pts_a.empty or pts_b.empty:
        raise ValueError("Las secciones ancla no tienen suficientes puntos reales para interpolar.")

    eta_a, z_a, zmin_a, width_a = _resample_profile_normalized(pts_a, n_profile_points)
    eta_b, z_b, zmin_b, width_b = _resample_profile_normalized(pts_b, n_profile_points)
    eta = np.linspace(-1.0, 1.0, int(max(n_profile_points, 5)))
    # Como ambas rejillas usan el mismo eta regular, la interpolación es directa.
    zrel_a = z_a - zmin_a
    zrel_b = z_b - zmin_b

    n_target = int(n_sections) if n_sections and int(n_sections) > 0 else int(len(target))
    new_pks = np.linspace(float(target["pk_m"].min()), float(target["pk_m"].max()), n_target)

    outside = sec[~in_range].copy()
    new_section_rows = []
    new_point_rows = []
    summary_rows = []

    for i, pk_new in enumerate(new_pks, start=1):
        ratio = 0.0 if pk_fin == pk_ini else (float(pk_new) - float(anchor_a["pk_m"])) / max(float(anchor_b["pk_m"]) - float(anchor_a["pk_m"]), 1e-9)
        ratio = float(np.clip(ratio, 0.0, 1.0))
        zmin = (1.0 - ratio) * zmin_a + ratio * zmin_b
        width = (1.0 - ratio) * width_a + ratio * width_b
        zrel = (1.0 - ratio) * zrel_a + ratio * zrel_b
        offsets = eta * width / 2.0
        zvals = zmin + zrel

        sec_row = _interpolate_section_row(anchor_a, anchor_b, float(pk_new), ratio)
        sec_row["section_id"] = i  # temporal; se reenumerará después de combinar.
        sec_row["section_id_original"] = sec_row.get("section_id_original", f"interp_{pk_new:.2f}")
        sec_row["n_puntos_total"] = len(offsets)
        sec_row["seleccion_modelacion"] = True
        new_section_rows.append(sec_row)

        for j, (xo, zo) in enumerate(zip(offsets, zvals), start=1):
            new_point_rows.append({
                "section_id": i,
                "pk_m": float(pk_new),
                "offset_m": float(xo),
                "z_m": float(zo),
                "point_order": j,
                "origen": "interpolada_auto_tramo",
            })

        summary_rows.append({
            "pk_m": float(pk_new),
            "ratio_interp": ratio,
            "ancho_interp_m": float(width),
            "cota_min_interp_m": float(np.min(zvals)),
            "cota_max_interp_m": float(np.max(zvals)),
        })

    sec_new = pd.DataFrame(new_section_rows)
    pts_new = pd.DataFrame(new_point_rows)

    combined_sec = pd.concat([outside, sec_new], ignore_index=True, sort=False)
    combined_sec = combined_sec.sort_values("pk_m").reset_index(drop=True)
    old_to_new = {}
    for new_id, (_, row) in enumerate(combined_sec.iterrows(), start=1):
        old_to_new[("outside", str(row.get("section_id")))] = new_id
        combined_sec.at[_, "section_id"] = new_id

    # Reconstituye puntos: fuera del rango se conservan, dentro se reemplazan por interpolados.
    outside_ids = set(sec[~in_range]["section_id"].astype(str))
    pts_out = pts[pts["section_id"].astype(str).isin(outside_ids)].copy()
    # Reasignar IDs de puntos fuera de rango según nuevo orden.
    mapping_out = {
        str(orig_sid): int(combined_sec[combined_sec.get("pk_m") == float(sec[sec["section_id"].astype(str) == str(orig_sid)]["pk_m"].iloc[0])]["section_id"].iloc[0])
        for orig_sid in outside_ids
        if not sec[sec["section_id"].astype(str) == str(orig_sid)].empty
    }
    if not pts_out.empty:
        pts_out["section_id"] = pts_out["section_id"].astype(str).map(mapping_out)
    # Reasignar IDs interpolados según PK.
    if not pts_new.empty:
        interp_mapping = {
            float(row["pk_m"]): int(row["section_id"])
            for _, row in combined_sec[combined_sec.get("origen", "").astype(str).str.contains("interpolada_auto_tramo", na=False)].iterrows()
        }
        pts_new["section_id"] = pts_new["pk_m"].map(interp_mapping)
    combined_pts = pd.concat([pts_out, pts_new], ignore_index=True, sort=False)
    combined_pts = combined_pts.sort_values(["pk_m", "section_id", "offset_m"]).reset_index(drop=True)

    # Ajusta review/modelación visibles.
    combined_sec["estado_revision"] = combined_sec.get("estado_revision", "")
    mask_interp = combined_sec.get("origen", pd.Series("", index=combined_sec.index)).astype(str).str.contains("interpolada_auto_tramo", na=False)
    combined_sec.loc[mask_interp, "estado_revision"] = "Rellenada"
    combined_sec.loc[mask_interp, "seleccion_modelacion"] = True

    resumen = pd.DataFrame(summary_rows)
    resumen["pk_ini_tramo_m"] = pk_ini
    resumen["pk_fin_tramo_m"] = pk_fin
    resumen["section_anchor_upstream"] = str(anchor_a.get("section_id"))
    resumen["section_anchor_downstream"] = str(anchor_b.get("section_id"))
    return combined_sec, combined_pts, resumen
