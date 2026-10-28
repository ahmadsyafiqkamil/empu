"""Shared helpers for the Gate 0 spike.

Throwaway code. Production code lives in api/empu/ and must not import this.
Never print the API key or request headers.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
BASE = "https://api.meta.ai/v1"
OUT = REPO / "data" / "spikes" / "gate0"
TESTDATA = Path(os.environ.get("EMPU_TESTDATA_DIR", REPO / "data-uji")).resolve()
SCHEMA_PATH = REPO / "docs" / "reference" / "muse-output.schema.json"
PACK_PATH = REPO / "docs" / "packs" / "batik_tulis.yaml"


def _api_key() -> str:
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("META_MODEL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("META_MODEL_API_KEY missing in .env")


def client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE,
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=httpx.Timeout(900, connect=30),
    )


def find_video(yt_id: str) -> Path:
    hits = sorted(p for p in TESTDATA.rglob("*.mp4") if f"[{yt_id}]" in p.name)
    if not hits:
        raise SystemExit(f"video [{yt_id}] not found under {TESTDATA}")
    return hits[0]


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def make_clip(src: Path, start: float, dur: float, dst: Path, *, strip_audio: bool = False) -> Path:
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    audio = ["-an"] if strip_audio else ["-c:a", "aac", "-ac", "1", "-b:a", "64k"]
    _ffmpeg(
        "-ss", str(start), "-i", str(src), "-t", str(dur),
        "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        *audio, str(dst),
    )
    return dst


def extract_frame(src: Path, t: float, dst: Path) -> Path:
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg("-ss", str(t), "-i", str(src), "-frames:v", "1", "-vf", "scale=-2:480", "-q:v", "2", str(dst))
    return dst


def upload(c: httpx.Client, path: Path, mime: str = "video/mp4") -> str:
    with path.open("rb") as f:
        r = c.post("/files", files={"file": (path.name, f, mime)},
                   data={"purpose": "user_data"}, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError(f"upload {r.status_code}: {r.text[:500]}")
    return r.json()["id"]


def post_json(c: httpx.Client, path: str, body: dict) -> tuple[int, dict | str]:
    r = c.post(path, json=body)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text[:2000]


def video_body(file_id: str, prompt: str, *, model: str = "muse-spark-1.3",
               text_format: dict | None = None) -> dict:
    body: dict = {
        "model": model,
        "max_output_tokens": 16000,
        "input": [{"role": "user", "content": [
            {"type": "input_video", "file_id": file_id},
            {"type": "input_text", "text": prompt},
        ]}],
    }
    if text_format is not None:
        body["text"] = {"format": text_format}
    return body


def output_text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts = []
    for item in resp.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts)


def parse_json(text: str) -> dict:
    """First complete JSON object in the text. Muse sometimes appends a second object."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("terms"), list):
            return obj
    return {}


def save(name: str, obj: object) -> Path:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    return path


def once(name: str, fn: Callable[[], dict]) -> dict:
    path = OUT / name
    if path.exists():
        return json.loads(path.read_text())
    result = fn()
    save(name, result)
    return result
