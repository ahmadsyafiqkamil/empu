"""Raw Meta API response cache keyed by segment hash + model + prompt version + mode."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(chunk_size):
            h.update(block)
    return h.hexdigest()


class ResponseCache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def key(segment_sha256: str, model: str, prompt_version: str, mode: str) -> str:
        return "__".join(_UNSAFE.sub("_", p) for p in (segment_sha256, model, prompt_version, mode))

    def path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key: str, payload: dict) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        dst = self.path(key)
        tmp = dst.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False))
        os.replace(tmp, dst)
        return dst
