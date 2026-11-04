import asyncio
import json

import pytest
from fastapi import HTTPException, Request

from src.api.app import app
from src.api.decisionproof import analysis, evaluation, scenarios


def test_catalog_evaluation_and_registration():
    root = "/v1/research/decisionproof/"
    paths = app.openapi()["paths"]
    assert "get" in paths[root + "scenarios"]
    assert "post" in paths[root + "analyze"]
    assert "get" in paths[root + "evaluation"]
    catalog = scenarios()
    assert catalog["synthetic"] is True
    assert all("evidence" in case and "actions" in case for case in catalog["scenarios"])
    assert {profile["cases"] for profile in evaluation()["profiles"]} == {len(catalog["scenarios"])}


@pytest.mark.parametrize(("body", "status"), [
    ({"scenario_id": "conflicting-income"}, 200),
    ({"scenario_id": "unknown-example"}, 404),
    ({"scenario_id": "consistent", "residual_min": "20000"}, 422),
    ({"scenario_id": "x" * 4096}, 413),
])
def test_analysis_request_contract(body, status):
    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    request = Request({"type": "http"}, receive)
    if status == 200:
        report = asyncio.run(analysis(request))
        assert report["scenario"]["id"] == body["scenario_id"]
        assert [state["residual"] for state in report["states"]] == [10000, 35000]
        assert len(report["reproducibility_id"]) == 64
    else:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(analysis(request))
        assert exc.value.status_code == status
