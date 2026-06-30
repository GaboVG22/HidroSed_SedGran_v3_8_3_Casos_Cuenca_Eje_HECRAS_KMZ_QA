# HidroSed v3.8.3 · Mejoras casos cuenca-eje / HEC-RAS / KMZ

Esta versión aplica el prompt correcto `Prompt_Mejoras_HidroSed_Casos_Cuenca_Eje_HECRAS_KMZ.docx` sobre la línea funcional v3.8.x, manteniendo compatibilidad con DEM multifuente, QA de cuenca, secciones compuestas y tablero HidroSed Maestra.

## Mejoras principales

1. Selector obligatorio **Caso tipo de modelación cuenca–eje** con cuatro casos:
   - Caso 1: Cuenca + eje dentro de la cuenca.
   - Caso 2: Cuenca + eje dentro y fuera de la cuenca.
   - Caso 3: Cuenca + eje marginal desde salida.
   - Caso 4: Cuenca aportante + eje externo alejado.

2. Alertas topográficas permanentes para los casos 2, 3 y 4.

3. Flujo de cuenca con estados trazables:
   - `cuenca_preliminar`.
   - `cuenca_validada`.
   - `cuenca_corregida`.
   - `cuenca_activa`.

4. Carga de cuenca corregida en KMZ/KML/GeoJSON/ZIP SHP, con comparación de área preliminar versus corregida.

5. Generación de eje automático DEM/thalweg si el usuario no carga eje manual.

6. Exportación KMZ ordenada en dos archivos principales:
   - `eje_cauce_cuenca.kmz`.
   - `cuenca_eje_curvas_unificado.kmz`.

7. Plantilla y carga de secciones tipo HEC-RAS:
   - `Formato_Carga_Secciones_HECRAS_HidroSed.xlsx`.
   - Hoja obligatoria `SECCIONES_HECRAS`.
   - Validación de columnas, puntos mínimos, duplicados, cotas y Manning.

8. Diagnóstico técnico descargable en TXT y CSV.

## Nota sobre documentos cargados

En futuras ejecuciones, si el archivo cargado no corresponde al contenido esperado del prompt o tema solicitado, debe avisarse al usuario antes de modificar la aplicación.
