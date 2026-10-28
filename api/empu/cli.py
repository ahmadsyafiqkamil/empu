"""Command line entry point: `empu analyze` (H1). Later phases add sub-commands."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import typer

from empu.cache import ResponseCache
from empu.config import Settings, get_settings
from empu.meta_client import MetaClient
from empu.packs import PackError, load_pack
from empu.pipeline.analyze import AnalyzeOptions, ChunkAnalysis, analyze_chunks, usage_totals
from empu.pipeline.chunk import cut_chunks, plan_chunks
from empu.pipeline.normalize import normalize_recording
from empu.pipeline.prompts import prompt_version_for

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """Empu: craft dictionary pipeline."""


def make_client(settings: Settings) -> MetaClient:
    return MetaClient.from_settings(settings)


def _chunk_row(r: ChunkAnalysis) -> dict:
    by_source = Counter(t.source.value for t in (r.output.terms if r.output else []))
    return {
        "idx": r.spec.idx,
        "start_s": r.spec.start_s,
        "end_s": r.spec.end_s,
        "n_terms": sum(by_source.values()),
        "by_source": {k: by_source.get(k, 0) for k in ("speech", "on_screen_text", "visual_only")},
        "cached": r.cached,
        "latency_s": round(r.latency_s, 1),
        "dropped": r.dropped,
        "error": r.error,
    }


@app.command()
def analyze(
    video: Path = typer.Argument(..., exists=True, dir_okay=False),
    pack_id: str = typer.Option(..., "--pack"),
    out: Path = typer.Option(..., "--out"),
    seeds: bool = typer.Option(True, "--seeds/--no-seeds"),
    strip_audio: bool = typer.Option(False, "--strip-audio"),
    structured: bool | None = typer.Option(None, "--structured/--no-structured"),
    max_chunks: int | None = typer.Option(None, "--max-chunks"),
) -> None:
    """Normalize, chunk and analyze one video with Muse. Writes JSON per chunk."""
    settings = get_settings()
    try:
        pack = load_pack(pack_id, settings.packs_dir)
    except PackError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e
    t0 = time.monotonic()
    media = normalize_recording(video, out / "media", strip_audio=strip_audio)
    specs = plan_chunks(media.duration_s, settings.chunk_window_s, settings.chunk_overlap_s)
    specs = specs[:max_chunks] if max_chunks else specs
    paths = cut_chunks(media.analysis_path, specs, out / "chunks")
    opts = AnalyzeOptions(
        model=settings.muse_model,
        seeds=seeds,
        structured=settings.structured_output if structured is None else structured,
        schema_variant=settings.structured_schema_variant,
    )
    client = make_client(settings)
    cache = ResponseCache(settings.data_dir / "cache" / "muse")

    def report(r: ChunkAnalysis) -> None:
        row = _chunk_row(r)
        typer.echo(
            f"chunk {row['idx']} {row['start_s']:.0f}-{row['end_s']:.0f}s terms={row['n_terms']} "
            f"{row['by_source']} cached={row['cached']} {row['latency_s']}s"
            + (f" ERROR {row['error']}" if row["error"] else "")
        )

    results = analyze_chunks(
        client,
        cache,
        pack,
        list(zip(specs, paths, strict=True)),
        opts,
        out_dir=out / "muse",
        concurrency=settings.analyze_concurrency,
        on_done=report,
    )
    summary = {
        "video": video.name,
        "pack": f"{pack.id}@{pack.version}",
        "model": opts.model,
        "prompt_version": prompt_version_for(seeds),
        "duration_s": round(media.duration_s, 2),
        "strip_audio": strip_audio,
        "chunks": [_chunk_row(r) for r in results],
        "usage": usage_totals([r.usage for r in results if not r.cached]),
        "wall_s": round(time.monotonic() - t0, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    failed = [r.spec.idx for r in results if r.error]
    typer.echo(f"done: {len(results)} chunks, failed={failed}, wall={summary['wall_s']}s -> {out}")
    if failed:
        raise typer.Exit(1)
