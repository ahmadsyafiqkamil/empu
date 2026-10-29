"""Consent lifecycle helpers."""

from sqlmodel import Session

from empu.enums import ConsentStatus
from empu.models import Recording, utcnow


def withdraw_consent(session: Session, recording_id: int) -> Recording:
    rec = session.get(Recording, recording_id)
    if rec is None:
        raise ValueError("recording not found")
    rec.consent_status = ConsentStatus.withdrawn
    rec.consent_withdrawn_at = utcnow()
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec
