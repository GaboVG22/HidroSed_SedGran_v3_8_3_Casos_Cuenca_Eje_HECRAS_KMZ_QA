
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import heapq
import math
import zipfile
from collections import deque

import numpy as np
import pandas as pd


@dataclass
class BasinResult:
    kmz_bytes: bytes
    kml_bytes: bytes
    preview_png: bytes | None
    metrics: dict


def _read_dem(path_or_bytes, max_cells: int = 1_500_000):
    import rasterio
    from rasterio import Affine
    from rasterio.io import MemoryFile

    if isinstance(path_or_bytes, (str, Path)):
        src_ctx = rasterio.open(path_or_bytes)
    else:
        mem = MemoryFile(path_or_bytes)
        src_ctx = mem.open()

    with src_ctx as src:
        data = src.read(1, masked=True).astype("float64").filled(np.nan)
        if src.nodata is not None:
            data = np.where(np.isclose(data, src.nodata), np.nan, data)
        transform = src.transform
        crs = src.crs
        factor = 1
        cells = int(data.shape[0] * data.shape[1])
        if cells > max_cells:
            factor = int(math.ceil(math.sqrt(cells / max_cells)))
            data = data[::factor, ::factor]
            transform = transform * Affine.scale(factor, factor)

    if int(np.isfinite(data).sum()) < 100:
        raise ValueError("El DEM no contiene suficientes datos válidos para delimitar la cuenca.")
    return data, transform, crs, factor


def _cell_sizes_m(transform, crs, shape):
    dx_raw = abs(float(transform.a))
    dy_raw = abs(float(transform.e))
    try:
        is_geo = bool(crs and getattr(crs, "is_geographic", False))
    except Exception:
        is_geo = False
    if is_geo:
        y_mid = transform.f + transform.e * (shape[0] / 2)
        dx = dx_raw * 111_320.0 * max(0.15, math.cos(math.radians(float(y_mid))))
        dy = dy_raw * 110_574.0
    else:
        dx, dy = dx_raw, dy_raw
    return float(dx), float(dy), float(math.sqrt(dx * dy))


def _lonlat_to_rowcol(lon, lat, transform, crs):
    if crs is not None:
        try:
            epsg = crs.to_epsg()
        except Exception:
            epsg = None
        if epsg != 4326:
            try:
                from pyproj import Transformer
                tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
                lon, lat = tr.transform(lon, lat)
            except Exception:
                pass
    inv = ~transform
    col, row = inv * (float(lon), float(lat))
    return int(round(row)), int(round(col))


def _rowcol_to_lonlat(row, col, transform, crs):
    x, y = transform * (float(col), float(row))
    if crs is not None:
        try:
            epsg = crs.to_epsg()
        except Exception:
            epsg = None
        if epsg != 4326:
            try:
                from pyproj import Transformer
                tr = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                x, y = tr.transform(x, y)
            except Exception:
                pass
    return float(x), float(y)


def _priority_flood(dem, valid):
    """Priority-Flood con epsilon para evitar flats cerrados.

    La versión sin epsilon puede dejar terrazas perfectamente planas después del
    relleno de depresiones; en ese caso D8 no encuentra pendiente positiva y la
    cuenca queda incompleta. Este relleno fuerza una pendiente mínima hacia el
    borde, manteniendo cambios altimétricos despreciables para uso hidrológico.
    """
    nrows, ncols = dem.shape
    filled = dem.copy()
    visited = np.zeros_like(valid, dtype=bool)
    heap = []

    finite = dem[np.isfinite(dem)]
    relief = float(np.nanmax(finite) - np.nanmin(finite)) if finite.size else 1.0
    eps = max(1e-6, relief * 1e-9)

    for r in range(nrows):
        for c in (0, ncols - 1):
            if valid[r, c] and not visited[r, c]:
                visited[r, c] = True
                heapq.heappush(heap, (filled[r, c], r, c))
    for c in range(ncols):
        for r in (0, nrows - 1):
            if valid[r, c] and not visited[r, c]:
                visited[r, c] = True
                heapq.heappush(heap, (filled[r, c], r, c))

    neigh = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    while heap:
        z, r, c = heapq.heappop(heap)
        for dr, dc in neigh:
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= nrows or cc < 0 or cc >= ncols:
                continue
            if not valid[rr, cc] or visited[rr, cc]:
                continue
            visited[rr, cc] = True
            if filled[rr, cc] <= z:
                filled[rr, cc] = z + eps
            heapq.heappush(heap, (filled[rr, cc], rr, cc))
    return filled


def _flow_dir_d8(filled, valid, dx, dy):
    nrows, ncols = filled.shape
    dst = np.full(nrows*ncols, -1, dtype=np.int64)
    neigh = [
        (-1,-1,math.hypot(dx,dy)),(-1,0,dy),(-1,1,math.hypot(dx,dy)),
        (0,-1,dx),(0,1,dx),
        (1,-1,math.hypot(dx,dy)),(1,0,dy),(1,1,math.hypot(dx,dy)),
    ]
    for r in range(nrows):
        for c in range(ncols):
            if not valid[r,c]:
                continue
            best = -1
            best_s = 0.0
            z = filled[r,c]
            for dr, dc, dist in neigh:
                rr, cc = r+dr, c+dc
                if rr < 0 or rr >= nrows or cc < 0 or cc >= ncols or not valid[rr,cc]:
                    continue
                s = (z - filled[rr,cc]) / max(dist, 1e-9)
                if s > best_s:
                    best_s = s
                    best = rr*ncols + cc
            dst[r*ncols+c] = best
    return dst


def _flow_acc(dst, valid):
    n = dst.size
    valid_f = valid.ravel()
    indeg = np.zeros(n, dtype=np.int32)
    edges = np.where((dst >= 0) & valid_f)[0]
    np.add.at(indeg, dst[edges], 1)
    acc = np.zeros(n, dtype=np.float64)
    acc[valid_f] = 1.0
    q = deque(np.where(valid_f & (indeg == 0))[0].tolist())
    while q:
        i = q.popleft()
        j = int(dst[i])
        if j >= 0:
            acc[j] += acc[i]
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)
    return acc.reshape(valid.shape)


def _snap(row, col, acc, valid, radius_cells):
    """Ajusta el punto de salida al píxel de mayor acumulación dentro de un radio circular."""
    nrows, ncols = acc.shape
    row = int(np.clip(row, 0, nrows-1))
    col = int(np.clip(col, 0, ncols-1))
    r0, r1 = max(0, row-radius_cells), min(nrows, row+radius_cells+1)
    c0, c1 = max(0, col-radius_cells), min(ncols, col+radius_cells+1)
    sub = acc[r0:r1, c0:c1].copy()
    sub_valid = valid[r0:r1, c0:c1]
    yy, xx = np.indices(sub.shape)
    d2 = (yy + r0 - row)**2 + (xx + c0 - col)**2
    circular = d2 <= radius_cells**2
    sub[~sub_valid] = -1
    sub[~circular] = -1
    if np.nanmax(sub) < 0:
        raise ValueError("No se encontró celda válida para ajustar el punto de control dentro del radio definido.")
    score = sub - 1e-6*d2
    rr, cc = np.unravel_index(int(np.nanargmax(score)), score.shape)
    return int(rr+r0), int(cc+c0)



def _snap_candidates(row, col, acc, valid, radius_cells, max_candidates=80):
    """Devuelve celdas candidatas dentro del radio para evitar saltar a un río principal lejano.

    El error típico en cuencas pequeñas ocurre cuando el punto de control está cerca de
    un cauce mayor: el ajuste por máxima acumulación salta a ese cauce y la cuenca pasa
    de decenas a miles de km². Esta función conserva candidatos alternativos para que
    el área esperada controle la selección.
    """
    nrows, ncols = acc.shape
    row = int(np.clip(row, 0, nrows-1))
    col = int(np.clip(col, 0, ncols-1))
    r0, r1 = max(0, row-radius_cells), min(nrows, row+radius_cells+1)
    c0, c1 = max(0, col-radius_cells), min(ncols, col+radius_cells+1)
    sub = acc[r0:r1, c0:c1].copy()
    sub_valid = valid[r0:r1, c0:c1]
    yy, xx = np.indices(sub.shape)
    d2 = (yy + r0 - row)**2 + (xx + c0 - col)**2
    circular = d2 <= radius_cells**2
    sub[~sub_valid] = -1
    sub[~circular] = -1
    if np.nanmax(sub) < 0:
        raise ValueError("No se encontró celda válida para ajustar el punto de control dentro del radio definido.")
    flat = sub.ravel()
    order = np.argsort(flat)[::-1]
    cands = []
    seen = set()
    for idx in order:
        val = float(flat[idx])
        if val < 0:
            break
        rr, cc = np.unravel_index(int(idx), sub.shape)
        gr, gc = int(rr+r0), int(cc+c0)
        key = (gr, gc)
        if key in seen:
            continue
        seen.add(key)
        dist_cells = math.sqrt(float(d2[rr, cc]))
        cands.append({
            "row": gr,
            "col": gc,
            "acc": val,
            "dist_cells": dist_cells,
            "dist_norm": dist_cells / max(radius_cells, 1),
        })
        if len(cands) >= max_candidates:
            break
    # Garantiza que la celda original también se pruebe.
    if valid[row, col] and (row, col) not in seen:
        cands.append({
            "row": int(row),
            "col": int(col),
            "acc": float(acc[row, col]),
            "dist_cells": 0.0,
            "dist_norm": 0.0,
        })
    return cands



def _coverage_stats(basin: np.ndarray, valid: np.ndarray) -> dict:
    """Diagnóstico de cobertura DEM para detectar cuencas truncadas.

    Una cuenca delimitada con D8 dentro de una ventana DEM debe quedar cerrada por
    divisorias internas. Si el polígono toca el borde del raster o celdas NoData,
    existe alta probabilidad de que la cuenca esté recortada por falta de DEM.
    """
    basin_b = np.asarray(basin, dtype=bool)
    valid_b = np.asarray(valid, dtype=bool)
    nrows, ncols = basin_b.shape
    basin_cells = int(basin_b.sum())
    if basin_cells <= 0:
        return {
            "basin_cells": 0,
            "border_touch_cells": 0,
            "border_touch_fraction": 0.0,
            "nodata_adjacent_cells": 0,
            "nodata_adjacent_fraction": 0.0,
            "valid_fraction_dem": float(np.mean(valid_b)) if valid_b.size else 0.0,
            "touches_dem_border": False,
            "touches_nodata": False,
        }

    border = np.zeros_like(basin_b, dtype=bool)
    if nrows:
        border[0, :] = True
        border[-1, :] = True
    if ncols:
        border[:, 0] = True
        border[:, -1] = True
    border_touch = int(np.logical_and(basin_b, border).sum())

    invalid = ~valid_b
    invalid_neigh = np.zeros_like(basin_b, dtype=bool)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            src_r0 = max(0, -dr)
            src_r1 = nrows - max(0, dr)
            src_c0 = max(0, -dc)
            src_c1 = ncols - max(0, dc)
            dst_r0 = max(0, dr)
            dst_r1 = nrows - max(0, -dr)
            dst_c0 = max(0, dc)
            dst_c1 = ncols - max(0, -dc)
            if src_r0 < src_r1 and src_c0 < src_c1:
                invalid_neigh[dst_r0:dst_r1, dst_c0:dst_c1] |= invalid[src_r0:src_r1, src_c0:src_c1]
    nodata_adjacent = int(np.logical_and(basin_b, invalid_neigh).sum())

    return {
        "basin_cells": basin_cells,
        "border_touch_cells": border_touch,
        "border_touch_fraction": float(border_touch / max(basin_cells, 1)),
        "nodata_adjacent_cells": nodata_adjacent,
        "nodata_adjacent_fraction": float(nodata_adjacent / max(basin_cells, 1)),
        "valid_fraction_dem": float(np.mean(valid_b)) if valid_b.size else 0.0,
        "touches_dem_border": bool(border_touch > 0),
        "touches_nodata": bool(nodata_adjacent > 0),
    }


def _diagnostic_item(control: str, ok: bool, severidad: str, mensaje: str, accion: str = "") -> dict:
    return {
        "control": str(control),
        "ok": bool(ok),
        "severidad": str(severidad),
        "mensaje": str(mensaje),
        "accion_recomendada": str(accion),
    }


def _validate_basin_candidate(
    *,
    basin: np.ndarray,
    valid: np.ndarray,
    area_km2: float,
    expected_area_km2: float | None,
    max_area_km2: float | None,
    r0: int,
    c0: int,
    r1: int,
    c1: int,
    acc: np.ndarray,
    snapped_dist_m: float,
    snap_radius_m: float,
    cell_m: float,
    decim: int,
) -> dict:
    """Controles mínimos antes de declarar una cuenca como validada."""
    nrows, ncols = valid.shape
    point_in_dem = bool(0 <= r0 < nrows and 0 <= c0 < ncols)
    point_valid = bool(point_in_dem and valid[r0, c0])
    outlet_valid = bool(0 <= r1 < nrows and 0 <= c1 < ncols and valid[r1, c1])
    basin_cells = int(np.asarray(basin, dtype=bool).sum())
    cov = _coverage_stats(basin, valid)
    original_acc = float(acc[r0, c0]) if point_in_dem and np.isfinite(acc[r0, c0]) else 0.0
    outlet_acc = float(acc[r1, c1]) if outlet_valid and np.isfinite(acc[r1, c1]) else 0.0
    acc_gain = outlet_acc / max(original_acc, 1.0)
    correction_applied = bool((not point_valid) or snapped_dist_m > max(cell_m * 1.5, 10.0) or acc_gain >= 2.0)

    diagnostics = []
    diagnostics.append(_diagnostic_item(
        "Punto dentro del DEM",
        point_in_dem,
        "error" if not point_in_dem else "ok",
        "El punto de control cae dentro del raster DEM." if point_in_dem else "El punto de control queda fuera del DEM.",
        "Aumentar margen de descarga o cargar un DEM que cubra el punto de salida." if not point_in_dem else "",
    ))
    diagnostics.append(_diagnostic_item(
        "Punto ajustado al cauce DEM",
        outlet_valid and snapped_dist_m <= max(float(snap_radius_m), cell_m),
        "ok" if outlet_valid else "error",
        (
            f"Salida ajustada a celda válida con acumulación {outlet_acc:.0f}; "
            f"desplazamiento {snapped_dist_m:.1f} m desde el punto original."
        ) if outlet_valid else "No se encontró una celda válida de salida.",
        "Aumentar radio de ajuste o revisar que el punto esté cerca del cauce real." if not outlet_valid else "",
    ))
    if correction_applied:
        diagnostics.append(_diagnostic_item(
            "Corrección automática del punto",
            True,
            "info",
            "Se corrigió automáticamente el punto de control hacia la celda de cauce más consistente dentro del radio definido.",
            "Verificar visualmente punto original versus punto ajustado en el KMZ/preview.",
        ))
    else:
        diagnostics.append(_diagnostic_item(
            "Corrección automática del punto",
            True,
            "ok",
            "El punto original ya es coherente con el cauce detectado por acumulación DEM.",
            "",
        ))

    no_border = not bool(cov["touches_dem_border"])
    no_nodata = not bool(cov["touches_nodata"])
    diagnostics.append(_diagnostic_item(
        "Cuenca no truncada por borde DEM",
        no_border,
        "error" if not no_border else "ok",
        (
            "La cuenca no toca el borde exterior del DEM."
            if no_border else
            f"La cuenca toca el borde del DEM en {cov['border_touch_cells']} celda(s); puede estar incompleta o truncada."
        ),
        "Aumentar el margen del DEM aguas arriba/lateralmente y volver a delinear." if not no_border else "",
    ))
    diagnostics.append(_diagnostic_item(
        "Cobertura DEM sin NoData en borde de cuenca",
        no_nodata,
        "error" if not no_nodata else "ok",
        (
            "No se detectan celdas de cuenca adyacentes a NoData."
            if no_nodata else
            f"La cuenca queda junto a {cov['nodata_adjacent_cells']} celda(s) NoData; el DEM podría no cubrir toda la divisoria."
        ),
        "Usar DEM sin vacíos o ampliar/descargar nuevamente la ventana DEM." if not no_nodata else "",
    ))

    enough_cells = bool(basin_cells >= 50)
    diagnostics.append(_diagnostic_item(
        "Tamaño mínimo de cuenca",
        enough_cells,
        "error" if not enough_cells else "ok",
        f"La cuenca contiene {basin_cells} celda(s) válidas.",
        "Revisar punto de salida/radio; una cuenca tan pequeña suele indicar punto mal ubicado." if not enough_cells else "",
    ))

    area_ok = True
    if max_area_km2 is not None and max_area_km2 > 0:
        area_ok = bool(area_km2 <= max_area_km2)
        diagnostics.append(_diagnostic_item(
            "Área dentro del máximo permitido",
            area_ok,
            "error" if not area_ok else "ok",
            (
                f"Área delimitada {area_km2:.2f} km² ≤ máximo {max_area_km2:.2f} km²."
                if area_ok else
                f"Área delimitada {area_km2:.2f} km² excede máximo {max_area_km2:.2f} km²."
            ),
            "Reducir radio de ajuste, revisar punto o aumentar el máximo solo si corresponde técnicamente." if not area_ok else "",
        ))

    expected_ratio = None
    expected_warn = False
    if expected_area_km2 is not None and expected_area_km2 > 0 and area_km2 > 0:
        expected_ratio = float(area_km2 / expected_area_km2)
        expected_warn = bool(expected_ratio > 3.0 or expected_ratio < 1.0 / 3.0)
        diagnostics.append(_diagnostic_item(
            "Contraste con área esperada",
            not expected_warn,
            "warning" if expected_warn else "ok",
            (
                f"Área delimitada {area_km2:.2f} km²; área esperada {expected_area_km2:.2f} km²; razón {expected_ratio:.2f}."
            ),
            "Revisar área esperada, punto de control, radio de ajuste o DEM." if expected_warn else "",
        ))

    if decim > 1:
        diagnostics.append(_diagnostic_item(
            "Resolución de procesamiento DEM",
            True,
            "warning",
            f"El DEM fue decimado por factor {decim}; puede perder detalle del cauce en quebradas pequeñas.",
            "Reducir margen DEM o aumentar máximo de celdas si se requiere mayor precisión.",
        ))

    controles_minimos = {
        "punto_dentro_dem": point_in_dem,
        "salida_ajustada_valida": outlet_valid and snapped_dist_m <= max(float(snap_radius_m), cell_m),
        "cuenca_no_toca_borde_dem": no_border,
        "cuenca_no_toca_nodata": no_nodata,
        "tamano_minimo_celdas": enough_cells,
        "area_dentro_maximo": area_ok,
    }
    validated = bool(all(controles_minimos.values()))
    acciones = [d["accion_recomendada"] for d in diagnostics if d.get("accion_recomendada")]
    flags = [d["mensaje"] for d in diagnostics if d.get("severidad") in {"warning", "error"}]
    return {
        "cuenca_validada": validated,
        "estado_validacion": "VALIDADA" if validated else "NO_VALIDADA",
        "controles_minimos": controles_minimos,
        "diagnostico_tecnico": diagnostics,
        "acciones_recomendadas": acciones,
        "advertencias": flags,
        "cobertura_dem": cov,
        "punto_original_valido_dem": point_valid,
        "correccion_automatica_punto": correction_applied,
        "acumulacion_punto_original_celdas": original_acc,
        "acumulacion_punto_ajustado_celdas": outlet_acc,
        "ganancia_acumulacion_ajuste": float(acc_gain),
        "razon_area_esperada": expected_ratio,
    }

def _evaluate_outlet_candidates(dst, valid, acc, row, col, radius_cells, dx, dy, expected_area_km2=None, max_area_km2=None, selection_mode="area_controlled", max_candidates=140):
    """Evalúa celdas de salida candidatas y calcula su cuenca aportante.

    Esta rutina queda separada de la selección para permitir, además de un outlet
    puntual, un cierre compuesto por varias celdas de salida. Ese caso es frecuente
    en quebradas sobre abanicos aluviales o caminos/terrazas, donde el DEM reparte
    el flujo en varios hilos y una celda puntual entrega solo media cuenca.
    """
    cands = _snap_candidates(row, col, acc, valid, radius_cells, max_candidates=max_candidates)
    evaluated = []
    ncols = valid.shape[1]
    for cand in cands:
        r1, c1 = int(cand["row"]), int(cand["col"])
        basin = _upstream_mask(dst, valid, r1*ncols + c1)
        area = float(int(basin.sum()) * dx * dy / 1_000_000)
        dist_norm = float(cand.get("dist_norm", 0.0))
        acc_val = max(float(cand.get("acc", 0.0)), 1.0)
        over = bool(max_area_km2 is not None and max_area_km2 > 0 and area > max_area_km2)
        cov = _coverage_stats(basin, valid)
        truncated = bool(cov.get("touches_dem_border") or cov.get("touches_nodata"))
        if expected_area_km2 is not None and expected_area_km2 > 0 and area > 0:
            area_term = abs(math.log(area / expected_area_km2))
        else:
            area_term = 0.0

        # Puntaje menor es mejor. Sin área esperada se privilegia acumulación,
        # pero se mantiene una penalización por distancia para no saltar a un río
        # principal ajeno al punto de control.
        if expected_area_km2 is None and max_area_km2 is None and selection_mode == "area_controlled":
            score = 0.32*dist_norm - 0.12*math.log(acc_val)
        else:
            score = area_term + 0.65*dist_norm - 0.04*math.log(acc_val)
        if truncated:
            score += 250.0 + 50.0*float(cov.get("border_touch_fraction", 0.0)) + 25.0*float(cov.get("nodata_adjacent_fraction", 0.0))
        if over:
            score += 1000.0 + area/max(max_area_km2 or 1.0, 1e-9)
        if selection_mode == "closest":
            score = dist_norm - 0.01*math.log(acc_val)
            if truncated:
                score += 250.0
        if selection_mode == "max_acc":
            score = -math.log(acc_val) + 0.03*dist_norm
            if truncated:
                score += 250.0
            if over:
                score += 1000.0 + area/max(max_area_km2 or 1.0, 1e-9)

        evaluated.append({
            "row": r1,
            "col": c1,
            "acc": acc_val,
            "area_km2": area,
            "dist_norm": dist_norm,
            "score": score,
            "over_max_area": over,
            "touches_dem_border": bool(cov.get("touches_dem_border")),
            "touches_nodata": bool(cov.get("touches_nodata")),
            "border_touch_cells": int(cov.get("border_touch_cells", 0)),
            "nodata_adjacent_cells": int(cov.get("nodata_adjacent_cells", 0)),
            "basin": basin,
        })
    if not evaluated:
        raise ValueError("No se pudo evaluar candidatos de salida para la cuenca.")
    return evaluated


def _select_outlet_candidate(dst, valid, acc, row, col, radius_cells, dx, dy, expected_area_km2=None, max_area_km2=None, selection_mode="area_controlled"):
    """Selecciona outlet ajustado con control de área.

    selection_mode:
    - max_acc: toma máxima acumulación con control de borde/NoData.
    - closest: usa celda válida más cercana.
    - area_controlled: evita candidatos que exceden max_area_km2 y prioriza área esperada si existe.
    """
    evaluated = _evaluate_outlet_candidates(
        dst, valid, acc, row, col, radius_cells, dx, dy,
        expected_area_km2=expected_area_km2,
        max_area_km2=max_area_km2,
        selection_mode=selection_mode,
        max_candidates=140,
    )
    evaluated_sorted = sorted(evaluated, key=lambda x: x["score"])
    chosen = evaluated_sorted[0]
    # Si todos exceden max_area, se selecciona el menor excedente, pero se advertirá.
    if max_area_km2 is not None and max_area_km2 > 0 and all(e["over_max_area"] for e in evaluated):
        chosen = min(evaluated, key=lambda x: x["area_km2"])
    report = [{k: v for k, v in e.items() if k != "basin"} for e in evaluated_sorted[:12]]
    return int(chosen["row"]), int(chosen["col"]), chosen["basin"], report


def _compose_portal_basin(
    dst,
    valid,
    acc,
    row,
    col,
    primary_row,
    primary_col,
    primary_basin,
    portal_radius_cells,
    dx,
    dy,
    *,
    expected_area_km2=None,
    max_area_km2=None,
    selection_mode="area_controlled",
    max_extra_outlets=8,
):
    """Une subcuencas drenantes a un portal de salida.

    En terreno árido con abanicos aluviales, caminos o cauces poco incisos, el DEM
    puede representar varios hilos de escurrimiento paralelos. Si se usa una sola
    celda de salida, la delimitación puede devolver media cuenca. Esta función
    evalúa varias celdas de salida dentro de un radio de portal y une las máscaras
    que aportan nueva superficie significativa, sin aceptar candidatas truncadas ni
    exceder el área máxima indicada por el usuario.
    """
    portal_radius_cells = max(1, int(portal_radius_cells))
    evaluated = _evaluate_outlet_candidates(
        dst, valid, acc, row, col, portal_radius_cells, dx, dy,
        expected_area_km2=expected_area_km2,
        max_area_km2=max_area_km2,
        selection_mode=selection_mode,
        max_candidates=220,
    )
    # Se ordena por acumulación alta y luego por distancia al punto original. Así se
    # capturan hilos principales sin incorporar cualquier ladera menor.
    ranked = sorted(evaluated, key=lambda e: (-float(e["acc"]), float(e["dist_norm"])))
    union = np.asarray(primary_basin, dtype=bool).copy()
    selected = []
    primary_area = float(int(union.sum()) * dx * dy / 1_000_000)
    best_area_error = abs(math.log(primary_area / expected_area_km2)) if expected_area_km2 and primary_area > 0 else None

    for e in ranked:
        if len(selected) >= int(max_extra_outlets):
            break
        if bool(e.get("touches_dem_border")) or bool(e.get("touches_nodata")):
            continue
        basin = np.asarray(e["basin"], dtype=bool)
        if not basin.any():
            continue
        # Saltar celdas que ya son equivalentes al outlet puntual elegido.
        if int(e["row"]) == int(primary_row) and int(e["col"]) == int(primary_col):
            continue
        new_cells = int(np.logical_and(basin, ~union).sum())
        basin_cells = int(basin.sum())
        if basin_cells <= 0:
            continue
        new_ratio = new_cells / max(basin_cells, 1)
        union_area_before = float(int(union.sum()) * dx * dy / 1_000_000)
        added_area = float(new_cells * dx * dy / 1_000_000)
        # Se exige aporte nuevo relevante. Umbral bajo para quebradas pequeñas.
        cell_area_km2 = float(dx * dy / 1_000_000)
        min_added = max(3.0 * cell_area_km2, 0.04 * max(union_area_before, primary_area, cell_area_km2))
        if added_area < min_added or new_ratio < 0.25:
            continue
        candidate_union = np.logical_or(union, basin)
        union_area = float(int(candidate_union.sum()) * dx * dy / 1_000_000)
        if max_area_km2 is not None and max_area_km2 > 0 and union_area > max_area_km2:
            continue
        cov = _coverage_stats(candidate_union, valid)
        if bool(cov.get("touches_dem_border")) or bool(cov.get("touches_nodata")):
            continue
        accept = False
        if expected_area_km2 is not None and expected_area_km2 > 0 and union_area > 0:
            err = abs(math.log(union_area / expected_area_km2))
            # Acepta si mejora el área esperada o si el outlet puntual estaba muy bajo.
            if best_area_error is None or err <= best_area_error * 0.98 or union_area_before < 0.70 * expected_area_km2:
                accept = True
                best_area_error = min(err, best_area_error if best_area_error is not None else err)
        else:
            # Sin área esperada: acepta hilos significativos dentro del portal.
            accept = True
        if accept:
            union = candidate_union
            selected.append({
                "row": int(e["row"]),
                "col": int(e["col"]),
                "acc": float(e["acc"]),
                "area_km2": float(e["area_km2"]),
                "added_area_km2": float(added_area),
                "union_area_km2": float(union_area),
                "dist_norm": float(e["dist_norm"]),
            })

    union_area = float(int(union.sum()) * dx * dy / 1_000_000)
    gain = union_area / max(primary_area, 1e-12)
    return union, {
        "modo_cierre_salida": "portal_compuesto",
        "portal_radius_cells": int(portal_radius_cells),
        "portal_area_puntual_km2": float(primary_area),
        "portal_area_compuesta_km2": float(union_area),
        "portal_factor_incremento_area": float(gain),
        "portal_outlets_adicionales": selected,
        "portal_total_outlets": int(1 + len(selected)),
    }


def _upstream_mask(dst, valid, outlet_idx):
    n = dst.size
    valid_f = valid.ravel()
    src = np.where((dst >= 0) & valid_f)[0]
    dest = dst[src]
    order = np.argsort(dest, kind="mergesort")
    dest_s = dest[order]
    src_s = src[order]
    basin = np.zeros(n, dtype=bool)
    if outlet_idx < 0 or outlet_idx >= n or not valid_f[outlet_idx]:
        return basin.reshape(valid.shape)
    stack = [int(outlet_idx)]
    basin[outlet_idx] = True
    while stack:
        target = stack.pop()
        lo = np.searchsorted(dest_s, target, side="left")
        hi = np.searchsorted(dest_s, target, side="right")
        for child in src_s[lo:hi]:
            child = int(child)
            if not basin[child]:
                basin[child] = True
                stack.append(child)
    return basin.reshape(valid.shape)


def _mask_to_polygon(mask, transform, crs, simplify_m=80.0):
    from skimage import measure
    from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
    from shapely.ops import transform as shp_transform, unary_union

    padded = np.pad(mask.astype(float), 1, mode="constant", constant_values=0.0)
    contours = measure.find_contours(padded, 0.5)
    polys = []
    for arr in contours:
        if len(arr) < 4:
            continue
        coords = []
        for row, col in arr:
            row = float(row) - 1.0
            col = float(col) - 1.0
            x, y = transform * (col, row)
            coords.append((x, y))
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        try:
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty or poly.area <= 0:
                continue
            polys.append(poly)
        except Exception:
            pass
    if not polys:
        raise RuntimeError("No se pudo vectorizar el polígono de cuenca.")

    geom = unary_union(polys)
    if isinstance(geom, GeometryCollection):
        only_polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon)) and not g.is_empty]
        if not only_polys:
            raise RuntimeError("No se pudo vectorizar el polígono de cuenca.")
        geom = unary_union(only_polys)
    if not geom.is_valid:
        geom = geom.buffer(0)
    try:
        is_geo = bool(crs and getattr(crs, "is_geographic", False))
    except Exception:
        is_geo = False
    tol = simplify_m / 111000.0 if is_geo else simplify_m
    if tol > 0:
        geom = geom.simplify(tol, preserve_topology=True)

    if crs is not None:
        try:
            epsg = crs.to_epsg()
        except Exception:
            epsg = None
        if epsg != 4326:
            from pyproj import Transformer
            tr = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
            geom = shp_transform(lambda x, y, z=None: tr.transform(x, y), geom)
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom

def _utm_crs(lon, lat):
    from pyproj import CRS
    zone = int((lon + 180)//6) + 1
    epsg = 32700 + zone if lat < 0 else 32600 + zone
    return CRS.from_epsg(epsg)


def _project_poly(poly_wgs):
    from shapely.ops import transform as shp_transform
    from pyproj import Transformer
    c = poly_wgs.centroid
    crs = _utm_crs(float(c.x), float(c.y))
    tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    return shp_transform(lambda x,y,z=None: tr.transform(x,y), poly_wgs), crs


def _morphometry(poly_wgs, basin_mask, acc, dx, dy, cell_m, outlet_rc, snapped_lon, snapped_lat, original_lon, original_lat, snapped_dist_m, flags):
    poly_m, crs = _project_poly(poly_wgs)
    area_km2 = float(poly_m.area / 1_000_000)
    area_ha = area_km2 * 100
    perimeter_km = float(poly_m.length / 1000)
    minx, miny, maxx, maxy = poly_m.bounds
    bbox_length_km = max((maxx-minx), (maxy-miny)) / 1000
    bbox_width_km = min((maxx-minx), (maxy-miny)) / 1000
    mean_width_km = area_km2 / bbox_length_km if bbox_length_km > 0 else float("nan")
    compactness_kc = 0.2821 * perimeter_km / math.sqrt(area_km2) if area_km2 > 0 else float("nan")
    form_factor = area_km2/(bbox_length_km**2) if bbox_length_km > 0 else float("nan")
    elongation_ratio = 1.128 * math.sqrt(area_km2)/bbox_length_km if bbox_length_km > 0 else float("nan")
    max_acc = float(np.nanmax(acc[basin_mask])) if int(basin_mask.sum()) else float("nan")
    return {
        "area_km2": area_km2,
        "area_ha": area_ha,
        "perimetro_km": perimeter_km,
        "epsg_morfometria": int(crs.to_epsg()),
        "centroide_lon": float(poly_wgs.centroid.x),
        "centroide_lat": float(poly_wgs.centroid.y),
        "bbox_largo_km": float(bbox_length_km),
        "bbox_ancho_km": float(bbox_width_km),
        "ancho_medio_km": float(mean_width_km),
        "coef_compacidad_kc": float(compactness_kc),
        "factor_forma": float(form_factor),
        "relacion_elongacion": float(elongation_ratio),
        "n_celdas_cuenca": int(basin_mask.sum()),
        "tamano_celda_m": float(cell_m),
        "acumulacion_salida_celdas": max_acc,
        "punto_original_lon": float(original_lon),
        "punto_original_lat": float(original_lat),
        "punto_ajustado_lon": float(snapped_lon),
        "punto_ajustado_lat": float(snapped_lat),
        "distancia_ajuste_m": float(snapped_dist_m),
        "cuenca_toca_borde_dem": bool(any("borde del DEM" in str(f) for f in flags)),
        "advertencias": flags,
    }


def _kml_poly(poly_wgs, metrics):
    from shapely.geometry import Polygon, MultiPolygon

    def polygon_kml(poly):
        coords = " ".join([f"{x:.8f},{y:.8f},0" for x, y in list(poly.exterior.coords)])
        inner = ""
        for ring in getattr(poly, "interiors", []):
            icoords = " ".join([f"{x:.8f},{y:.8f},0" for x, y in list(ring.coords)])
            inner += f"<innerBoundaryIs><LinearRing><coordinates>{icoords}</coordinates></LinearRing></innerBoundaryIs>"
        return f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs>{inner}</Polygon>"

    if isinstance(poly_wgs, MultiPolygon):
        geom_kml = "<MultiGeometry>" + "".join(polygon_kml(g) for g in poly_wgs.geoms if isinstance(g, Polygon)) + "</MultiGeometry>"
    else:
        geom_kml = polygon_kml(poly_wgs)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>Cuenca delimitada HidroSed</name>
<Style id="basin"><LineStyle><color>ff0000ff</color><width>2</width></LineStyle><PolyStyle><color>330000ff</color></PolyStyle></Style>
<Placemark><name>Cuenca delimitada automática</name><description>Área {metrics["area_km2"]:.3f} km2</description><styleUrl>#basin</styleUrl>
{geom_kml}
</Placemark>
<Placemark><name>Punto original</name><Point><coordinates>{metrics["punto_original_lon"]:.8f},{metrics["punto_original_lat"]:.8f},0</coordinates></Point></Placemark>
<Placemark><name>Punto ajustado al cauce</name><Point><coordinates>{metrics["punto_ajustado_lon"]:.8f},{metrics["punto_ajustado_lat"]:.8f},0</coordinates></Point></Placemark>
</Document></kml>'''

def _preview(mask, acc, outlet_rc):
    import io
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=(8,6))
    acc_log = np.log10(np.where(acc > 0, acc, np.nan))
    ax.imshow(acc_log)
    ax.contour(mask.astype(float), levels=[0.5], linewidths=1.5)
    ax.scatter([outlet_rc[1]], [outlet_rc[0]], s=30)
    ax.set_title("Cuenca delimitada y acumulación de flujo")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def delineate_basin(
    path_or_bytes,
    outlet_lon: float,
    outlet_lat: float,
    snap_radius_m: float = 500.0,
    max_cells: int = 20_000_000,
    simplify_m: float = 80.0,
    expected_area_km2: float | None = None,
    max_area_km2: float | None = None,
    selection_mode: str = 'area_controlled',
    outlet_closure_mode: str = 'auto_portal',
    portal_radius_m: float | None = None,
) -> BasinResult:
    data, transform, crs, decim = _read_dem(path_or_bytes, max_cells=max_cells)
    valid = np.isfinite(data)
    dx, dy, cell_m = _cell_sizes_m(transform, crs, data.shape)
    filled = _priority_flood(data, valid)
    dst = _flow_dir_d8(filled, valid, dx, dy)
    acc = _flow_acc(dst, valid)
    r0, c0 = _lonlat_to_rowcol(outlet_lon, outlet_lat, transform, crs)
    if not (0 <= r0 < data.shape[0] and 0 <= c0 < data.shape[1]):
        raise ValueError("El punto de control queda fuera del DEM descargado. Aumenta el margen.")
    radius_cells = max(1, int(math.ceil(snap_radius_m/max(cell_m,1e-9))))
    r1, c1, basin, candidate_report = _select_outlet_candidate(
        dst, valid, acc, r0, c0, radius_cells, dx, dy,
        expected_area_km2=expected_area_km2,
        max_area_km2=max_area_km2,
        selection_mode=selection_mode,
    )

    portal_info = {
        "modo_cierre_salida": "puntual",
        "portal_aplicado": False,
        "portal_radio_m": None,
        "portal_factor_incremento_area": 1.0,
        "portal_outlets_adicionales": [],
        "portal_total_outlets": 1,
    }
    if str(outlet_closure_mode) in {"auto_portal", "portal_union"}:
        p_radius_m = float(portal_radius_m) if portal_radius_m is not None and float(portal_radius_m) > 0 else max(float(snap_radius_m) * 2.5, 750.0)
        p_radius_cells = max(radius_cells, int(math.ceil(p_radius_m / max(cell_m, 1e-9))))
        basin_union, pinfo = _compose_portal_basin(
            dst, valid, acc, r0, c0, r1, c1, basin, p_radius_cells, dx, dy,
            expected_area_km2=expected_area_km2,
            max_area_km2=max_area_km2,
            selection_mode=selection_mode,
        )
        pinfo["portal_radio_m"] = float(p_radius_cells * cell_m)
        single_area = float(int(basin.sum()) * dx * dy / 1_000_000)
        union_area = float(int(basin_union.sum()) * dx * dy / 1_000_000)
        gain = union_area / max(single_area, 1e-12)
        use_portal = False
        if str(outlet_closure_mode) == "portal_union":
            use_portal = len(pinfo.get("portal_outlets_adicionales", [])) > 0
        else:
            # Automático: usar portal si recupera superficie relevante sin romper controles.
            if expected_area_km2 is not None and expected_area_km2 > 0 and single_area > 0 and union_area > 0:
                single_err = abs(math.log(single_area / expected_area_km2))
                union_err = abs(math.log(union_area / expected_area_km2))
                use_portal = bool(gain >= 1.12 and union_err <= single_err * 0.98)
            else:
                use_portal = bool(gain >= 1.18 and len(pinfo.get("portal_outlets_adicionales", [])) > 0)
        if use_portal:
            basin = basin_union
            portal_info = pinfo
            portal_info["portal_aplicado"] = True
        else:
            portal_info.update(pinfo)
            portal_info["portal_aplicado"] = False

    snapped_lon, snapped_lat = _rowcol_to_lonlat(r1, c1, transform, crs)
    snapped_dist = math.hypot((r1-r0)*dy, (c1-c0)*dx)
    basin_cells = int(basin.sum())
    area_est_km2 = float(basin_cells * dx * dy / 1_000_000)

    validation = _validate_basin_candidate(
        basin=basin,
        valid=valid,
        area_km2=area_est_km2,
        expected_area_km2=expected_area_km2,
        max_area_km2=max_area_km2,
        r0=r0,
        c0=c0,
        r1=r1,
        c1=c1,
        acc=acc,
        snapped_dist_m=snapped_dist,
        snap_radius_m=float(max(snap_radius_m, portal_info.get("portal_radio_m") or snap_radius_m)) if portal_info.get("portal_aplicado") else float(snap_radius_m),
        cell_m=cell_m,
        decim=decim,
    )
    if portal_info.get("portal_aplicado"):
        validation.setdefault("diagnostico_tecnico", []).append(_diagnostic_item(
            "Cierre compuesto de salida",
            True,
            "info",
            (
                "Se detectó riesgo de cuenca incompleta por salida puntual. "
                f"Se aplicó portal compuesto con {portal_info.get('portal_total_outlets', 1)} outlet(s); "
                f"área puntual {portal_info.get('portal_area_puntual_km2', 0):.3f} km², "
                f"área compuesta {portal_info.get('portal_area_compuesta_km2', area_est_km2):.3f} km²."
            ),
            "Revisar visualmente que los hilos capturados correspondan al mismo exutorio o abanico de descarga.",
        ))
    elif str(outlet_closure_mode) == "auto_portal" and portal_info.get("portal_factor_incremento_area", 1.0) >= 1.18:
        validation.setdefault("diagnostico_tecnico", []).append(_diagnostic_item(
            "Cierre compuesto de salida",
            True,
            "warning",
            "El portal compuesto encontró superficie adicional, pero no mejoró suficientemente el control de área o excedía restricciones.",
            "Probar modo 'Portal compuesto forzado', aumentar radio portal o revisar área esperada/máxima.",
        ))
        validation.setdefault("advertencias", []).append("Existe posible cuenca aportante parcial: probar cierre compuesto de salida si el resultado visual es incompleto.")
    flags = list(validation.get("advertencias", []))
    poly = _mask_to_polygon(basin, transform, crs, simplify_m=simplify_m)
    metrics = _morphometry(poly, basin, acc, dx, dy, cell_m, (r1,c1), snapped_lon, snapped_lat, outlet_lon, outlet_lat, snapped_dist, flags)
    metrics.update(validation)
    metrics.update(portal_info)
    metrics["area_esperada_km2"] = float(expected_area_km2) if expected_area_km2 is not None else None
    metrics["area_maxima_control_km2"] = float(max_area_km2) if max_area_km2 is not None else None
    metrics["modo_seleccion_salida"] = str(selection_mode)
    metrics["modo_cierre_salida_usuario"] = str(outlet_closure_mode)
    metrics["candidatos_salida_top"] = candidate_report
    metrics["punto_original_row"] = int(r0)
    metrics["punto_original_col"] = int(c0)
    metrics["punto_ajustado_row"] = int(r1)
    metrics["punto_ajustado_col"] = int(c1)
    metrics["radio_ajuste_m"] = float(snap_radius_m)
    kml = _kml_poly(poly, metrics).encode("utf-8")
    import io
    kmz_buf = io.BytesIO()
    with zipfile.ZipFile(kmz_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml)
    png = _preview(basin, acc, (r1,c1))
    return BasinResult(kmz_bytes=kmz_buf.getvalue(), kml_bytes=kml, preview_png=png, metrics=metrics)

def metrics_dataframe(metrics: dict) -> pd.DataFrame:
    labels = {
        "area_km2": "Área cuenca [km²]",
        "area_ha": "Área cuenca [ha]",
        "perimetro_km": "Perímetro [km]",
        "bbox_largo_km": "Largo característico bbox [km]",
        "bbox_ancho_km": "Ancho característico bbox [km]",
        "ancho_medio_km": "Ancho medio [km]",
        "coef_compacidad_kc": "Coeficiente compacidad Kc",
        "factor_forma": "Factor de forma",
        "relacion_elongacion": "Relación de elongación",
        "tamano_celda_m": "Tamaño celda procesada [m]",
        "distancia_ajuste_m": "Distancia ajuste punto [m]",
        "acumulacion_salida_celdas": "Acumulación salida [celdas]",
        "estado_validacion": "Estado validación QA",
        "cuenca_validada": "Cuenca validada",
        "correccion_automatica_punto": "Corrección automática del punto",
        "cuenca_toca_borde_dem": "Cuenca toca borde DEM",
        "acumulacion_punto_original_celdas": "Acumulación punto original [celdas]",
        "acumulacion_punto_ajustado_celdas": "Acumulación punto ajustado [celdas]",
        "ganancia_acumulacion_ajuste": "Ganancia acumulación ajuste",
        "modo_cierre_salida": "Modo cierre de salida",
        "portal_aplicado": "Portal compuesto aplicado",
        "portal_radio_m": "Radio portal compuesto [m]",
        "portal_total_outlets": "N° outlets usados",
        "portal_factor_incremento_area": "Factor incremento área por portal",
    }
    return pd.DataFrame([{"parametro": lab, "clave": k, "valor": metrics.get(k)} for k, lab in labels.items()])
