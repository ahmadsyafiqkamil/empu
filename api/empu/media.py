"""Media layout under data_dir (spec section 9). The DB stores paths relative to data_dir."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


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
