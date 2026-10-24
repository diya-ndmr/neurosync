from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record_audit_event(
    db: Session,
    *,
    action: str,
    outcome: str,
    actor_reference: str,
    actor_id: Optional[str] = None,
    request_id: Optional[str] = None,
    source_ip: Optional[str] = None,
) -> None:
    db.add(AuditEvent(
        actor_id=actor_id,
        actor_reference=actor_reference,
        action=action,
        outcome=outcome,
        request_id=request_id,
        source_ip=source_ip,
    ))