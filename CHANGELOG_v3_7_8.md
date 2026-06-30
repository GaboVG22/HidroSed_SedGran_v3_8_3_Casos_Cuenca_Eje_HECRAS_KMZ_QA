# CHANGELOG · HidroSed Maestra Integrada v3.7.8

## Objetivo
Aplicar el formato visual de las referencias entregadas por el usuario a la aplicación HidroSed, sin perder la funcionalidad hidráulica, sedimentológica y de secciones compuestas ya incorporada en v3.7.7.

## Cambios principales

1. **Formato visual HidroSed Maestra Integrada**
   - Se agregó una barra lateral oscura con flujo de trabajo numerado.
   - Se incorporó estado visual por etapa: proyecto, DEM/curvas, eje, secciones, hidrología, hidráulica, sedimentos, modelo 3D e informe.
   - Se actualizó el encabezado general con estética tipo tablero ejecutivo.

2. **Dashboard ejecutivo de transporte de sedimentos**
   - Tarjetas KPI: capacidad de transporte, carga de fondo, velocidad media, tensión de corte, D50 y tramo/PK analizado.
   - Perfil longitudinal con cota de terreno, lámina de agua, fondo actual, fondo socavado y bandas de tendencia.
   - Gráfico de capacidad por periodo de retorno.
   - Tabla por tramos representativos.

3. **Dashboard ejecutivo de resultados de socavación**
   - Tarjetas KPI: periodo de retorno, socavación general, socavación local, sección evaluada y estado.
   - Vista transversal con lámina de agua, terreno natural y fondo socavado.
   - Resumen por sección y perfil longitudinal auxiliar.

4. **Módulo visual nuevo**
   - Se agregó `modules/maestra_ui.py` con utilidades de CSS, formato PK, tarjetas, tablas y figuras Plotly.

5. **Imágenes de referencia**
   - Se incorporaron las imágenes entregadas por el usuario como assets limpios:
     - `assets/dashboard_maestra_transporte_sedimentos.png`
     - `assets/dashboard_maestra_resultados_socavacion.png`

6. **Pruebas nuevas**
   - Se agregó `tests/test_maestra_ui.py` para validar helpers, KPI, figuras y tablas del nuevo formato.

## Compatibilidad

- No se elimina el flujo anterior por pestañas.
- No se altera el motor hidráulico ni sedimentológico.
- Se mantiene el editor de sección compuesta natural + rectangular/trapecial.
- Se conservan exportaciones CSV, Excel, HTML 3D y reportes.
