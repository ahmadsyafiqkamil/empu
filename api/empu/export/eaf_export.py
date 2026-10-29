import os
import tempfile
from pathlib import Path

import pympi

from empu.models import Recording

TIERS = ("term", "spoken", "gloss-id", "gloss-en", "source", "stage")


def build_eaf(rec: Recording, rows: list) -> str:
    eaf = pympi.Elan.Eaf()
    media = rec.display_path or "display.mp4"
    eaf.add_linked_file(file_path=media, relpath=Path(media).name, mimetype="video/mp4")
    for tier in TIERS:
        if tier not in eaf.tiers:
            eaf.add_tier(tier)
    for entry, occs in rows:
        for o in occs:
            if o.recording_id != rec.id:
                continue
            start = int(o.t_start * 1000)
            end = int(max(o.t_end, o.t_start + 0.1) * 1000)
            eaf.add_annotation("term", start, end, entry.term)
            eaf.add_annotation("spoken", start, end, o.spoken or entry.term)
            eaf.add_annotation("gloss-id", start, end, entry.gloss_id)
            eaf.add_annotation("gloss-en", start, end, entry.gloss_en)
            eaf.add_annotation("source", start, end, o.source.value)
            eaf.add_annotation("stage", start, end, entry.stage_id or o.stage_id or "")
    fd, path = tempfile.mkstemp(suffix=".eaf")
    os.close(fd)
    try:
        eaf.to_file(path)
        return Path(path).read_text()
    finally:
        os.unlink(path)
