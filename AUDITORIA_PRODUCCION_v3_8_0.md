# Auditoría producción HidroSed v3.8.0

## Objetivo
Corregir el caso en que la app entrega solo parte de la cuenca aportante por usar una única celda de salida en zonas de abanico aluvial o cauce dividido.

## Archivos modificados

- `app/modules/watershed_morphometry.py`
- `app/app.py`
- `app/tests/test_watershed_validation_v379.py`

## Controles ejecutados

- `python -m compileall -q .`: OK
- `python -m pytest -q`: OK, 34 pruebas aprobadas
- Prueba unitaria nueva de portal compuesto: OK
- Smoke test de vectorización/KML con MultiPolygon: OK

## Limitación del sandbox
No fue posible levantar visualmente Streamlit en este contenedor porque el módulo/ejecutable `streamlit` no está instalado en el ambiente. La validación realizada cubre compilación completa, pruebas unitarias, lógica de cierre compuesto y generación KML.

## Resultado técnico
La app ahora puede validar una cuenca usando outlet puntual o portal compuesto. Si la cuenca puntual queda incompleta y el portal recupera superficie adicional sin violar controles de borde/NoData/área máxima, se aplica automáticamente y se informa en el diagnóstico técnico.
