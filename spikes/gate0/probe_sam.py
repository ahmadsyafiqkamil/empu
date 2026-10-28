"""Gate 0.3 (rerun): SAM 3.1 with descriptive English prompts on clean close-ups.

Request shape proven earlier (docs/reference/uji-kelayakan/uji_sam.py): Responses API,
content = [input_text prompt, input_image data URL]. Output text contains tokens like
<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;...|>. Decision 28 Oct: bbox only.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

from common import OUT, REPO, client, extract_frame, find_video, once, output_text, post_json

MODEL = "sam-3.1"
SAM_OUT = OUT / "sam"
BOX = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
CANTING = ["pen with wooden handle", "small copper cup on a wooden stick", "wooden stick with copper tip"]
OLD_KEYFRAME = REPO / "docs" / "reference" / "uji-kelayakan" / "klip" / "canting-keyframe.jpg"
# (name, youtube_id or None for OLD_KEYFRAME, seconds, prompts)
FRAMES = [
    ("canting-closeup-50", "71EDWiILmv0", 50.0, CANTING),
    ("canting-closeup-100", "71EDWiILmv0", 100.0, CANTING),
    ("canting-closeup-125", "71EDWiILmv0", 125.0, CANTING),
    ("canting-row", None, 0.0, CANTING[1:]),
    ("wajan", "7-WQ3DKKn0w", 100.0, ["small black wok", "small stove"]),
]


def boxes_in(text: str) -> list[tuple[int, int, int, int, int, int]]:
    return [tuple(map(int, m.groups())) for m in BOX.finditer(text)]


def draw(image: Path, boxes: list, dst: Path) -> None:
    im = Image.open(image).convert("RGB")
    d = ImageDraw.Draw(im)
    for x1, y1, x2, y2, w, h in boxes:
        sx, sy = im.size[0] / w, im.size[1] / h
        d.rectangle([x1 * sx, y1 * sy, x2 * sx, y2 * sy], outline=(255, 0, 0), width=4)
    im.save(dst, quality=90)


def main() -> None:
    SAM_OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    with client() as c:
        for name, yt, t, prompts in FRAMES:
            frame = OLD_KEYFRAME if yt is None else extract_frame(find_video(yt), t, SAM_OUT / f"{name}.jpg")
            data_url = "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode()
            for i, prompt in enumerate(prompts):
                tag = f"{name}.p{i}"

                def call(prompt=prompt, data_url=data_url) -> dict:
                    body = {"model": MODEL, "stream": False, "input": [{"role": "user", "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ]}]}
                    status, resp = post_json(c, "/responses", body)
                    return {"status": status, "response": resp}

                raw = once(f"sam/{tag}.raw.json", call)
                text = output_text(raw["response"]) if isinstance(raw["response"], dict) else ""
                boxes = boxes_in(text)
                draw(frame, boxes, SAM_OUT / f"{tag}.boxes.jpg")
                summary.append({"frame": name, "prompt": prompt, "status": raw["status"],
                                "n_boxes": len(boxes), "boxes": boxes[:4]})
                print(f"{tag:28s} {raw['status']} boxes={len(boxes)} '{prompt}'", flush=True)
    (OUT / "sam.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
