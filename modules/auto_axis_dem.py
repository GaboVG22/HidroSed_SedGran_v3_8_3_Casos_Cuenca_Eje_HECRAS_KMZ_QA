from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import LineString

from modules import watershed_morphometry as wm


@dataclass
class AutoAxisResult:
    coords_wgs84: list[tuple[float, float]]
    metadata: dict[str, Any]


def generate_main_thalweg_axis_from_dem(
    dem_path: str | Path | bytes,
    outlet_lon: float,
    outlet_lat: float,
    snap_radius_m: float = 500.0,
    max_cells: int = 2_500_000,
    max_length_km: float = 30.0,
    min_points: int = 3,
) -> AutoAxisResult:
    """Genera un eje automático aguas arriba siguiendo el tributario de mayor acumulación.

    La rutina usa D8/accumulación del módulo de cuenca y no reemplaza un eje levantado en terreno.
    Es un respaldo para que la exportación KMZ no falle cuando el usuario no cargó eje manual.
    """
    data, transform, crs, decim = wm._read_dem(dem_path, max_cells=int(max_cells))
    valid = __import__('numpy').isfinite(data)
    dx, dy, cell_m = wm._cell_sizes_m(transform, crs, data.shape)
    filled = wm._priority_flood(data, valid)
    dst = wm._flow_dir_d8(filled, valid, dx, dy)
    acc = wm._flow_acc(dst, valid)
    r0, c0 = wm._lonlat_to_rowcol(outlet_lon, outlet_lat, transform, crs)
    if not (0 <= r0 < data.shape[0] and 0 <= c0 < data.shape[1]):
        raise ValueError('Punto fuera del DEM para generar eje automático.')
    radius_cells = max(1, int(math.ceil(float(snap_radius_m) / max(cell_m, 1e-9))))
    r, c = wm._snap(r0, c0, acc, valid, radius_cells)
    nrows, ncols = valid.shape
    coords_rc = [(int(r), int(c))]
    max_steps = max(int(max_length_km * 1000.0 / max(cell_m, 1.0)), int(min_points))
    # vecinos que drenan a la celda actual: se escoge el mayor acumulado que no sea el mismo punto.
    for _ in range(max_steps):
        best = None
        best_acc = -1.0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if rr < 0 or rr >= nrows or cc < 0 or cc >= ncols or not valid[rr, cc]:
                    continue
                if int(dst[rr * ncols + cc]) == int(r * ncols + c):
                    a = float(acc[rr, cc])
                    if a > best_acc:
                        best_acc = a
                        best = (rr, cc)
        if best is None:
            break
        r, c = best
        if coords_rc and (r, c) == coords_rc[-1]:
            break
        coords_rc.append((int(r), int(c)))
        # Detener cuando la acumulación se vuelve muy pequeña.
        if best_acc <= 2:
            break
    coords_wgs = [wm._rowcol_to_lonlat(rr, cc, transform, crs) for rr, cc in coords_rc]
    # El eje se guarda de aguas arriba a salida para que el PK 0 pueda definirse coherentemente si se requiere.
    coords_wgs = [(float(x), float(y)) for x, y in reversed(coords_wgs)]
    if len(coords_wgs) < 2:
        raise ValueError('No se pudo formar un eje automático con al menos dos puntos.')
    # Simplificación ligera para no cargar Google Earth con miles de puntos.
    try:
        line = LineString(coords_wgs)
        tol = max(1e-7, min(2e-4, float(cell_m) / 111000.0 * 0.5))
        line = line.simplify(tol, preserve_topology=False)
        coords_wgs = [(float(x), float(y)) for x, y in line.coords]
    except Exception:
        pass
    return AutoAxisResult(coords_wgs, {
        'source': 'automatic_dem_thalweg',
        'points': len(coords_wgs),
        'cell_m': float(cell_m),
        'decimation_factor': int(decim),
        'max_length_km': float(max_length_km),
        'snap_radius_m': float(snap_radius_m),
    })
