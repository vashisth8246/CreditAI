from itertools import combinations

import pytest
from pydantic import ValidationError

from src.decisionproof import AnalysisRequest, SCENARIOS, Verification, analyze, benchmark, plan


def test_independent_income_reversal_and_exact_boundary():
    result = analyze(AnalysisRequest(scenario_id="conflicting-income"))
    assert [s["residual"] for s in result["states"]] == [10000, 35000]
    assert result["meets_count"] == 1 and result["consequential"] == ["income"]
    assert result["strategies"]["DecisionProof"]["actions"] == ["income-record"]
    assert result["strategies"]["DecisionProof"]["possible_observations"] == 2
    boundary = analyze(AnalysisRequest(scenario_id="conflicting-income", residual_min=10000))
    assert boundary["meets_count"] == 2


def test_missing_outdated_variable_and_irrelevant_examples():
    expected = {"consistent": 1, "missing-income": 1, "missing-emi": 1, "variable-income": 2,
                "outdated": 1, "irrelevant": 2, "no-option": 1, "multiple": 4}
    for identifier, count in expected.items():
        result = analyze(AnalysisRequest(scenario_id=identifier))
        assert result["meets_count"] == count, identifier
    irrelevant = analyze(AnalysisRequest(scenario_id="irrelevant"))
    assert irrelevant["consequential"] == []
    assert irrelevant["strategies"]["DecisionProof"]["cost"] == 0
    assert not irrelevant["strategies"]["Manual review on any uncertainty"]["resolved"]
    blocked = analyze(AnalysisRequest(scenario_id="no-option"))
    assert blocked["status"] == "manual_review_required"
    assert blocked["strategies"]["DecisionProof"]["unresolved_groups"] == 1


def test_optimizer_matches_independent_opposite_pair_oracle_under_all_costs():
    for profile in ("base", "income_costly", "combined_costly"):
        for key in SCENARIOS:
            result = analyze(AnalysisRequest(scenario_id=key, cost_profile=profile))
            states = result["states"]
            opposites = [(a, b) for a, b in combinations(states, 2) if a["outcome"] != b["outcome"]]
            actions = [a for a in result["verification_options"] if a["permitted"]]
            costs = []
            for count in range(len(actions) + 1):
                for subset in combinations(actions, count):
                    if all(any(a[field] != b[field] for action in subset for field in action["reveals"]) for a,b in opposites):
                        costs.append(sum(action["cost"] for action in subset))
            selected = result["strategies"]["DecisionProof"]
            assert selected["resolved"] == bool(costs)
            if costs:
                assert selected["cost"] == min(costs)


def test_zero_cost_and_unpermitted_actions_and_replay():
    request = AnalysisRequest(scenario_id="conflicting-income")
    first, second = analyze(request), analyze(request)
    assert first["reproducibility_id"] == second["reproducibility_id"]
    assert first["reproducibility_id"] != analyze(AnalysisRequest(scenario_id=request.scenario_id, residual_min=40000))["reproducibility_id"]
    free = Verification(id="free", label="Free check", reveals=["income"], cost=0)
    forbidden = Verification(id="forbidden", label="Forbidden", reveals=["income"], cost=0, permitted=False)
    chosen = plan(first["states"], [forbidden, free])["DecisionProof"]
    assert chosen["resolved"] and chosen["actions"] == ["free"]


def test_validation_and_maximum_case():
    with pytest.raises(ValidationError):
        AnalysisRequest(scenario_id="consistent", residual_min="20000")
    with pytest.raises(ValidationError):
        AnalysisRequest(scenario_id="consistent", payment_ratio_bps=10001)
    data = SCENARIOS["consistent"].model_dump()
    data["evidence"][1]["id"] = data["evidence"][0]["id"]
    with pytest.raises(ValidationError):
        type(SCENARIOS["consistent"]).model_validate(data)
    large = analyze(AnalysisRequest(scenario_id="multiple", residual_min=1_000_000, payment_ratio_bps=10000))
    assert len(large["states"]) == 8 and large["meets_count"] == 0
    for profile in benchmark()["profiles"]:
        assert profile["cases"] == 9
        assert profile["strategies"]["DecisionProof"]["resolved"] == 8
