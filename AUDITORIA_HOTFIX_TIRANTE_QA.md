# Auditoría Hotfix Tirante QA

## Problema revisado
En la visualización de sección se observaba una cota de agua cercana a 1112 m y un tirante superior a 250-300 m sobre un fondo cercano a 800 m. Ese resultado no es físicamente razonable para un caudal del orden de 60 m³/s.

## Causa técnica identificada
1. El módulo hidráulico asumía que el mayor PK correspondía siempre a aguas abajo.
2. Si el eje KMZ fue dibujado desde aguas abajo hacia aguas arriba, el mayor PK queda en cotas más altas.
3. La condición de borde se aplicaba entonces en una sección alta y esa cota se propagaba hacia secciones bajas, generando tirantes artificiales de cientos de metros.
4. En cauces de fuerte pendiente, la marcha subcrítica por energía también podía extrapolar niveles fuera de la sección transversal si la geometría o el sentido hidráulico no eran adecuados.

## Correcciones aplicadas
- Detección automática de orientación hidráulica por regresión cota de fondo vs PK.
- Si el PK crece hacia cotas mayores, el cálculo invierte el orden hidráulico internamente.
- Se agregan columnas de trazabilidad: `orientacion_eje_detectada`, `orden_hidraulico`, `pendiente_fondo_dz_dpk`.
- Se agrega control QA de tirante irreal: si la lámina excede la topografía de la sección de forma no física, se reemplaza por tirante normal local y se marca el registro.
- Se agregan columnas: `control_tirante_irreal`, `wse_original_m`, `wse_limite_QA_m`, `criterio_control_tirante`.
- La interfaz informa cuando el QA corrige registros y recomienda revisar sentido del eje, ancho de sección o condición de borde.

## Verificación
- `python3 -m compileall -q .`: OK.
- `PYTHONPATH=. python3 test_supreme_internal.py`: 10/10 pruebas OK.
- Prueba sintética con eje dibujado aguas abajo→aguas arriba: el tirante de sección baja deja de quedar artificialmente a cota alta y se calcula con tirante normal local, quedando marcado en QA.

## Nota de uso
Si aparece `pk_crece_hacia_aguas_arriba_corregido`, no es necesariamente error de usuario: significa que el eje fue dibujado en sentido contrario al supuesto hidráulico. La aplicación ahora lo corrige internamente, pero para modelación definitiva conviene dibujar el eje desde aguas arriba hacia aguas abajo o revisar el sentido hidráulico antes de exportar resultados.
