# HidroSed SedGran v3.8.2 · Casos de aplicación y salida cartográfica enlazada

## Mejoras aplicadas

1. Se incorpora selector de **caso de aplicación HidroSed** con 4 tipologías de relación cuenca–eje:
   - Caso 1: cuenca + eje interno.
   - Caso 2: cuenca + eje de modelación conectado.
   - Caso 3: cuenca + eje marginal.
   - Caso 4: cuenca + eje externo alejado.

2. Se agregan fichas técnicas desplegables para disminuir sobrecarga visual:
   - Descripción del caso.
   - Uso hidráulico.
   - Insumos mínimos.
   - Controles QA.
   - Salidas recomendadas.
   - Imagen referencial del caso.

3. Se agregan imágenes referenciales en `app/assets`:
   - `caso_1_cuenca_eje_interno.png`
   - `caso_2_cuenca_eje_conectado.png`
   - `caso_3_cuenca_eje_marginal.png`
   - `caso_4_cuenca_eje_externo.png`

4. Se enlaza el caso seleccionado con alertas de respaldo topográfico:
   - Casos 2, 3 y 4 muestran alerta cuando no existen curvas de nivel/topografía de respaldo.
   - Caso 4 queda identificado como caso crítico por requerir trazabilidad de transferencia hidrológica al eje externo.

5. Se mejora la exportación cartográfica:
   - Nuevo KMZ/KML `cuenca_eje_cauce`.
   - Nuevo KMZ/KML unificado `cuenca_eje_curvas_nivel`.
   - La salida cuenca + curvas ahora puede incluir también el eje activo.

## Archivos principales modificados

- `app.py`
- `modules/application_cases.py`
- `modules/basin_contours_export.py`
- `tests/test_application_cases.py`
- `tests/test_basin_axis_export_v382.py`

## Auditoría

- `compileall`: OK.
- `pytest`: 43 pruebas aprobadas.
- Pruebas nuevas de casos: OK.
- Pruebas nuevas de exportación cuenca + eje + curvas: OK.
