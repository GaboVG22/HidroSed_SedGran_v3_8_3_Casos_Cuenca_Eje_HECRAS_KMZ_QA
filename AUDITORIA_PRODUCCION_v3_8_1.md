# Auditoría producción v3.8.1 · DEM multifuente

## Alcance probado
- Compilación completa de la aplicación.
- Pruebas unitarias del nuevo registro de fuentes DEM.
- Pruebas unitarias de generación de nombres y URLs Copernicus DEM COG.
- Pruebas unitarias de cálculo de teselas para bbox en Chile.
- Regresión completa de pruebas existentes.

## Resultados

```text
compileall completo: OK
pytest completo: 37 pruebas aprobadas
nuevas pruebas DEM multifuente: OK
```

## Observaciones
- No se ejecutó descarga real desde internet dentro del contenedor de QA.
- La lógica de red queda protegida con errores claros para timeout, HTTP >= 400, respuesta vacía y respuesta no GeoTIFF.
- Streamlit no está instalado en el contenedor de QA, por lo que no se levantó la interfaz visual aquí.

## Riesgos controlados
- OpenTopography conserva API Key individual del usuario.
- Copernicus público puede no tener ciertas teselas GLO-30 liberadas; la app informa fallas de teselas.
- NASA Earthdata, USGS EarthExplorer y ASF Vertex usan sesión/login/EULA, por lo que se operan como flujo asistido para no manejar contraseñas en HidroSed.
