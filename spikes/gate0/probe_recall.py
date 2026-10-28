"""Gate 0.2: recall of 8 spoken terms in #NgertiBatik (7-WQ3DKKn0w), 75 s segments, prompt v3.

Pass: >= 6 of 8 matched with source=speech and |dt| <= 5 s. Otherwise Mode B is default.
"""

from __future__ import annotations

import json
import re
import statistics

from common import (OUT, client, find_video, make_clip, once, output_text, parse_json,
                    post_json, upload, video_body)
from prompt_v3 import build

DURATION = 241.0
WINDOW, OVERLAP = 75.0, 10.0
GOLD = [
    ("pola", 85, 87, ["pola", "memola", "molani"]),
    ("lilin malam", 109, 109, ["malam", "lilin", "lilin malam"]),
    ("spangkring", 122, 122, ["spangkring", "spang kring", "sangkring"]),
    ("membatik", 126, 128, ["membatik", "mencanting", "canting", "nyanting"]),
    ("mewarna", 145, 149, ["mewarna", "mewarnai", "pewarnaan", "warna"]),
    ("hcl", 155, 155, ["hcl", "asam klorida"]),
    ("waterglass", 162, 165, ["waterglass", "water glass", "natrium silikat"]),
    ("nglorod", 173, 173, ["nglorod", "ngelorod", "ngelorot", "lorod", "lorot", "dilorot",
                           "dilorod", "pelorodan"]),
]
NARRATION_START = 80.0


def plan(duration: float) -> list[tuple[int, float, float]]:
    out, start, idx = [], 0.0, 0
    while True:
        end = min(start + WINDOW, duration)
        out.append((idx, start, end))
        if end >= duration:
            return out
        start += WINDOW - OVERLAP
        idx += 1


def has_variant(text: str, variants: list[str]) -> bool:
    low = f" {text.lower()} "
    return any(re.search(rf"(?<!\w){re.escape(v)}(?!\w)", low) for v in variants)


def dist(t: float, lo: float, hi: float) -> float:
    return 0.0 if lo <= t <= hi else min(abs(t - lo), abs(t - hi))


def main() -> None:
    src = find_video("7-WQ3DKKn0w")
    segments = plan(DURATION)
    found: list[dict] = []
    for idx, start, end in segments:
        clip = make_clip(src, start, end - start, OUT / "clips" / f"ngertibatik-seg{idx}.mp4")

        def call(clip=clip, idx=idx, start=start, end=end) -> dict:
            with client() as c:
                fid = upload(c, clip)
                prompt = build(idx + 1, len(segments), end - start)
                status, resp = post_json(c, "/responses", video_body(fid, prompt))
                if status >= 400:
                    raise RuntimeError(f"{status}: {str(resp)[:500]}")
                return resp

        parsed = parse_json(output_text(once(f"recall-seg{idx}.raw.json", call)))
        (OUT / f"recall-seg{idx}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=1))
        for t in parsed.get("terms", []):
            found.append({**t, "abs_t": float(t.get("t_start", 0)) + start, "seg": idx})
        print(f"seg{idx} {start:.0f}-{end:.0f}: {len(parsed.get('terms', []))} terms", flush=True)

    speech = [t for t in found if t.get("source") == "speech"]
    hits, dts = [], []
    for name, lo, hi, variants in GOLD:
        cands = [t for t in speech
                 if has_variant(f"{t.get('term', '')} {t.get('spoken', '')}", variants)
                 and dist(t["abs_t"], lo, hi) <= 5]
        if cands:
            best = min(cands, key=lambda t: dist(t["abs_t"], lo, hi))
            hits.append({"gold": name, "muse": best.get("term"), "t": round(best["abs_t"], 1)})
            dts.append(dist(best["abs_t"], lo, hi))
        else:
            near = [(t.get("term"), t.get("source"), round(t["abs_t"], 1)) for t in found
                    if has_variant(f"{t.get('term', '')} {t.get('spoken', '')}", variants)]
            hits.append({"gold": name, "muse": None, "nearest_any_source": near})
    n_hit = sum(1 for h in hits if h["muse"])
    summary = {
        "hits": hits,
        "recall": f"{n_hit}/8",
        "pass": n_hit >= 6,
        "median_dt": round(statistics.median(dts), 1) if dts else None,
        "speech_before_80s": [(t.get("term"), round(t["abs_t"], 1)) for t in speech
                              if t["abs_t"] < NARRATION_START],
        "n_terms_total": len(found),
        "by_source": {s: sum(1 for t in found if t.get("source") == s)
                      for s in ("speech", "on_screen_text", "visual_only")},
    }
    (OUT / "recall.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
