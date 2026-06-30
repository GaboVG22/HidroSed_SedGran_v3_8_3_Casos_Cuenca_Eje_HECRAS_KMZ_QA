from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

G = 9.81
DEFAULT_PERIODS = [2, 5, 10, 25, 50, 100, 200]


def _safe_float(x, default=np.nan):
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except Exception:
        return default


def morphometry_table(
    area_km2: float,
    length_main_km: float,
    z_max_m: float,
    z_min_m: float,
    perimeter_km: float | None = None,
    drainage_length_km: float | None = None,
    urban_pct: float = 0.0,
    rural_pct: float = 0.0,
    agricultural_pct: float = 0.0,
    forest_pct: float = 0.0,
    natural_pct: float = 0.0,
    regime: str = "pluvial",
) -> pd.DataFrame:
    """Builds a reusable morphometric summary from manual or file data."""
    A = max(_safe_float(area_km2, 0), 0)
    L = max(_safe_float(length_main_km, 0), 0)
    zmax = _safe_float(z_max_m, np.nan)
    zmin = _safe_float(z_min_m, np.nan)
    H = zmax - zmin if np.isfinite(zmax) and np.isfinite(zmin) else np.nan
    P = _safe_float(perimeter_km, np.nan)
    D = _safe_float(drainage_length_km, np.nan)
    compactness = P / (2 * math.sqrt(math.pi * A)) if A > 0 and np.isfinite(P) and P > 0 else np.nan
    form_factor = A / (L * L) if L > 0 else np.nan
    drainage_density = D / A if A > 0 and np.isfinite(D) else np.nan
    slope_channel = H / (L * 1000) if L > 0 and np.isfinite(H) else np.nan
    zmean = (zmax + zmin) / 2 if np.isfinite(zmax) and np.isfinite(zmin) else np.nan
    shape = "alargada" if np.isfinite(form_factor) and form_factor < 0.30 else ("intermedia" if np.isfinite(form_factor) and form_factor < 0.75 else "compacta")
    rows = [
        ("area_cuenca_km2", A, "km²", "Área drenante"),
        ("longitud_cauce_principal_km", L, "km", "Longitud del cauce principal"),
        ("desnivel_m", H, "m", "Cota máxima menos cota mínima"),
        ("pendiente_media_cauce_m_m", slope_channel, "m/m", "Desnivel / longitud de cauce"),
        ("altitud_media_m", zmean, "m", "Promedio preliminar entre cota máxima y mínima"),
        ("altitud_maxima_m", zmax, "m", "Cota máxima"),
        ("altitud_minima_m", zmin, "m", "Cota mínima"),
        ("perimetro_cuenca_km", P, "km", "Perímetro de cuenca"),
        ("coeficiente_compacidad", compactness, "-", "Kc = P/(2√(πA))"),
        ("factor_forma", form_factor, "-", "Ff = A/L²"),
        ("forma_cuenca", shape, "texto", "Clasificación preliminar según Ff"),
        ("densidad_drenaje_km_km2", drainage_density, "km/km²", "Longitud total de drenaje / área"),
        ("regimen_hidrologico", regime, "texto", "pluvial, nival o nivo-pluvial"),
        ("porcentaje_urbano", urban_pct, "%", "Uso urbano"),
        ("porcentaje_rural", rural_pct, "%", "Uso rural"),
        ("porcentaje_agricola", agricultural_pct, "%", "Uso agrícola"),
        ("porcentaje_forestal", forest_pct, "%", "Uso forestal"),
        ("porcentaje_natural", natural_pct, "%", "Uso natural"),
    ]
    return pd.DataFrame(rows, columns=["parametro", "valor", "unidad", "descripcion"])


def tc_methods(
    length_main_km: float,
    elevation_diff_m: float,
    area_km2: float | None = None,
    user_tc_h: float | None = None,
    rector_method: str = "Mediana de métodos",
) -> pd.DataFrame:
    """Compares concentration time methods with applicability warnings.

    The equations are preliminary/normative-audit formulas and keep units explicit.
    """
    Lkm = max(_safe_float(length_main_km, 0), 0)
    Lm = Lkm * 1000.0
    H = max(_safe_float(elevation_diff_m, 0), 0)
    A = max(_safe_float(area_km2, np.nan), 0) if area_km2 is not None else np.nan
    S = H / max(Lm, 1e-9)
    rows = []

    def add(name, tc_h, formula, validity, warn=""):
        rows.append({
            "metodo": name,
            "tc_h": float(tc_h) if np.isfinite(tc_h) else np.nan,
            "tc_min": float(tc_h) * 60 if np.isfinite(tc_h) else np.nan,
            "formula": formula,
            "variables": f"L={Lkm:.3f} km; H={H:.2f} m; S={S:.5f}; A={A:.3f} km²" if np.isfinite(A) else f"L={Lkm:.3f} km; H={H:.2f} m; S={S:.5f}",
            "rango_validez": validity,
            "advertencia": warn or "OK",
        })

    warn_geom = "Datos insuficientes: requiere L>0, H>0" if Lkm <= 0 or H <= 0 else ""
    if not warn_geom:
        kirpich_min = 0.01947 * (Lm ** 0.77) * (S ** -0.385)
        add("California Highways / Manual de Carreteras", kirpich_min / 60.0, "Tc[min]=0,01947·L[m]^0,77·S^-0,385", "cuencas pequeñas/medianas, cauces naturales", "OK")
        add("Kirpich", kirpich_min / 60.0, "Tc[min]=0,0195·L[m]^0,77·S^-0,385", "cuencas rurales empinadas", "OK")
        temez_h = 0.3 * ((Lkm / max(S ** 0.25, 1e-9)) ** 0.76)
        add("Témez", temez_h, "Tc[h]=0,3·(L[km]/S^0,25)^0,76", "cuencas naturales no reguladas", "OK")
        if np.isfinite(A) and A > 0:
            giandotti_h = (4 * math.sqrt(A) + 1.5 * Lkm) / max(0.8 * math.sqrt(H), 1e-9)
            add("Giandotti", giandotti_h, "Tc[h]=(4√A+1,5L)/(0,8√H)", "cuencas medianas; requiere A y H", "OK")
            ventura_h = 0.1272 * math.sqrt(A / max(S, 1e-9))
            add("Ventura", ventura_h, "Tc[h]=0,1272·√(A/S)", "cuencas naturales; requiere A y S", "OK")
            bw_h = 0.243 * (Lkm / max((A ** 0.1) * (S ** 0.2), 1e-9))
            add("Bransby-Williams", bw_h, "Tc[h]=0,243·L/(A^0,1·S^0,2)", "cuencas rurales; uso comparativo", "OK")
        else:
            add("Giandotti", np.nan, "Tc[h]=(4√A+1,5L)/(0,8√H)", "requiere A y H", "No aplicable: falta área")
            add("Ventura", np.nan, "Tc[h]=0,1272·√(A/S)", "requiere A y S", "No aplicable: falta área")
            add("Bransby-Williams", np.nan, "Tc[h]=0,243·L/(A^0,1·S^0,2)", "requiere A y S", "No aplicable: falta área")
    else:
        for m in ["California Highways / Manual de Carreteras", "Kirpich", "Témez", "Giandotti", "Ventura", "Bransby-Williams"]:
            add(m, np.nan, "ver método", "requiere geometría básica", warn_geom)

    if user_tc_h is not None and np.isfinite(_safe_float(user_tc_h, np.nan)) and _safe_float(user_tc_h, np.nan) > 0:
        add("Valor manual justificado", float(user_tc_h), "Tc ingresado por usuario", "requiere justificación documental", "Requiere respaldo técnico")

    df = pd.DataFrame(rows)
    valid = df["tc_h"].dropna()
    avg = valid.mean() if len(valid) else np.nan
    med = valid.median() if len(valid) else np.nan
    df.loc[len(df)] = {"metodo": "Promedio de métodos", "tc_h": avg, "tc_min": avg * 60 if np.isfinite(avg) else np.nan, "formula": "promedio de métodos válidos", "variables": "", "rango_validez": "comparativo", "advertencia": "usar solo con criterio técnico"}
    df.loc[len(df)] = {"metodo": "Mediana de métodos", "tc_h": med, "tc_min": med * 60 if np.isfinite(med) else np.nan, "formula": "mediana de métodos válidos", "variables": "", "rango_validez": "comparativo robusto", "advertencia": "usar solo con criterio técnico"}
    df["metodo_rector"] = df["metodo"].astype(str).eq(str(rector_method))
    if len(valid) >= 2:
        spread = (valid.max() - valid.min()) / max(valid.median(), 1e-9) * 100
        df["diferencia_global_pct"] = spread
        if spread > 25:
            df["advertencia_comparacion"] = "Diferencia entre métodos >25%; justificar método rector."
        else:
            df["advertencia_comparacion"] = "Comparación dentro de rango razonable."
    else:
        df["diferencia_global_pct"] = np.nan
        df["advertencia_comparacion"] = "No hay suficientes métodos válidos."
    return df


def select_tc_value(tc_df: pd.DataFrame, rector_method: str) -> tuple[float, str]:
    if tc_df is None or tc_df.empty:
        return np.nan, "sin_datos"
    hit = tc_df[tc_df["metodo"].astype(str) == str(rector_method)]
    if hit.empty:
        hit = tc_df[tc_df.get("metodo_rector", pd.Series(False)).fillna(False)]
    if hit.empty:
        hit = tc_df.dropna(subset=["tc_h"]).head(1)
    if hit.empty:
        return np.nan, "sin_metodo_valido"
    return _safe_float(hit.iloc[0]["tc_h"], np.nan), str(hit.iloc[0]["metodo"])


def idf_from_p24_duration(
    p24_table: pd.DataFrame,
    cd_table: pd.DataFrame,
    periods: Iterable[float] = DEFAULT_PERIODS,
    durations_h: Iterable[float] = (0.25, 0.5, 1, 2, 3, 6, 12, 24),
) -> pd.DataFrame:
    """Computes editable IDF curves: i(T,t)=P24(T)*Cd(t)/t."""
    p = p24_table.copy()
    c = cd_table.copy()
    # Accept common column aliases.
    pcols = {col.lower(): col for col in p.columns}
    ccols = {col.lower(): col for col in c.columns}
    Tcol = pcols.get("t_anios") or pcols.get("t") or p.columns[0]
    Pcol = pcols.get("p24_mm") or pcols.get("p24") or p.columns[1]
    Dcol = ccols.get("duracion_h") or ccols.get("duracion") or c.columns[0]
    Cdcol = ccols.get("cd") or ccols.get("coef_duracion") or c.columns[1]
    pT = pd.to_numeric(p[Tcol], errors="coerce").to_numpy(dtype=float)
    pV = pd.to_numeric(p[Pcol], errors="coerce").to_numpy(dtype=float)
    dT = pd.to_numeric(c[Dcol], errors="coerce").to_numpy(dtype=float)
    dV = pd.to_numeric(c[Cdcol], errors="coerce").to_numpy(dtype=float)
    maskp = np.isfinite(pT) & np.isfinite(pV)
    maskd = np.isfinite(dT) & np.isfinite(dV) & (dT > 0)
    if maskp.sum() < 1 or maskd.sum() < 1:
        return pd.DataFrame()
    pT, pV = pT[maskp], pV[maskp]
    dT, dV = dT[maskd], dV[maskd]
    orderp = np.argsort(pT); pT, pV = pT[orderp], pV[orderp]
    orderd = np.argsort(dT); dT, dV = dT[orderd], dV[orderd]
    rows = []
    for T in periods:
        T = float(T)
        P24 = np.interp(T, pT, pV)
        extrap_T = bool(T < np.min(pT) or T > np.max(pT))
        for dur in durations_h:
            dur = float(dur)
            Cd = np.interp(dur, dT, dV)
            extrap_d = bool(dur < np.min(dT) or dur > np.max(dT))
            i = P24 * Cd / max(dur, 1e-9)
            rows.append({
                "T_anios": T,
                "duracion_h": dur,
                "P24_mm": float(P24),
                "Cd": float(Cd),
                "intensidad_mm_h": float(i),
                "extrapola_T": extrap_T,
                "extrapola_duracion": extrap_d,
                "advertencia": "; ".join([x for x, flag in [("extrapola T", extrap_T), ("extrapola duración", extrap_d)] if flag]) or "OK",
            })
    return pd.DataFrame(rows)


def interpolate_intensity(idf_df: pd.DataFrame, T: float, duration_h: float) -> float:
    if idf_df is None or idf_df.empty:
        return np.nan
    df = idf_df.copy()
    df["T_anios"] = pd.to_numeric(df["T_anios"], errors="coerce")
    df["duracion_h"] = pd.to_numeric(df["duracion_h"], errors="coerce")
    df["intensidad_mm_h"] = pd.to_numeric(df["intensidad_mm_h"], errors="coerce")
    hit = df[np.isclose(df["T_anios"], float(T))].sort_values("duracion_h")
    if hit.empty:
        # Interpolate by nearest durations first, then by T for requested duration.
        rows = []
        for tval, grp in df.groupby("T_anios"):
            rows.append((float(tval), float(np.interp(duration_h, grp["duracion_h"], grp["intensidad_mm_h"]))))
        rows = sorted(rows)
        return float(np.interp(T, [r[0] for r in rows], [r[1] for r in rows]))
    return float(np.interp(duration_h, hit["duracion_h"], hit["intensidad_mm_h"]))


def rational_method_design(area_km2: float, idf_df: pd.DataFrame, tc_h: float, c_base: float, periods: Iterable[float] = DEFAULT_PERIODS, c_factors: dict | None = None) -> pd.DataFrame:
    A = _safe_float(area_km2, np.nan)
    C0 = _safe_float(c_base, np.nan)
    rows = []
    for T in periods:
        factor = 1.0
        if c_factors:
            factor = _safe_float(c_factors.get(float(T), c_factors.get(int(T), 1.0)), 1.0)
        C = C0 * factor
        i = interpolate_intensity(idf_df, float(T), float(tc_h))
        Q = C * i * A / 3.6 if np.isfinite(C) and np.isfinite(i) and np.isfinite(A) else np.nan
        warnings = []
        if C < 0.03: warnings.append("C<0,03")
        if C > 0.80: warnings.append("C>0,80")
        if not np.isfinite(i): warnings.append("sin intensidad IDF")
        if np.isfinite(A) and A > 25: warnings.append("área alta para método racional; justificar")
        rows.append({
            "T_anios": float(T), "metodo": "Racional", "Q_m3s": Q,
            "C_base": C0, "factor_C": factor, "C_final": C,
            "intensidad_mm_h": i, "duracion_h": tc_h, "area_km2": A,
            "formula": "Q=C·i·A/3,6", "advertencia": "; ".join(warnings) or "OK",
        })
    return pd.DataFrame(rows)


def verni_king_modified(area_km2: float, p24_table: pd.DataFrame, c10: float = 1.0, ratios: dict | None = None, periods: Iterable[float] = DEFAULT_PERIODS, p24_constant_mm: float | None = None, audit_constant: bool = False) -> pd.DataFrame:
    p = p24_table.copy()
    Tcol = "T_anios" if "T_anios" in p.columns else p.columns[0]
    Pcol = "P24_mm" if "P24_mm" in p.columns else p.columns[1]
    pT = pd.to_numeric(p[Tcol], errors="coerce").to_numpy(dtype=float)
    pV = pd.to_numeric(p[Pcol], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(pT) & np.isfinite(pV)
    pT, pV = pT[mask], pV[mask]
    order = np.argsort(pT); pT, pV = pT[order], pV[order]
    A = max(_safe_float(area_km2, 0), 0)
    C10 = _safe_float(c10, 1.0)
    ratios = ratios or {2: 0.68, 5: 0.86, 10: 1.00, 25: 1.18, 50: 1.32, 100: 1.48, 200: 1.65}
    rows = []
    for T in periods:
        T = float(T)
        P24 = float(np.interp(T, pT, pV)) if len(pT) else np.nan
        ratio = _safe_float(ratios.get(int(T), ratios.get(float(T), 1.0)), 1.0)
        CT = C10 * ratio
        Q_norm = CT * 0.00618 * (P24 ** 1.24) * (A ** 0.88) if np.isfinite(P24) else np.nan
        Q_const = np.nan
        diff = np.nan
        diff_pct = np.nan
        warn = "OK"
        if audit_constant and p24_constant_mm is not None:
            Pc = _safe_float(p24_constant_mm, np.nan)
            Q_const = CT * 0.00618 * (Pc ** 1.24) * (A ** 0.88) if np.isfinite(Pc) else np.nan
            diff = Q_const - Q_norm if np.isfinite(Q_const) and np.isfinite(Q_norm) else np.nan
            diff_pct = diff / max(abs(Q_norm), 1e-9) * 100 if np.isfinite(diff) else np.nan
            warn = "Auditoría: P24 constante no coincide con modo normativo P24(T)." if np.isfinite(Q_const) and abs(diff_pct) > 1 else "OK"
        rows.append({"T_anios": T, "metodo": "Verni-King Modificado", "Q_m3s": Q_norm, "C10": C10, "ratio_CT_C10": ratio, "C_T": CT, "P24_T_mm": P24, "Q_P24_constante_m3s": Q_const, "diferencia_m3s": diff, "diferencia_pct": diff_pct, "formula": "Q=C(T)·0,00618·P24(T)^1,24·A^0,88", "advertencia": warn})
    return pd.DataFrame(rows)


def dga_ac_design(q10_m3s: float, alpha: float = 1.25, ratios: dict | None = None, periods: Iterable[float] = DEFAULT_PERIODS, zone: str = "Zona homogénea manual", curve: str = "media") -> pd.DataFrame:
    Q10 = _safe_float(q10_m3s, np.nan)
    a = _safe_float(alpha, np.nan)
    ratios = ratios or {2: 0.55, 5: 0.78, 10: 1.00, 25: 1.28, 50: 1.52, 100: 1.80, 200: 2.10}
    rows = []
    for T in periods:
        r = _safe_float(ratios.get(int(T), ratios.get(float(T), np.nan)), np.nan)
        qmed = Q10 * r if np.isfinite(Q10) and np.isfinite(r) else np.nan
        qinst = a * qmed if np.isfinite(a) and np.isfinite(qmed) else np.nan
        warn = []
        if not np.isfinite(a): warn.append("falta alpha")
        if np.isfinite(a) and not (1.0 <= a <= 2.0): warn.append("alpha fuera de rango usual")
        if not np.isfinite(Q10): warn.append("falta Q10")
        rows.append({"T_anios": float(T), "metodo": "DGA-AC", "zona_homogenea": zone, "curva": curve, "Qmed_m3s": qmed, "alpha_inst": a, "Q_m3s": qinst, "ratio_QT_Q10": r, "formula": "Qinst(T)=α·Qmed(T)", "advertencia": "; ".join(warn) or "OK"})
    return pd.DataFrame(rows)


def scs_cn_runoff(area_km2: float, p24_table: pd.DataFrame, cn: float, periods: Iterable[float] = DEFAULT_PERIODS, duration_h: float = 24.0) -> pd.DataFrame:
    p = p24_table.copy()
    Tcol = "T_anios" if "T_anios" in p.columns else p.columns[0]
    Pcol = "P24_mm" if "P24_mm" in p.columns else p.columns[1]
    pT = pd.to_numeric(p[Tcol], errors="coerce").to_numpy(dtype=float)
    pV = pd.to_numeric(p[Pcol], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(pT) & np.isfinite(pV)
    pT, pV = pT[mask], pV[mask]
    order = np.argsort(pT); pT, pV = pT[order], pV[order]
    A = _safe_float(area_km2, np.nan)
    CN = min(max(_safe_float(cn, 75), 30), 100)
    Smm = 25400.0 / CN - 254.0
    Ia = 0.2 * Smm
    rows = []
    for T in periods:
        P = float(np.interp(float(T), pT, pV)) if len(pT) else np.nan
        Pe = ((P - Ia) ** 2) / (P + 0.8 * Smm) if np.isfinite(P) and P > Ia else 0.0
        volume_m3 = Pe / 1000.0 * A * 1e6 if np.isfinite(A) else np.nan
        Qtri = 0.208 * A * Pe / max(duration_h, 1e-9) if np.isfinite(A) else np.nan
        rows.append({"T_anios": float(T), "metodo": "SCS-CN preliminar", "Q_m3s": Qtri, "CN": CN, "P24_mm": P, "Pe_mm": Pe, "volumen_escorrentia_m3": volume_m3, "formula": "Pe=(P-0,2S)^2/(P+0,8S); Qp preliminar", "advertencia": "hidrograma preliminar; requiere distribución temporal"})
    return pd.DataFrame(rows)


def adopt_design_flows(method_tables: list[pd.DataFrame], criterion: str = "Mediana", manual_values: dict | None = None, declared_criterion: str | None = None, weights: dict | None = None, required_periods: Iterable[float] = DEFAULT_PERIODS) -> pd.DataFrame:
    dfs = []
    for df in method_tables:
        if df is not None and not df.empty and {"T_anios", "metodo", "Q_m3s"}.issubset(df.columns):
            dfs.append(df[["T_anios", "metodo", "Q_m3s"]].copy())
    if not dfs:
        return pd.DataFrame()
    long = pd.concat(dfs, ignore_index=True)
    long["T_anios"] = pd.to_numeric(long["T_anios"], errors="coerce")
    long["Q_m3s"] = pd.to_numeric(long["Q_m3s"], errors="coerce")
    piv = long.pivot_table(index="T_anios", columns="metodo", values="Q_m3s", aggfunc="mean").reset_index()
    method_cols = [c for c in piv.columns if c != "T_anios"]
    qmat = piv[method_cols]
    piv["Promedio"] = qmat.mean(axis=1)
    piv["Mediana"] = qmat.median(axis=1)
    piv["Máximo"] = qmat.max(axis=1)
    adopted = []
    crit = str(criterion)
    for _, row in piv.iterrows():
        T = float(row["T_anios"])
        val = np.nan
        if crit.lower().startswith("prom"):
            val = row["Promedio"]
        elif crit.lower().startswith("med"):
            val = row["Mediana"]
        elif "max" in crit.lower() or "máx" in crit.lower() or "envol" in crit.lower():
            val = row["Máximo"]
        elif crit in method_cols:
            val = row[crit]
        elif crit.lower().startswith("ponder") and weights:
            num = 0.0; den = 0.0
            for m in method_cols:
                w = _safe_float(weights.get(m, 0), 0)
                q = _safe_float(row[m], np.nan)
                if np.isfinite(q) and w > 0:
                    num += w * q; den += w
            val = num / den if den > 0 else np.nan
        elif crit.lower().startswith("manual") and manual_values:
            val = _safe_float(manual_values.get(T, manual_values.get(int(T), np.nan)), np.nan)
        adopted.append(val)
    piv["Adoptado"] = adopted
    piv["Criterio"] = criterion
    declared = declared_criterion or criterion
    obs = []
    sem = []
    for _, row in piv.iterrows():
        msgs = []
        severity = "verde"
        vals = pd.to_numeric(row[method_cols], errors="coerce").dropna()
        T = row["T_anios"]
        adopted_val = _safe_float(row["Adoptado"], np.nan)
        if len(vals) >= 2:
            spread = (vals.max() - vals.min()) / max(vals.median(), 1e-9) * 100
            if spread > 50:
                msgs.append("diferencia entre métodos >50%")
                severity = "amarillo"
            if spread > 100:
                severity = "rojo"
        if str(declared).lower().startswith("prom") and np.isfinite(adopted_val) and abs(adopted_val - row["Promedio"]) > max(0.01, 0.03 * max(abs(row["Promedio"]), 1e-9)):
            msgs.append("criterio declarado promedio no coincide con adoptado")
            severity = "rojo"
        if str(criterion).lower().startswith("manual") and not np.isfinite(adopted_val):
            msgs.append("valor manual sin dato/justificación")
            severity = "rojo"
        if float(T) not in [float(x) for x in required_periods]:
            msgs.append("período no requerido o no estándar")
            severity = max(severity, "amarillo") if severity != "rojo" else "rojo"
        obs.append("; ".join(msgs) or "consistente")
        sem.append(severity)
    piv["auditoria_adopcion"] = obs
    piv["semaforo"] = sem
    return piv
