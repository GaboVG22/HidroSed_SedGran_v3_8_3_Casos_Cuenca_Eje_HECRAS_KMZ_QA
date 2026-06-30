from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import pandas as pd

SHEET_NAME = 'SECCIONES_HECRAS'

REQUIRED_COLUMNS = [
    'River', 'Reach', 'Tramo', 'XS_ID', 'River_Station_km', 'Chainage_m',
    'Point_No', 'Station_m', 'Elevation_m', 'Bank', 'Manning_n',
    'Left_Bank_Station_m', 'Right_Bank_Station_m',
    'Reach_Length_LOB_m', 'Reach_Length_Channel_m', 'Reach_Length_ROB_m',
    'Contraction_Coeff', 'Expansion_Coeff', 'Coord_X_UTM', 'Coord_Y_UTM', 'Comentario'
]

NUMERIC_COLUMNS = [
    'River_Station_km', 'Chainage_m', 'Point_No', 'Station_m', 'Elevation_m', 'Manning_n',
    'Left_Bank_Station_m', 'Right_Bank_Station_m', 'Reach_Length_LOB_m',
    'Reach_Length_Channel_m', 'Reach_Length_ROB_m', 'Contraction_Coeff', 'Expansion_Coeff',
    'Coord_X_UTM', 'Coord_Y_UTM'
]

@dataclass
class HecRasSectionsResult:
    ok: bool
    sections_df: pd.DataFrame
    points_df: pd.DataFrame
    errors_df: pd.DataFrame
    summary_df: pd.DataFrame


def hecras_template_bytes() -> bytes:
    rows = []
    # Dos secciones de ejemplo mínimas, estilo HEC-RAS: Station/Elevation por punto.
    example = [
        ('Rio_Ejemplo', 'Tramo_Principal', 'AB', 'XS_0000', 0.000, 0.0, [(-12, 105), (-4, 101), (0, 100), (4, 101), (12, 105)]),
        ('Rio_Ejemplo', 'Tramo_Principal', 'AB', 'XS_0100', 0.100, 100.0, [(-12, 104.5), (-4, 100.5), (0, 99.8), (4, 100.6), (12, 104.8)]),
    ]
    for river, reach, tramo, xs, rs, ch, pts in example:
        for i, (station, elev) in enumerate(pts, start=1):
            rows.append({
                'River': river, 'Reach': reach, 'Tramo': tramo, 'XS_ID': xs,
                'River_Station_km': rs, 'Chainage_m': ch, 'Point_No': i,
                'Station_m': station, 'Elevation_m': elev,
                'Bank': 'Channel' if abs(station) <= 4 else '', 'Manning_n': 0.035,
                'Left_Bank_Station_m': -4, 'Right_Bank_Station_m': 4,
                'Reach_Length_LOB_m': 100, 'Reach_Length_Channel_m': 100, 'Reach_Length_ROB_m': 100,
                'Contraction_Coeff': 0.10, 'Expansion_Coeff': 0.30,
                'Coord_X_UTM': None, 'Coord_Y_UTM': None, 'Comentario': 'Ejemplo: reemplazar por datos reales'
            })
    df = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)
    meta = pd.DataFrame([
        {'Campo': c, 'Descripción': _column_description(c)} for c in REQUIRED_COLUMNS
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        meta.to_excel(writer, sheet_name='DICCIONARIO', index=False)
        workbook = writer.book
        ws = writer.sheets[SHEET_NAME]
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1})
        for col, name in enumerate(df.columns):
            ws.write(0, col, name, header_fmt)
            ws.set_column(col, col, max(14, min(28, len(name) + 3)))
        writer.sheets['DICCIONARIO'].set_column(0, 1, 34)
    return buf.getvalue()


def _column_description(c: str) -> str:
    desc = {
        'River': 'Nombre del río, cauce o sistema',
        'Reach': 'Nombre del tramo',
        'Tramo': 'Código AB, BC, Marginal o Externo',
        'XS_ID': 'Identificador de sección transversal',
        'River_Station_km': 'Kilometraje o estación de río',
        'Chainage_m': 'Progresiva en metros',
        'Point_No': 'Número del punto dentro de la sección',
        'Station_m': 'Distancia transversal tipo HEC-RAS',
        'Elevation_m': 'Cota del punto',
        'Bank': 'LOB, Channel, ROB o vacío',
        'Manning_n': 'Rugosidad Manning n',
        'Coord_X_UTM': 'Coordenada X UTM opcional',
        'Coord_Y_UTM': 'Coordenada Y UTM opcional',
    }
    return desc.get(c, 'Campo hidráulico/topográfico de sección tipo HEC-RAS')


def read_hecras_sections_excel(file_or_bytes: Any) -> HecRasSectionsResult:
    errors = []
    try:
        xls = pd.ExcelFile(file_or_bytes)
    except Exception as exc:
        return HecRasSectionsResult(False, pd.DataFrame(), pd.DataFrame(), pd.DataFrame([
            {'Fila': '', 'Sección': '', 'Campo': 'archivo', 'Error': str(exc), 'Acción recomendada': 'Verifique que sea un Excel válido .xlsx'}
        ]), pd.DataFrame())
    if SHEET_NAME not in xls.sheet_names:
        return HecRasSectionsResult(False, pd.DataFrame(), pd.DataFrame(), pd.DataFrame([
            {'Fila': '', 'Sección': '', 'Campo': SHEET_NAME, 'Error': f'No existe la hoja {SHEET_NAME}', 'Acción recomendada': 'Use la plantilla oficial HidroSed'}
        ]), pd.DataFrame())
    df = pd.read_excel(xls, sheet_name=SHEET_NAME)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    for c in missing:
        errors.append({'Fila': '', 'Sección': '', 'Campo': c, 'Error': 'Columna obligatoria faltante', 'Acción recomendada': 'Agregar columna desde plantilla'})
    if missing:
        return HecRasSectionsResult(False, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(errors), pd.DataFrame())
    df = df[REQUIRED_COLUMNS].copy()
    # Normalización y validación numérica.
    for c in NUMERIC_COLUMNS:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    for idx, row in df.iterrows():
        excel_row = int(idx) + 2
        xs = str(row.get('XS_ID', ''))
        for c in ['XS_ID', 'Station_m', 'Elevation_m']:
            if pd.isna(row.get(c)) or str(row.get(c)).strip() == '':
                errors.append({'Fila': excel_row, 'Sección': xs, 'Campo': c, 'Error': 'Valor obligatorio vacío o no numérico', 'Acción recomendada': 'Completar dato'})
        if pd.notna(row.get('Elevation_m')) and float(row.get('Elevation_m')) < -50:
            errors.append({'Fila': excel_row, 'Sección': xs, 'Campo': 'Elevation_m', 'Error': 'Cota negativa extrema', 'Acción recomendada': 'Verificar datum vertical y signo de cota'})
        if pd.notna(row.get('Manning_n')) and not (0.010 <= float(row.get('Manning_n')) <= 0.200):
            errors.append({'Fila': excel_row, 'Sección': xs, 'Campo': 'Manning_n', 'Error': 'Manning fuera de rango usual 0.010–0.200', 'Acción recomendada': 'Revisar rugosidad'})
    # Validaciones por sección.
    clean = df.dropna(subset=['XS_ID', 'Station_m', 'Elevation_m']).copy()
    for xs, g in clean.groupby('XS_ID', dropna=False):
        if len(g) < 3:
            errors.append({'Fila': '', 'Sección': xs, 'Campo': 'XS_ID', 'Error': 'La sección tiene menos de 3 puntos', 'Acción recomendada': 'Agregar puntos transversales'})
        dup = g[g.duplicated('Station_m', keep=False)]
        if not dup.empty:
            errors.append({'Fila': ','.join(str(int(i)+2) for i in dup.index[:8]), 'Sección': xs, 'Campo': 'Station_m', 'Error': 'Estaciones duplicadas dentro de la sección', 'Acción recomendada': 'Eliminar duplicados o ajustar Station_m'})
        st_values = g['Station_m'].dropna().tolist()
        if len(st_values) >= 2 and len(set(st_values)) != len(st_values):
            pass
    ok = len(errors) == 0
    points = clean.sort_values(['River_Station_km', 'XS_ID', 'Station_m']).copy()
    points['section_id'] = points['XS_ID'].astype(str)
    points['offset_m'] = points['Station_m'].astype(float)
    points['z_m'] = points['Elevation_m'].astype(float)
    summary_rows = []
    for xs, g in points.groupby('XS_ID'):
        summary_rows.append({
            'XS_ID': xs,
            'Tramo': ';'.join(sorted(set(str(v) for v in g['Tramo'].dropna()))),
            'River_Station_km': float(g['River_Station_km'].dropna().iloc[0]) if g['River_Station_km'].notna().any() else None,
            'Chainage_m': float(g['Chainage_m'].dropna().iloc[0]) if g['Chainage_m'].notna().any() else None,
            'n_puntos': int(len(g)),
            'station_min_m': float(g['Station_m'].min()),
            'station_max_m': float(g['Station_m'].max()),
            'cota_min_m': float(g['Elevation_m'].min()),
            'cota_max_m': float(g['Elevation_m'].max()),
        })
    summary = pd.DataFrame(summary_rows).sort_values(['River_Station_km', 'XS_ID']) if summary_rows else pd.DataFrame()
    errors_df = pd.DataFrame(errors, columns=['Fila', 'Sección', 'Campo', 'Error', 'Acción recomendada'])
    return HecRasSectionsResult(ok, summary.copy(), points, errors_df, summary)


def section_source_summary(auto_sections: bool, excel_sections: bool, selected_source: str) -> dict[str, Any]:
    return {'auto_sections': bool(auto_sections), 'excel_sections': bool(excel_sections), 'selected_source': selected_source}
