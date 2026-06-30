# Hotfix Axis Line TypeError v3.7.6B

## Problema observado
Al abrir la pestaña `4 · Curvas y eje`, la aplicación mostraba:

`TypeError` en `app.py`, línea asociada a:
```python
st.write(f"Puntos del eje: {len(st.session_state['axis_line'])}")
```

## Causa
El eje preliminar podía quedar guardado como objeto `shapely.geometry.LineString`.
Ese objeto no siempre soporta `len()` directamente. Por eso, al intentar mostrar la cantidad de puntos del eje, Streamlit detenía la ejecución.

## Corrección aplicada
Se agregaron funciones robustas:

- `_axis_line_coords(axis_obj)`
- `_axis_line_point_count(axis_obj)`
- `_axis_line_as_linestring(axis_obj)`

La aplicación ahora normaliza el eje de cauce antes de:
- contar puntos;
- mostrar el eje activo;
- generar secciones DEM;
- enviar el eje a lámina cartográfica.

## Validación
- `python -m compileall .` : OK
- `python -m unittest discover -s tests` : 12/12 OK
- `python test_supreme_internal.py` : 10/10 OK

## Nota
El warning `Spreadsheet runtime warmup failed` mostrado durante las pruebas pertenece al entorno interno de generación de archivos, no a HidroSed ni a Streamlit.
