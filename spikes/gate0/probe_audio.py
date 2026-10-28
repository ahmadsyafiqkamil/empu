"""Gate 0.1 (rerun): #NgertiBatik narration 80-155 s, with and without audio.

The earlier nglowong test is confounded by burned-in karaoke subtitles. This segment has
narration and almost no on-screen text.
Pass: speech terms without audio <= 50% of speech terms with audio, AND the no-audio
transcript is not a near-copy of the with-audio transcript.
"""

from __future__ import annotations

import difflib
import json

from common import (OUT, client, find_video, make_clip, once, output_text, parse_json,
                    post_json, upload, video_body)
from prompt_v3 import build

START, DUR = 80.0, 75.0


def run_one(clip, name: str) -> dict:
    def call() -> dict:
        with client() as c:
            fid = upload(c, clip)
            status, resp = post_json(c, "/responses", video_body(fid, build(1, 1, DUR)))
            if status >= 400:
                raise RuntimeError(f"{status}: {str(resp)[:500]}")
            return resp

    return parse_json(output_text(once(f"{name}.raw.json", call)))


def summarize(parsed: dict) -> dict:
    terms = parsed.get("terms", [])
    speech = [t for t in terms if t.get("source") == "speech"]
    return {
        "speech_heard": parsed.get("speech_heard"),
        "transcript_excerpt": parsed.get("transcript_excerpt", ""),
        "n_terms": len(terms),
        "n_speech": len(speech),
        "speech_terms": [(t.get("term"), t.get("t_start")) for t in speech],
        "by_source": {s: sum(1 for t in terms if t.get("source") == s)
                      for s in ("speech", "on_screen_text", "visual_only")},
    }


def main() -> None:
    src = find_video("7-WQ3DKKn0w")
    with_audio = make_clip(src, START, DUR, OUT / "clips" / "ngertibatik-80-155.mp4")
    no_audio = make_clip(src, START, DUR, OUT / "clips" / "ngertibatik-80-155-noaudio.mp4", strip_audio=True)
    a = summarize(run_one(with_audio, "audio2-with"))
    b = summarize(run_one(no_audio, "audio2-without"))
    similarity = difflib.SequenceMatcher(None, a["transcript_excerpt"].lower(),
                                         b["transcript_excerpt"].lower()).ratio()
    ratio = (b["n_speech"] / a["n_speech"]) if a["n_speech"] else None
    verdict = bool(a["n_speech"]) and ratio is not None and ratio <= 0.5 and similarity < 0.6
    summary = {"with": a, "without": b, "speech_ratio": ratio,
               "transcript_similarity": round(similarity, 2), "muse_hears_audio": verdict}
    (OUT / "audio2.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
