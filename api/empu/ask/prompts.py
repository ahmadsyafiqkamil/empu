"""Ask Empu prompt and answer schema.

Text-only, one call per question. The model receives rows taken from entries the
caller may show, and must cite their ids. Any change to TEMPLATE or the row format
must bump ASK_PROMPT_VERSION: it is part of the cache key.
"""

from __future__ import annotations

from empu.ask.index import IndexEntry

ASK_PROMPT_VERSION = "ask-v1"

RESPONSE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "lang", "entry_ids", "insufficient"],
    "properties": {
        "answer": {"type": "string"},
        "lang": {"type": "string", "enum": ["id", "en", "jv", "other"]},
        "entry_ids": {"type": "array", "items": {"type": "integer"}},
        "insufficient": {"type": "boolean"},
    },
}

TEMPLATE = """Kamu penjaga kamus keahlian {pack_name}. Kamu menjawab HANYA dari daftar istilah di bawah.

ATURAN
1. Jawab dalam bahasa yang dipakai penanya.
2. Pakai hanya istilah di daftar. Jangan menambah pengetahuan dari luar daftar.
3. Setiap klaim harus ditopang id istilah dari daftar. Tulis id-nya di entry_ids.
4. Kalau daftar tidak menjawab pertanyaan, isi insufficient=true dan katakan terus terang bahwa arsip belum memuatnya. Jangan menebak.
5. Hormati label sumber: speech = diucapkan, on_screen_text = tertulis di layar, visual_only = hanya terlihat. Jangan menulis "dia mengatakan" untuk yang hanya terlihat.
6. Jangan mengarang waktu atau kutipan.
7. Maksimal 90 kata.

PERTANYAAN PENGGUNA
{question}

DAFTAR ISTILAH ({count} baris)
{rows}

Jawab hanya dengan JSON: answer, lang (id/en/jv/other), entry_ids (array id), insufficient (boolean).
"""

SOURCE_NOTE = {
    "speech": "diucapkan",
    "on_screen_text": "tertulis di layar",
    "visual_only": "hanya terlihat",
}


def _variants(values: tuple[str, ...], term: str) -> str:
    rest = [v for v in values if v.strip() and v.casefold() != term.casefold()]
    return ", ".join(rest)


def format_rows(rows: list[IndexEntry], *, scope: str) -> str:
    """One line per entry. `status` is only shown to the studio, where it is actionable."""
    lines: list[str] = []
    for row in rows:
        parts = [f"id={row.id}", f"istilah={row.term}", f"kategori={row.category}"]
        if row.stage_id:
            parts.append(f"tahap={row.stage_id}")
        variants = _variants(row.variants, row.term)
        if variants:
            parts.append(f"varian={variants}")
        if row.gloss_id:
            parts.append(f"arti_id={row.gloss_id}")
        if row.gloss_en:
            parts.append(f"arti_en={row.gloss_en}")
        if scope == "studio":
            parts.append(f"status={row.status}")
        for ev in row.evidence:
            note = SOURCE_NOTE.get(ev.source, ev.source)
            parts.append(f'{ev.source}@{ev.t_start:.1f}="{ev.quote}" ({note})')
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


def build_prompt(rows: list[IndexEntry], question: str, *, pack_name: str, scope: str) -> str:
    return TEMPLATE.format(
        pack_name=pack_name,
        question=question,
        count=len(rows),
        rows=format_rows(rows, scope=scope),
    )
