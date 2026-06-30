# Changelog · HidroSed SedGran v3.7.7 · Secciones compuestas natural + artificial

## Mejora principal incorporada

Se agregó el módulo **Editor de sección compuesta**, orientado a insertar una geometría rectangular o trapecial dentro de una sección natural ya generada por HidroSed.

La mejora responde al flujo técnico solicitado:

```text
ANTES:  sección natural irregular generada desde DEM / KMZ / curvas.
SE AGREGA: canal rectangular o trapecial de diseño dentro del cauce.
DESPUÉS: sección compuesta, conservando riberas naturales y regularizando el cauce central.
```

## Funcionalidades nuevas

1. **Fusión puntual por sección**
   - Selección de una sección existente.
   - Vista previa Antes / Después.
   - Aplicación de canal rectangular o trapecial.
   - Conservación de riberas naturales fuera de la huella artificial.

2. **Fusión por tramo de PK**
   - Selección de PK inicial y PK final.
   - Aplicación de la misma geometría a todas las secciones del tramo.
   - Opción de usar cota mínima natural por sección, rebaje relativo o cota absoluta única.

3. **Parámetros de diseño**
   - Tipo: rectangular o trapecial.
   - Ancho basal / fondo.
   - Profundidad útil.
   - Talud izquierdo H:V.
   - Talud derecho H:V.
   - Desplazamiento respecto del eje hidráulico.
   - Ancho de transición lateral para suavizar la unión con terreno natural.

4. **Trazabilidad técnica**
   - Guarda copia interna de secciones y puntos antes de la primera fusión.
   - Marca las secciones intervenidas como `Rellenada` / `fusionada_diseno`.
   - Exporta resumen CSV de fusión.
   - Limpia resultados hidráulicos/sedimentológicos previos para evitar cálculos con geometría antigua.

5. **Compatibilidad hidráulica**
   - La geometría fusionada alimenta directamente el motor hidráulico irregular 1D.
   - En secciones rectangulares se evita duplicidad exacta de offsets, representando paredes casi verticales para que se integre el perímetro mojado.

## Archivos agregados

```text
modules/design_section_fusion.py
tests/test_design_section_fusion.py
```

## Validación ejecutada

- `python -m compileall -q .` sin errores.
- `python -m pytest -q` con 27 pruebas aprobadas.
- Pruebas específicas de sección compuesta: construcción trapecial, fusión rectangular puntual y fusión por tramo.

## Nota honesta de entorno

En este sandbox no está instalado el ejecutable `streamlit`, por lo que no fue posible levantar visualmente la interfaz. La aplicación mantiene `streamlit==1.45.1` en `requirements.txt` para despliegue en Streamlit Cloud / Hugging Face / ambiente local.
