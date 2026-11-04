"""Bounded, synthetic-only evidence partitioning. No model inference or external action."""
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations, product
from json import dumps
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

FieldName = Literal["income", "expenses", "existing_emi"]
FIELDS = ("income", "expenses", "existing_emi")
VERSION = "decisionproof-discrete-v1"
LIMITATION = (
    "Explicitly synthetic discrete alternatives. A verification reveals the exact listed field values "
    "in this simulation; real verification may be incomplete or wrong. No probabilities, Indian policy "
    "validation, credit-model mapping, or external verification are implied."
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Contract):
    id: StrictStr = Field(max_length=40)
    field: FieldName
    claimed: StrictInt | None = Field(default=None, ge=0, le=1_000_000)
    values: list[StrictInt] = Field(min_length=1, max_length=4)
    status: Literal["consistent", "missing", "conflicting", "outdated", "incomplete", "variable", "unverified"]
    source: StrictStr = Field(max_length=80)
    collected_at: StrictStr = "2026-10-01T00:00:00Z"
    period: StrictStr = "Illustrative month"
    provenance: Literal["synthetic"] = "synthetic"
    explanation: StrictStr = Field(max_length=300)

    @model_validator(mode="after")
    def bounded_values(self):
        if len(set(self.values)) != len(self.values) or any(not 0 <= v <= 1_000_000 for v in self.values):
            raise ValueError("Evidence alternatives must be unique INR amounts within bounds.")
        return self


class Verification(Contract):
    id: StrictStr = Field(max_length=40)
    label: StrictStr = Field(max_length=110)
    reveals: list[FieldName] = Field(min_length=1, max_length=3)
    cost: StrictInt = Field(ge=0, le=100)
    permitted: bool = True


class Scenario(Contract):
    id: StrictStr = Field(max_length=40)
    title: StrictStr = Field(max_length=100)
    explanation: StrictStr = Field(max_length=300)
    evidence: list[Evidence] = Field(min_length=3, max_length=3)
    actions: list[Verification] = Field(max_length=8)
    proposed_emi: StrictInt = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def unique_evidence(self):
        if {item.field for item in self.evidence} != set(FIELDS) or len({item.id for item in self.evidence}) != 3:
            raise ValueError("Exactly one uniquely identified evidence item per policy field is required.")
        if len({action.id for action in self.actions}) != len(self.actions):
            raise ValueError("Verification action IDs must be unique.")
        return self


class AnalysisRequest(Contract):
    scenario_id: StrictStr = Field(max_length=40)
    residual_min: StrictInt = Field(default=20000, ge=0, le=1_000_000)
    payment_ratio_bps: StrictInt = Field(default=4000, ge=0, le=10000)
    cost_profile: Literal["base", "income_costly", "combined_costly"] = "base"


def example(identifier, title, fields, note, *, actions=None):
    evidence = []
    for field, (status, values) in zip(FIELDS, fields):
        evidence.append(Evidence(
            id=f"{identifier}-{field}", field=field, values=values,
            claimed=values[-1] if status not in ("missing", "unverified") else None,
            status=status, source="Synthetic supporting record" if status == "consistent" else "Synthetic applicant scenario",
            period="Previous quarter (stale)" if status == "outdated" else "Illustrative month",
            explanation=note if status != "consistent" else "One value stipulated by this synthetic case.",
        ))
    if actions is None:
        actions = [
            Verification(id="income-record", label="Confirm the relevant monthly income record", reveals=["income"], cost=4),
            Verification(id="debt-record", label="Clarify existing monthly EMI", reveals=["existing_emi"], cost=3),
            Verification(id="expense-record", label="Clarify monthly essential expenses", reveals=["expenses"], cost=2),
            Verification(id="combined-record", label="Review a combined income and debt record", reveals=["income", "existing_emi"], cost=6),
            Verification(id="external-query", label="External account inquiry (unavailable)", reveals=["income"], cost=0, permitted=False),
        ]
    return Scenario(id=identifier, title=title, explanation=note, evidence=evidence, actions=actions, proposed_emi=15000)


SCENARIOS = {case.id: case for case in [
    example("consistent", "Complete and consistent", [("consistent", [90000]), ("consistent", [30000]), ("consistent", [10000])], "All modeled amounts agree."),
    example("missing-income", "Missing income evidence", [("missing", [55000, 95000]), ("consistent", [30000]), ("consistent", [10000])], "No supporting income value is stipulated; two plausible alternatives are tested."),
    example("conflicting-income", "Conflicting income evidence", [("conflicting", [65000, 90000]), ("consistent", [30000]), ("consistent", [10000])], "Declared income and observed deposits differ. Timing, deductions or incomplete coverage could explain the gap."),
    example("missing-emi", "Unverified existing EMI", [("consistent", [85000]), ("consistent", [30000]), ("unverified", [5000, 25000])], "The existing debt payment has not been confirmed."),
    example("variable-income", "Irregular freelancer income", [("variable", [55000, 80000, 105000]), ("consistent", [30000]), ("consistent", [10000])], "Three possible monthly income levels represent variability; no outcome probabilities are assigned."),
    example("outdated", "Outdated income document", [("outdated", [60000, 90000]), ("consistent", [30000]), ("consistent", [10000])], "An older synthetic record may not describe the current month."),
    example("irrelevant", "Conflict that cannot reverse the result", [("consistent", [110000]), ("conflicting", [28000, 33000]), ("consistent", [5000])], "Both expense interpretations leave enough residual money under the default policy."),
    example("multiple", "Multiple consequential gaps", [("conflicting", [65000, 90000]), ("incomplete", [24000, 42000]), ("unverified", [5000, 15000])], "Income, expense coverage and existing EMI may each affect the simulated result."),
    example("no-option", "No permitted verification available", [("missing", [65000, 90000]), ("consistent", [30000]), ("consistent", [10000])], "The consequential income gap cannot be resolved by any permitted action.", actions=[]),
]}


def outcomes(case, residual_min, ratio_bps):
    options = {item.field: sorted(item.values) for item in case.evidence}
    states = []
    for income, expenses, existing in product(*(options[field] for field in FIELDS)):
        payment = existing + case.proposed_emi
        residual = income - expenses - payment
        meets = income > 0 and residual >= residual_min and payment * 10000 <= income * ratio_bps
        states.append(dict(income=income, expenses=expenses, existing_emi=existing, residual=residual,
                           payment_ratio_bps=round(payment * 10000 / income) if income else None,
                           outcome="meets_simulated_policy" if meets else "outside_simulated_policy"))
    return states


def outcome_partition(states, fields):
    groups = {}
    for state in states:
        key = tuple(state[name] for name in fields)
        groups.setdefault(key, set()).add(state["outcome"])
    return groups


def plan(states, actions):
    """Minimum total cost over nonadaptive action sets separating every opposite-outcome pair."""
    def summarize(selected):
        reveals = sorted({field for action in selected for field in action.reveals})
        groups = outcome_partition(states, reveals)
        unresolved = sum(len(labels) > 1 for labels in groups.values())
        return dict(actions=[action.id for action in selected], cost=sum(action.cost for action in selected),
                    resolved=unresolved == 0, unresolved_groups=unresolved, possible_observations=len(groups), reveals=reveals)
    allowed = [action for action in actions if action.permitted]
    best = None
    for count in range(len(allowed) + 1):
        for subset in combinations(allowed, count):
            row = summarize(subset)
            key = (row["cost"], count, tuple(sorted(row["actions"])))
            if row["resolved"] and (best is None or key < best[0]):
                best = key, row
    def prefix(ordered):
        for count in range(len(ordered) + 1):
            result = summarize(ordered[:count])
            if result["resolved"]:
                return result
        return summarize(ordered)
    return {
        "No verification": summarize([]), "Verify all": summarize(allowed),
        "Fixed sequence": prefix(allowed),
        "Cheapest first": prefix(sorted(allowed, key=lambda action: (action.cost, action.id))),
        "DecisionProof": best[1] if best else summarize([]),
    }


def analyze(request, case=None):
    case = case or SCENARIOS[request.scenario_id]
    multipliers = {"income_costly": {"income-record": 3}, "combined_costly": {"combined-record": 3}}
    adjustments = multipliers.get(request.cost_profile, {})
    actions = [action.model_copy(update={"cost": action.cost * adjustments.get(action.id, 1)}) for action in case.actions]
    states = outcomes(case, request.residual_min, request.payment_ratio_bps)
    count = sum(state["outcome"] == "meets_simulated_policy" for state in states)
    consequential = [field for field in FIELDS if any(
        len(labels) > 1 for labels in outcome_partition(states, [name for name in FIELDS if name != field]).values()
    )]
    comparison = plan(states, actions)
    # Conservative review baseline withholds a policy result whenever any input varies.
    if any(len(item.values) > 1 for item in case.evidence):
        comparison["Manual review on any uncertainty"] = comparison["No verification"] | {"resolved": False}
    else:
        comparison["Manual review on any uncertainty"] = comparison["No verification"].copy()
    status = ("stable_under_tested_scenarios" if count in (0, len(states)) else
              "additional_verification_recommended" if comparison["DecisionProof"]["resolved"] else "manual_review_required")
    policy = request.model_dump()
    audit = dict(method=VERSION, scenario=case.model_dump(), policy=policy, states=states, consequential=consequential,
                 status=status, meets_count=count, verification_options=[a.model_dump() for a in actions],
                 strategies=comparison, limitation=LIMITATION,
                 sensitivity=[
                     {"residual_min": value, "meets_count": sum(row["outcome"] == "meets_simulated_policy" for row in outcomes(case, value, request.payment_ratio_bps))}
                     for value in sorted({max(0, request.residual_min - 5000), request.residual_min, min(1_000_000, request.residual_min + 5000)})
                 ],
                 ratio_sensitivity=[
                     {"payment_ratio_bps": value, "meets_count": sum(row["outcome"] == "meets_simulated_policy" for row in outcomes(case, request.residual_min, value))}
                     for value in sorted({max(0, request.payment_ratio_bps - 500), request.payment_ratio_bps, min(10000, request.payment_ratio_bps + 500)})
                 ])
    return audit | {"reproducibility_id": sha256(dumps(audit, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                    "generated_at": datetime.now(timezone.utc).isoformat()}


def benchmark():
    from time import perf_counter
    output = []
    for profile in ("base", "income_costly", "combined_costly"):
        start = perf_counter()
        cases = [analyze(AnalysisRequest(scenario_id=key, cost_profile=profile)) for key in SCENARIOS]
        aggregates = {}
        for name in cases[0]["strategies"]:
            rows = [case["strategies"][name] for case in cases]
            unnecessary = 0
            for case, row in zip(cases, rows):
                selected = [action for action in case["verification_options"] if action["id"] in row["actions"]]
                for action in selected:
                    others = {field for candidate in selected if candidate is not action for field in candidate["reveals"]}
                    unnecessary += row["resolved"] and all(len(labels) == 1 for labels in outcome_partition(case["states"], sorted(others)).values())
            aggregates[name] = dict(cost=sum(row["cost"] for row in rows),
                                    actions=sum(len(row["actions"]) for row in rows),
                                    resolved=sum(row["resolved"] for row in rows),
                                    individually_removable_actions=unnecessary)
        output.append(dict(cost_profile=profile, cases=len(cases),
                           reversals=sum(bool(case["consequential"]) for case in cases),
                           strategies=aggregates, elapsed_ms=round((perf_counter() - start) * 1000, 3)))
    return {"method": VERSION, "synthetic": True, "profiles": output, "limitation": LIMITATION}
