from __future__ import annotations
import pandas as pd

from modules.maestra_ui import (
    format_pk, select_return_period, transport_kpis,
    transport_longitudinal_figure, capacity_by_return_period_figure,
    representative_reach_table, scour_kpis,
)


def sample_data():
    sed = pd.DataFrame({
        "section_id": [1, 2, 3],
        "pk_m": [0.0, 1000.0, 23540.0],
        "T_anios": [100, 100, 100],
        "Qs_total_m3_s": [6.23, 12.35, 18.72],
        "qb_MPM_m2_s": [1.1, 2.2, 2.48],
        "tau_Pa": [1.5, 2.7, 3.62],
        "D50_m": [0.0286, 0.0286, 0.0286],
        "Shields": [0.03, 0.08, 0.12],
        "socavacion_general_m": [0.12, 0.42, 1.45],
    })
    hyd = pd.DataFrame({
        "section_id": [1, 2, 3],
        "pk_m": [0.0, 1000.0, 23540.0],
        "T_anios": [100, 100, 100],
        "velocidad_m_s": [2.0, 2.3, 2.6],
        "cota_fondo_m": [790.0, 760.0, 735.0],
        "cota_agua_m": [795.0, 770.0, 781.25],
        "cota_ribera_izq_m": [800.0, 782.0, 785.0],
        "cota_ribera_der_m": [802.0, 784.0, 786.0],
    })
    return sed, hyd


def test_format_pk_maestra():
    assert format_pk(23540.0) == "23+540 m"
    assert format_pk(0.0, False) == "0+000"


def test_transport_dashboard_helpers():
    sed, hyd = sample_data()
    assert select_return_period(sed) == 100.0
    cards = transport_kpis(sed, hyd, None, 100)
    assert len(cards) == 6
    assert "18.72" in cards[0]["sub"]
    fig = transport_longitudinal_figure(sed, hyd, None, 100)
    assert len(fig.data) >= 4
    fig2 = capacity_by_return_period_figure(sed)
    assert len(fig2.data) == 1
    tbl = representative_reach_table(sed, 100)
    assert not tbl.empty
    scards = scour_kpis(3, 100, hyd, sed)
    assert any(c["label"] == "Socavación general" for c in scards)
