"""Gate 0.4 (rerun): text.format json_schema with the FULL v3 schema.

The earlier test passed with a simplified schema (Indonesian enums). This checks the real
contract. Falls back to a stripped schema (no maxLength/minimum/$schema/$id/title/description).
"""

from __future__ import annotations

import copy
import json

import jsonschema

from common import (OUT, SCHEMA_PATH, client, find_video, make_clip, once, output_text,
                    parse_json, post_json, upload, video_body)
from prompt_v3 import build

STRIP = {"maxLength", "minimum", "$schema", "$id", "title", "description"}


def stripped(node):
    if isinstance(node, dict):
        return {k: stripped(v) for k, v in node.items() if k not in STRIP}
    if isinstance(node, list):
        return [stripped(v) for v in node]
    return node


def attempt(c, file_id: str, prompt: str, name: str, schema: dict) -> dict:
    fmt = {"type": "json_schema", "name": "empu_terms", "schema": schema, "strict": True}
    status, resp = post_json(c, "/responses", video_body(file_id, prompt, text_format=fmt))
    result = {"variant": name, "status": status, "error": None, "valid_json": False,
              "schema_valid": False, "raw": resp}
    if status >= 400:
        result["error"] = resp if isinstance(resp, str) else json.dumps(resp)[:1500]
        return result
    try:
        parsed = json.loads(output_text(resp))
        result["valid_json"] = True
    except ValueError:
        parsed = parse_json(output_text(resp))
    try:
        jsonschema.validate(parsed, json.loads(SCHEMA_PATH.read_text()))
        result["schema_valid"] = True
    except jsonschema.ValidationError as e:
        result["error"] = f"schema: {e.message}"
    return result


def main() -> None:
    full = json.loads(SCHEMA_PATH.read_text())
    clip = make_clip(find_video("7-WQ3DKKn0w"), 120, 30, OUT / "clips" / "ngertibatik-120-150.mp4")
    prompt = build(1, 1, 30)

    def run() -> dict:
        with client() as c:
            fid = upload(c, clip)
            attempts = [attempt(c, fid, prompt, "full", copy.deepcopy(full))]
            if attempts[0]["status"] >= 400:
                attempts.append(attempt(c, fid, prompt, "stripped", stripped(full)))
            return {"file_id": fid, "attempts": attempts}

    data = once("structured.json", run)
    for a in data["attempts"]:
        print(a["variant"], a["status"], "json:", a["valid_json"], "schema:", a["schema_valid"],
              "err:", (a["error"] or "")[:300])


if __name__ == "__main__":
    main()
