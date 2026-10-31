"""Command line entry point: `empu analyze` (H1). Later phases add sub-commands."""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml
from sqlmodel import Session, col, func, select

from empu.ask import collect_entries, read_questions, warm_questions
from empu.ask.engine import pack_display_name
from empu.ask.index import build_index
from empu.ask.prompts import RESPONSE_SCHEMA
from empu.cache import ResponseCache
from empu.config import REPO_ROOT, Settings, get_settings
from empu.db import init_db, make_engine
from empu.enums import AccessLevel, ContributorRole, PipelineMode, Source, SourceKind
from empu.evaluation.baseline import baseline_against_pack, parse_vtt
from empu.evaluation.gold import load_gold
from empu.evaluation.retrieval import evaluate_retrieval, load_questions
from empu.evaluation.runner import pred_from_db, run_clip, write_results
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


eval_app = typer.Typer(no_args_is_help=True)
app.add_typer(eval_app, name="eval", help="Evaluation commands.")

GOLD_FIELDS = [
    "clip_id",
    "t_start",
    "t_end",
    "spoken",
    "term",
    "category",
    "source",
    "stage",
    "visible_object",
    "note",
    "annotator",
]


def _clips_from_set(set_path: Path) -> list[dict]:
    data = yaml.safe_load(set_path.read_text(encoding="utf-8")) or {}
    out: list[dict] = []
    for item in data.get("clips") or []:
        if isinstance(item, dict) and item.get("id"):
            out.append(item)
    for item in data.get("demo_cc_by") or []:
        if isinstance(item, dict) and item.get("id"):
            out.append(item)
    return out


def _clip_by_id(set_path: Path, clip_id: str) -> dict | None:
    return next((i for i in _clips_from_set(set_path) if i.get("id") == clip_id), None)


def _find_recording_by_youtube(session: Session, youtube_id: str | None) -> Recording | None:
    if not youtube_id:
        return None
    for rec in session.exec(select(Recording)):
        if rec.source_url and youtube_id in rec.source_url:
            return rec
    return None


def _find_vtt(testdata_dir: Path, youtube_id: str | None) -> Path | None:
    if not youtube_id:
        return None
    root = Path(testdata_dir)
    if not root.exists():
        return None
    for suffix in (".id.vtt", ".id-orig.vtt", ".vtt"):
        for p in root.rglob(f"*[{youtube_id}]*{suffix}"):
            return p
    return None


def _gold_path(item: dict, gold_dir: Path) -> Path | None:
    """Resolve a clip's gold CSV. Returns None for an explicit control clip
    (gold: null) or when the file is absent."""
    if "gold" not in item:
        p = Path(gold_dir) / f"{item['id']}.csv"
        return p if p.is_file() else None
    raw = item["gold"]
    if raw is None:
        return None  # control clip
    p = Path(str(raw))
    if not p.is_absolute():
        p = REPO_ROOT / str(raw)
    return p if p.is_file() else None


def _aggregate(clips: dict) -> dict:
    def _mean(key: str) -> float | None:
        vals = [m[key] for m in clips.values() if isinstance(m, dict) and m.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "speech_recall": _mean("speech_recall"),
        "speech_precision": _mean("speech_precision"),
        "median_time_error_s": _mean("median_time_error_s"),
        "source_accuracy": _mean("source_accuracy"),
    }


@eval_app.command("run")
def eval_run(
    set_path: Path = typer.Option(..., "--set", exists=True, dir_okay=False),
    gold_dir: Path = typer.Option(..., "--gold", exists=True, file_okay=False),
    out: Path = typer.Option(..., "--out"),
) -> None:
    """Score every clip in a test-set against gold and write an aggregate JSON."""
    settings = get_settings()
    pack = load_pack(_default_pack_id(settings), settings.packs_dir)
    clips: dict = {}
    notes: list[str] = []
    with Session(_engine(settings)) as session:
        for item in _clips_from_set(set_path):
            cid = item["id"]
            rec = _find_recording_by_youtube(session, item.get("youtube_id"))
            pred = pred_from_db(session, rec.id) if rec else []
            gold_path = _gold_path(item, gold_dir)
            if gold_path is None:
                clips[cid] = {
                    "n_pred_speech": sum(1 for p in pred if p.source is Source.speech),
                    "n_pred": len(pred),
                }
                continue
            if rec is None:
                notes.append(f"{cid}: no recording matched youtube_id {item.get('youtube_id')}")
                clips[cid] = {"error": "no recording", "n_pred": 0}
                continue
            baseline = None
            vtt = _find_vtt(settings.testdata_dir, item.get("youtube_id"))
            if vtt is not None:
                baseline = baseline_against_pack(parse_vtt(vtt), pack)
            clips[cid] = run_clip(load_gold(gold_path), pred, pack, baseline=baseline)
    payload = {
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pack": f"{pack.id}@{pack.version}",
        "mode": settings.pipeline_mode,
        "clips": clips,
        "aggregate": _aggregate(clips),
        "notes": notes,
    }
    write_results(out, payload)
    typer.echo(f"wrote {out}: {len(clips)} clips")


@eval_app.command("draft-gold")
def draft_gold(
    clip_id: str = typer.Argument(...),
    set_path: Path = typer.Option(None, "--set", exists=True, dir_okay=False),
    out: Path = typer.Option(None, "--out"),
) -> None:
    """Draft a gold answer-key CSV from a clip's DB occurrences (annotator=DRAFT)."""
    settings = get_settings()
    set_path = set_path or REPO_ROOT / "docs" / "eval" / "test-set.yaml"
    if not set_path.is_file():
        typer.echo(f"error: test set not found: {set_path}", err=True)
        raise typer.Exit(2)
    item = _clip_by_id(set_path, clip_id)
    if item is None:
        typer.echo(f"error: clip {clip_id!r} not found in {set_path}", err=True)
        raise typer.Exit(2)
    with Session(_engine(settings)) as session:
        rec = _find_recording_by_youtube(session, item.get("youtube_id"))
        if rec is None:
            typer.echo(
                f"error: no recording for {clip_id!r} (youtube {item.get('youtube_id')})",
                err=True,
            )
            raise typer.Exit(2)
        rows = []
        for o in session.exec(select(Occurrence).where(Occurrence.recording_id == rec.id)):
            e = session.get(Entry, o.entry_id)
            if e is None:
                continue
            rows.append(
                {
                    "clip_id": clip_id,
                    "t_start": o.t_start,
                    "t_end": o.t_end,
                    "spoken": o.spoken or e.term,
                    "term": e.term,
                    "category": e.category.value,
                    "source": o.source.value,
                    "stage": o.stage_id or "",
                    "visible_object": o.visible_object_en or "",
                    "note": "DRAFT",
                    "annotator": "DRAFT",
                }
            )
    out = out or REPO_ROOT / "docs" / "eval" / "kunci-jawaban" / f"{clip_id}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GOLD_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    typer.echo(f"wrote {out}: {len(rows)} rows (annotator=DRAFT)")


@eval_app.command("retrieval")
def eval_retrieval(
    archive: str = typer.Option(..., "--archive", help="Archive slug."),
    questions: Path = typer.Option(..., "--questions", exists=True, dir_okay=False),
    scope: str = typer.Option("public", "--scope", help="public | studio"),
    k: int = typer.Option(4, "--k", help="How many ranked rows count as retrieved."),
) -> None:
    """Measure how often the entries a question needs survive ranking."""
    settings = get_settings()
    with Session(_engine(settings)) as session:
        arch = session.exec(select(Archive).where(Archive.slug == archive)).first()
        if arch is None:
            typer.echo(f"error: no archive with slug {archive!r}", err=True)
            raise typer.Exit(2)
        try:
            pairs = collect_entries(session, arch.id, scope)
        except ValueError as e:
            typer.echo(f"error: {e}", err=True)
            raise typer.Exit(2) from e
        rows = build_index(pairs)
    if not rows:
        typer.echo(f"error: no entries for scope {scope!r} in {archive!r}", err=True)
        raise typer.Exit(2)
    report = evaluate_retrieval(load_questions(questions), rows, k=k)
    typer.echo(
        f"rows={report.n_rows} k={report.k} questions={report.n_questions} "
        f"question_recall={report.question_recall:.2f} term_recall={report.term_recall:.2f}"
    )
    for miss in report.misses:
        missing = "|".join(miss["missing"])
        typer.echo(f"miss: {miss['question']} missing={missing} rank={miss['rank']}")


ask_app = typer.Typer(no_args_is_help=True)
app.add_typer(ask_app, name="ask", help="Ask Empu commands.")


@ask_app.command("warm")
def ask_warm(
    archive: str = typer.Option(..., "--archive", help="Archive slug."),
    questions: Path = typer.Option(..., "--questions", exists=True, dir_okay=False),
    scope: str = typer.Option("public", "--scope", help="public | studio"),
) -> None:
    """Answer the demo questions now and keep them in the same cache the server reads."""
    settings = get_settings()
    items = read_questions(questions)
    calls = 0
    with Session(_engine(settings)) as session:
        arch = session.exec(select(Archive).where(Archive.slug == archive)).first()
        if arch is None:
            typer.echo(f"error: archive not found: {archive}", err=True)
            raise typer.Exit(2)
        client = make_client(settings)
        model_name = settings.muse_model

        def ask(prompt: str):
            nonlocal calls
            calls += 1
            return client.respond_text(prompt, model=model_name, schema=RESPONSE_SCHEMA)

        results = warm_questions(
            session,
            archive_id=arch.id,
            questions=items,
            ask_model=ask,
            cache=ResponseCache(settings.data_dir / "cache" / "ask"),
            model=model_name,
            pack_name=pack_display_name(arch, settings),
            scope=scope,
        )
    for r in results:
        line = f"cached={r.cached} refused={r.refused} evidence={r.n_evidence} {r.question}"
        typer.echo(f"{line} error={r.error}" if r.error else line)
    warmed = sum(1 for r in results if r.error is None)
    typer.echo(f"warmed {warmed} of {len(results)} ({calls} model calls)")
