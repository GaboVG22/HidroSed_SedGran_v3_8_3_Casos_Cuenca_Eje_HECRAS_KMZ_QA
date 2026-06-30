from __future__ import annotations

import math
import numpy as np
import pandas as pd

G = 9.81


def _sf(x, default=np.nan):
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except Exception:
        return default


def general_scour_methods(profile_df: pd.DataFrame, d50_m: float = 0.05, d90_m: float = 0.15) -> pd.DataFrame:
    """Preliminary general scour comparison: Neill, Lischtvan-Levediev, Laursen and shear-based."""
    if profile_df is None or profile_df.empty:
        return pd.DataFrame()
    rows = []
    for _, r in profile_df.iterrows():
        y = _sf(r.get("tirante_max_m"), np.nan)
        V = _sf(r.get("velocidad_m_s"), np.nan)
        Fr = _sf(r.get("Froude"), np.nan)
        Rh = _sf(r.get("radio_hidraulico_m"), np.nan)
        S = _sf(r.get("pendiente_energia", 0.01), 0.01)
        tau = 1000 * G * Rh * S if np.isfinite(Rh) else np.nan
        theta = tau / ((2650 - 1000) * G * max(d50_m, 1e-6)) if np.isfinite(tau) else np.nan
        methods = {
            "Neill preliminar": max(0.0, 0.30 * y + 0.10 * V) if np.isfinite(y) and np.isfinite(V) else np.nan,
            "Lischtvan-Levediev preliminar": max(0.0, 0.18 * y * (max(V, 0) / max(math.sqrt(G * max(y, 1e-6)), 1e-9)) ** 0.6) if np.isfinite(y) and np.isfinite(V) else np.nan,
            "Laursen preliminar": max(0.0, 0.20 * y * max(Fr, 0) ** 0.7) if np.isfinite(y) and np.isfinite(Fr) else np.nan,
            "Esfuerzo cortante crítico": max(0.0, (theta - 0.047) * 8 * d90_m) if np.isfinite(theta) else np.nan,
        }
        for m, sc in methods.items():
            rows.append({
                "section_id": r.get("section_id"), "pk_m": r.get("pk_m"), "T_anios": r.get("T_anios"),
                "metodo_socavacion_general": m, "socavacion_general_m": sc,
                "tau_Pa": tau, "Shields": theta,
                "advertencia": "preliminar; contrastar con método normativo/manual aplicable"
            })
    return pd.DataFrame(rows)


def local_scour_preliminary(hydraulic_row: dict, structure_type: str = "pila", width_m: float = 1.0, attack_angle_deg: float = 0.0, bed_factor: float = 1.0, foundation_level_m: float | None = None) -> dict:
    y = _sf(hydraulic_row.get("tirante_max_m"), np.nan)
    V = _sf(hydraulic_row.get("velocidad_m_s"), np.nan)
    Fr = _sf(hydraulic_row.get("Froude"), np.nan)
    a = max(_sf(width_m, 1.0), 1e-6)
    angle_factor = 1.0 + min(abs(_sf(attack_angle_deg, 0.0)), 45.0) / 90.0
    typ = str(structure_type).lower()
    if "estrib" in typ:
        ys = 1.1 * angle_factor * bed_factor * y * max(Fr, 0.05) ** 0.43 if np.isfinite(y) and np.isfinite(Fr) else np.nan
    elif "contr" in typ or "alcantar" in typ or "caj" in typ:
        ys = 0.6 * y * (max(V, 0.0) / max(math.sqrt(9.81 * max(y, 1e-6)), 1e-9)) if np.isfinite(y) and np.isfinite(V) else np.nan
    else:
        ys = 2.0 * angle_factor * bed_factor * a * max(y / max(a, 1e-6), 0.1) ** 0.35 * max(Fr, 0.05) ** 0.43 if np.isfinite(y) and np.isfinite(Fr) else np.nan
    zbed = _sf(hydraulic_row.get("cota_fondo_m"), np.nan)
    z_scour = zbed - ys if np.isfinite(zbed) and np.isfinite(ys) else np.nan
    warn = []
    if foundation_level_m is None:
        warn.append("sin cota de fundación")
    elif np.isfinite(z_scour) and foundation_level_m > z_scour:
        warn.append("fundación dentro de zona socavable")
    return {
        "tipo_obra": structure_type,
        "ancho_efectivo_m": a,
        "angulo_ataque_deg": attack_angle_deg,
        "socavacion_local_m": ys,
        "cota_fondo_socavado_local_m": z_scour,
        "advertencia": "; ".join(warn) or "OK",
    }


def protection_design_preliminary(velocity_m_s: float, shear_pa: float | None = None, side_slope_hv: float = 2.0, specific_gravity_stone: float = 2.65, safety_factor: float = 1.25) -> pd.DataFrame:
    V = max(_sf(velocity_m_s, 0.0), 0.0)
    s = max(_sf(specific_gravity_stone, 2.65), 1.1)
    fs = max(_sf(safety_factor, 1.25), 1.0)
    tau = _sf(shear_pa, np.nan)
    # Isbash-style preliminary stable diameter.
    D50_isbash = fs * V * V / (1.7 * G * (s - 1.0)) if V > 0 else np.nan
    D50_tau = fs * tau / (0.047 * 1000 * G * (s - 1.0)) if np.isfinite(tau) and tau > 0 else np.nan
    D50 = np.nanmax([D50_isbash, D50_tau]) if np.isfinite(D50_isbash) or np.isfinite(D50_tau) else np.nan
    rows = []
    rows.append({"tipo_proteccion": "enrocado / escollera", "D50_min_m": D50, "espesor_min_m": 1.5 * D50 if np.isfinite(D50) else np.nan, "enterramiento_pie_m": 2.0 * D50 if np.isfinite(D50) else np.nan, "longitud_transicion_recomendada_m": 6.0 * D50 if np.isfinite(D50) else np.nan, "filtro_geotextil": "sí, salvo filtro granular diseñado", "advertencia": "predimensionamiento; verificar estabilidad, disponibilidad de roca y Manual de Carreteras"})
    rows.append({"tipo_proteccion": "gaviones", "D50_min_m": D50 * 0.6 if np.isfinite(D50) else np.nan, "espesor_min_m": max(0.30, D50) if np.isfinite(D50) else np.nan, "enterramiento_pie_m": 1.5 * D50 if np.isfinite(D50) else np.nan, "longitud_transicion_recomendada_m": 5.0 * D50 if np.isfinite(D50) else np.nan, "filtro_geotextil": "obligatorio", "advertencia": "verificar malla, abrasión, socavación de pie y durabilidad"})
    rows.append({"tipo_proteccion": "colchón Reno", "D50_min_m": D50 * 0.5 if np.isfinite(D50) else np.nan, "espesor_min_m": max(0.17, 0.8 * D50) if np.isfinite(D50) else np.nan, "enterramiento_pie_m": 1.5 * D50 if np.isfinite(D50) else np.nan, "longitud_transicion_recomendada_m": 5.0 * D50 if np.isfinite(D50) else np.nan, "filtro_geotextil": "obligatorio", "advertencia": "útil en taludes y fondos; revisar anclaje y borde de transición"})
    return pd.DataFrame(rows)
