# Auditoría producción · HidroSed SedGran v3.7.9

## Controles ejecutados

- `python -m compileall .`: OK
- `pytest -q`: 33 pruebas aprobadas
- `streamlit run app.py --server.headless true --server.port 8519`: servidor levantado correctamente
- Health check `/_stcore/health`: HTTP 200 OK

## Pruebas nuevas

- Detección de cuenca truncada por borde del DEM.
- Detección de contacto con NoData.
- Bloqueo de cuenca no validada.
- Aprobación de candidato que cumple controles mínimos.

## Advertencias conocidas

- El ajuste automático depende de la calidad/resolución del DEM y del radio de búsqueda.
- Si el DEM fue descargado con margen insuficiente, la app no declara la cuenca como validada; exige ampliar DEM o cargar uno completo.
- Las advertencias de `test_supreme_internal.py` corresponden a pruebas históricas que retornan tuplas; no afectan el resultado funcional.
