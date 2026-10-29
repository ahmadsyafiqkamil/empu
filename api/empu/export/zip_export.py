import io
import json
import zipfile

from sqlmodel import Session

from empu.config import Settings
from empu.export.common import ExportScope, entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.eaf_export import build_eaf
from empu.export.json_export import build_json
from empu.media import abs_from_rel
from empu.models import Archive, Recording
from empu.packs import CraftPack


def build_zip(
    session: Session, archive: Archive, pack: CraftPack, scope: ExportScope, settings: Settings
) -> bytes:
    rows = entries_for_scope(session, archive.id, scope)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "empu-dataset.json",
            json.dumps(build_json(session, archive, pack, scope), ensure_ascii=False, indent=1),
        )
        z.writestr("entries.csv", build_csv(rows, session))
        rec_ids = {o.recording_id for _, occs in rows for o in occs}
        for rid in rec_ids:
            rec = session.get(Recording, rid)
            if rec is None:
                continue
            subset = [(e, [o for o in occs if o.recording_id == rid]) for e, occs in rows]
            z.writestr(f"{rid}.eaf", build_eaf(rec, subset))
        copied: set[str] = set()
        for e, occs in rows:
            paths = [e.crop_path, e.overlay_path]
            for o in occs:
                paths.extend([o.clip_path, o.audio_path, o.keyframe_path])
            for rel in paths:
                if not rel or rel in copied:
                    continue
                try:
                    src = abs_from_rel(settings.data_dir, rel)
                except ValueError:
                    continue
                if src.is_file():
                    z.write(src, arcname=f"media/{rel}")
                    copied.add(rel)
        z.writestr("README.txt", _readme(archive, pack, rows, session))
    return buf.getvalue()


def _readme(archive: Archive, pack: CraftPack, rows, session: Session) -> str:
    lines = [
        f"Empu export — {archive.title}",
        f"Craft pack: {pack.id} {pack.version}",
        "Clips are trimmed from the source recordings.",
        "",
        "Attribution:",
    ]
    seen: set[int] = set()
    for _, occs in rows:
        for o in occs:
            rec = session.get(Recording, o.recording_id)
            if rec and rec.attribution and rec.id not in seen:
                seen.add(rec.id)
                extra = f" Source: {rec.source_url}" if rec.source_url else ""
                lines.append(f"- {rec.attribution}{extra}")
    lines += [
        "",
        "Data remains with the makers and their community (CARE principles).",
        "Not for sale or third-party model training without permission.",
        "",
    ]
    return "\n".join(lines)
