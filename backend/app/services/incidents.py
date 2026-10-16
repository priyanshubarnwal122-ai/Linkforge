from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentAction, OperationalEvent
from app.services.incident_policy import validate_remediation_action

ACTION_PENDING = "pending"
ACTION_APPROVED = "approved"
ACTION_EXECUTED = "executed"


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    component: str,
    message: str,
    severity: str = "info",
    evidence: dict | None = None,
) -> OperationalEvent:
    event = OperationalEvent(
        event_type=event_type,
        component=component,
        message=message,
        severity=severity,
        evidence=evidence,
        occurred_at=datetime.now(UTC),
    )
    session.add(event)
    await session.flush()
    return event


async def detect_incidents(session: AsyncSession, *, window_minutes: int = 5) -> list[Incident]:
    """Create incidents from deterministic error-rate rules.

    This deliberately uses persisted events only; an unavailable AI provider
    cannot affect detection or ordinary redirects.
    """
    since = datetime.now(UTC) - timedelta(minutes=window_minutes)
    rows = await session.execute(
        select(OperationalEvent.component, func.count(OperationalEvent.id).label("count"))
        .where(OperationalEvent.occurred_at >= since, OperationalEvent.severity.in_(["error", "critical"]))
        .group_by(OperationalEvent.component)
    )
    incidents: list[Incident] = []
    for component, count in rows:
        existing = (await session.execute(select(Incident).where(Incident.component == component, Incident.status == "open"))).scalars().first()
        if existing:
            continue
        severity = "critical" if count >= 10 else "high" if count >= 5 else "medium"
        incident = Incident(
            title=f"Elevated errors in {component}",
            severity=severity,
            component=component,
            started_at=since,
            summary=f"{count} error events observed in the last {window_minutes} minutes.",
            evidence=[{"rule": "error_rate", "count": count, "window_minutes": window_minutes}],
        )
        session.add(incident)
        await session.flush()
        await session.execute(
            OperationalEvent.__table__.update()
            .where(
                OperationalEvent.component == component,
                OperationalEvent.occurred_at >= since,
                OperationalEvent.severity.in_(["error", "critical"]),
                OperationalEvent.incident_id.is_(None),
            )
            .values(incident_id=incident.id)
        )
        incidents.append(incident)
    return incidents


async def request_remediation(
    session: AsyncSession, *, incident: Incident, action: str, user_id: str
) -> IncidentAction:
    action = validate_remediation_action(action)
    record = IncidentAction(
        incident_id=incident.id,
        action=action,
        status=ACTION_PENDING,
        requested_by=uuid.UUID(user_id),
        requested_at=datetime.now(UTC),
    )
    session.add(record)
    await session.flush()
    return record


async def approve_remediation(
    session: AsyncSession, *, record: IncidentAction, user_id: str
) -> IncidentAction:
    if record.status != ACTION_PENDING:
        raise ValueError("Only pending remediation actions can be approved.")
    record.status = ACTION_APPROVED
    record.approved_by = uuid.UUID(user_id)
    record.approved_at = datetime.now(UTC)
    await session.flush()
    return record


async def execute_remediation(session: AsyncSession, *, record: IncidentAction) -> IncidentAction:
    if record.status != ACTION_APPROVED:
        raise ValueError("Remediation must be approved before execution.")
    incident = (await session.execute(select(Incident).where(Incident.id == record.incident_id))).scalar_one()
    now = datetime.now(UTC)
    if record.action == "acknowledge_incident":
        if incident.status == "open":
            incident.status = "acknowledged"
    elif record.action == "resolve_incident":
        incident.status = "resolved"
        incident.resolved_at = now
    else:  # Defense in depth if a record was modified outside this service.
        raise ValueError("Action is not in the safe remediation allowlist.")
    record.status = ACTION_EXECUTED
    record.executed_at = now
    record.result = {"incident_status": incident.status}
    await session.flush()
    return record
