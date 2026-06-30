# HidroSed SedGran v3.8.1 · DEM multifuente QA

## Mejora principal
Se reemplaza el flujo rígido "solo OpenTopography" por un módulo DEM multifuente en la pestaña **2 · DEM**.

## Fuentes incorporadas

1. **OpenTopography API**
   - Mantiene API Key.
   - Mantiene COP30, NASADEM, SRTMGL1 y SRTMGL3.
   - Mantiene descarga normal/por teselas.

2. **Copernicus DEM GLO-30 público COG**
   - Nueva descarga directa desde teselas públicas Cloud Optimized GeoTIFF.
   - No requiere API Key en este modo.
   - Calcula teselas 1°x1° desde el bbox, descarga, mosaica y recorta al bbox.

3. **URL directa GeoTIFF/COG**
   - Permite ingresar un enlace directo a GeoTIFF o COG.
   - Admite token Bearer opcional.
   - Valida que la respuesta sea realmente TIFF/GeoTIFF y no HTML/JSON.

4. **DEM manual GeoTIFF**
   - Se mantiene y se mejora como flujo robusto para plataformas con login.

5. **NASA Earthdata, USGS EarthExplorer y ASF Vertex**
   - Quedan como fuentes asistidas.
   - HidroSed muestra bbox y matriz de autenticación.
   - El usuario descarga fuera de la app y carga GeoTIFF manual.

## Archivos agregados
- `app/modules/dem_sources.py`
- `app/tests/test_dem_sources.py`

## Archivos modificados
- `app/app.py`

## Criterio de diseño
No se guardan contraseñas de portales externos. Para portales con sesión compleja se usa descarga asistida y carga manual de GeoTIFF.
