# HidroSed Maestra Integrada v3.8.3 · Casos de aplicación, DEM multifuente y QA cuenca

Plataforma Streamlit para hidrología, hidráulica 1D, sedimentos, socavación, DEM OpenTopography, curvas de nivel, secciones, rugosidad, granulometría KMZ, QA e incertidumbre.


## Mejora v3.7.9 · Corrección automática de punto y cuenca validada

- Ajusta automáticamente el punto de control al cauce real detectado por acumulación de flujo del DEM.
- Evalúa candidatos de salida y penaliza alternativas que generen cuencas truncadas.
- Detecta si la cuenca toca borde del DEM o zonas NoData.
- Muestra diagnóstico técnico con controles mínimos, severidad y acción recomendada.
- Solo habilita KMZ/KML y uso posterior cuando `estado_validacion = VALIDADA`.

## Mejora v3.7.8 · Formato visual HidroSed Maestra Integrada

Se incorporó el formato visual de referencia enviado por el usuario:

- Barra lateral oscura tipo flujo de trabajo con 12 etapas.
- Tarjetas KPI para transporte de sedimentos, velocidad, tensión de corte, D50 y tramo PK.
- Panel longitudinal con tendencia de erosión/equilibrio/deposición.
- Panel ejecutivo de resultados de socavación por sección.
- Resumen por sección y perfil del cauce en formato tablero.
- Galería de referencia con las dos imágenes entregadas por el usuario.

La mejora se agregó sin eliminar el flujo técnico existente, manteniendo tablas, exportación, QA, trazabilidad y el editor de secciones compuestas v3.7.7.

## Mejora v3.7.7 · Editor de sección compuesta

Se incorporó una herramienta para insertar una sección rectangular o trapecial dentro de una sección natural existente. La app conserva las riberas naturales, reemplaza el tramo central por geometría de diseño, permite aplicación puntual o por tramo de PK, guarda trazabilidad y obliga a recalcular hidráulica/sedimentos después de modificar la geometría.

## Main file path

```text
app.py
```

## Mejoras principales v3.0

1. Plataforma visual superior con panel tipo centro de control hidráulico.
2. Nuevo módulo de rugosidad avanzada: ingreso manual, tabla Manning, Cowan y Strickler/granulometría.
3. Rugosidad diferenciable por margen izquierda, cauce principal y margen derecha.
4. Sección trapezoidal estimada cuando no existan secciones suficientes desde DEM/topografía.
5. Secciones trapezoidales por tramo con ancho de fondo, profundidad, taludes, pendiente y cota inicial.
6. Capacidad hidráulica preliminar de secciones trapezoidales con tirante normal, crítico, velocidad y Froude.
7. Granulometría georreferenciada con tabla CSV/XLSX y KMZ/KML de muestras.
8. Validación granulométrica: orden D50/D84/D90, unidades, positividad y confianza.
9. Interpolación longitudinal de D50, D84, D90 y D95 por PK y asignación a cada sección.
10. Transferencia hidrológica dual área-altitud-distancia.
11. Semáforo maestro de confianza por bloque técnico.
12. Conserva descarga DEM OpenTopography normal o por teselas y mosaico interno.
13. Conserva delimitación de cuenca, curvas por teselas, secciones reales, hidrología, hidráulica conectada y 3D.
14. Agrega trazabilidad técnica para rugosidad y granulometría.
15. Agrega reporte interno de 10 corridas de verificación.

## Nuevos módulos

```text
modules/roughness_engine.py
modules/synthetic_trapezoid_sections.py
modules/granulometry_kmz.py
modules/hydrologic_transfer_dual.py
modules/supreme_dashboard.py
modules/maestra_ui.py
```

## Corridas internas

Se ejecutó una suite interna con 10 ciclos x 10 pruebas = 100 verificaciones OK.

Archivo de reporte:

```text
outputs/reporte_10_corridas_supremo.csv
```

## Limitaciones honestas

- No se probó descarga real OpenTopography desde esta sesión porque requiere API Key activa y ejecución con internet en Streamlit Cloud.
- La sección trapezoidal es un modo estimativo/preliminar y no reemplaza levantamiento topográfico.
- El motor hidráulico es 1D permanente tipo HEC-RAS simplificado/mejorado, útil para análisis técnico preliminar; no reemplaza una modelación oficial calibrada cuando existan singularidades, puentes, alcantarillas, flujo no permanente o condiciones 2D.
- La rugosidad estimada por Cowan/tabla/Strickler debe verificarse en terreno cuando el proyecto pase a diseño definitivo.


## Hotfix DEM

Corrección aplicada:
- Se agregó la importación faltante:
  `download_dem_normal_or_tiled` y `recommended_tiling`
  desde `modules/opentopo_tiled_download.py`.

Este hotfix corrige el error:
`NameError: name 'recommended_tiling' is not defined`.


## Hotfix Topografía Opcional

Corrección aplicada:
- Las curvas de nivel de apoyo topográfico quedan estrictamente opcionales.
- Si no se cargan, el proceso continúa con DEM.
- Si se cargan pero fallan, el proceso continúa con DEM.
- Si no contienen cotas válidas, el proceso continúa con DEM.
- Durante la generación de secciones, cualquier error del apoyo topográfico cae a modo DEM sin detener el flujo.


## Hotfix Curvas por Teselas

Corrección aplicada:
- Se reemplazó `cs.collections` por `cs.allsegs` en `modules/tiled_contours.py`.
- Corrige el error: `'QuadContourSet' object has no attribute 'collections'`.
- El modo por teselas vuelve a generar curvas KMZ/KML unificadas.


## Hotfix Cloud Safe para curvas

Corrección aplicada:
- `runtime.txt` con Python 3.11 para Streamlit Cloud.
- Dependencias geoespaciales acotadas.
- Curvas por teselas sin crear mallas X/Y grandes.
- Downsampling automático por tesela para evitar caída por memoria.
- `cs.allsegs` compatible con Matplotlib actual.
- Metadata por tesela para revisar factor de reducción, niveles y placemarks.


## v3.1 - Verificación cuenca + curvas de nivel

Se incorpora salida equivalente a la app de referencia cuencadem0:

- La cuenca se mantiene delimitada por el motor D8/Priority-Flood.
- Las curvas de nivel se pueden recortar al polígono de cuenca.
- Se genera un solo KMZ/KML con cuenca + curvas de nivel.
- Se agrega vista previa tipo EPSG:4326 con cuenca y curvas.
- Botón: `Descargar KMZ cuenca + curvas de nivel`.


## v3.1.1 Hotfix Cuenca Anti-Snap

Corrección crítica de delimitación:
- El ajuste del punto al cauce ya no usa solamente máxima acumulación.
- Se agregó modo `Controlado por área`.
- Se agregó área esperada aproximada.
- Se agregó área máxima permitida.
- Se redujo radio inicial recomendado a 250 m.
- Se evalúan candidatos alternativos de salida.
- Se muestra tabla QA de candidatos evaluados.

Recomendación para cuencas pequeñas:
- Radio: 100 a 500 m.
- Modo: Controlado por área.
- Área esperada: área aproximada real, por ejemplo 20 km².
- Área máxima permitida: 2 a 5 veces el área esperada, por ejemplo 50 a 100 km².


## v3.1.4 BBox demcop30 integrado

Esta versión aplica dentro de la misma aplicación v3.1.1 la lógica de la app `demcop30_streamlit`:

- BBox controlado por tamaño esperado de cuenca.
- Unidad por defecto en km.
- Preajustes para quebrada pequeña, cuenca pequeña, mediana y grande.
- Advertencias si el BBox es desproporcionado respecto del área referencial.
- DEM manual GeoTIFF opcional, para usar DEM ya descargado con app estable.
- Mantiene OpenTopography, descarga normal/por partes, Anti-Snap y curvas.

Importante:
- El área bbox es la ventana rectangular del DEM.
- El área bbox no es la superficie real de la cuenca.
- La cuenca se delimita en la pestaña 3 usando el DEM y el punto de control.


## v3.1.6 SedGran

Nombre corto: **HidroSed SedGran**.

Mejoras:
- Módulo granulométrico por defecto con 6 perfiles tipo.
- Lectura Excel/CSV de granulometría real.
- Soporta columnas de diámetros D16/D30/D50/D84/D90 o curvas por tamiz.
- Interpola D5, D10, D16, D25, D30, D35, D50, D60, D65, D75, D84, D90, D95.
- Calcula Dm, Cu, Cc y clasificación del material.
- Tabla interna de diámetro usado por metodología.
- La hidráulica/sedimentos usa D50 y D90 adoptados desde el módulo.


## v3.1.7 SedGran Fix

Corrección:
- Se elimina un expander anidado dentro del módulo de granulometría.
- Streamlit no permite `st.expander` dentro de otro `st.expander`.
- Se reemplaza la tabla interna por pestañas: Diámetros, Metodologías, Curva granulométrica y Muestras Excel/CSV.


## v3.1.8 SectionSafe Fix

Corrección:
- El cálculo hidráulico ya no se detiene si falta la nube de puntos de una sección.
- Si aparece una sección en `sections_df` pero no en `section_points_df`, se crea una sección trapezoidal sintética fallback.
- La tabla hidráulica marca `geometria_status` y `geometria_fallback`.
- La app muestra QA de geometría usada en el cálculo.
- Esto evita errores tipo: `No hay puntos para la sección 581`.


## v3.1.9 Preview3D / Manual de Carreteras

Cambios candidatos:
- Corrige error Plotly `showlegend` por valores numpy.bool_.
- Agrega ventana de revisión de secciones seleccionadas.
- Agrega perfil longitudinal 3D previo de secciones.
- Colores QA: verde aceptadas, azul rellenadas, rojo eliminadas/revisar.
- Permite seleccionar qué estados mostrar.
- Incorpora galería técnica de referencia visual.
- Agrega mensaje de alineación preliminar con Manual de Carreteras.


## v3.2 Isoyetas y matriz normativa

Cambios:
- Incorpora `data/isoyetas/Precipitaciones_Maximas_Diarias.kmz` si está disponible.
- Agrega `modules/isoyetas_engine.py`.
- Lee KMZ/KML de isoyetas.
- Extrae valores P24 desde nombres/descripciones.
- Estima P24 por:
  - isoyeta que contiene/toca el punto,
  - ponderación espacial con cuenca,
  - interpolación IDW con isoyetas cercanas.
- Permite cargar KMZ/KML externo de isoyetas.
- P24 manual queda como respaldo.
- Agrega `modules/normativa_hidrosed.py`.
- Genera matriz normativa Manual de Carreteras / DGA / HEC-RAS / Sedimentos.
- Muestra puntaje de confianza normativa-hidrológica.


## v3.4 HEC-RAS QA 3D Base DGA

Candidata de revisión avanzada:
- Vistas 3D fijas: planta/superior, lateral, aguas arriba, aguas abajo, isométrica y rotación libre.
- Exportación HTML 3D.
- Motor hidráulico conectado tipo HEC-RAS con paso estándar.
- Sensibilidad automática Manning ±20%.
- QA hidráulica automática por sección.
- Sedimentos avanzados: Shields, MPM, Engelund-Hansen, densidad del agua por temperatura, movilidad del lecho.
- Socavación general y local preliminar.
- Monte Carlo para incertidumbre Q/n/D50/S.
- Puntaje de confianza 1 a 10.
- Base DGA/Sedimentos precargada comprimida.
- Excel avanzado con hojas: Confianza_v6, Incertidumbre_MC_v6, Calibracion_v6 (cuando exista), Sensibilidad_Manning.

Ver `AUDITORIA_SEDGRAN_V34_HECRAS_QA_3D.md`.


## v3.5 Normativa DGA/MC/IDF/Pmax123

Corrección solicitada:
- La hidrología ahora incorpora estructura de cumplimiento Manual DGA + Manual de Carreteras + IDF + precipitación máxima 1, 2 y 3 días.
- No se desordena la plataforma: los controles nuevos quedan en una sección compacta y los resultados en pestañas.
- Ver `AUDITORIA_SEDGRAN_V35_NORMATIVA.md`.


## v3.6 Correctivas prioritarias

Se aplican las acciones correctivas priorizadas en la auditoría:
1. Frecuencia real de caudales máximos diarios conectada a Q(T).
2. Relleno pluviométrico por regresión/razón normal.
3. Validación estación-isoyeta con semáforo y adopción conservadora.
4. Calibración automática de Manning con cotas observadas.
5. Rangos de aplicación para MPM, Engelund-Hansen, Shields y socavación.
6. Coeficientes regionales en CSV editable.
7. Memoria de cálculo automática.
8. Pruebas unitarias adicionales para cuencas pequeñas, medianas, nivales y fuera de rango.
9. Visualización de isoyetas.
10. Exportación completa en Excel avanzado.


## v3.7 Correctivas Plus

Mejoras:
- Ventana experta de sección seleccionada.
- Gráfico transversal con lámina de agua, área mojada, socavación y depositación.
- Tabla resumen por sección: hidráulica, sedimentos, QA y sensibilidad Manning.
- Conserva v3.6: hidrología normativa, correctivas, base DGA, isoyetas, HEC-RAS QA y exportaciones.


## v3.7.1 Hotfix Imports

Corrección:
- Se corrige `NameError: load_catalog is not defined`.
- Se restauran importaciones de `data_catalog_engine`, `hydrology_normative_v35` y `corrective_actions_v36`.
- Se agrega `numpy` para la ventana experta de secciones.


## v3.7.2 Hotfix secciones reales + QA producción

Correcciones:
- Se reemplaza visualización plana de secciones por perfiles transversales reales en 3D.
- Se corrigen filtros `Ver aceptadas`, `Ver rellenadas`, `Ver eliminadas`.
- Se agrega ventana 2D por sección en el módulo 5 Secciones.
- Se agrega auditoría de producción con 10 pruebas:
  1. compileall completo;
  2. revisión estática;
  3. búsqueda NameError/KeyError/AttributeError;
  4. arranque real Streamlit;
  5. ejecución de pestañas;
  6. botones críticos;
  7. datos demo;
  8. archivos reales;
  9. exportables;
  10. informe de errores corregidos.

Ver `AUDITORIA_PRODUCCION_SEDGRAN_V372.md`.


## v3.7.3 Hotfix imports isoyetas/normativa + QA producción

Correcciones:
- Corrige `read_isoyetas_kmz_kml` no definido.
- Corrige `normative_hydraulic_hydrology_check` no definido.
- Mantiene v3.7.2: secciones 3D reales, filtros operativos y ventana 2D por sección.
- QA producción ejecutado y documentado.

Ver `AUDITORIA_PRODUCCION_SEDGRAN_V373.md`.


## v3.7.4 Secciones v13 replicada

Esta versión mantiene el `app.py` principal de v3.7.3 y replica la aplicación `app_secciones_kmz_v13_fix_km_final_utm19s_3d` dentro del paquete.

Rutas:
- `app.py`: aplicación principal HidroSed SedGran v3.7.3.
- `secciones_v13_original_replicada/app_secciones_kmz.py`: réplica de la aplicación standalone subida por el usuario.
- `app_secciones_kmz_v13_fix_km_final_utm19s_3d.py`: copia directa en raíz.
- `modules/sections_v13_core.py`: motor de cálculo v13 integrado en HidroSed, verificado funcionalmente idéntico a la app subida salvo la función de interfaz `_fid_from_option`.

Ver auditoría: `AUDITORIA_PRODUCCION_SEDGRAN_V374_SECCIONES_REPLICADA.md`.

---

# Actualización v3.7.6 · Auditoría General Hidráulica Sedimentos QA

Esta versión incorpora una nueva pestaña **11 · Auditoría general**, orientada a proyectos hidrológicos e hidráulicos genéricos: puentes, defensas fluviales, esteros, ríos, quebradas, canales naturales, alcantarillas, cajones, desembocaduras, humedales y obras de protección.

Incluye:
- comparador de tiempo de concentración;
- módulo IDF regional editable;
- caudales por Racional, Verni-King Modificado, DGA-AC y SCS-CN preliminar;
- auditor de caudal adoptado;
- condición aguas abajo, marea, humedal y barra litoral;
- socavación general y local preliminar;
- predimensionamiento de protección fluvial;
- auditoría de informe externo;
- sistema de puntaje técnico 0 a 10;
- exportación Excel, Markdown, DOCX y PDF;
- carpeta `tests/` con 12 pruebas genéricas.

Para ejecutar:

```bash
pip install -r requirements.txt
streamlit run app.py
```


## Mejora v3.8.3 · Casos de aplicación y salidas enlazadas

Se agrega selector de cuatro casos cuenca–eje, imágenes referenciales, fichas desplegables, alertas de respaldo topográfico para casos 2, 3 y 4, y exportación KMZ/KML cuenca + eje y cuenca + eje + curvas.
