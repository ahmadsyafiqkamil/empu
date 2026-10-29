"""Media layout under data_dir (spec section 9). The DB stores paths relative to data_dir."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from sqlmodel import Session

from empu.enums import ConsentStatus
from empu.models import Archive, Entry, Occurrence, Recording
from empu.visibility import entry_is_public, public_occurrences, recording_is_public


def recording_dir(data_dir: Path, archive_id: int, recording_id: int) -> Path:
    return Path(data_dir) / "archives" / str(archive_id) / "recordings" / str(recording_id)


def occurrence_dir(data_dir: Path, archive_id: int, recording_id: int, occurrence_id: int) -> Path:
    return recording_dir(data_dir, archive_id, recording_id) / "occurrences" / str(occurrence_id)


def entry_dir(data_dir: Path, archive_id: int, entry_id: int) -> Path:
    return Path(data_dir) / "archives" / str(archive_id) / "entries" / str(entry_id)


def rel_to_data(data_dir: Path, path: Path) -> str:
    return Path(path).resolve().relative_to(Path(data_dir).resolve()).as_posix()


def abs_from_rel(data_dir: Path, rel: str) -> Path:
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"invalid media path: {rel!r}")
    return Path(data_dir).joinpath(*p.parts)


def can_access_media(session: Session, rel_path: str, *, has_key: bool) -> bool:
    rel = rel_path.lstrip("/")
    parts = PurePosixPath(rel).parts
    if has_key:
        if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "recordings":
            try:
                rec = session.get(Recording, int(parts[3]))
            except ValueError:
                return False
            return rec is not None and rec.consent_status is not ConsentStatus.withdrawn
        return bool(parts) and parts[0] == "archives"
    if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "recordings":
        try:
            rec = session.get(Recording, int(parts[3]))
        except ValueError:
            return False
        if rec is None:
            return False
        arch = session.get(Archive, rec.archive_id)
        if arch is not None and arch.is_sandbox:
            # Sandbox media is unlisted but URL-addressable so the judge's view renders.
            return rec.consent_status is not ConsentStatus.withdrawn
        if not recording_is_public(rec):
            return False
        # Occurrence evidence (clip/audio/keyframe) must also pass entry visibility,
        # so a private or unreviewed term on a public recording never leaks.
        if len(parts) >= 6 and parts[4] == "occurrences":
            try:
                occ = session.get(Occurrence, int(parts[5]))
            except ValueError:
                return False
            if occ is None:
                return False
            entry = session.get(Entry, occ.entry_id)
            if entry is None:
                return False
            return entry_is_public(entry, public_occurrences(session, entry.id))
        return True
    if len(parts) >= 4 and parts[0] == "archives" and parts[2] == "entries":
        try:
            entry = session.get(Entry, int(parts[3]))
        except ValueError:
            return False
        if entry is None:
            return False
        arch = session.get(Archive, entry.archive_id)
        if arch is not None and arch.is_sandbox:
            return True
        return entry_is_public(entry, public_occurrences(session, entry.id))
    return False
