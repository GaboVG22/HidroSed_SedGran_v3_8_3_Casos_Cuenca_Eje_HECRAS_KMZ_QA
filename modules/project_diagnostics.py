from __future__ import annotations

from typing import Any
import pandas as pd


def bool_txt(v: Any) -> str:
    return 'Sí' if bool(v) else 'No'


def build_project_diagnostics(state: dict, case_title: str = '') -> pd.DataFrame:
    basin_metrics = state.get('basin_active_metrics') or state.get('basin_metrics') or {}
    rows = [
        ('Caso tipo seleccionado', case_title or state.get('application_case_key', 'sin_dato')),
        ('Estado cuenca preliminar', 'Disponible' if state.get('basin_preliminar_kml') or state.get('basin_candidate_kml') else 'No disponible'),
        ('Estado cuenca corregida', 'Disponible' if state.get('basin_corregida_kml') else 'No disponible'),
        ('Cuenca activa usada', state.get('cuenca_activa_tipo', 'cuenca_validada' if state.get('basin_kml') else 'sin_cuenca_activa')),
        ('Área cuenca activa km²', basin_metrics.get('area_km2', 'sin_dato')),
        ('Existe eje manual', bool_txt(state.get('axis_source') == 'manual_kmz')),
        ('Existe eje automático', bool_txt(state.get('axis_auto_coords') or state.get('axis_source', '').startswith('automatico'))),
        ('Existe curvas de cuenca', bool_txt(state.get('contours_kml') or state.get('basin_contours_kml'))),
        ('Existe curvas de eje', bool_txt(state.get('axis_contours_kml') or state.get('topo_support_df') is not None)),
        ('Existe secciones cargadas Excel', bool_txt(state.get('hecras_sections_points') is not None)),
        ('Existe secciones generadas', bool_txt(state.get('section_points_df') is not None or state.get('sections_df') is not None)),
        ('Advertencias activas', '; '.join(state.get('active_warnings', [])) if state.get('active_warnings') else 'Sin advertencias registradas'),
        ('KMZ eje disponible', bool_txt(state.get('export_axis_hidrosed_kmz'))),
        ('KMZ unificado disponible', bool_txt(state.get('export_unified_hidrosed_kmz'))),
    ]
    return pd.DataFrame(rows, columns=['Variable', 'Valor'])


def diagnostics_to_txt(df: pd.DataFrame) -> bytes:
    lines = ['Diagnóstico técnico del proyecto HidroSed', '']
    for _, r in df.iterrows():
        lines.append(f"{r['Variable']}: {r['Valor']}")
    return ('\n'.join(lines) + '\n').encode('utf-8')
