"""SAM 3.1 grounding on one keyframe. Bounding box only (Gate 0); crop = bbox + 15% padding."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw

from empu.cache import ResponseCache, sha256_file
from empu.enums import SamStatus
from empu.meta_client import Detection, MetaAPIError, output_text, parse_sam_boxes
from empu.packs import CraftPack

PAD = 0.15


@dataclass
class GroundResult:
    status: SamStatus
    prompt_used: str | None
    detections: list[Detection] = field(default_factory=list)
    crop_path: Path | None = None
    overlay_path: Path | None = None
    error: str | None = None


def sam_prompts_for(
    pack: CraftPack, *, pack_term_id: str | None, is_novel: bool, visible_object_en: str | None
) -> list[str]:
    if pack_term_id:
        t = pack.term(pack_term_id)
        if t is None or not t.visual or not t.sam_prompt:
            return []
        return [p.strip() for p in t.sam_prompt.split(",") if p.strip()]
    if is_novel and visible_object_en and visible_object_en.strip():
        return [visible_object_en.strip()]
    return []


def crop_box(
    size: tuple[int, int], bbox: tuple[float, float, float, float], pad: float = PAD
) -> tuple[int, int, int, int]:
    w, h = size
    x1, y1, x2, y2 = bbox[0] * w, bbox[1] * h, bbox[2] * w, bbox[3] * h
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    return (
        max(0, int(x1 - px)),
        max(0, int(y1 - py)),
        min(w, round(x2 + px)),
        min(h, round(y2 + py)),
    )


def _area(d: Detection) -> float:
    x1, y1, x2, y2 = d.bbox_xyxy
    return (x2 - x1) * (y2 - y1)


def _raw_for(
    client: Any, cache: ResponseCache, keyframe: Path, sha: str, prompt: str, model: str
) -> dict:
    sam_id = "sam-" + hashlib.sha1(prompt.encode()).hexdigest()[:10]
    key = ResponseCache.key(sha, model, sam_id, "img")
    if (hit := cache.get(key)) is not None:
        return hit["raw"]
    raw = client.segment_image_raw(keyframe, prompt, model=model)
    cache.put(key, {"raw": raw, "prompt": prompt, "model": model})
    return raw


def ground_keyframe(
    client: Any,
    cache: ResponseCache,
    keyframe: Path,
    prompts: list[str],
    out_dir: Path,
    *,
    model: str,
) -> GroundResult:
    if not prompts:
        return GroundResult(SamStatus.skipped, None)
    try:
        sha = sha256_file(keyframe)
        used, dets = None, []
        for prompt in prompts:
            raw = _raw_for(client, cache, keyframe, sha, prompt, model)
            dets = parse_sam_boxes(output_text(raw), prompt)
            if dets:
                used = prompt
                break
        if not dets:
            return GroundResult(SamStatus.empty, None)
        chosen = max(dets, key=_area)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        crop_path, overlay_path = out_dir / "crop.png", out_dir / "overlay.jpg"
        with Image.open(keyframe) as src:
            im = src.convert("RGB")
        im.crop(crop_box(im.size, chosen.bbox_xyxy)).save(crop_path)
        draw = ImageDraw.Draw(im)
        w, h = im.size
        for d in dets:
            x1, y1, x2, y2 = d.bbox_xyxy
            draw.rectangle(
                [x1 * w, y1 * h, x2 * w, y2 * h],
                outline=(255, 196, 0),
                width=6 if d is chosen else 2,
            )
        im.save(overlay_path, quality=88)
        return GroundResult(SamStatus.ok, used, dets, crop_path, overlay_path)
    except (MetaAPIError, httpx.HTTPError, OSError) as e:
        return GroundResult(SamStatus.error, None, error=str(e)[:500])
