import json
import os
import re
from typing import Any

from aiops_hub.config import get_settings
from aiops_hub.models import IncidentTriageRequest, IncidentTriageResponse

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]


SEVERITY_RULES = {
    "critical": ["outage", "down", "data loss", "sev1", "security breach", "unavailable"],
    "high": ["latency", "timeouts", "packet loss", "error rate", "unhealthy"],
    "medium": ["degraded", "retry", "throttle", "warning"],
}

CAUSE_RULES = {
    r"(auth|permission|forbidden|unauthorized)": "IAM or credential configuration issue",
    r"(timeout|latency|network|connection reset|packet)": "Network path or connectivity issue",
    r"(quota|limit|capacity|insufficient)": "Resource quota/capacity exhausted",
    r"(disk|storage|iops|filesystem)": "Storage performance or availability issue",
    r"(cpu|memory|oom|pressure)": "Compute resource saturation",
    r"(dns|name resolution)": "DNS resolution issue",
}

ACTION_LIBRARY = {
    "low": ["Continue monitoring and collect trend data for 30 minutes."],
    "medium": ["Run diagnostic_bundle and attach output to ticket.", "Validate recent infra changes in last deployment window."],
    "high": [
        "Check impacted instance/network/storage components and trigger targeted recovery runbook.",
        "Notify on-call engineer and track service-level indicators every 5 minutes.",
    ],
    "critical": [
        "Declare incident and page incident commander immediately.",
        "Start service failover or rollback plan.",
        "Open war-room channel and begin customer impact assessment.",
    ],
}


class IncidentTriageEngine:
    def triage(self, request: IncidentTriageRequest) -> IncidentTriageResponse:
        heuristic = self._heuristic_triage(request)
        llm_result = self._llm_enrichment(request)
        if llm_result:
            return llm_result
        return heuristic

    def _heuristic_triage(self, request: IncidentTriageRequest) -> IncidentTriageResponse:
        text = f"{request.title}\n{request.description}\n{request.logs or ''}".lower()
        severity = "low"

        for level in ("critical", "high", "medium"):
            if any(token in text for token in SEVERITY_RULES[level]):
                severity = level
                break

        causes = []
        for pattern, cause in CAUSE_RULES.items():
            if re.search(pattern, text):
                causes.append(cause)

        if not causes:
            causes.append("Insufficient telemetry in alert payload; require expanded diagnostics")

        actions = ACTION_LIBRARY[severity]
        summary = f"{request.provider.upper()} incident triaged as {severity.upper()} with {len(causes)} likely cause(s)."

        return IncidentTriageResponse(
            severity=severity,  # type: ignore[arg-type]
            suspected_causes=sorted(set(causes)),
            recommended_actions=actions,
            summary=summary,
        )

    def _llm_enrichment(self, request: IncidentTriageRequest) -> IncidentTriageResponse | None:
        settings = get_settings()
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not settings.enable_openai_enrichment or not api_key or OpenAI is None:
            return None

        client = OpenAI(api_key=api_key)
        prompt = {
            "provider": request.provider,
            "title": request.title,
            "description": request.description,
            "logs": request.logs,
            "metadata": request.metadata,
            "instruction": (
                "Return strict JSON with keys: severity (low/medium/high/critical),"
                " suspected_causes (array), recommended_actions (array), summary (string)."
            ),
        }

        try:
            result = client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": "You are an SRE incident triage assistant. Return only valid JSON.",
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
            )
        except Exception:
            return None

        text = getattr(result, "output_text", "")
        if not text:
            return None

        parsed = _safe_load_json_object(text)
        if not parsed:
            return None

        try:
            return IncidentTriageResponse(**parsed)
        except Exception:
            return None


def _safe_load_json_object(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
