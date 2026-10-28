"""Per-segment Muse analysis with raw-response cache, one repair retry, and parallelism."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from empu.cache import ResponseCache, sha256_file
from empu.meta_client import MetaAPIError, TranscriptSegment, extract_json, output_text
from empu.muse_schema import MuseProcessStep, MuseSegmentOutput, MuseTerm, load_json_schema
from empu.packs import CraftPack
from empu.pipeline.chunk import ChunkSpec
from empu.pipeline.prompts import build_prompt, prompt_version_for

RETRY_SUFFIX = (
    "\n\nJawaban sebelumnya tidak valid: {error}\n"
    "Ulangi. Jawab HANYA dengan satu objek JSON sesuai skema di atas."
)
NO_JSON = "no JSON object in model output"


@dataclass(frozen=True)
class AnalyzeOptions:
    model: str
    seeds: bool = True
    structured: bool = False
    schema_variant: Literal["full", "stripped"] = "full"
    max_output_tokens: int = 16000


@dataclass
class ChunkAnalysis:
    spec: ChunkSpec
    path: Path
    sha256: str
    cache_key: str
    prompt_version: str
    output: MuseSegmentOutput | None
    raw_path: Path | None
    parsed_path: Path | None
    usage: dict
    latency_s: float
    file_id: str | None
    cached: bool
    attempts: int
    dropped: int
    error: str | None


def coerce_segment(parsed: dict | None) -> tuple[MuseSegmentOutput | None, int, str | None]:
    if parsed is None:
        return None, 0, NO_JSON
    if not isinstance(parsed.get("terms"), list):
        return None, 0, "missing 'terms' list"
    dropped = 0
    items: dict[str, list[Any]] = {"terms": [], "process_steps": []}
    for key, model in (("terms", MuseTerm), ("process_steps", MuseProcessStep)):
        for raw in parsed.get(key) or []:
            try:
                items[key].append(model.model_validate(raw))
            except ValidationError:
                dropped += 1
    try:
        out = MuseSegmentOutput.model_validate({**parsed, "terms": [], "process_steps": []})
    except ValidationError as e:
        return None, 0, str(e)[:1000]
    out.terms, out.process_steps = items["terms"], items["process_steps"]
    return out, dropped, None


def usage_totals(usages: list[dict]) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    for u in usages:
        total["input_tokens"] += int(u.get("input_tokens") or 0)
        total["output_tokens"] += int(u.get("output_tokens") or 0)
        details = u.get("output_tokens_details") or {}
        total["reasoning_tokens"] += int(
            details.get("reasoning_tokens") or u.get("reasoning_tokens") or 0
        )
    return total


def _write_json(path: Path, obj: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    return path


def analyze_chunk(
    client: Any,
    cache: ResponseCache,
    pack: CraftPack,
    spec: ChunkSpec,
    path: Path,
    opts: AnalyzeOptions,
    *,
    seg_total: int,
    out_dir: Path,
    transcript: list[TranscriptSegment] | None = None,
) -> ChunkAnalysis:
    sha = sha256_file(path)
    version = prompt_version_for(opts.seeds, transcript=bool(transcript))
    request_mode = "B" if transcript else "A"
    key = ResponseCache.key(sha, opts.model, version, request_mode)
    raw_path, parsed_path = out_dir / f"{spec.idx}.raw.json", out_dir / f"{spec.idx}.json"

    def result(output, raw, usage, latency, file_id, cached, attempts, dropped, error):
        if raw is not None:
            _write_json(raw_path, raw)
        if output is not None:
            _write_json(parsed_path, output.model_dump(mode="json"))
        return ChunkAnalysis(
            spec,
            Path(path),
            sha,
            key,
            version,
            output,
            raw_path if raw is not None else None,
            parsed_path if output is not None else None,
            usage,
            latency,
            file_id,
            cached,
            attempts,
            dropped,
            error,
        )

    if (hit := cache.get(key)) is not None:
        output, dropped, err = coerce_segment(_parse_raw(hit["raw"]))
        return result(
            output,
            hit["raw"],
            hit.get("usage", {}),
            hit.get("latency_s", 0.0),
            hit.get("file_id"),
            True,
            hit.get("attempts", 1),
            dropped,
            err,
        )

    prompt = build_prompt(
        pack,
        seg_index=spec.idx + 1,
        seg_total=seg_total,
        seg_duration=spec.duration_s,
        seeds=opts.seeds,
        transcript=transcript,
    )
    schema = load_json_schema(opts.schema_variant) if opts.structured else None
    usages: list[dict] = []
    latency, file_id, raw, err = 0.0, None, None, None
    try:
        file_id = client.upload_file(path)
        for attempt in (1, 2):
            text = prompt if attempt == 1 else prompt + RETRY_SUFFIX.format(error=err)
            res = client.analyze_video(
                file_id,
                text,
                model=opts.model,
                schema=schema,
                max_output_tokens=opts.max_output_tokens,
            )
            usages.append(res.usage)
            latency += res.latency_s
            raw = res.raw
            output, dropped, err = coerce_segment(res.parsed)
            if output is None and err == NO_JSON and res.parse_error:
                err = res.parse_error
            if output is not None:
                usage = usage_totals(usages)
                cache.put(
                    key,
                    {
                        "raw": raw,
                        "usage": usage,
                        "latency_s": latency,
                        "file_id": file_id,
                        "model": opts.model,
                        "prompt_version": version,
                        "mode": request_mode,
                        "attempts": attempt,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
                return result(output, raw, usage, latency, file_id, False, attempt, dropped, None)
        return result(None, raw, usage_totals(usages), latency, file_id, False, 2, 0, err)
    except (MetaAPIError, httpx.HTTPError) as e:
        return result(
            None,
            raw,
            usage_totals(usages),
            latency,
            file_id,
            False,
            len(usages),
            0,
            str(e),
        )


def _parse_raw(raw: dict) -> dict | None:
    try:
        return extract_json(output_text(raw))
    except ValueError:
        return None


def analyze_chunks(
    client: Any,
    cache: ResponseCache,
    pack: CraftPack,
    items: list[tuple[ChunkSpec, Path]],
    opts: AnalyzeOptions,
    *,
    out_dir: Path,
    concurrency: int = 3,
    on_done: Callable[[ChunkAnalysis], None] | None = None,
    transcripts: dict[int, list[TranscriptSegment]] | None = None,
) -> list[ChunkAnalysis]:
    total = len(items)
    results: list[ChunkAnalysis] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [
            pool.submit(
                analyze_chunk,
                client,
                cache,
                pack,
                spec,
                path,
                opts,
                seg_total=total,
                out_dir=out_dir,
                transcript=(transcripts or {}).get(spec.idx),
            )
            for spec, path in items
        ]
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            if on_done is not None:
                on_done(res)
    return sorted(results, key=lambda r: r.spec.idx)
