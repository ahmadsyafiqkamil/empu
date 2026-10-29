import csv
from dataclasses import dataclass
from pathlib import Path

from empu.enums import Category, Source


@dataclass(frozen=True)
class GoldRow:
    clip_id: str
    t_start: float
    t_end: float
    spoken: str
    term: str
    category: Category
    source: Source
    stage: str
    visible_object: str
    note: str
    annotator: str


def load_gold(path: Path) -> list[GoldRow]:
    rows: list[GoldRow] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            if (raw.get("annotator") or "").strip().lower() == "contoh":
                continue
            if not (raw.get("term") or "").strip():
                continue
            cat = raw.get("category") or "other"
            category = Category(cat) if cat in {c.value for c in Category} else Category.other
            rows.append(GoldRow(
                clip_id=raw["clip_id"], t_start=float(raw["t_start"]), t_end=float(raw["t_end"]),
                spoken=raw.get("spoken") or raw["term"], term=raw["term"],
                category=category, source=Source(raw["source"]),
                stage=raw.get("stage") or "", visible_object=raw.get("visible_object") or "",
                note=raw.get("note") or "", annotator=raw.get("annotator") or "",
            ))
    return rows
