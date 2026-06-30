from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go


MAESTRA_CSS = r"""
<style>
:root{
  --hm-bg:#f7f9fc;
  --hm-card:#ffffff;
  --hm-line:#e5eaf3;
  --hm-text:#172033;
  --hm-muted:#64748b;
  --hm-blue:#2563eb;
  --hm-blue-soft:#dbeafe;
  --hm-green:#22c55e;
  --hm-green-soft:#dcfce7;
  --hm-orange:#f97316;
  --hm-red:#ef4444;
  --hm-purple:#7c3aed;
  --hm-cyan:#0ea5e9;
  --hm-gold:#f59e0b;
  --hm-sidebar:#142033;
  --hm-sidebar2:#0b1524;
}
.stApp{background:var(--hm-bg);}
.block-container{padding-top:1.25rem; padding-left:1.4rem; padding-right:1.4rem; max-width:1560px;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--hm-sidebar2),var(--hm-sidebar));}
section[data-testid="stSidebar"] *{color:#eaf2ff;}
section[data-testid="stSidebar"] .stButton button{background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.16); color:#fff; border-radius:10px;}
.hm-page-card{background:var(--hm-card); border:1px solid var(--hm-line); border-radius:16px; padding:20px 24px; box-shadow:0 8px 22px rgba(15,23,42,.045); margin-bottom:1rem;}
.hm-title{font-size:1.42rem; line-height:1.2; font-weight:800; color:var(--hm-text); margin:0;}
.hm-subtitle{font-size:.92rem; color:var(--hm-muted); margin-top:.25rem;}
.hm-card-grid{display:grid; grid-template-columns:repeat(6,minmax(150px,1fr)); gap:12px; margin:.75rem 0 .2rem 0;}
@media(max-width:1200px){.hm-card-grid{grid-template-columns:repeat(3,minmax(150px,1fr));}}
@media(max-width:760px){.hm-card-grid{grid-template-columns:repeat(1,minmax(150px,1fr));}}
.hm-kpi-card{background:#fff; border:1px solid var(--hm-line); border-radius:12px; padding:14px 16px; min-height:92px; box-shadow:0 4px 13px rgba(15,23,42,.035); display:flex; gap:12px; align-items:flex-start;}
.hm-kpi-icon{width:34px; height:34px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:21px; font-weight:800; flex:0 0 34px;}
.hm-kpi-label{font-size:.78rem; color:#334155; line-height:1.15; margin-bottom:5px;}
.hm-kpi-value{font-size:1.08rem; color:#111827; font-weight:800; line-height:1.1;}
.hm-kpi-sub{font-size:.73rem; color:var(--hm-muted); margin-top:4px; line-height:1.2;}
.hm-panel{background:#fff; border:1px solid var(--hm-line); border-radius:14px; padding:14px 16px; box-shadow:0 6px 18px rgba(15,23,42,.035); margin-bottom:1rem;}
.hm-panel-title{font-size:.94rem; font-weight:800; color:#1f2937; margin-bottom:8px;}
.hm-status-ok{display:inline-flex; align-items:center; gap:6px; color:#16a34a; font-weight:800;}
.hm-chip{display:inline-block; border-radius:999px; padding:4px 10px; font-size:.78rem; font-weight:700; background:#eaf2ff; color:#1d4ed8; margin:2px 4px 2px 0;}
.hm-footer{background:#eaf2ff; color:#1d4ed8; border:1px solid #c7ddff; border-radius:8px; padding:9px 14px; font-size:.76rem; display:flex; flex-wrap:wrap; gap:22px; margin-top:8px;}
.hm-workflow-title{font-size:.78rem; opacity:.72; letter-spacing:.04em; text-transform:uppercase; margin:18px 0 10px;}
.hm-app-name{font-size:1.12rem; font-weight:850; margin:2px 0 18px;}
.hm-step{display:flex; align-items:center; gap:12px; padding:8px 8px; border-radius:12px; margin:3px 0; position:relative;}
.hm-step.active{background:linear-gradient(90deg,rgba(37,99,235,.55),rgba(37,99,235,.12));}
.hm-step-num{width:26px; height:26px; border-radius:999px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(191,219,254,.75); font-size:.78rem; font-weight:800; color:#bfdbfe; flex:0 0 26px;}
.hm-step.active .hm-step-num{background:#3b82f6; color:white; border-color:#60a5fa;}
.hm-step-label{font-size:.95rem; font-weight:650;}
.hm-step-check{margin-left:auto; width:20px; height:20px; border-radius:999px; display:flex; align-items:center; justify-content:center; background:#22c55e; color:#052e16; font-weight:900; font-size:.78rem;}
.hm-project-card{background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.13); border-radius:12px; padding:12px; margin-top:16px;}
.hm-project-title{font-size:.75rem; opacity:.72; margin-bottom:5px;}
.hm-project-name{font-weight:800; color:white;}
div[data-testid="stMetric"]{background:#fff; border:1px solid var(--hm-line); border-radius:12px; padding:10px 12px; box-shadow:0 4px 13px rgba(15,23,42,.035);}
.stTabs [data-baseweb="tab-list"]{gap:6px;}
.stTabs [data-baseweb="tab"]{height:42px; background:#fff; border:1px solid var(--hm-line); border-radius:11px 11px 0 0; padding:8px 14px;}
.stTabs [aria-selected="true"]{background:#eaf2ff !important; color:#1d4ed8 !important;}
[data-testid="stDataFrame"]{border-radius:12px; overflow:hidden;}
</style>
"""


def fmt_num(value, suffix: str = "", decimals: int = 2, empty: str = "—") -> str:
    try:
        v = float(value)
        if not math.isfinite(v):
            return empty
    except Exception:
        return empty
    if abs(v) >= 1000:
        txt = f"{v:,.{decimals}f}"
    else:
        txt = f"{v:.{decimals}f}"
    return f"{txt} {suffix}".strip()


def format_pk(pk_m, with_unit: bool = True) -> str:
    try:
        pk = float(pk_m)
        if not math.isfinite(pk):
            return "—"
    except Exception:
        return "—"
    km = int(pk // 1000)
    rest = pk - km * 1000
    out = f"{km}+{rest:06.2f}" if abs(rest - round(rest)) > 1e-6 else f"{km}+{int(round(rest)):03d}"
    return f"{out} m" if with_unit else out


def select_return_period(df: pd.DataFrame | None, preferred: float = 100.0) -> float | None:
    if df is None or df.empty or "T_anios" not in df.columns:
        return None
    vals = pd.to_numeric(df["T_anios"], errors="coerce").dropna().astype(float).unique().tolist()
    if not vals:
        return None
    for target in [preferred, 100.0, max(vals)]:
        for v in vals:
            if abs(v - target) < 1e-6:
                return float(v)
    return float(sorted(vals)[-1])


def _filter_t(df: pd.DataFrame | None, T: float | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    dd = df.copy()
    if T is not None and "T_anios" in dd.columns:
        dd = dd[pd.to_numeric(dd["T_anios"], errors="coerce") == float(T)]
    return dd


def _mean_or_nan(s) -> float:
    vals = pd.to_numeric(s, errors="coerce").dropna()
    return float(vals.mean()) if len(vals) else float("nan")


def _max_or_nan(s) -> float:
    vals = pd.to_numeric(s, errors="coerce").dropna()
    return float(vals.max()) if len(vals) else float("nan")


def _first_col(df: pd.DataFrame, cols: Iterable[str], default=np.nan):
    for c in cols:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce")
    return pd.Series([default] * len(df), index=df.index, dtype="float64")


def transport_kpis(
    sediment_df: pd.DataFrame | None,
    hydraulic_df: pd.DataFrame | None = None,
    sections_df: pd.DataFrame | None = None,
    T: float | None = None,
    project_name: str = "Proyecto activo",
) -> list[dict]:
    sed = _filter_t(sediment_df, T)
    hyd = _filter_t(hydraulic_df, T)
    q_total = _max_or_nan(sed.get("Qs_total_m3_s", pd.Series(dtype=float)))
    q_mean = _mean_or_nan(sed.get("Qs_total_m3_s", pd.Series(dtype=float)))
    qb = _mean_or_nan(sed.get("qb_MPM_m2_s", sed.get("Qb_MPM_m3_s", pd.Series(dtype=float))))
    vel = _mean_or_nan(hyd.get("velocidad_m_s", pd.Series(dtype=float)))
    tau = _max_or_nan(sed.get("tau_Pa", pd.Series(dtype=float)))
    d50 = _mean_or_nan(sed.get("D50_m", pd.Series(dtype=float)))
    if math.isfinite(d50):
        d50_mm = d50 * 1000.0
    else:
        d50_mm = _mean_or_nan(sed.get("D50_mm", pd.Series(dtype=float)))
    if not sed.empty and "pk_m" in sed.columns:
        pk_vals = pd.to_numeric(sed["pk_m"], errors="coerce").dropna()
    elif sections_df is not None and not sections_df.empty and "pk_m" in sections_df.columns:
        pk_vals = pd.to_numeric(sections_df["pk_m"], errors="coerce").dropna()
    else:
        pk_vals = pd.Series(dtype=float)
    tramo = f"{format_pk(pk_vals.min(), False)} – {format_pk(pk_vals.max(), False)}" if len(pk_vals) else "—"
    longitud = (float(pk_vals.max() - pk_vals.min())/1000.0) if len(pk_vals) >= 2 else float("nan")
    return [
        {"label":"Capacidad de transporte", "value":fmt_num(q_total, "m³/s"), "sub":f"Máx. puntual {fmt_num(q_total, 'm³/s')} · prom. {fmt_num(q_mean, 'm³/s')}", "icon":"⇆", "accent":"purple"},
        {"label":"Carga de fondo", "value":fmt_num(qb, "m²/s"), "sub":"Promedio MPM preliminar", "icon":"⌁", "accent":"orange"},
        {"label":"Velocidad media", "value":fmt_num(vel, "m/s"), "sub":"Promedio en cauce", "icon":"≋", "accent":"blue"},
        {"label":"Tensión de corte", "value":fmt_num(tau, "Pa"), "sub":"Máx. en el cauce", "icon":"⊥", "accent":"red"},
        {"label":"D50 del material", "value":fmt_num(d50_mm, "mm"), "sub":"Diámetro medio", "icon":"⠿", "accent":"gold"},
        {"label":"Tramo / PK analizado", "value":tramo, "sub":f"Longitud {fmt_num(longitud, 'km')}", "icon":"⚑", "accent":"green"},
    ]


def kpi_cards_html(cards: list[dict]) -> str:
    color = {
        "purple": ("#f3e8ff", "#7c3aed"),
        "orange": ("#ffedd5", "#f97316"),
        "blue": ("#dbeafe", "#2563eb"),
        "red": ("#ffe4e6", "#ef4444"),
        "gold": ("#fef3c7", "#f59e0b"),
        "green": ("#dcfce7", "#16a34a"),
        "cyan": ("#cffafe", "#0891b2"),
    }
    items = []
    for c in cards:
        bg, fg = color.get(c.get("accent", "blue"), color["blue"])
        items.append(
            f"""<div class='hm-kpi-card'>
              <div class='hm-kpi-icon' style='background:{bg}; color:{fg}'>{c.get('icon','•')}</div>
              <div><div class='hm-kpi-label'>{c.get('label','')}</div>
              <div class='hm-kpi-value'>{c.get('value','—')}</div>
              <div class='hm-kpi-sub'>{c.get('sub','')}</div></div>
            </div>"""
        )
    return "<div class='hm-card-grid'>" + "".join(items) + "</div>"


def dashboard_header_html(title: str, subtitle: str = "") -> str:
    return f"""<div class='hm-page-card'><div class='hm-title'>{title}</div><div class='hm-subtitle'>{subtitle}</div></div>"""


def workflow_html(steps: list[tuple[int, str, bool]], active: int | None = None, project_name: str = "Proyecto activo", project_id: str = "") -> str:
    rows = ["<div class='hm-app-name'>☰ &nbsp; HidroSed Maestra Integrada</div>", "<div class='hm-workflow-title'>Flujo de trabajo</div>"]
    for n, label, ok in steps:
        cls = "hm-step active" if active == n else "hm-step"
        check = "<div class='hm-step-check'>✓</div>" if ok else ""
        rows.append(f"<div class='{cls}'><div class='hm-step-num'>{n}</div><div class='hm-step-label'>{label}</div>{check}</div>")
    rows.append(f"""<div class='hm-project-card'><div class='hm-project-title'>Proyecto activo</div><div class='hm-project-name'>{project_name}</div><div style='font-size:.72rem; opacity:.72'>ID: {project_id}</div></div>""")
    return "".join(rows)


def _trend_labels(df: pd.DataFrame) -> pd.Series:
    if "tendencia_sedimentaria" in df.columns:
        raw = df["tendencia_sedimentaria"].astype(str)
        return raw.map({
            "erosion_alta":"Erosión", "transporte_activo":"Equilibrio", "estable_deposicion_probable":"Deposición",
            "socavacion_relevante":"Erosión", "socavacion_moderada":"Erosión", "depositacion_equilibrio":"Deposición",
        }).fillna(raw)
    if "Shields" in df.columns:
        th = pd.to_numeric(df["Shields"], errors="coerce")
        return pd.Series(np.select([th > 0.10, th > 0.047, th <= 0.047], ["Erosión", "Equilibrio", "Deposición"], default="Sin dato"), index=df.index)
    return pd.Series(["Sin dato"] * len(df), index=df.index)


def transport_longitudinal_figure(
    sediment_df: pd.DataFrame | None,
    hydraulic_df: pd.DataFrame | None = None,
    sections_df: pd.DataFrame | None = None,
    T: float | None = None,
) -> go.Figure:
    sed = _filter_t(sediment_df, T)
    hyd = _filter_t(hydraulic_df, T)
    base = pd.DataFrame()
    if not hyd.empty and "pk_m" in hyd.columns:
        cols = [c for c in ["section_id","pk_m","cota_fondo_m","cota_agua_m","cota_ribera_izq_m","cota_ribera_der_m"] if c in hyd.columns]
        base = hyd[cols].copy()
    elif sections_df is not None and not sections_df.empty and "pk_m" in sections_df.columns:
        cols = [c for c in ["section_id","pk_m","cota_fondo_m","z_min","cota_min_m","cota_ribera_izq_m","cota_ribera_der_m"] if c in sections_df.columns]
        base = sections_df[cols].copy()
    if not sed.empty and "pk_m" in sed.columns:
        sed_cols = [c for c in ["section_id","pk_m","socavacion_general_m","Qs_total_m3_s","Shields","tendencia_sedimentaria"] if c in sed.columns]
        sedm = sed[sed_cols].copy()
        if not base.empty and "section_id" in base.columns and "section_id" in sedm.columns:
            base["section_id"] = base["section_id"].astype(str)
            sedm["section_id"] = sedm["section_id"].astype(str)
            base = base.merge(sedm, on="section_id", how="outer", suffixes=("", "_sed"))
            if "pk_m_sed" in base.columns:
                base["pk_m"] = pd.to_numeric(base.get("pk_m"), errors="coerce").fillna(pd.to_numeric(base["pk_m_sed"], errors="coerce"))
        else:
            base = sedm
    if base.empty or "pk_m" not in base.columns:
        return go.Figure().update_layout(title="Sin datos suficientes para el perfil longitudinal")
    base["pk_m"] = pd.to_numeric(base["pk_m"], errors="coerce")
    base = base.dropna(subset=["pk_m"]).sort_values("pk_m")
    bed = _first_col(base, ["cota_fondo_m", "z_min", "cota_min_m"])
    if bed.isna().all():
        bed = pd.Series(np.linspace(100, 90, len(base)), index=base.index)
    water = _first_col(base, ["cota_agua_m"])
    water = water.fillna(bed + max(float(np.nanstd(bed))*0.15, 1.0))
    rib_left = _first_col(base, ["cota_ribera_izq_m"])
    rib_right = _first_col(base, ["cota_ribera_der_m"])
    terrain = pd.concat([rib_left, rib_right, bed], axis=1).max(axis=1).fillna(bed + max(float(np.nanstd(bed))*0.35, 2.0))
    scour = _first_col(base, ["socavacion_general_m"]).fillna(0)
    scour_bed = bed - scour
    trend = _trend_labels(base)
    x = base["pk_m"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=terrain, name="Cota del terreno", mode="lines", line=dict(color="#2563eb", width=2.5), hovertemplate="PK %{x:.0f} m<br>Cota terreno %{y:.2f} m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=water, name="Lámina de agua", mode="lines", line=dict(color="#60a5fa", width=2), fill="tonexty", fillcolor="rgba(96,165,250,0.22)", hovertemplate="PK %{x:.0f} m<br>Agua %{y:.2f} m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=bed, name="Fondo actual", mode="lines", line=dict(color="#d97706", width=2), hovertemplate="PK %{x:.0f} m<br>Fondo %{y:.2f} m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=scour_bed, name="Fondo socavado", mode="lines", line=dict(color="#ef4444", width=2, dash="dash"), hovertemplate="PK %{x:.0f} m<br>Fondo socavado %{y:.2f} m<extra></extra>"))
    colors = {"Erosión":"rgba(239,68,68,0.22)", "Equilibrio":"rgba(245,158,11,0.22)", "Deposición":"rgba(34,197,94,0.24)", "Sin dato":"rgba(148,163,184,0.16)"}
    # Add colored bands between scoured and bed elevations by trend in contiguous segments.
    if len(base) >= 2:
        for lab in ["Erosión", "Equilibrio", "Deposición", "Sin dato"]:
            mask = trend.astype(str).eq(lab).to_numpy()
            idxs = np.where(mask)[0]
            if len(idxs) == 0:
                continue
            # plot points with fill; gaps are handled using NaNs.
            xx, y1, y2 = [], [], []
            for i in range(len(base)):
                if mask[i]:
                    xx.append(float(x.iloc[i])); y1.append(float(bed.iloc[i])); y2.append(float(scour_bed.iloc[i]))
                else:
                    xx.append(np.nan); y1.append(np.nan); y2.append(np.nan)
            fig.add_trace(go.Scatter(x=xx, y=y1, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=xx, y=y2, mode="lines", line=dict(width=0), fill="tonexty", fillcolor=colors[lab], name=lab, hoverinfo="skip"))
    if len(base) >= 2:
        ticks = np.linspace(float(x.min()), float(x.max()), min(7, len(base)))
        for t in ticks[1:-1]:
            fig.add_vline(x=t, line=dict(color="#94a3b8", width=1, dash="dash"), opacity=.55)
    fig.update_layout(
        title="Perfil longitudinal – Tendencia de erosión/deposición",
        xaxis_title="PK (m)", yaxis_title="Cota (m)", height=430,
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.26, xanchor="center", x=.5),
        margin=dict(l=45, r=20, t=55, b=80),
        hovermode="x unified",
        font=dict(family="Inter, Arial, sans-serif", color="#1f2937"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5eaf3", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5eaf3", zeroline=False)
    return fig


def capacity_by_return_period_figure(sediment_df: pd.DataFrame | None, q_design_df: pd.DataFrame | None = None) -> go.Figure:
    df = pd.DataFrame()
    if sediment_df is not None and not sediment_df.empty and {"T_anios", "Qs_total_m3_s"}.issubset(sediment_df.columns):
        df = sediment_df.groupby("T_anios", as_index=False)["Qs_total_m3_s"].max().rename(columns={"Qs_total_m3_s":"valor"})
    elif q_design_df is not None and not q_design_df.empty:
        tcol = "T_anios" if "T_anios" in q_design_df.columns else None
        qcol = "Q_m3s" if "Q_m3s" in q_design_df.columns else None
        if tcol and qcol:
            df = q_design_df[[tcol, qcol]].rename(columns={tcol:"T_anios", qcol:"valor"})
    fig = go.Figure()
    if df.empty:
        fig.update_layout(title="Sin datos para gráfico por periodo de retorno", height=320)
        return fig
    df["T_anios"] = pd.to_numeric(df["T_anios"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna().sort_values("T_anios")
    fig.add_trace(go.Bar(x=[f"{int(t)} años" for t in df["T_anios"]], y=df["valor"], name="Capacidad", marker=dict(color="#3b82f6"), text=[fmt_num(v, "") for v in df["valor"]], textposition="outside"))
    fig.update_layout(title="Capacidad de transporte por periodo de retorno (Q)", xaxis_title="Periodo de retorno", yaxis_title="m³/s", height=320, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=45, r=20, t=50, b=45), font=dict(family="Inter, Arial, sans-serif", color="#1f2937"))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5eaf3", zeroline=False)
    return fig


def representative_reach_table(sediment_df: pd.DataFrame | None, T: float | None = None, n_bins: int = 6) -> pd.DataFrame:
    sed = _filter_t(sediment_df, T)
    if sed.empty or "pk_m" not in sed.columns:
        return pd.DataFrame()
    sed = sed.copy()
    sed["pk_m"] = pd.to_numeric(sed["pk_m"], errors="coerce")
    sed = sed.dropna(subset=["pk_m"]).sort_values("pk_m")
    if sed.empty:
        return pd.DataFrame()
    bins = np.linspace(float(sed["pk_m"].min()), float(sed["pk_m"].max()), min(n_bins, len(sed)) + 1)
    if len(np.unique(bins)) < 2:
        bins = np.array([sed["pk_m"].min(), sed["pk_m"].max()+1])
    sed["_bin"] = pd.cut(sed["pk_m"], bins=bins, include_lowest=True, duplicates="drop")
    trend = _trend_labels(sed)
    sed["_trend_label"] = trend
    rows = []
    for interval, g in sed.groupby("_bin", observed=True):
        if g.empty:
            continue
        pmin = float(g["pk_m"].min()); pmax = float(g["pk_m"].max())
        rows.append({
            "Tramo (PK)": f"{format_pk(pmin, False)} – {format_pk(pmax, False)}",
            "Longitud (m)": round(max(pmax - pmin, 0), 0),
            "Q100 (m³/s)": round(_mean_or_nan(g.get("Q_m3s", pd.Series(dtype=float))), 2),
            "Cap. transp. total (m³/s)": round(_mean_or_nan(g.get("Qs_total_m3_s", pd.Series(dtype=float))), 3),
            "Carga de fondo (m²/s)": round(_mean_or_nan(g.get("qb_MPM_m2_s", g.get("Qb_MPM_m3_s", pd.Series(dtype=float)))), 3),
            "Tendencia": g["_trend_label"].mode().iloc[0] if len(g["_trend_label"].mode()) else "—",
            "Máx. erosión (m)": round(_max_or_nan(g.get("socavacion_general_m", pd.Series(dtype=float))), 2),
            "Máx. deposición (m)": round(_max_or_nan(g.get("depositacion_m", pd.Series(dtype=float))) if "depositacion_m" in g.columns else 0.0, 2),
        })
    return pd.DataFrame(rows)


def scour_kpis(section_id, T, hydraulic_df=None, sediment_df=None) -> list[dict]:
    hyd = _filter_t(hydraulic_df, T)
    sed = _filter_t(sediment_df, T)
    if not hyd.empty and "section_id" in hyd.columns:
        hyd = hyd[hyd["section_id"].astype(str) == str(section_id)]
    if not sed.empty and "section_id" in sed.columns:
        sed = sed[sed["section_id"].astype(str) == str(section_id)]
    scour_general = _max_or_nan(sed.get("socavacion_general_m", pd.Series(dtype=float)))
    scour_local = _max_or_nan(sed.get("socavacion_local_prelim_m", pd.Series(dtype=float)))
    if not math.isfinite(scour_local):
        total = _max_or_nan(sed.get("socavacion_total_prelim_m", pd.Series(dtype=float)))
        scour_local = total if math.isfinite(total) else np.nan
    pk = _mean_or_nan(hyd.get("pk_m", sed.get("pk_m", pd.Series(dtype=float))))
    status = "Aceptable" if (not math.isfinite(scour_general) or scour_general < 2.0) else "Revisar"
    return [
        {"label":"Periodo de retorno", "value":f"Tr = {int(T) if T else '—'} años", "sub":"Evento evaluado", "icon":"≋", "accent":"blue"},
        {"label":"Socavación general", "value":fmt_num(scour_general, "m"), "sub":"Profundidad máxima media", "icon":"↓", "accent":"orange"},
        {"label":"Socavación local", "value":fmt_num(scour_local, "m"), "sub":"Profundidad máxima local", "icon":"◎", "accent":"red"},
        {"label":"Sección evaluada", "value":format_pk(pk) if math.isfinite(pk) else str(section_id), "sub":"Aguas abajo / sección activa", "icon":"⌣", "accent":"blue"},
        {"label":"Estado", "value":status, "sub":"Dentro de criterios" if status == "Aceptable" else "Requiere revisión", "icon":"✓", "accent":"green" if status == "Aceptable" else "red"},
    ]


def footer_html(modelo: str = "HidroSed SedGran", src: str = "WGS 84 / UTM", unidades: str = "SI", fecha: str = "") -> str:
    fecha_part = f"<span>Fecha de cálculo: {fecha}</span>" if fecha else ""
    return f"""<div class='hm-footer'><span>Modelo: {modelo}</span><span>Unidades: {unidades}</span>{fecha_part}<span>SRC: {src}</span></div>"""
