# HidroSed SedGran v3.8.0 · QA Cuenca Completa / Portal Compuesto

## Problema corregido
En puntos de control ubicados en abanicos aluviales, caminos, cauces poco incisos o sectores donde el DEM reparte el flujo en varios hilos paralelos, la delimitación puntual podía capturar solo una parte de la cuenca aportante. Visualmente el resultado aparecía como una cuenca estrecha o incompleta, equivalente a “media cuenca”.

## Mejora aplicada
Se incorpora un sistema de **cierre compuesto de salida**:

- Mantiene el ajuste automático del punto al cauce DEM.
- Evalúa el outlet puntual principal.
- Busca hilos de salida adicionales dentro de un radio de portal.
- Une subcuencas laterales que aportan al mismo exutorio/abanico.
- Rechaza candidatas que toquen borde DEM, NoData o excedan el área máxima definida.
- Conserva diagnóstico técnico y trazabilidad de los outlets adicionales usados.

## Nuevos modos de cierre

- `Automático: puntual + portal si falta cuenca`.
- `Portal compuesto forzado`.
- `Solo outlet puntual`.

## Parámetro nuevo

- `Radio portal compuesto [m]`: 250, 500, 750, 1000, 1500, 2000, 3000, 5000.

Para casos como el mostrado por el usuario, se recomienda partir con 1000 a 3000 m.
