"""Bounded, evidence-backed incident investigation."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.incident import Incident, OperationalEvent

MAX_EVIDENCE_EVENTS = 100
MAX_MESSAGE_LENGTH = 500


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str
    component: str
    occurred_at: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class InvestigationResult(BaseModel):
    """Strict shape exposed from every investigation provider."""
    model_config = ConfigDict(extra="forbid")
    observed_facts: list[str] = Field(min_length=1, max_length=20)
    root_cause_hypothesis: str = Field(min_length=1, max_length=500)
    confidence: Literal["low", "medium", "high"]
    uncertainty: list[str] = Field(min_length=1, max_length=20)
    recommended_next_step: str = Field(min_length=1, max_length=500)
    evidence: list[EvidenceRecord] = Field(max_length=MAX_EVIDENCE_EVENTS)


async def collect_evidence(
    session: AsyncSession, incident: Incident, *, max_events: int = MAX_EVIDENCE_EVENTS
) -> list[EvidenceRecord]:
    """Collect only linked events, bounded to avoid unbounded prompts/results."""
    limit = max(1, min(max_events, MAX_EVIDENCE_EVENTS))
    rows = (await session.execute(
        select(OperationalEvent).where(OperationalEvent.incident_id == incident.id)
        .order_by(OperationalEvent.occurred_at).limit(limit)
    )).scalars().all()
    return [EvidenceRecord(
        event_id=str(event.id), event_type=event.event_type, component=event.component,
        occurred_at=event.occurred_at.isoformat(), message=event.message[:MAX_MESSAGE_LENGTH],
        evidence=event.evidence if isinstance(event.evidence, dict) else {},
    ) for event in rows]


def deterministic_investigation(incident: Incident, evidence: list[EvidenceRecord]) -> InvestigationResult:
    return InvestigationResult(
        observed_facts=[f"{len(evidence)} persisted events are linked to this incident.", f"The affected component is {incident.component}."],
        root_cause_hypothesis=f"The {incident.component} component experienced elevated errors.",
        confidence="medium" if evidence else "low",
        uncertainty=["Underlying dependency cause is not established by redirect telemetry alone.", "No causal claim is made beyond the persisted incident evidence."],
        recommended_next_step="Check service health and dependency logs before approving remediation.", evidence=evidence,
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```").removeprefix("json").removesuffix("```").strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


async def _gemini_investigation(
    incident: Incident, evidence: list[EvidenceRecord], settings: Settings,
    *, client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
) -> InvestigationResult:
    prompt = ("Return only JSON matching this schema: observed_facts (array of strings), "
        "root_cause_hypothesis (string), confidence (low|medium|high), uncertainty "
        "(non-empty array of strings), recommended_next_step (string), evidence "
        "(the supplied evidence records, unchanged). Analyze only this data.\n" +
        json.dumps({"incident": {"component": incident.component, "summary": incident.summary}, "evidence": [item.model_dump() for item in evidence]}))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}}
    async with client_factory(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        response.raise_for_status()
        body = response.json()
    return InvestigationResult.model_validate(_extract_json(body["candidates"][0]["content"]["parts"][0]["text"]))


async def investigate_incident(
    session: AsyncSession, incident: Incident, *, settings: Settings | None = None,
    client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
) -> InvestigationResult:
    settings = settings or get_settings()
    evidence = await collect_evidence(session, incident)
    if settings.gemini_api_key:
        try:
            return await _gemini_investigation(incident, evidence, settings, client_factory=client_factory)
        except Exception:
            pass
    return deterministic_investigation(incident, evidence)
