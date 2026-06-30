from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class ApplicationCase:
    key: str
    short_name: str
    title: str
    description: str
    hydraulic_use: str
    required_inputs: List[str]
    optional_inputs: List[str]
    topo_required: bool
    qa_focus: List[str]
    recommended_outputs: List[str]
    alert_level: str
    image_file: str


_CASES: Dict[str, ApplicationCase] = {
    "case_1_basin_internal_axis": ApplicationCase(
        key="case_1_basin_internal_axis",
        short_name="Caso 1",
        title="Cuenca + eje interno del cauce",
        description=(
            "Caso estándar. El punto de control se ubica en el exutorio de la cuenca y el eje del cauce "
            "queda dentro del polígono aportante. Puede usarse eje cargado o eje generado desde el DEM."
        ),
        hydraulic_use="Modelación del cauce principal de la propia cuenca aportante.",
        required_inputs=["Punto de control", "DEM completo", "Cuenca validada", "Eje interno o eje DEM"],
        optional_inputs=["Curvas de nivel de respaldo", "Granulometría", "Secciones HEC-RAS"],
        topo_required=False,
        qa_focus=[
            "El punto debe ajustar al cauce real del DEM.",
            "La cuenca no debe tocar bordes NoData del DEM.",
            "El eje debe quedar contenido principalmente en la cuenca.",
        ],
        recommended_outputs=["KMZ cuenca", "KMZ eje", "KMZ cuenca + eje + curvas", "Excel secciones"],
        alert_level="normal",
        image_file="caso_1_cuenca_eje_interno.png",
    ),
    "case_2_basin_user_axis_connected": ApplicationCase(
        key="case_2_basin_user_axis_connected",
        short_name="Caso 2",
        title="Cuenca + eje dentro y fuera de la cuenca",
        description=(
            "El eje tiene un tramo dentro o asociado directamente a la cuenca y otro tramo que continúa fuera de ella. "
            "Usa la lógica A–B para el tramo asociado a la cuenca y B–C para el tramo aguas abajo o externo."
        ),
        hydraulic_use="Modelación con eje definido por el usuario, manteniendo conectividad hidráulica con la cuenca.",
        required_inputs=["Punto de control", "DEM", "Cuenca validada", "Eje KMZ/KML conectado", "Curvas de nivel de respaldo"],
        optional_inputs=["Curvas DEM generadas", "Perfil longitudinal", "Secciones manuales"],
        topo_required=True,
        qa_focus=[
            "Verificar que el eje se conecte con el exutorio o con el tramo de salida.",
            "Comparar el eje con curvas de nivel para evitar secciones planas o invertidas.",
            "Advertir si el eje se aleja del thalweg detectado por el DEM.",
        ],
        recommended_outputs=["KMZ cuenca", "KMZ eje", "KMZ cuenca + eje + curvas", "Excel secciones tipo HEC-RAS"],
        alert_level="warning",
        image_file="caso_2_cuenca_eje_conectado.png",
    ),
    "case_3_basin_marginal_axis": ApplicationCase(
        key="case_3_basin_marginal_axis",
        short_name="Caso 3",
        title="Cuenca + eje marginal desde salida",
        description=(
            "El eje del cauce comienza en el punto final de la cuenca y se extiende justo fuera del margen del polígono. "
            "Representa un tramo de descarga o encauzamiento marginal inmediatamente aguas abajo o lateral a la cuenca."
        ),
        hydraulic_use="Transferir los caudales de la cuenca hacia un eje marginal contiguo para evaluar capacidad o desborde.",
        required_inputs=["Punto de control", "DEM", "Cuenca validada", "Eje marginal", "Curvas de nivel de respaldo"],
        optional_inputs=["Portal compuesto de salida", "Secciones de diseño rectangular/trapecial", "Condición aguas abajo"],
        topo_required=True,
        qa_focus=[
            "Confirmar que el eje nace en el exutorio o punto final de la cuenca.",
            "Validar la continuidad entre cuenca, eje marginal y curvas de nivel.",
            "Aplicar transferencia de caudal al tramo marginal.",
        ],
        recommended_outputs=["KMZ cuenca", "KMZ eje marginal", "KMZ unificado cuenca + eje + curvas", "Informe de transferencia de caudal"],
        alert_level="warning",
        image_file="caso_3_cuenca_eje_marginal.png",
    ),
    "case_4_basin_external_axis": ApplicationCase(
        key="case_4_basin_external_axis",
        short_name="Caso 4",
        title="Cuenca aportante + eje externo alejado",
        description=(
            "La cuenca aporta caudales a un eje de modelación ubicado fuera y alejado del polígono aportante. "
            "Debe tratarse como una transferencia hidrológica hacia un tramo externo, no como cauce interno de la cuenca."
        ),
        hydraulic_use="Asignar caudales de una cuenca aportante a un cauce, canal o tramo externo de análisis.",
        required_inputs=["Punto de control", "DEM", "Cuenca validada", "Eje externo", "Curvas de nivel de respaldo", "Criterio de transferencia de caudal"],
        optional_inputs=["Distancia de transferencia", "Ajuste por área/altitud", "Secciones artificiales", "Condición de borde"],
        topo_required=True,
        qa_focus=[
            "Advertir que el eje no pertenece geométricamente a la cuenca.",
            "Exigir trazabilidad del método de transferencia de caudal.",
            "Revisar que las secciones se generen con topografía local del eje externo.",
        ],
        recommended_outputs=["KMZ cuenca aportante", "KMZ eje externo", "KMZ unificado cuenca + eje + curvas", "Memoria de transferencia hidrológica"],
        alert_level="critical",
        image_file="caso_4_cuenca_eje_externo.png",
    ),
}


def application_cases() -> Dict[str, ApplicationCase]:
    return dict(_CASES)


def case_labels() -> List[str]:
    return [f"{c.short_name} · {c.title}" for c in _CASES.values()]


def case_key_from_label(label: str) -> str:
    for key, case in _CASES.items():
        if label == f"{case.short_name} · {case.title}" or label == case.title or label == case.key:
            return key
    raise KeyError(f"Caso de aplicación no reconocido: {label}")


def get_application_case(key: str | None) -> ApplicationCase:
    if not key:
        return _CASES["case_1_basin_internal_axis"]
    return _CASES.get(key, _CASES["case_1_basin_internal_axis"])


def cases_dataframe() -> pd.DataFrame:
    rows = []
    for c in _CASES.values():
        d = asdict(c)
        d["topo_required"] = "Sí" if c.topo_required else "No obligatorio"
        d["required_inputs"] = "; ".join(c.required_inputs)
        d["qa_focus"] = "; ".join(c.qa_focus)
        rows.append(d)
    return pd.DataFrame(rows)[[
        "short_name", "title", "topo_required", "hydraulic_use", "required_inputs", "qa_focus", "alert_level"
    ]]


def topo_support_status(case_key: str | None, has_topo_support: bool, has_generated_contours: bool) -> dict:
    case = get_application_case(case_key)
    topo_ok = bool(has_topo_support or has_generated_contours)
    required = bool(case.topo_required)
    if required and not topo_ok:
        return {
            "ok": False,
            "required": True,
            "level": "warning" if case.alert_level != "critical" else "error",
            "message": (
                f"{case.short_name}: requiere curvas de nivel/topografía de respaldo antes de generar o aceptar secciones. "
                "Cargue curvas KMZ/KML, genere curvas desde DEM o use un DEM local suficientemente detallado."
            ),
        }
    if required and topo_ok:
        return {
            "ok": True,
            "required": True,
            "level": "success",
            "message": f"{case.short_name}: respaldo topográfico disponible para secciones y eje de modelación.",
        }
    return {
        "ok": True,
        "required": False,
        "level": "info",
        "message": f"{case.short_name}: curvas de respaldo recomendadas, pero no obligatorias para este caso estándar.",
    }


def output_plan_for_case(case_key: str | None) -> List[str]:
    case = get_application_case(case_key)
    return list(case.recommended_outputs)


def case_image_path(case_key: str | None, assets_dir: str | Path = "assets") -> Path:
    case = get_application_case(case_key)
    return Path(assets_dir) / case.image_file
