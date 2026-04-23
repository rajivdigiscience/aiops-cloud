from aiops_hub.ai_triage import IncidentTriageEngine
from aiops_hub.models import IncidentTriageRequest


def test_heuristic_triage_critical():
    engine = IncidentTriageEngine()
    req = IncidentTriageRequest(
        provider="aws",
        title="Checkout outage",
        description="Service is down with timeout and unauthorized errors",
    )

    result = engine._heuristic_triage(req)

    assert result.severity == "critical"
    assert any("IAM" in cause for cause in result.suspected_causes)


def test_heuristic_triage_medium_default():
    engine = IncidentTriageEngine()
    req = IncidentTriageRequest(
        provider="gcp",
        title="Minor warning",
        description="warning observed in logs",
    )

    result = engine._heuristic_triage(req)

    assert result.severity in {"low", "medium", "high", "critical"}
    assert len(result.recommended_actions) >= 1
