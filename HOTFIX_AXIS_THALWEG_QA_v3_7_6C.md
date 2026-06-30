# Hotfix QA eje-thalweg v3.7.6C

## Objetivo
Verificar que el eje de cauce generado automáticamente, cuando no se ingresa manualmente, coincida con la cota más baja de cada sección transversal.

## Problema técnico
Un eje preliminar recto puede cruzar una sección lejos del thalweg. En ese caso, el offset 0 no coincide con la menor cota de la sección, lo que puede distorsionar:
- cota de fondo hidráulica;
- tirantes;
- área mojada;
- velocidad;
- desborde;
- socavación y sedimentos.

## Corrección incorporada
Se agregó el módulo:

`modules/axis_thalweg_qaqc.py`

Funciones principales:
- `verify_and_snap_axis_to_section_minima`
- `summarize_axis_thalweg_qa`

## Criterio implementado
Para cada sección:
1. Busca el punto topográfico con menor cota.
2. Calcula el desfase entre ese punto y el offset 0.
3. Si el eje fue generado automáticamente:
   - recentra la sección para que el punto más bajo quede en offset 0;
   - actualiza la cota de fondo;
   - actualiza el eje hidráulico local con las coordenadas del thalweg si existen lon/lat;
   - reconstruye el eje automático como línea de puntos bajos cuando hay suficientes coordenadas.
4. Si el eje fue manual:
   - no se corrige automáticamente;
   - queda informado como `REVISAR` si supera la tolerancia.

## Variables agregadas
En secciones:
- `cota_eje_minima_m`
- `offset_minimo_original_m`
- `desfase_eje_thalweg_m`
- `eje_coincide_cota_minima`
- `eje_recentrado_al_thalweg`
- `axis_source_qaqc`
- `criterio_eje_thalweg`

En puntos:
- `offset_original_m`

En sesión/interfaz:
- `axis_thalweg_qa_df`
- `axis_thalweg_qa_summary`

## Interfaz
En la pestaña de secciones se agregó:
`QA eje de cauce vs cota mínima de sección`

Muestra:
- secciones verificadas;
- secciones recentradas al thalweg;
- secciones a revisar;
- desfase máximo eje-thalweg;
- tabla completa de QA.

## Auditoría
- `python -m compileall .`: OK
- `python -m unittest discover -s tests`: 14/14 OK
- `python test_supreme_internal.py`: 10/10 OK

## Nota
El warning `Spreadsheet runtime warmup failed` mostrado en el entorno de generación pertenece al sandbox interno y no a HidroSed.
