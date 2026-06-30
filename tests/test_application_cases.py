from modules.application_cases import (
    application_cases, case_labels, case_key_from_label,
    get_application_case, topo_support_status, output_plan_for_case,
)


def test_four_application_cases_exist_and_labels_are_stable():
    cases = application_cases()
    assert len(cases) == 4
    labels = case_labels()
    assert labels[0].startswith("Caso 1")
    assert labels[-1].startswith("Caso 4")
    for label in labels:
        key = case_key_from_label(label)
        assert key in cases


def test_cases_2_3_4_require_topographic_support():
    cases = application_cases()
    assert cases["case_1_basin_internal_axis"].topo_required is False
    assert cases["case_2_basin_user_axis_connected"].topo_required is True
    assert cases["case_3_basin_marginal_axis"].topo_required is True
    assert cases["case_4_basin_external_axis"].topo_required is True


def test_topographic_support_status_blocks_warning_for_required_cases_without_curves():
    status = topo_support_status("case_3_basin_marginal_axis", False, False)
    assert status["ok"] is False
    assert status["required"] is True
    assert "requiere curvas" in status["message"]

    ok = topo_support_status("case_3_basin_marginal_axis", False, True)
    assert ok["ok"] is True
    assert ok["level"] == "success"


def test_external_axis_output_plan_mentions_transfer_traceability():
    case = get_application_case("case_4_basin_external_axis")
    assert "transferencia" in case.description.lower() or "transferencia" in case.hydraulic_use.lower()
    plan = " ".join(output_plan_for_case(case.key)).lower()
    assert "transferencia" in plan
