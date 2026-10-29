import csv
import io

from sqlmodel import Session

from empu.models import Contributor, Recording

HEADERS = [
    "term",
    "category",
    "stage",
    "gloss_id",
    "gloss_en",
    "variants",
    "is_novel",
    "status",
    "access_level",
    "maestro",
    "recording",
    "t_start",
    "t_end",
    "source",
    "confidence",
    "clip_path",
]


def build_csv(rows, session: Session) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADERS)
    w.writeheader()
    for entry, occs in rows:
        variants = "|".join(entry.variants_json or [])
        targets = occs or [None]
        for o in targets:
            rec = session.get(Recording, o.recording_id) if o else None
            contrib = (
                session.get(Contributor, rec.contributor_id) if rec and rec.contributor_id else None
            )
            w.writerow(
                {
                    "term": entry.term,
                    "category": entry.category.value,
                    "stage": entry.stage_id or "",
                    "gloss_id": entry.gloss_id,
                    "gloss_en": entry.gloss_en,
                    "variants": variants,
                    "is_novel": entry.is_novel,
                    "status": entry.status.value,
                    "access_level": entry.access_level.value,
                    "maestro": contrib.name if contrib else "",
                    "recording": rec.title if rec else "",
                    "t_start": o.t_start if o else "",
                    "t_end": o.t_end if o else "",
                    "source": o.source.value if o else "",
                    "confidence": o.confidence.value if o else "",
                    "clip_path": (o.clip_path or "") if o else "",
                }
            )
    return buf.getvalue()
