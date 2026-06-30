from __future__ import annotations

import numpy as np
import pandas as pd


def downstream_scenarios(
    base_level_m: float,
    mean_sea_level_m: float | None = None,
    high_tide_m: float | None = None,
    design_tide_m: float | None = None,
    storm_surge_m: float = 0.0,
    meteorological_setup_m: float = 0.0,
    wetland_level_m: float | None = None,
    lagoon_bar_level_m: float | None = None,
) -> pd.DataFrame:
    """Creates downstream control scenarios for outfalls, wetlands and tidal influence."""
    rows = []
    def add(name, level, components, warning=""):
        rows.append({"escenario": name, "cota_control_m": float(level) if level is not None and np.isfinite(float(level)) else np.nan, "componentes": components, "advertencia": warning or "OK"})
    add("sin influencia aguas abajo", base_level_m, "pendiente normal / condición base")
    if mean_sea_level_m is not None:
        add("marea normal", mean_sea_level_m, "nivel medio del mar")
    if high_tide_m is not None:
        add("pleamar máxima", high_tide_m, "pleamar máxima")
    if design_tide_m is not None:
        add("marea de diseño", design_tide_m + storm_surge_m + meteorological_setup_m, "pleamar diseño + marejada + sobre-elevación meteorológica")
    if wetland_level_m is not None:
        add("humedal / laguna", wetland_level_m, "nivel de humedal o laguna")
    if lagoon_bar_level_m is not None:
        add("barra litoral", lagoon_bar_level_m, "cota de barra litoral / embalsamiento")
    if design_tide_m is not None and wetland_level_m is not None:
        add("combinado lluvia-marea-humedal", max(design_tide_m + storm_surge_m + meteorological_setup_m, wetland_level_m), "máximo entre marea de diseño ajustada y humedal", "revisar simultaneidad hidrológica")
    return pd.DataFrame(rows)


def audit_downstream_influence(profile_df: pd.DataFrame, scenarios_df: pd.DataFrame, influence_length_m: float = 1000.0) -> pd.DataFrame:
    """Estimates sections affected by a downstream fixed level using a simple backwater screening."""
    if profile_df is None or profile_df.empty or scenarios_df is None or scenarios_df.empty:
        return pd.DataFrame()
    prof = profile_df.copy()
    if "T_anios" in prof.columns:
        # highest return period by default for screening
        prof = prof[pd.to_numeric(prof["T_anios"], errors="coerce") == pd.to_numeric(prof["T_anios"], errors="coerce").max()].copy()
    prof = prof.sort_values("pk_m")
    pkmax = float(pd.to_numeric(prof["pk_m"], errors="coerce").max())
    rows = []
    for _, sc in scenarios_df.iterrows():
        level = float(sc.get("cota_control_m", np.nan))
        if not np.isfinite(level):
            continue
        affected = prof[pd.to_numeric(prof["pk_m"], errors="coerce") >= pkmax - float(influence_length_m)].copy()
        if affected.empty:
            continue
        affected["delta_control_m"] = level - pd.to_numeric(affected.get("cota_agua_m"), errors="coerce")
        n_aff = int((affected["delta_control_m"] > 0.05).sum())
        rows.append({
            "escenario": sc.get("escenario"),
            "cota_control_m": level,
            "longitud_revision_m": influence_length_m,
            "secciones_afectadas": n_aff,
            "delta_max_m": float(max(affected["delta_control_m"].max(), 0.0)) if affected["delta_control_m"].notna().any() else np.nan,
            "advertencia": "control aguas abajo puede elevar perfil" if n_aff > 0 else "sin influencia relevante en screening",
        })
    return pd.DataFrame(rows)
