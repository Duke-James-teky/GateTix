
import json

from sqlalchemy.orm import Session

from app.models.growth import EventAuditLog


def log_event_action(
    db: Session,
    *,
    event_id: int,
    actor_id: int,
    action: str,
    details: dict | None = None,
) -> EventAuditLog:
    """Record an important action performed on an event."""

    audit_log = EventAuditLog(
        event_id=event_id,
        actor_id=actor_id,
        action=action,
        details=json.dumps(details or {}),
    )

    db.add(audit_log)
    db.flush()

    return audit_log
