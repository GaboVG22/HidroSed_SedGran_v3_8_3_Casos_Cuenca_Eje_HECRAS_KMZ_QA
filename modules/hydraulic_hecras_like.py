
from __future__ import annotations

import math
import numpy as np
import pandas as pd


G = 9.81


def _section_points(points_df: pd.DataFrame, section_id: int) -> pd.DataFrame:
    df = points_df[points_df["section_id"] == section_id].copy()
    if df.empty:
        raise ValueError(f"No hay puntos para la sección {section_id}.")
    df = df.sort_values("offset_m")
    df = df[np.isfinite(df["offset_m"]) & np.isfinite(df["z_m"])]
    if len(df) < 3:
        raise ValueError(f"La sección {section_id} tiene menos de 3 puntos válidos.")
    return df


def _section_points_safe(points_df: pd.DataFrame, sec_row: pd.Series, fallback_width: float = 30.0) -> tuple[pd.DataFrame, str]:
    """Obtiene puntos de sección sin detener el modelo.

    Si la tabla de puntos no contiene una sección generada en el resumen
    (caso típico: "No hay puntos para la sección 581"), construye una
    sección trapezoidal sintética mínima a partir de ancho/cota disponible.
    Esto permite continuar el cálculo y marca el resultado como fallback.
    """
    section_id = int(sec_row.get("section_id", -1))
    try:
        return _section_points(points_df, section_id), "real"
    except Exception:
        pass

    B = sec_row.get("ancho_m", sec_row.get("width_m", sec_row.get("ancho_referencia_m", fallback_width)))
    try:
        B = float(B)
        if not np.isfinite(B) or B <= 0:
            B = fallback_width
    except Exception:
        B = fallback_width

    zbed = sec_row.get("cota_fondo_m", sec_row.get("z_min_m", sec_row.get("z_m", 0.0)))
    try:
        zbed = float(zbed)
        if not np.isfinite(zbed):
            zbed = 0.0
    except Exception:
        zbed = 0.0

    # Taludes suaves para sección sintética. No busca reemplazar una sección real;
    # solo evita detener el cálculo y mantiene trazabilidad.
    h_bank = max(2.0, min(12.0, B * 0.12))
    df = pd.DataFrame({
        "section_id": [section_id, section_id, section_id, section_id, section_id],
        "offset_m": [-B/2, -B/4, 0.0, B/4, B/2],
        "z_m": [zbed + h_bank, zbed + h_bank*0.35, zbed, zbed + h_bank*0.35, zbed + h_bank],
    })
    return df, "fallback_trapezoidal_sin_puntos"


def _section_props_at_wse(df: pd.DataFrame, wse: float) -> dict:
    """Propiedades hidráulicas de una sección irregular para una cota de agua.

    Integra por segmentos lineales de la polilínea transversal:
    área mojada, perímetro mojado, ancho superior, profundidad media,
    radio hidráulico.
    """
    x = df["offset_m"].to_numpy(dtype=float)
    z = df["z_m"].to_numpy(dtype=float)
    order = np.argsort(x)
    x = x[order]
    z = z[order]

    area = 0.0
    perimeter = 0.0
    top_width = 0.0

    for i in range(len(x) - 1):
        x1, x2 = x[i], x[i + 1]
        z1, z2 = z[i], z[i + 1]
        dx = abs(x2 - x1)
        if dx <= 0:
            continue

        d1 = wse - z1
        d2 = wse - z2
        if d1 <= 0 and d2 <= 0:
            continue

        seg_len = math.hypot(dx, z2 - z1)

        if d1 > 0 and d2 > 0:
            area += 0.5 * (d1 + d2) * dx
            perimeter += seg_len
            top_width += dx
        else:
            # Un punto mojado y otro seco: triángulo hasta la intersección.
            if d1 > 0 and d2 <= 0:
                frac = d1 / max(d1 - d2, 1e-12)
                dx_sub = dx * frac
                dz_sub = abs(wse - z1)
                area += 0.5 * d1 * dx_sub
                perimeter += math.hypot(dx_sub, dz_sub)
                top_width += dx_sub
            elif d2 > 0 and d1 <= 0:
                frac = d2 / max(d2 - d1, 1e-12)
                dx_sub = dx * frac
                dz_sub = abs(wse - z2)
                area += 0.5 * d2 * dx_sub
                perimeter += math.hypot(dx_sub, dz_sub)
                top_width += dx_sub

    hydraulic_radius = area / perimeter if perimeter > 0 else np.nan
    mean_depth = area / top_width if top_width > 0 else np.nan
    zmin = float(np.nanmin(z))
    zmax = float(np.nanmax(z))
    return {
        "area_m2": float(area),
        "perimetro_mojado_m": float(perimeter),
        "ancho_superior_m": float(top_width),
        "radio_hidraulico_m": float(hydraulic_radius),
        "profundidad_media_m": float(mean_depth),
        "tirante_max_m": float(max(wse - zmin, 0.0)),
        "cota_fondo_m": zmin,
        "cota_borde_max_m": zmax,
        "relieve_seccion_m": float(max(zmax - zmin, 0.0)),
        "wse_excede_topografia_m": float(max(wse - zmax, 0.0)),
        "wse_m": float(wse),
    }


def _conveyance(area: float, radius: float, n: float) -> float:
    if area <= 0 or radius <= 0 or n <= 0:
        return np.nan
    return (1.0 / n) * area * (radius ** (2.0 / 3.0))


def _velocity(Q: float, area: float) -> float:
    return Q / area if area and area > 0 else np.nan


def _energy(wse: float, Q: float, area: float, alpha: float = 1.0) -> float:
    V = _velocity(Q, area)
    if not np.isfinite(V):
        return np.nan
    return wse + alpha * V * V / (2 * G)


def _critical_depth_simple(df: pd.DataFrame, Q: float, y_max: float = 50.0) -> float:
    """Estimación preliminar de calado crítico en sección irregular.

    Busca mínimo de energía específica y^ + V²/2g respecto a la cota mínima.
    """
    zmin = float(df["z_m"].min())
    ys = np.linspace(0.02, y_max, 300)
    best_y = np.nan
    best_E = np.inf
    for y in ys:
        p = _section_props_at_wse(df, zmin + y)
        A = p["area_m2"]
        if A <= 0:
            continue
        V = Q / A
        E = y + V * V / (2 * G)
        if E < best_E:
            best_E = E
            best_y = y
    return float(best_y)


def _normal_depth_irregular(df: pd.DataFrame, Q: float, slope: float, n: float) -> float:
    """Calado normal aproximado por Manning en sección irregular."""
    zmin = float(df["z_m"].min())
    zmax = float(df["z_m"].max())
    hi = max(zmax - zmin + 5.0, 1.0)
    lo = 0.01

    def q_at_y(y):
        p = _section_props_at_wse(df, zmin + y)
        K = _conveyance(p["area_m2"], p["radio_hidraulico_m"], n)
        if not np.isfinite(K):
            return 0.0
        return K * math.sqrt(max(slope, 1e-8))

    # Expandir cota superior si se requiere.
    while q_at_y(hi) < Q and hi < 300:
        hi *= 1.6

    for _ in range(80):
        mid = (lo + hi) / 2
        if q_at_y(mid) < Q:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)




def _wse_reasonable_limit(df: pd.DataFrame) -> tuple[float, float, float]:
    """Límites QA para evitar láminas extrapoladas cientos de metros.

    La sección transversal generada desde DEM no representa una caja cerrada.
    Si la lámina supera demasiado los puntos altos de la sección, el resultado
    deja de ser hidráulico y pasa a ser una extrapolación geométrica.
    """
    x = pd.to_numeric(df["offset_m"], errors="coerce").to_numpy(dtype=float)
    z = pd.to_numeric(df["z_m"], errors="coerce").to_numpy(dtype=float)
    z = z[np.isfinite(z)]
    x = x[np.isfinite(x)]
    if len(z) == 0:
        return np.inf, np.inf, np.nan
    zmin = float(np.nanmin(z))
    zmax = float(np.nanmax(z))
    relief = max(zmax - zmin, 0.01)
    width = float(np.nanmax(x) - np.nanmin(x)) if len(x) >= 2 else np.nan
    # Margen de sobreborde permitido para revisión preliminar. Si se supera,
    # la sección probablemente quedó corta o el eje está invertido.
    overbank_margin = max(1.5, min(5.0, 0.25 * relief))
    # Profundidad máxima admisible antes de activar corrección.
    max_depth = max(relief + overbank_margin, min(50.0, 2.5 * relief + overbank_margin))
    if np.isfinite(width) and width > 0:
        max_depth = min(max_depth, max(8.0, 0.35 * width))
    return float(zmin + max_depth), float(zmax + overbank_margin), float(relief)


def _guard_wse_irreal(
    df: pd.DataFrame,
    Q: float,
    wse: float,
    n: float,
    slope: float,
    metodo: str,
) -> tuple[float, dict, str]:
    """Reemplaza niveles de agua claramente no físicos por tirante normal local.

    Corrige casos típicos: eje KMZ dibujado al revés, condición de borde mal
    ingresada o marcha subcrítica inapropiada en cauces muy pendientes.
    """
    p = _section_props_at_wse(df, wse)
    V = _velocity(Q, p["area_m2"])
    y = p["tirante_max_m"]
    max_wse_depth, max_wse_topo, relief = _wse_reasonable_limit(df)
    bad_by_topo = np.isfinite(max_wse_topo) and wse > max_wse_topo and (not np.isfinite(V) or V < 0.05 or y > max(2.5 * relief, 15.0))
    bad_by_depth = np.isfinite(max_wse_depth) and wse > max_wse_depth
    if bad_by_topo or bad_by_depth:
        zmin = float(df["z_m"].min())
        y_n = _normal_depth_irregular(df, Q, max(slope, 1e-6), n) if np.isfinite(Q) and Q > 0 else 0.01
        wse_corr = zmin + y_n
        # Si incluso el tirante normal extrapola demasiado, se limita a la envolvente
        # razonable y se marca para revisión; no debe presentarse como diseño final.
        if np.isfinite(max_wse_depth):
            wse_corr = min(wse_corr, max_wse_depth)
        p_corr = _section_props_at_wse(df, wse_corr)
        p_corr["control_tirante_irreal"] = True
        p_corr["wse_original_m"] = float(wse)
        p_corr["criterio_control_tirante"] = "corregido_a_tirante_normal_local"
        p_corr["wse_limite_QA_m"] = float(max_wse_depth) if np.isfinite(max_wse_depth) else np.nan
        return float(wse_corr), p_corr, metodo + "_QA_tirante_normal_local"

    p["control_tirante_irreal"] = False
    p["wse_original_m"] = float(wse)
    p["criterio_control_tirante"] = "sin_correccion"
    p["wse_limite_QA_m"] = float(max_wse_depth) if np.isfinite(max_wse_depth) else np.nan
    return float(wse), p, metodo


def _solve_upstream_wse(
    downstream_energy: float,
    Q: float,
    df_up: pd.DataFrame,
    df_down: pd.DataFrame,
    dx_m: float,
    n_up: float,
    n_down: float,
    contraction_coeff: float,
    expansion_coeff: float,
    alpha: float,
    slope_floor: float = 1e-6,
) -> tuple[float, dict]:
    """Resuelve WSE aguas arriba por ecuación de energía.

    E_up = E_down + hf + h_local
    hf ≈ L * Q² / K_avg²
    h_local = C * |V_up²/2g - V_down²/2g|
    """
    zmin_up = float(df_up["z_m"].min())
    zmin_down = float(df_down["z_m"].min())

    # Datos aguas abajo a partir de energía conocida: aproximar WSE_down por energía
    # usando nivel que haga E(wse_down) cercano.
    def solve_wse_from_energy(df, target_E):
        zmin = float(df["z_m"].min())
        lo, hi = zmin + 0.01, max(target_E + 20.0, zmin + 1.0)
        for _ in range(80):
            mid = (lo + hi) / 2
            p = _section_props_at_wse(df, mid)
            E = _energy(mid, Q, p["area_m2"], alpha)
            if not np.isfinite(E) or E < target_E:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    wse_down = solve_wse_from_energy(df_down, downstream_energy)
    p_down = _section_props_at_wse(df_down, wse_down)
    V_down = _velocity(Q, p_down["area_m2"])
    K_down = _conveyance(p_down["area_m2"], p_down["radio_hidraulico_m"], n_down)

    def residual(wse_up):
        p_up = _section_props_at_wse(df_up, wse_up)
        A_up = p_up["area_m2"]
        R_up = p_up["radio_hidraulico_m"]
        V_up = _velocity(Q, A_up)
        K_up = _conveyance(A_up, R_up, n_up)
        if not np.isfinite(K_up) or not np.isfinite(K_down) or K_up <= 0 or K_down <= 0:
            return -1e9
        K_avg = 0.5 * (K_up + K_down)
        hf = max(dx_m, 0.01) * Q * Q / max(K_avg * K_avg, 1e-12)
        dvh = abs((V_up * V_up - V_down * V_down) / (2 * G)) if np.isfinite(V_up) and np.isfinite(V_down) else 0.0
        c_loss = expansion_coeff if (V_up < V_down) else contraction_coeff
        h_local = c_loss * dvh
        E_up = _energy(wse_up, Q, A_up, alpha)
        return E_up - (downstream_energy + hf + h_local)

    lo = zmin_up + 0.01
    hi = max(zmin_up + 1.0, downstream_energy + 30.0, zmin_down + 1.0)

    # Expandir hasta que residual positivo.
    for _ in range(40):
        if residual(hi) > 0:
            break
        hi += max(5.0, 0.2 * abs(hi))
        if hi > zmin_up + 500:
            break

    for _ in range(100):
        mid = (lo + hi) / 2
        if residual(mid) < 0:
            lo = mid
        else:
            hi = mid

    wse_up = (lo + hi) / 2
    p_up = _section_props_at_wse(df_up, wse_up)
    V_up = _velocity(Q, p_up["area_m2"])
    K_up = _conveyance(p_up["area_m2"], p_up["radio_hidraulico_m"], n_up)
    K_avg = 0.5 * (K_up + K_down) if np.isfinite(K_up) and np.isfinite(K_down) else np.nan
    hf = max(dx_m, 0.01) * Q * Q / max(K_avg * K_avg, 1e-12) if np.isfinite(K_avg) else np.nan
    dvh = abs((V_up * V_up - V_down * V_down) / (2 * G)) if np.isfinite(V_up) and np.isfinite(V_down) else np.nan
    c_loss = expansion_coeff if (np.isfinite(V_up) and np.isfinite(V_down) and V_up < V_down) else contraction_coeff
    h_local = c_loss * dvh if np.isfinite(dvh) else np.nan

    info = {
        "hf_m": hf,
        "h_local_m": h_local,
        "K_up": K_up,
        "K_down": K_down,
        "V_down_m_s": V_down,
        "wse_down_reconstruida_m": wse_down,
    }
    return float(wse_up), info


def hecras_like_steady_profile(
    sections_df: pd.DataFrame,
    points_df: pd.DataFrame,
    q_design: pd.DataFrame,
    n_manning: float = 0.035,
    downstream_mode: str = "tirante_normal",
    downstream_wse: float | None = None,
    slope_energy: float = 0.01,
    contraction_coeff: float = 0.10,
    expansion_coeff: float = 0.30,
    alpha: float = 1.0,
    orientation_mode: str = "auto_by_bed_slope",
) -> pd.DataFrame:
    """Perfil permanente 1D tipo HEC-RAS, simplificado.

    - Ordena secciones por PK.
    - Calcula condición de borde aguas abajo.
    - Marcha aguas arriba con balance de energía.
    - Usa geometría irregular real de cada sección transversal.
    """
    if sections_df is None or points_df is None or q_design is None:
        return pd.DataFrame()
    if len(sections_df) == 0 or len(points_df) == 0 or len(q_design) == 0:
        return pd.DataFrame()

    sec = sections_df.copy()
    if "section_id" not in sec.columns:
        sec["section_id"] = np.arange(1, len(sec) + 1)
    if "pk_m" not in sec.columns:
        sec["pk_m"] = np.arange(len(sec), dtype=float)

    # Orientación hidráulica robusta. La versión anterior asumía que el mayor PK
    # siempre era aguas abajo. Si el eje KMZ fue dibujado desde aguas abajo hacia
    # aguas arriba, esa hipótesis eleva artificialmente la lámina de agua en las
    # primeras secciones. Se detecta la pendiente fondo-PK y se invierte el orden
    # cuando el PK crece hacia cotas mayores.
    zmins_detectados = []
    geom_status_detectado = []
    for _, _sec_row in sec.iterrows():
        _df_tmp, _geom_status = _section_points_safe(points_df, _sec_row)
        zmins_detectados.append(float(_df_tmp["z_m"].min()))
        geom_status_detectado.append(_geom_status)
    sec["_zmin_detect_m"] = zmins_detectados
    sec["_geom_status_detect"] = geom_status_detectado

    pk_num = pd.to_numeric(sec["pk_m"], errors="coerce").to_numpy(dtype=float)
    zmin_num = pd.to_numeric(sec["_zmin_detect_m"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(pk_num) & np.isfinite(zmin_num)
    slope_z_vs_pk = np.nan
    if valid.sum() >= 2 and np.nanmax(pk_num[valid]) > np.nanmin(pk_num[valid]):
        try:
            slope_z_vs_pk = float(np.polyfit(pk_num[valid], zmin_num[valid], 1)[0])
        except Exception:
            slope_z_vs_pk = np.nan

    order_ascending = True
    orientacion_detectada = "pk_crece_hacia_aguas_abajo_asumido"
    if str(orientation_mode).lower() in ["auto", "auto_by_bed_slope", "automatico"] and np.isfinite(slope_z_vs_pk):
        if slope_z_vs_pk > 0:
            order_ascending = False
            orientacion_detectada = "pk_crece_hacia_aguas_arriba_corregido"
        else:
            order_ascending = True
            orientacion_detectada = "pk_crece_hacia_aguas_abajo"
    elif str(orientation_mode).lower() in ["descending", "pk_decreciente", "reverse"]:
        order_ascending = False
        orientacion_detectada = "orden_pk_descendente_forzado"
    elif str(orientation_mode).lower() in ["ascending", "pk_creciente"]:
        order_ascending = True
        orientacion_detectada = "orden_pk_ascendente_forzado"

    sec = sec.sort_values("pk_m", ascending=order_ascending).reset_index(drop=True)
    sec["orden_hidraulico"] = np.arange(1, len(sec) + 1)
    sec["orientacion_eje_detectada"] = orientacion_detectada
    sec["pendiente_fondo_dz_dpk"] = slope_z_vs_pk
    # Mantiene todas las secciones del resumen. Las que no tengan puntos reales
    # se resolverán con geometría fallback para que el proceso no se detenga.
    results = []

    for _, qrow in q_design.iterrows():
        Q = float(qrow["Q_m3s"])
        T = float(qrow["T_anios"])
        energies = {}

        # Condición de borde en última sección aguas abajo = mayor PK.
        ds = sec.iloc[-1]
        ds_id = int(ds["section_id"])
        df_ds, geom_status_ds = _section_points_safe(points_df, ds)
        zmin_ds = float(df_ds["z_m"].min())

        if downstream_mode == "cota_conocida" and downstream_wse is not None:
            wse_ds = max(float(downstream_wse), zmin_ds + 0.01)
        else:
            y_n = _normal_depth_irregular(df_ds, Q, max(slope_energy, 1e-6), n_manning)
            y_c = _critical_depth_simple(df_ds, Q)
            # Subcrítico por defecto: aguas abajo se usa tirante normal,
            # pero nunca menor que crítico en régimen rápido inestable.
            wse_ds = zmin_ds + max(y_n, min(y_c, y_n))

        wse_ds, p_ds, metodo_ds = _guard_wse_irreal(
            df_ds, Q, wse_ds, n_manning, max(slope_energy, 1e-6), "borde_aguas_abajo"
        )
        V_ds = _velocity(Q, p_ds["area_m2"])
        E_ds = _energy(wse_ds, Q, p_ds["area_m2"], alpha)
        energies[ds_id] = E_ds

        # Guardar DS
        results.append(_row_output(ds, T, Q, p_ds, V_ds, E_ds, n_manning, 0.0, 0.0, metodo_ds, geom_status_ds))

        # Marcha aguas arriba, desde penúltima hacia primera.
        prev_energy = E_ds
        prev_df = df_ds
        prev_pk = float(ds["pk_m"])
        for idx in range(len(sec) - 2, -1, -1):
            up = sec.iloc[idx]
            up_id = int(up["section_id"])
            df_up, geom_status_up = _section_points_safe(points_df, up)
            dx = abs(prev_pk - float(up["pk_m"]))
            wse_up, info = _solve_upstream_wse(
                downstream_energy=prev_energy,
                Q=Q,
                df_up=df_up,
                df_down=prev_df,
                dx_m=dx,
                n_up=n_manning,
                n_down=n_manning,
                contraction_coeff=contraction_coeff,
                expansion_coeff=expansion_coeff,
                alpha=alpha,
            )
            wse_up, p_up, metodo_up = _guard_wse_irreal(
                df_up, Q, wse_up, n_manning, max(slope_energy, 1e-6), "paso_estandar_energia"
            )
            V_up = _velocity(Q, p_up["area_m2"])
            E_up = _energy(wse_up, Q, p_up["area_m2"], alpha)
            results.append(_row_output(
                up, T, Q, p_up, V_up, E_up, n_manning,
                info.get("hf_m", np.nan), info.get("h_local_m", np.nan),
                metodo_up,
                geom_status_up,
            ))
            prev_energy = E_up
            prev_df = df_up
            prev_pk = float(up["pk_m"])

    out = pd.DataFrame(results)
    if len(out):
        out = out.sort_values(["T_anios", "pk_m"]).reset_index(drop=True)
    return out


def _row_output(sec_row, T, Q, props, V, E, n, hf, hlocal, metodo, geometria_status="real"):
    y = props["tirante_max_m"]
    Fr = V / math.sqrt(G * max(props["profundidad_media_m"], 1e-9)) if np.isfinite(V) and np.isfinite(props["profundidad_media_m"]) else np.nan
    return {
        "section_id": int(sec_row["section_id"]),
        "pk_m": float(sec_row["pk_m"]),
        "T_anios": T,
        "Q_m3s": Q,
        "metodo_hidraulico": metodo,
        "cota_fondo_m": props["cota_fondo_m"],
        "cota_agua_m": props["wse_m"],
        "tirante_max_m": y,
        "area_m2": props["area_m2"],
        "perimetro_mojado_m": props["perimetro_mojado_m"],
        "radio_hidraulico_m": props["radio_hidraulico_m"],
        "ancho_superior_m": props["ancho_superior_m"],
        "profundidad_media_m": props["profundidad_media_m"],
        "velocidad_m_s": V,
        "Froude": Fr,
        "energia_m": E,
        "n_manning": n,
        "perdida_friccion_m": hf,
        "perdida_local_m": hlocal,
        "geometria_status": geometria_status,
        "geometria_fallback": geometria_status != "real",
        "orden_hidraulico": sec_row.get("orden_hidraulico", np.nan),
        "orientacion_eje_detectada": sec_row.get("orientacion_eje_detectada", "sin_dato"),
        "pendiente_fondo_dz_dpk": sec_row.get("pendiente_fondo_dz_dpk", np.nan),
        "cota_borde_max_m": props.get("cota_borde_max_m", np.nan),
        "wse_excede_topografia_m": props.get("wse_excede_topografia_m", np.nan),
        "control_tirante_irreal": props.get("control_tirante_irreal", False),
        "wse_original_m": props.get("wse_original_m", props.get("wse_m", np.nan)),
        "wse_limite_QA_m": props.get("wse_limite_QA_m", np.nan),
        "criterio_control_tirante": props.get("criterio_control_tirante", "sin_dato"),
    }


def sediment_from_hecras_profile(profile_df: pd.DataFrame, d50_m: float = 0.045, d90_m: float = 0.20, slope_energy: float = 0.01) -> pd.DataFrame:
    """Transporte y socavación usando el perfil hidráulico conectado."""
    if profile_df is None or len(profile_df) == 0:
        return pd.DataFrame()

    rho = 1000.0
    rhos = 2650.0
    Rsub = (rhos - rho) / rho
    theta_cr = 0.047
    rows = []

    for _, row in profile_df.iterrows():
        Rh = float(row.get("radio_hidraulico_m", np.nan))
        B = float(row.get("ancho_superior_m", np.nan))
        y = float(row.get("tirante_max_m", np.nan))
        zbed = float(row.get("cota_fondo_m", np.nan))
        tau = rho * G * Rh * slope_energy if np.isfinite(Rh) else np.nan
        theta = tau / ((rhos - rho) * G * d50_m) if d50_m > 0 and np.isfinite(tau) else np.nan
        excess = max(theta - theta_cr, 0) if np.isfinite(theta) else np.nan
        qb_mpm = 8 * (excess ** 1.5) * math.sqrt(Rsub * G * d50_m**3) if np.isfinite(excess) else np.nan
        qs_total = qb_mpm * B if np.isfinite(qb_mpm) and np.isfinite(B) else np.nan
        scour = max(0, 0.15 * y + 2.0 * max(theta - theta_cr, 0) * d90_m) if np.isfinite(y) and np.isfinite(theta) else np.nan

        rows.append({
            "section_id": int(row["section_id"]),
            "pk_m": float(row["pk_m"]),
            "T_anios": float(row["T_anios"]),
            "Q_m3s": float(row["Q_m3s"]),
            "tau_Pa": tau,
            "Shields": theta,
            "D50_m": d50_m,
            "D90_m": d90_m,
            "qb_MPM_m2_s": qb_mpm,
            "Qs_total_m3_s": qs_total,
            "socavacion_general_m": scour,
            "cota_fondo_socavado_m": zbed - scour if np.isfinite(zbed) and np.isfinite(scour) else np.nan,
            "estado": "movil" if np.isfinite(theta) and theta > theta_cr else "estable/preliminar",
        })

    return pd.DataFrame(rows)
