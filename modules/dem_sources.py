from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import io
import math
import tempfile

import requests

from .opentopo_engine import download_dem
from .opentopo_tiled_download import TileDownloadResult, split_bbox, mosaic_geotiffs


@dataclass(frozen=True)
class DemSourceInfo:
    """Ficha operacional de una fuente DEM para la interfaz HidroSed."""

    key: str
    label: str
    product: str
    resolution: str
    auth_type: str
    requires_api_key: bool
    requires_login: bool
    direct_in_app: bool
    recommended_use: str
    notes: str


def dem_source_registry() -> Dict[str, DemSourceInfo]:
    """Fuentes DEM soportadas o asistidas por HidroSed.

    direct_in_app=True significa que la app puede intentar la descarga desde
    Streamlit usando bbox y credenciales simples. Las fuentes con portales de
    sesión compleja se dejan como flujo asistido: la app muestra el bbox y el
    usuario sube el GeoTIFF descargado.
    """
    entries = [
        DemSourceInfo(
            key="opentopography",
            label="OpenTopography API",
            product="COP30 / NASADEM / SRTMGL1 / SRTMGL3",
            resolution="30 m aprox. según producto",
            auth_type="API Key gratuita",
            requires_api_key=True,
            requires_login=False,
            direct_in_app=True,
            recommended_use="Opción principal cuando el servicio está activo.",
            notes="Requiere API Key de OpenTopography. Permite descarga por bbox y teselas.",
        ),
        DemSourceInfo(
            key="copernicus_public_cog",
            label="Copernicus DEM GLO-30 público COG",
            product="Copernicus DSM COG GLO-30",
            resolution="30 m aprox.",
            auth_type="Sin API Key para bucket público COG",
            requires_api_key=False,
            requires_login=False,
            direct_in_app=True,
            recommended_use="Respaldo automático cuando OpenTopography falla o no hay API Key.",
            notes="Descarga teselas públicas COG de 1°x1° y las mosaica/corta al bbox.",
        ),
        DemSourceInfo(
            key="direct_geotiff_url",
            label="URL directa GeoTIFF/COG",
            product="GeoTIFF / Cloud Optimized GeoTIFF",
            resolution="Según archivo",
            auth_type="Sin auth o token Bearer opcional",
            requires_api_key=False,
            requires_login=False,
            direct_in_app=True,
            recommended_use="Para enlaces firmados, buckets públicos o DEM institucionales.",
            notes="La URL debe devolver directamente un archivo TIFF/GeoTIFF, no una página HTML.",
        ),
        DemSourceInfo(
            key="manual_geotiff",
            label="DEM manual GeoTIFF",
            product="GeoTIFF cargado por usuario",
            resolution="Según archivo",
            auth_type="No aplica",
            requires_api_key=False,
            requires_login=False,
            direct_in_app=False,
            recommended_use="Camino más robusto cuando una plataforma externa está caída.",
            notes="Descarga fuera de la app y carga el .tif/.tiff en HidroSed.",
        ),
        DemSourceInfo(
            key="nasa_earthdata",
            label="NASA Earthdata / LP DAAC",
            product="NASADEM / SRTM y otros DEM NASA",
            resolution="30 m aprox. según producto",
            auth_type="Cuenta Earthdata Login",
            requires_api_key=False,
            requires_login=True,
            direct_in_app=False,
            recommended_use="Alternativa oficial para NASADEM cuando se requiere trazabilidad NASA.",
            notes="Flujo asistido: descargar con Earthdata Search o script autenticado y cargar GeoTIFF.",
        ),
        DemSourceInfo(
            key="usgs_earthexplorer",
            label="USGS EarthExplorer / SRTM",
            product="SRTM 1 Arc-Second Global / Void Filled",
            resolution="30 m aprox.",
            auth_type="Cuenta USGS/EROS; puede exigir EULA",
            requires_api_key=False,
            requires_login=True,
            direct_in_app=False,
            recommended_use="Alternativa estable para SRTM 30 m.",
            notes="Flujo asistido: descargar desde EarthExplorer y cargar el GeoTIFF.",
        ),
        DemSourceInfo(
            key="asf_vertex_alos",
            label="ASF Vertex / ALOS PALSAR",
            product="ALOS PALSAR RTC/DEM 12,5 m según disponibilidad",
            resolution="12,5 m aprox. cuando está disponible",
            auth_type="Cuenta NASA Earthdata/ASF",
            requires_api_key=False,
            requires_login=True,
            direct_in_app=False,
            recommended_use="Mejor detalle para quebradas, cauces angostos y secciones.",
            notes="Flujo asistido: descargar en ASF Vertex y cargar el GeoTIFF.",
        ),
    ]
    return {e.key: e for e in entries}


def dem_source_table() -> List[dict]:
    return [asdict(v) for v in dem_source_registry().values()]


def _deg_tag(value: int, positive_prefix: str, negative_prefix: str, width: int) -> str:
    prefix = positive_prefix if value >= 0 else negative_prefix
    return f"{prefix}{abs(int(value)):0{width}d}_00"


def copernicus_tile_id(lat_floor: int, lon_floor: int) -> str:
    """ID de tesela Copernicus DEM COG para la celda 1°x1°.

    Ejemplo Chile: lat_floor=-30, lon_floor=-71 ->
    Copernicus_DSM_COG_10_S30_00_W071_00_DEM
    """
    lat_tag = _deg_tag(int(lat_floor), "N", "S", 2)
    lon_tag = _deg_tag(int(lon_floor), "E", "W", 3)
    return f"Copernicus_DSM_COG_10_{lat_tag}_{lon_tag}_DEM"


def copernicus_tile_url(lat_floor: int, lon_floor: int) -> str:
    folder = copernicus_tile_id(lat_floor, lon_floor)
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{folder}/{folder}.tif"


def _int_range_for_bbox(min_val: float, max_val: float) -> range:
    start = math.floor(float(min_val))
    # Si max_val cae exacto en entero, esa tesela no se requiere.
    end = math.ceil(float(max_val))
    return range(start, end)


def copernicus_tiles_for_bbox(bbox: Dict[str, float]) -> List[dict]:
    south, north = sorted([float(bbox["south"]), float(bbox["north"])])
    west, east = sorted([float(bbox["west"]), float(bbox["east"])])
    tiles: List[dict] = []
    for lat_floor in _int_range_for_bbox(south, north):
        for lon_floor in _int_range_for_bbox(west, east):
            tid = copernicus_tile_id(lat_floor, lon_floor)
            tiles.append({
                "tile_id": tid,
                "lat_floor": int(lat_floor),
                "lon_floor": int(lon_floor),
                "url": copernicus_tile_url(lat_floor, lon_floor),
                "bbox": {
                    "south": float(lat_floor),
                    "north": float(lat_floor + 1),
                    "west": float(lon_floor),
                    "east": float(lon_floor + 1),
                },
            })
    return tiles


def _looks_like_tiff(data: bytes) -> bool:
    return bool(data) and (data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"))


def _ensure_geotiff_bytes(data: bytes, source_label: str) -> bytes:
    if not data:
        raise RuntimeError(f"{source_label}: respuesta vacía.")
    lower = data[:800].lower()
    if lower.startswith(b"<html") or b"<html" in lower or b"access denied" in lower:
        preview = data.decode("utf-8", errors="ignore")[:400]
        raise RuntimeError(f"{source_label}: la respuesta no es GeoTIFF directo. Vista previa: {preview}")
    # Algunos COG remotos pueden incluir metadatos previos en casos raros, pero
    # para descarga directa exigimos firma TIFF para evitar guardar HTML/JSON.
    if not _looks_like_tiff(data):
        preview = data[:80]
        raise RuntimeError(f"{source_label}: no parece TIFF/GeoTIFF válido. Primeros bytes: {preview!r}")
    return data


def download_url_bytes(url: str, token: str | None = None, timeout=(10, 240)) -> bytes:
    url = (url or "").strip()
    if not url:
        raise ValueError("Debe ingresar una URL directa a GeoTIFF/COG.")
    headers = {"User-Agent": "HidroSed-DEM-Multifuente/3.8.1"}
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
    except requests.Timeout as exc:
        raise RuntimeError("Tiempo de espera agotado descargando URL directa DEM.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"No fue posible conectar con URL DEM: {exc}") from exc
    if r.status_code >= 400:
        raise RuntimeError(f"URL DEM respondió HTTP {r.status_code}.")
    return _ensure_geotiff_bytes(r.content, "URL DEM")


def _download_one_copernicus_tile(tile: dict, timeout=(10, 240)) -> bytes:
    try:
        r = requests.get(tile["url"], timeout=timeout, headers={"User-Agent": "HidroSed-DEM-Multifuente/3.8.1"})
    except requests.Timeout as exc:
        raise RuntimeError(f"Tiempo agotado descargando {tile['tile_id']}.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"No fue posible descargar {tile['tile_id']}: {exc}") from exc
    if r.status_code == 404:
        raise FileNotFoundError(f"Tesela no disponible: {tile['tile_id']}")
    if r.status_code >= 400:
        raise RuntimeError(f"{tile['tile_id']} respondió HTTP {r.status_code}.")
    return _ensure_geotiff_bytes(r.content, tile["tile_id"])


def crop_mosaic_to_bbox(tile_files: List[Path], bbox: Dict[str, float]) -> bytes:
    import rasterio
    from rasterio.merge import merge

    datasets = []
    try:
        for p in tile_files:
            datasets.append(rasterio.open(p))
        bounds = (float(bbox["west"]), float(bbox["south"]), float(bbox["east"]), float(bbox["north"]))
        mosaic, out_transform = merge(datasets, bounds=bounds)
        meta = datasets[0].meta.copy()
        meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "compress": "deflate",
            "predictor": 2,
        })
        with rasterio.io.MemoryFile() as mem:
            with mem.open(**meta) as dst:
                dst.write(mosaic)
            return mem.read()
    finally:
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass


def download_copernicus_public_dem(
    bbox: Dict[str, float],
    progress_callback=None,
    crop_to_bbox: bool = True,
) -> TileDownloadResult:
    """Descarga Copernicus DEM GLO-30 COG público, mosaica y retorna GeoTIFF.

    No usa API Key. Si algunas teselas no existen, se omiten; si no se puede
    obtener ninguna tesela, falla con diagnóstico claro.
    """
    tiles = copernicus_tiles_for_bbox(bbox)
    if not tiles:
        raise ValueError("BBox inválido: no se generaron teselas Copernicus.")
    tmp = Path(tempfile.mkdtemp(prefix="hidrosed_copdem_"))
    tile_paths: List[Path] = []
    meta_tiles: List[dict] = []
    failures: List[str] = []
    for idx, tile in enumerate(tiles, start=1):
        if progress_callback:
            progress_callback(f"Descargando Copernicus DEM {idx}/{len(tiles)} · {tile['tile_id']}...", (idx - 1) / max(len(tiles), 1))
        try:
            data = _download_one_copernicus_tile(tile)
        except FileNotFoundError as exc:
            failures.append(str(exc))
            continue
        fp = tmp / f"{tile['tile_id']}.tif"
        fp.write_bytes(data)
        tile_paths.append(fp)
        meta_tiles.append({"tile_id": tile["tile_id"], "url": tile["url"], "bytes": len(data)})
    if not tile_paths:
        detail = "; ".join(failures[:5]) if failures else "sin detalle"
        raise RuntimeError(f"No se pudo descargar ninguna tesela Copernicus DEM para el bbox. {detail}")
    if progress_callback:
        progress_callback("Uniendo teselas Copernicus DEM en GeoTIFF único...", 0.92)
    if crop_to_bbox:
        dem_bytes = crop_mosaic_to_bbox(tile_paths, bbox)
    else:
        dem_bytes = mosaic_geotiffs(tile_paths)
    if progress_callback:
        progress_callback("DEM Copernicus listo.", 1.0)
    return TileDownloadResult(dem_bytes=dem_bytes, metadata={
        "source": "Copernicus DEM GLO-30 público COG",
        "download_mode": "public_cog_tiled",
        "tiles_requested": len(tiles),
        "tiles_downloaded": len(tile_paths),
        "tile_metadata": meta_tiles,
        "tile_failures": failures[:20],
        "mosaic_bytes": len(dem_bytes),
        "crop_to_bbox": bool(crop_to_bbox),
    })
