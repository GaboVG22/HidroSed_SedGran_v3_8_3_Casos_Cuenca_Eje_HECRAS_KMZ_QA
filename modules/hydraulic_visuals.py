from __future__ import annotations

import numpy as np
import pandas as pd


G = 9.81


def _section_points(points_df: pd.DataFrame, section_id) -> pd.DataFrame:
    if points_df is None or points_df.empty or "section_id" not in points_df.columns:
        return pd.DataFrame()
    pts = points_df[points_df["section_id"].astype(str) == str(section_id)].copy()
    if pts.empty:
        return pts
    for c in ["offset_m", "z_m", "pk_m"]:
        if c in pts.columns:
            pts[c] = pd.to_numeric(pts[c], errors="coerce")
    return pts.dropna(subset=["offset_m", "z_m"]).sort_values("offset_m")


def detect_overflow_sections(profile_df: pd.DataFrame, points_df: pd.DataFrame) -> pd.DataFrame:
    if profile_df is None or profile_df.empty:
        return pd.DataFrame()
    out = profile_df.copy()
    rows = []
    for _, row in out.iterrows():
        sid = row.get("section_id")
        pts = _section_points(points_df, sid)
        wse = pd.to_numeric(pd.Series([row.get("cota_agua_m")]), errors="coerce").iloc[0]
        if pts.empty or not np.isfinite(wse):
            left_bank = np.nan
            right_bank = np.nan
            overflow_left = False
            overflow_right = False
            height_left = np.nan
            height_right = np.nan
            side = "sin_dato"
        else:
            left = pts[pts["offset_m"] <= 0]
            right = pts[pts["offset_m"] >= 0]
            left_bank = float(left["z_m"].max()) if not left.empty else float(pts["z_m"].max())
            right_bank = float(right["z_m"].max()) if not right.empty else float(pts["z_m"].max())
            height_left = max(float(wse - left_bank), 0.0)
            height_right = max(float(wse - right_bank), 0.0)
            overflow_left = bool(height_left > 0.01)
            overflow_right = bool(height_right > 0.01)
            if overflow_left and overflow_right:
                side = "bilateral"
            elif overflow_left:
                side = "izquierda"
            elif overflow_right:
                side = "derecha"
            else:
                side = "sin_desborde"
        rows.append({
            "section_id": sid,
            "pk_m": row.get("pk_m", np.nan),
            "T_anios": row.get("T_anios", np.nan),
            "cota_ribera_izq_m": left_bank,
            "cota_ribera_der_m": right_bank,
            "desborde_izq": overflow_left,
            "desborde_der": overflow_right,
            "desborde_bool": bool(overflow_left or overflow_right),
            "margen_desborde": side,
            "altura_desborde_izq_m": height_left,
            "altura_desborde_der_m": height_right,
            "altura_desborde_max_m": np.nanmax([height_left, height_right]) if np.isfinite(height_left) or np.isfinite(height_right) else np.nan,
        })
    add = pd.DataFrame(rows)
    merged = out.merge(add, on=["section_id", "pk_m", "T_anios"], how="left")
    return merged


def create_hydraulic_longitudinal_figure(
    profile_df: pd.DataFrame,
    T_select: float | int | None = None,
    variable_mode: str = "Lámina de agua y desborde",
    vertical_reference: str = "Cota del terreno",
):
    import plotly.graph_objects as go

    if profile_df is None or profile_df.empty:
        raise ValueError("No existe perfil hidráulico para graficar.")
    prof = profile_df.copy()
    if T_select is None and "T_anios" in prof.columns:
        T_select = float(pd.to_numeric(prof["T_anios"], errors="coerce").dropna().max())
    if T_select is not None and "T_anios" in prof.columns:
        prof = prof[pd.to_numeric(prof["T_anios"], errors="coerce") == float(T_select)].copy()
    if prof.empty:
        raise ValueError("No existen datos del periodo de retorno seleccionado.")
    prof = prof.sort_values("pk_m").copy()

    x = pd.to_numeric(prof["pk_m"], errors="coerce")
    zbed = pd.to_numeric(prof.get("cota_fondo_m"), errors="coerce")
    wse = pd.to_numeric(prof.get("cota_agua_m"), errors="coerce")
    yn = pd.to_numeric(prof.get("cota_normal_manning_m"), errors="coerce")
    yc = pd.to_numeric(prof.get("calado_critico_m"), errors="coerce") + zbed
    e_line = pd.to_numeric(prof.get("energia_m"), errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=zbed,
        mode="lines",
        line=dict(color="#c26d16", width=3),
        name="Terreno / fondo",
        hovertemplate="PK %{x:.0f} m<br>Fondo %{y:.2f} m<extra></extra>",
    ))

    if variable_mode in ["Lámina de agua y desborde", "yn / yc / energía"]:
        fig.add_trace(go.Scatter(
            x=x, y=wse,
            mode="lines",
            line=dict(color="#2563eb", width=3),
            name="Lámina de agua",
            hovertemplate="PK %{x:.0f} m<br>Cota agua %{y:.2f} m<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=list(x) + list(x[::-1]),
            y=list(wse) + list(zbed[::-1]),
            fill="toself",
            mode="none",
            fillcolor="rgba(59,130,246,0.22)",
            name="Área hidráulica longitudinal",
            hoverinfo="skip",
        ))

    if variable_mode == "yn / yc / energía":
        if yn.notna().any():
            fig.add_trace(go.Scatter(x=x, y=yn, mode="lines", line=dict(color="#0ea5e9", dash="dash"), name="yn"))
        if yc.notna().any():
            fig.add_trace(go.Scatter(x=x, y=yc, mode="lines", line=dict(color="#ef4444", dash="dot"), name="yc"))
        if e_line.notna().any():
            fig.add_trace(go.Scatter(x=x, y=e_line, mode="lines", line=dict(color="#7c3aed", dash="dashdot"), name="Línea de energía"))

    if variable_mode == "Velocidad / Froude":
        vel = pd.to_numeric(prof.get("velocidad_m_s"), errors="coerce")
        fr = pd.to_numeric(prof.get("Froude"), errors="coerce")
        fig.add_trace(go.Scatter(
            x=x, y=wse,
            mode="markers+lines",
            marker=dict(
                size=8,
                color=vel,
                colorscale="Blues",
                showscale=True,
                colorbar=dict(title="Vel. [m/s]"),
            ),
            line=dict(color="rgba(37,99,235,0.5)", width=2),
            name="Lámina coloreada por velocidad",
            customdata=np.stack([vel.fillna(np.nan), fr.fillna(np.nan)], axis=1),
            hovertemplate="PK %{x:.0f} m<br>Cota agua %{y:.2f} m<br>Velocidad %{customdata[0]:.2f} m/s<br>Froude %{customdata[1]:.2f}<extra></extra>",
        ))

    if variable_mode == "Tensión de corte / energía":
        tau = pd.to_numeric(prof.get("tau_Pa"), errors="coerce")
        fig.add_trace(go.Scatter(
            x=x, y=wse,
            mode="markers+lines",
            marker=dict(
                size=9,
                color=tau,
                colorscale="Turbo",
                showscale=True,
                colorbar=dict(title="τ [Pa]"),
            ),
            line=dict(color="rgba(37,99,235,0.5)", width=2),
            name="Lámina coloreada por tensión",
            customdata=np.stack([tau.fillna(np.nan), e_line.fillna(np.nan)], axis=1),
            hovertemplate="PK %{x:.0f} m<br>Cota agua %{y:.2f} m<br>Tensión %{customdata[0]:.2f} Pa<br>Energía %{customdata[1]:.2f} m<extra></extra>",
        ))
        if e_line.notna().any():
            fig.add_trace(go.Scatter(x=x, y=e_line, mode="lines", line=dict(color="#7c3aed", dash="dashdot"), name="Línea de energía"))

    if "desborde_bool" in prof.columns and prof["desborde_bool"].fillna(False).any():
        odf = prof[prof["desborde_bool"].fillna(False)]
        fig.add_trace(go.Scatter(
            x=odf["pk_m"],
            y=odf["cota_agua_m"],
            mode="markers",
            marker=dict(size=10, color="#dc2626", symbol="triangle-up"),
            name="Secciones con desborde",
            customdata=np.stack([
                pd.to_numeric(odf.get("altura_desborde_max_m"), errors="coerce").fillna(np.nan),
                odf.get("margen_desborde", pd.Series("", index=odf.index)).astype(str),
            ], axis=1),
            hovertemplate="PK %{x:.0f} m<br>Cota agua %{y:.2f} m<br>Desborde %{customdata[1]}<br>Altura %{customdata[0]:.2f} m<extra></extra>",
        ))

    title = f"Perfil longitudinal hidráulico · Tr={int(T_select) if pd.notna(T_select) else 'NA'} años · {variable_mode}"
    if vertical_reference != "Cota del terreno":
        title += f" · Ref.: {vertical_reference}"
    fig.update_layout(
        title=title,
        xaxis_title="PK [m]",
        yaxis_title="Cota [m]",
        height=540,
        legend=dict(orientation="h"),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def summarize_overflow_sections(profile_df: pd.DataFrame) -> pd.DataFrame:
    if profile_df is None or profile_df.empty or "desborde_bool" not in profile_df.columns:
        return pd.DataFrame()
    odf = profile_df[profile_df["desborde_bool"].fillna(False)].copy()
    if odf.empty:
        return pd.DataFrame()
    keep = [c for c in [
        "section_id", "pk_m", "T_anios", "margen_desborde",
        "altura_desborde_izq_m", "altura_desborde_der_m", "altura_desborde_max_m",
        "cota_ribera_izq_m", "cota_ribera_der_m", "cota_agua_m", "velocidad_m_s", "Froude"
    ] if c in odf.columns]
    return odf[keep].sort_values(["T_anios", "pk_m"]).reset_index(drop=True)
