"""Pipeline orchestrator: one job through all stages; progress on job row (spec 8, D7)."""

from __future__ import annotations

import shutil
import time
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from empu.cache import ResponseCache
from empu.config import Settings
from empu.enums import ChunkStatus, JobStatus, PipelineMode, SamStatus, TimeSource
from empu.media import abs_from_rel, entry_dir, occurrence_dir, recording_dir, rel_to_data
from empu.models import Archive, Chunk, Entry, Job, Occurrence, Recording, utcnow
from empu.packs import CraftPack, load_pack
from empu.persist import persist_results
from empu.pipeline.analyze import AnalyzeOptions, ChunkAnalysis, analyze_chunks, usage_totals
from empu.pipeline.chunk import ChunkSpec, cut_chunks, plan_chunks
from empu.pipeline.evidence import extract_keyframe, make_evidence
from empu.pipeline.ffmpeg import has_audio, probe_duration
from empu.pipeline.ground import ground_keyframe, sam_prompts_for
from empu.pipeline.merge import merge_analyses
from empu.pipeline.normalize import normalize_recording
from empu.pipeline.process_map import build_process_map
from empu.pipeline.transcribe import (
    Transcriber,
    Word,
    realign,
    transcribe_cached,
    whisper_transcriber,
)

JOB_STAGES = (
    JobStatus.normalizing,
    JobStatus.chunking,
    JobStatus.analyzing,
    JobStatus.merging,
    JobStatus.grounding,
    JobStatus.cutting,
)
DEFAULT_ASR_MODEL = "small"


class PipelineError(RuntimeError):
    pass


class StageTracker:
    def __init__(self, session: Session, job: Job) -> None:
        self.session, self.job = session, job
        self.current: JobStatus | None = None
        self._t0 = 0.0

    def _commit(self) -> None:
        self.session.add(self.job)
        self.session.commit()

    def update(self, frac: float, detail: str | None = None) -> None:
        idx = JOB_STAGES.index(self.current) if self.current in JOB_STAGES else 0
        self.job.progress = round(min(1.0, (idx + max(0.0, min(1.0, frac))) / len(JOB_STAGES)), 3)
        if detail is not None:
            self.job.detail = detail
        self._commit()

    @contextmanager
    def stage(self, status: JobStatus) -> Iterator[None]:
        self.current, self._t0 = status, time.monotonic()
        self.job.status = status
        self.job.timings_json = {
            **self.job.timings_json,
            status.value: {"started_at": utcnow().isoformat(), "finished_at": None},
        }
        self.update(0.0, "")
        yield
        self.job.timings_json = {
            **self.job.timings_json,
            status.value: {
                **self.job.timings_json[status.value],
                "finished_at": utcnow().isoformat(),
                "seconds": round(time.monotonic() - self._t0, 1),
            },
        }
        self.update(1.0)


def _pack_for(session: Session, rec: Recording, settings: Settings) -> CraftPack:
    archive = session.get(Archive, rec.archive_id)
    if archive is None:
        raise PipelineError(f"archive {rec.archive_id} not found")
    return load_pack(archive.craft_pack_id, settings.packs_dir)


def _upsert_chunks(
    session: Session, rec: Recording, specs: list[ChunkSpec], paths: list[Path], data_dir: Path
) -> dict[int, Chunk]:
    existing = {c.idx: c for c in session.exec(select(Chunk).where(Chunk.recording_id == rec.id))}
    rows: dict[int, Chunk] = {}
    for spec, path in zip(specs, paths, strict=True):
        row = existing.pop(spec.idx, None) or Chunk(
            recording_id=rec.id, idx=spec.idx, start_s=0, end_s=0, path=""
        )
        row.start_s, row.end_s, row.path = spec.start_s, spec.end_s, rel_to_data(data_dir, path)
        row.status, row.error = ChunkStatus.pending, None
        session.add(row)
        rows[spec.idx] = row
    for stale in existing.values():
        session.delete(stale)
    session.commit()
    return rows


def _store_chunk_results(
    session: Session, rows: dict[int, Chunk], results: list[ChunkAnalysis], data_dir: Path
) -> None:
    for r in results:
        row = rows[r.spec.idx]
        row.sha256, row.file_id, row.cached = r.sha256, r.file_id, r.cached
        row.status = ChunkStatus.failed if r.error else ChunkStatus.done
        row.error, row.usage_json, row.latency_s = r.error, r.usage, r.latency_s
        row.raw_path = rel_to_data(data_dir, r.raw_path) if r.raw_path else None
        row.parsed_path = rel_to_data(data_dir, r.parsed_path) if r.parsed_path else None
        session.add(row)
    session.commit()


def _ground(
    session: Session,
    rec: Recording,
    entries: list[Entry],
    display: Path,
    *,
    client: Any,
    settings: Settings,
    pack: CraftPack,
    tracker: StageTracker,
) -> Counter:
    sam_cache = ResponseCache(settings.data_dir / "cache" / "sam")
    counts: Counter = Counter()
    for i, entry in enumerate(entries, start=1):
        best = (
            session.get(Occurrence, entry.best_occurrence_id) if entry.best_occurrence_id else None
        )
        if best is None or best.recording_id != rec.id:
            continue
        odir = occurrence_dir(settings.data_dir, rec.archive_id, rec.id, best.id)
        keyframe = extract_keyframe(display, (best.t_start + best.t_end) / 2, odir / "keyframe.jpg")
        best.keyframe_path = rel_to_data(settings.data_dir, keyframe)
        prompts = sam_prompts_for(
            pack,
            pack_term_id=entry.pack_term_id,
            is_novel=entry.is_novel,
            visible_object_en=best.visible_object_en,
        )
        if settings.sam_enabled and prompts:
            edir = entry_dir(settings.data_dir, rec.archive_id, entry.id)
            res = ground_keyframe(
                client, sam_cache, keyframe, prompts, edir, model=settings.sam_model
            )
            entry.sam_status, entry.sam_prompt = res.status, res.prompt_used or prompts[0]
            entry.crop_path = (
                rel_to_data(settings.data_dir, res.crop_path) if res.crop_path else None
            )
            entry.overlay_path = (
                rel_to_data(settings.data_dir, res.overlay_path) if res.overlay_path else None
            )
        else:
            entry.sam_status, entry.crop_path, entry.overlay_path = SamStatus.skipped, None, None
        counts[entry.sam_status.value] += 1
        session.add_all([best, entry])
        tracker.update(i / max(1, len(entries)), f"image {i}/{len(entries)}")
    session.commit()
    return counts


def _cut(
    session: Session, rec: Recording, display: Path, settings: Settings, tracker: StageTracker
) -> int:
    occs = list(
        session.exec(
            select(Occurrence).where(Occurrence.recording_id == rec.id).order_by(Occurrence.t_start)
        )
    )
    for i, o in enumerate(occs, start=1):
        ev = make_evidence(
            display,
            o.t_start,
            o.t_end,
            rec.duration_s or o.t_end,
            occurrence_dir(settings.data_dir, rec.archive_id, rec.id, o.id),
        )
        o.clip_path = rel_to_data(settings.data_dir, ev.clip)
        o.audio_path = rel_to_data(settings.data_dir, ev.audio) if ev.audio else None
        o.keyframe_path = rel_to_data(settings.data_dir, ev.keyframe)
        session.add(o)
        if i % 10 == 0 or i == len(occs):
            tracker.update(i / len(occs), f"clip {i}/{len(occs)}")
    session.commit()
    return len(occs)


def process_recording(
    session: Session,
    job_id: int,
    *,
    client: Any,
    settings: Settings,
    transcriber: Transcriber | None = None,
) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise PipelineError(f"job {job_id} not found")
    rec = session.get(Recording, job.recording_id)
    tracker = StageTracker(session, job)
    job.started_at = job.started_at or utcnow()
    job.error, job.usage_json, job.timings_json = None, {}, {}
    rec.status = JobStatus.normalizing
    session.add(rec)
    usage: dict[str, Any] = {"warnings": []}
    try:
        pack = _pack_for(session, rec, settings)
        data_dir = settings.data_dir
        rec_dir = recording_dir(data_dir, rec.archive_id, rec.id)

        with tracker.stage(JobStatus.normalizing):
            src = abs_from_rel(data_dir, rec.original_path)
            arch = session.get(Archive, rec.archive_id)
            if arch and arch.is_sandbox and probe_duration(src) > settings.sandbox_max_duration_s:
                raise PipelineError("sandbox recordings are limited to 3 minutes")
            media = normalize_recording(src, rec_dir)
            rec.display_path = rel_to_data(data_dir, media.display_path)
            rec.analysis_path = rel_to_data(data_dir, media.analysis_path)
            rec.duration_s = round(media.duration_s, 2)
            session.add(rec)

        with tracker.stage(JobStatus.chunking):
            specs = plan_chunks(media.duration_s, settings.chunk_window_s, settings.chunk_overlap_s)
            paths = cut_chunks(media.analysis_path, specs, rec_dir / "chunks")
            rows = _upsert_chunks(session, rec, specs, paths, data_dir)

        with tracker.stage(JobStatus.analyzing), ThreadPoolExecutor(max_workers=1) as pool:
            words_future: Future[list[Word]] | None = None
            if job.mode is PipelineMode.B and has_audio(media.display_path):
                model_name = settings.transcribe_model or DEFAULT_ASR_MODEL
                language = (rec.language_hint or "id").split(",")[0].strip() or "id"
                words_future = pool.submit(
                    transcribe_cached,
                    media.display_path,
                    transcriber or whisper_transcriber(model_name, language),
                    cache_root=data_dir / "cache" / "asr",
                    model_name=model_name,
                )
            done = 0

            def on_done(_: ChunkAnalysis) -> None:
                nonlocal done
                done += 1
                tracker.update(done / len(specs), f"segment {done}/{len(specs)}")

            opts = AnalyzeOptions(
                model=settings.muse_model,
                structured=settings.structured_output,
                schema_variant=settings.structured_schema_variant,
            )
            results = analyze_chunks(
                client,
                ResponseCache(data_dir / "cache" / "muse"),
                pack,
                list(zip(specs, paths, strict=True)),
                opts,
                out_dir=rec_dir / "muse",
                concurrency=settings.analyze_concurrency,
                on_done=on_done,
            )
            _store_chunk_results(session, rows, results, data_dir)
            usage["muse"] = usage_totals([r.usage for r in results if not r.cached])
            usage["cached_chunks"] = sum(r.cached for r in results)
            failed = [r for r in results if r.error]
            if failed:
                raise PipelineError(
                    f"{len(failed)}/{len(results)} segments failed: "
                    + "; ".join(f"#{r.spec.idx}: {r.error[:200]}" for r in failed)
                )
            words: list[Word] = []
            if words_future is not None:
                try:
                    words = words_future.result()
                except Exception as e:  # noqa: BLE001  (ASR is an aid; Mode B degrades to Muse times)
                    usage["warnings"].append(f"transcription failed, using Muse times: {e}"[:300])

        with tracker.stage(JobStatus.merging):
            shutil.rmtree(rec_dir / "occurrences", ignore_errors=True)
            steps = build_process_map(results, pack)
            retime = (lambda occs: realign(occs, words)) if words else None
            drafts = merge_analyses(results, pack, steps=steps, retime=retime)
            touched = persist_results(
                session, rec, drafts, steps, {i: r.id for i, r in rows.items()}
            )
            all_occs = [o for d in drafts for o in d.occurrences]
            usage |= {
                "entries": len(drafts),
                "novel": sum(d.canon.is_novel for d in drafts),
                "occurrences": len(all_occs),
                "asr_retimed": sum(o.time_source is TimeSource.asr for o in all_occs),
            }

        with tracker.stage(JobStatus.grounding):
            usage["sam"] = dict(
                _ground(
                    session,
                    rec,
                    touched,
                    media.display_path,
                    client=client,
                    settings=settings,
                    pack=pack,
                    tracker=tracker,
                )
            )

        with tracker.stage(JobStatus.cutting):
            _cut(session, rec, media.display_path, settings, tracker)

        job.status, job.progress, job.detail, job.finished_at = (
            JobStatus.ready,
            1.0,
            "ready",
            utcnow(),
        )
        job.usage_json = usage
        rec.status = JobStatus.ready
        session.add_all([job, rec])
        session.commit()
    except Exception as e:  # noqa: BLE001  (the worker must survive; the error is shown in S3)
        session.rollback()
        job = session.get(Job, job_id)
        rec = session.get(Recording, job.recording_id)
        stage = tracker.current.value if tracker.current else "setup"
        job.status, job.finished_at = JobStatus.failed, utcnow()
        job.error = f"{stage}: {type(e).__name__}: {e}"[:2000]
        job.usage_json = usage
        rec.status = JobStatus.failed
        session.add_all([job, rec])
        session.commit()
