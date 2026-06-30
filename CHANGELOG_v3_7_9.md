# HidroSed SedGran v3.7.9 · QA punto-cauce-cuenca

## Mejora aplicada
Se implementó el prompt de control de delineación de cuencas:

1. Corrección automática de puntos de control mal ubicados.
2. Ajuste del punto al cauce real detectado desde el DEM mediante acumulación de flujo.
3. Delineación con control de cuenca completa.
4. Detección y bloqueo de cuencas truncadas por borde del DEM o NoData.
5. Advertencia explícita cuando el DEM no cubre toda la cuenca.
6. Diagnóstico técnico tabular con controles, severidad, mensaje y acción recomendada.
7. La aplicación solo habilita descarga y uso posterior de la cuenca cuando pasa los controles mínimos.

## Cambios principales

- `modules/watershed_morphometry.py`
  - Nuevo diagnóstico de cobertura DEM.
  - Nuevo resumen de controles mínimos.
  - Penalización de candidatos de salida que generan cuencas truncadas.
  - Métricas QA: `cuenca_validada`, `estado_validacion`, `controles_minimos`, `diagnostico_tecnico`, `acciones_recomendadas`, `cobertura_dem`.

- `app.py`
  - Nuevo flujo en pestaña `3 · Cuenca y morfometría`.
  - La cuenca no validada se muestra solo como candidata de diagnóstico.
  - Se eliminan salidas oficiales anteriores cuando se ejecuta una nueva delineación.
  - Descarga de KMZ/KML bloqueada si la cuenca no está validada.

- `tests/test_watershed_validation_v379.py`
  - Pruebas de borde DEM, NoData y validación mínima.

## Resultado esperado
Si el punto de control cae lejos del cauce, la app intentará corregirlo dentro del radio definido. Si el DEM no cubre toda la cuenca o el polígono toca el borde del raster, el resultado queda como `NO_VALIDADA` y no avanza como cuenca oficial.
