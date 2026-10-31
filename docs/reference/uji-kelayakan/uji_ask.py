"""Probe: does the Responses API accept a text-only input with a json_schema format?

Ask Empu (docs/superpowers/specs/2026-10-31-ask-empu-design.md) needs a single
text call per question. Video is proven (docs/reference/meta-model-api.md); text-only
with structured output is not. Run once, from the repo root:

    cd api && uv run python ../docs/reference/uji-kelayakan/uji_ask.py

Writes the raw response to api/tests/fixtures/ask/probe.raw.json.
Never prints headers or the API key.
"""

import json
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
EMPU_ROOT = HERE.parents[2]
OUT = EMPU_ROOT / "api" / "tests" / "fixtures" / "ask" / "probe.raw.json"
BASE = "https://api.meta.ai/v1"
MODEL = "muse-spark-1.3"

RESPONSE_SCHEMA = {
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

ROWS = [
    '- id=1 | istilah=canting | arti_id="alat pena tembaga untuk menorehkan malam panas" '
    '| speech@134.0="ini namanya canting"',
    '- id=2 | istilah=nglorod | arti_id="meluruhkan malam dari kain dengan air mendidih" '
    "| visual_only@210.0=\"kain diaduk di air mendidih\"",
]

PROMPT = f"""Kamu penjaga kamus keahlian batik tulis. Kamu menjawab HANYA dari daftar istilah di bawah.

ATURAN
1. Jawab dalam bahasa yang dipakai penanya.
2. Pakai hanya istilah di daftar.
3. Setiap klaim harus ditopang id istilah dari daftar. Tulis id-nya di entry_ids.
4. Kalau daftar tidak menjawab pertanyaan, isi insufficient=true.

PERTANYAAN PENGGUNA
Apa itu canting?

DAFTAR ISTILAH (2 baris)
{chr(10).join(ROWS)}

Jawab hanya dengan JSON: answer, lang (id/en/jv/other), entry_ids (array id), insufficient (boolean).
"""


def api_key() -> str:
    for line in (EMPU_ROOT / ".env").read_text().splitlines():
        if line.startswith("META_MODEL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("META_MODEL_API_KEY is missing from .env at the repo root")


def main() -> None:
    body = {
        "model": MODEL,
        # Muse Spark spends reasoning tokens out of this budget: 400 was all
        # reasoning and produced an empty answer (status=incomplete).
        "max_output_tokens": 2000,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": PROMPT}]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "empu_answer",
                "schema": RESPONSE_SCHEMA,
                "strict": True,
            }
        },
    }
    t0 = time.monotonic()
    r = httpx.post(
        f"{BASE}/responses",
        headers={"Authorization": f"Bearer {api_key()}"},
        json=body,
        timeout=120,
    )
    latency = time.monotonic() - t0

    if r.status_code >= 400:
        print(f"status={r.status_code}")
        print(r.text[:2000])
        sys.exit(1)

    raw = r.json()
    text = raw.get("output_text")
    if not isinstance(text, str):
        parts = [
            c.get("text", "")
            for item in raw.get("output", []) or []
            for c in item.get("content", []) or []
            if c.get("type") in ("output_text", "text")
        ]
        text = "\n".join(parts)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(raw, ensure_ascii=False, indent=2))

    print(f"status={raw.get('status')}")
    print(f"latency_s={latency:.2f}")
    print(f"usage={json.dumps(raw.get('usage') or {})}")
    print("text:")
    print(text)


if __name__ == "__main__":
    main()
