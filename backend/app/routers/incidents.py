from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import CurrentUserId, DbSession, require_verified
from app.exceptions import NotFoundError
from app.models.incident import Incident, IncidentAction, OperationalEvent
from app.schemas import IncidentActionRequest
from app.services.incidents import (
    approve_remediation,
    detect_incidents,
    execute_remediation,
    request_remediation,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("/")
async def list_incidents(user_id: CurrentUserId, db: DbSession) -> list[dict]:
    # Incident data is operational and account-independent for now; access is
    # still authenticated so it is not exposed as an anonymous admin surface.
    rows = (await db.execute(select(Incident).order_by(Incident.started_at.desc()).limit(100))).scalars().all()
    return [{"id": str(row.id), "title": row.title, "severity": row.severity, "status": row.status,
             "component": row.component, "started_at": row.started_at, "summary": row.summary,
             "evidence": row.evidence or []} for row in rows]


@router.post("/detect")
async def run_detection(user_id: CurrentUserId, db: DbSession) -> dict:
    incidents = await detect_incidents(db)
    return {"created": len(incidents), "incident_ids": [str(item.id) for item in incidents]}


@router.post("/{incident_id}/investigate")
async def investigate_incident(incident_id: str, user_id: CurrentUserId, db: DbSession) -> dict:
    """Return an evidence-backed baseline investigation.

    The deterministic investigator is intentionally useful without an AI key:
    it reports observed event counts and explicitly labels the root cause as a
    hypothesis rather than inventing one.
    """
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        return {"status": "not_found"}
    incident = (await db.execute(select(Incident).where(Incident.id == incident_uuid))).scalars().first()
    if not incident:
        return {"status": "not_found"}
    events = (await db.execute(select(OperationalEvent).where(OperationalEvent.incident_id == incident.id).order_by(OperationalEvent.occurred_at))).scalars().all()
    evidence = [{"event_id": str(event.id), "event_type": event.event_type, "component": event.component,
                 "occurred_at": event.occurred_at, "message": event.message, "evidence": event.evidence or {}}
                for event in events]
    finding = {
        "observed_facts": [f"{len(events)} persisted events are linked to this incident."],
        "root_cause_hypothesis": f"The {incident.component} component experienced elevated errors.",
        "confidence": "medium" if events else "low",
        "unknowns": ["Underlying dependency cause is not established by redirect telemetry alone."],
        "recommended_next_step": "Check service health and dependency logs before approving remediation.",
        "evidence": evidence,
    }
    incident.evidence = evidence
    incident.summary = finding["root_cause_hypothesis"]
    await db.flush()
    return {"status": "complete", "incident_id": incident_id, "investigation": finding}


def _action_response(record: IncidentAction) -> dict:
    return {"id": str(record.id), "incident_id": str(record.incident_id), "action": record.action,
            "status": record.status, "requested_by": str(record.requested_by),
            "approved_by": str(record.approved_by) if record.approved_by else None,
            "requested_at": record.requested_at, "approved_at": record.approved_at,
            "executed_at": record.executed_at, "result": record.result}


def _uuid(value: str, message: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise NotFoundError(message) from exc


@router.post("/{incident_id}/actions")
async def create_action(incident_id: str, payload: IncidentActionRequest, db: DbSession, user=Depends(require_verified)) -> dict:
    incident = (await db.execute(select(Incident).where(Incident.id == _uuid(incident_id, "Incident not found.")))).scalar_one_or_none()
    if not incident:
        raise NotFoundError("Incident not found.")
    try:
        record = await request_remediation(db, incident=incident, action=payload.action, user_id=str(user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _action_response(record)


@router.post("/{incident_id}/actions/{action_id}/approve")
async def approve_action(incident_id: str, action_id: str, db: DbSession, user=Depends(require_verified)) -> dict:
    record = (await db.execute(select(IncidentAction).where(
        IncidentAction.id == _uuid(action_id, "Incident action not found."),
        IncidentAction.incident_id == _uuid(incident_id, "Incident action not found."),
    ))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Incident action not found.")
    try:
        record = await approve_remediation(db, record=record, user_id=str(user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _action_response(record)


@router.post("/{incident_id}/actions/{action_id}/execute")
async def execute_action(incident_id: str, action_id: str, db: DbSession, user=Depends(require_verified)) -> dict:
    record = (await db.execute(select(IncidentAction).where(
        IncidentAction.id == _uuid(action_id, "Incident action not found."),
        IncidentAction.incident_id == _uuid(incident_id, "Incident action not found."),
    ))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Incident action not found.")
    try:
        record = await execute_remediation(db, record=record)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _action_response(record)
