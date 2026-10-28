"""Command line entry point: `empu analyze` (H1). Later phases add sub-commands."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import typer
from sqlmodel import Session, col, func, select

from empu.cache import ResponseCache
from empu.config import Settings, get_settings
from empu.db import init_db, make_engine
from empu.enums import AccessLevel, ContributorRole, PipelineMode, SourceKind
from empu.intake import (
    IntakeError,
    RecordingMeta,
    create_recording,
    enqueue_job,
    get_or_create_archive,
    meta_from_license_file,
)
from empu.meta_client import MetaClient
from empu.models import Archive, Entry, Job, Occurrence, Recording
from empu.packs import PackError, list_packs, load_pack
from empu.pipeline.analyze import AnalyzeOptions, ChunkAnalysis, analyze_chunks, usage_totals
from empu.pipeline.chunk import cut_chunks, plan_chunks
from empu.pipeline.normalize import normalize_recording
from empu.pipeline.prompts import prompt_version_for
from empu.pipeline.run import process_recording

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """Empu: craft dictionary pipeline."""


def make_client(settings: Settings) -> MetaClient:
    return MetaClient.from_settings(settings)


def _default_pack_id(settings: Settings) -> str:
    ids = sorted(p.id for p in list_packs(settings.packs_dir))
    if not ids:
        typer.echo("error: no craft packs found", err=True)
        raise typer.Exit(2)
    return ids[0]


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


db_app = typer.Typer(no_args_is_help=True)
app.add_typer(db_app, name="db", help="Database commands.")


def _engine(settings: Settings):
    engine = make_engine(settings.db_url)
    init_db(engine)
    return engine


@db_app.command("init")
def db_init(reset: bool = typer.Option(False, "--reset", help="Drop all tables first.")) -> None:
    settings = get_settings()
    init_db(make_engine(settings.db_url), reset=reset)
    typer.echo(f"database ready: {settings.db_url}")


def _run_job(settings: Settings, session: Session, job_id: int) -> None:
    process_recording(session, job_id, client=make_client(settings), settings=settings)
    job = session.get(Job, job_id)
    typer.echo(f"job {job.id}: {job.status.value} {job.error or ''}")
    typer.echo(
        json.dumps(
            {
                "timings": {k: v.get("seconds") for k, v in job.timings_json.items()},
                "usage": job.usage_json,
            },
            ensure_ascii=False,
        )
    )
    if job.status.value != "ready":
        raise typer.Exit(1)


@app.command()
def ingest(
    video: Path = typer.Argument(..., exists=True, dir_okay=False),
    archive: str = typer.Option(..., "--archive", help="Archive slug (created if missing)."),
    archive_title: str | None = typer.Option(None, "--archive-title"),
    pack_id: str | None = typer.Option(
        None, "--pack", help="Craft pack id (default: sole pack on disk)."
    ),
    title: str | None = typer.Option(None, "--title"),
    license_file: Path | None = typer.Option(
        None,
        "--license-file",
        exists=True,
        help="docs/eval/lisensi/<id>.json for a CC BY video.",
    ),
    contributor: str | None = typer.Option(None, "--contributor"),
    role: ContributorRole = typer.Option(ContributorRole.maestro, "--role"),
    consent_confirmed: bool = typer.Option(False, "--consent-confirmed"),
    consent_scope: AccessLevel = typer.Option(AccessLevel.public, "--consent-scope"),
    consent_note: str = typer.Option("", "--consent-note"),
    consent_evidence: str = typer.Option("", "--consent-evidence"),
    source_kind: SourceKind = typer.Option(SourceKind.own_recording, "--source-kind"),
    mode: PipelineMode | None = typer.Option(None, "--mode"),
    demo: bool = typer.Option(False, "--demo", help="Mark the archive as the pinned demo archive."),
    run: bool = typer.Option(False, "--run", help="Process now instead of waiting for the worker."),
) -> None:
    """Register a recording with consent metadata and queue (or run) its job."""
    settings = get_settings()
    try:
        if license_file is not None:
            meta = meta_from_license_file(license_file, contributor_name=contributor)
            meta.title = title or meta.title
        else:
            meta = RecordingMeta(
                title=title or video.stem,
                contributor_name=contributor,
                contributor_role=role,
                consent_confirmed=consent_confirmed,
                consent_scope=consent_scope,
                consent_note=consent_note,
                consent_evidence=consent_evidence,
                source_kind=source_kind,
            )
        with Session(_engine(settings)) as session:
            arc = get_or_create_archive(
                session,
                archive,
                title=archive_title or archive,
                pack_id=pack_id or _default_pack_id(settings),
                is_demo=demo,
            )
            rec, job = create_recording(session, settings, arc, video, meta, mode=mode)
            typer.echo(
                f"recording {rec.id} in archive {arc.slug}, job {job.id} queued "
                f"(mode {job.mode.value})"
            )
            if run:
                _run_job(settings, session, job.id)
    except IntakeError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e


@app.command()
def reprocess(
    recording_id: int,
    mode: PipelineMode | None = typer.Option(None, "--mode"),
    run: bool = typer.Option(False, "--run"),
) -> None:
    """Queue a new job for an existing recording (Muse and SAM come from cache when unchanged)."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        rec = session.get(Recording, recording_id)
        if rec is None:
            typer.echo(f"error: recording {recording_id} not found", err=True)
            raise typer.Exit(2)
        job = enqueue_job(session, settings, rec, mode=mode)
        typer.echo(f"job {job.id} queued for recording {rec.id}")
        if run:
            _run_job(settings, session, job.id)


@app.command("process")
def process_cmd(job_id: int) -> None:
    """Run one queued job in this process (debugging)."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        _run_job(settings, session, job_id)


@app.command()
def status(archive: str | None = typer.Option(None, "--archive")) -> None:
    """Print recordings, latest job, and entry counts."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        q = select(Archive)
        if archive:
            q = q.where(Archive.slug == archive)
        for arc in session.exec(q):
            ents = list(session.exec(select(Entry).where(Entry.archive_id == arc.id)))
            by_status = Counter(e.status.value for e in ents)
            by_sam = Counter(e.sam_status.value for e in ents)
            typer.echo(
                f"[{arc.slug}] entries={len(ents)} {dict(by_status)} sam={dict(by_sam)} "
                f"novel={sum(e.is_novel for e in ents)}"
            )
            for rec in session.exec(select(Recording).where(Recording.archive_id == arc.id)):
                job = session.exec(
                    select(Job).where(Job.recording_id == rec.id).order_by(col(Job.id).desc())
                ).first()
                n_occ = session.exec(
                    select(func.count())
                    .select_from(Occurrence)
                    .where(Occurrence.recording_id == rec.id)
                ).one()
                job_txt = f"{job.id}:{job.status.value} {job.detail}" if job else "-"
                typer.echo(
                    f"  rec {rec.id} '{rec.title}' {rec.status.value} occ={n_occ} job={job_txt}"
                )
