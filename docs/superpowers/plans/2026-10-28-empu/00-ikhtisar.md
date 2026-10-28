# Empu: Ikhtisar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun Empu Edisi Batik Tulis (unggah rekaman berizin → pipeline Muse + SAM → Studio validasi → Kamus publik → ekspor → evaluasi jujur) dan mengirimkannya sebelum Rabu 4 Nov 2026, 22:00 WIB.

**Architecture:** Satu paket Python `empu` (di `api/`) berisi pustaka pipeline, server FastAPI, worker berbasis tabel `job`, dan CLI Typer. Semua panggilan Meta lewat `api/empu/meta_client.py` dengan cache respons mentah. Frontend Next.js (App Router) di `web/` memanggil API lewat rewrite same-origin. Deploy Docker Compose (web, api, worker, caddy).

**Tech Stack:** Python 3.12 (uv), FastAPI 0.16x, SQLModel + SQLite, Pydantic v2 + pydantic-settings, httpx, tenacity, rapidfuzz, pympi-ling, PyYAML, Pillow, Typer, pytest + respx, ruff. ffmpeg/ffprobe via subprocess. Next.js 16, TypeScript, Tailwind 4, vitest. Docker Compose + Caddy.

---

## Daftar file plan

| File | Hari | Isi | Gate |
|---|---|---|---|
| `00-ikhtisar.md` | – | Dokumen ini: konstanta global, peta file, kontrak antarmodul, gate, aturan potong | – |
| `h0-gate0-spike.md` | Rab 28 Okt | Init repo, akses video uji, spike Gate 0 (structured output, audio, recall, SAM, model transkripsi), catat keputusan | **Gate 0** |
| `h1-scaffold-pipeline-inti.md` | Kam 29 Okt | Scaffold `api/`, config, craft pack loader, skema Muse, `meta_client`, cache, normalisasi, segmen, prompt, analisis, CLI `empu analyze` | – |
| `h2-gabung-bukti-sam-worker.md` | Jum 30 Okt | Model DB, kanonisasi + dedup + entri, peta tahapan, klip/audio/keyframe, SAM, orkestrator, worker, Mode B (kondisional) | **Gate 1** |
| `h3-api-web-studio.md` | Sab 31 Okt | REST API inti, review, media Range, scaffold web, S2 Unggah, S3 Progres, S4 Studio | – |
| `h4-kamus-tahapan-ekspor.md` | Min 1 Nov | Aturan visibilitas publik, API publik, S1, S5 Kamus + detail, S6 Peta tahapan, ekspor JSON/CSV/ELAN/ZIP + S7 | – |
| `h5-evaluasi-bukti.md` | Sen 2 Nov | Kunci jawaban, `empu eval`, baseline ASR, ablasi, S8 Bukti, proses rekaman sanggar | **Gate 2** |
| `h6-izin-sandbox-deploy.md` | Sel 3 Nov | Cabut izin end-to-end, level akses, sandbox juri, arsip demo, polesan, Docker + Caddy, deploy VPS, README | – |
| `h7-demo-submission.md` | Rab 4 Nov | Video demo, teks submission, pemeriksaan akhir, kirim | **Kirim 22:00 WIB** |

Kerjakan berurutan. Setiap file berdiri sendiri: implementer cukup membaca `00-ikhtisar.md` + file fase yang sedang dikerjakan.

---

## Global Constraints

Berlaku untuk **setiap task** di semua fase. Disalin dari `CLAUDE.md` dan spec.

- Spec `docs/superpowers/specs/2026-10-28-empu-design.md` adalah sumber kebenaran. Kalau plan bertentangan dengan spec, spec menang.
- Ikuti gate di spec bagian 15. Kalau gate gagal, potong fitur sesuai urutan potong (di bawah), jangan memperpanjang jadwal.
- **Pengetahuan keterampilan hanya di craft pack.** Tidak boleh ada istilah batik (`canting`, `malam`, `nglorod`, dll.) di `api/empu/**`. Tes boleh memakai pack sungguhan sebagai fixture. Task H1-3 menambah tes `test_no_hardcoded_craft_terms`.
- **AI mengusulkan, manusia memutuskan.** Publik hanya jika `entry.status ∈ {accepted, edited}` **dan** `entry.access_level = public` **dan** rekaman sumber `consent_status = granted` **dan** `consent_scope = public`. Entri tanpa kemunculan publik ikut tersembunyi.
- **Label sumber** (`speech` / `on_screen_text` / `visual_only`) tidak boleh hilang di DB, API, UI, maupun ekspor.
- **Gambar hanya dari frame asli.** Tidak ada gambar buatan AI dalam bentuk apa pun.
- **Semua panggilan Meta API lewat `api/empu/meta_client.py`.** Cache respons mentah dengan kunci `sha256(segmen) + model + prompt_version + mode`. Kalau cache ada, jangan panggil API. (Pengecualian satu-satunya: skrip spike H0 di `spikes/gate0/`, yang tidak dipakai lagi setelah Gate 0.)
- **Rahasia:** `META_MODEL_API_KEY` dan `STUDIO_KEY` di `.env` root repo. Jangan dicetak, di-log, atau di-commit. Satu-satunya pembaca env di paket `empu` adalah `api/empu/config.py` (pakai `SecretStr`).
- **Data dan hak cipta:** jangan commit video, `data/`, `data-uji/`, `arsip-hidup-batik/`. Video YouTube berlisensi standar hanya untuk evaluasi internal (`source_kind = internal_eval`, tidak pernah publik). Video CC BY (`demo_cc_by`) boleh publik **dengan atribusi** (kreator, URL, lisensi, "dipotong") di halaman entri, ekspor, README, dan video demo.
- **Klaim validasi:** "divalidasi oleh ahli" hanya untuk entri dengan `review_event.actor` = kreator/ahli. Selain itu "divalidasi oleh pendokumentasi".
- **Tes tidak boleh memanggil API sungguhan.** Pakai fixture di `api/tests/fixtures/` dan `respx`/fake client.
- Setiap perubahan teks prompt menaikkan `PROMPT_VERSION`.
- Kode, identifier, nama tabel, enum, pesan commit: bahasa Inggris. Teks UI: bahasa Inggris (istilah keahlian tetap asli; glosa ID dan EN). Dokumen `docs/`: bahasa Indonesia.
- Batas unggah: 500 MB dan 20 menit per rekaman. Sandbox: 3 menit + kuota harian.
- Segmen default 75 detik, overlap 10 detik. Dedup overlap |Δt| ≤ 4 detik. Fuzzy kanonisasi rapidfuzz rasio ≥ 90. Klip bukti `t_start − 1,0` s.d. `t_end + 1,5`, min 3 s, maks 8 s. Padding crop SAM 15%.
- Retry Meta API: backoff eksponensial untuk 429 dan 5xx (dan error transport), maksimal 4 kali retry. 4xx lain tidak di-retry.
- Polling progres di frontend: setiap 2 detik.
- Kalau ada ambiguitas soal izin, akses publik, atau klaim ke juri: **tanya Syafiq**.

## Keputusan yang sudah diambil (28 Okt)

| # | Keputusan | Sumber |
|---|---|---|
| D1 | Semua default spec bagian 17 dipakai (repo baru di folder Empu, UI Inggris, Docker Compose di VPS, SQLite, `STUDIO_KEY`, Mode A sampai Gate 0 memutuskan) | Syafiq, 28 Okt |
| D2 | Gate 0 butir 2 memakai **prompt v3** (prompt produksi), bukan v2. Spec bagian 15 diperbarui di task H0-7 | Syafiq, 28 Okt |
| D3 | Ekspor `scope=all`: semua entri **kecuali** `rejected`/`merged`, termasuk `proposed` dan `private`; kemunculan dari rekaman yang izinnya dicabut **tetap dikecualikan**; status dan `access_level` tiap entri ikut diekspor. `scope=public` memakai aturan visibilitas publik | Syafiq, 28 Okt |
| D4 | Python dipin ke **3.12** lewat uv (mesin default 3.14; wheel seperti `ctranslate2` untuk faster-whisper sering tertinggal di versi Python terbaru) | Plan |
| D5 | Tabel `occurrence` menambah kolom `stage_id` (tahap pack hasil resolusi) dan `entry` menambah `canon_key` (kunci pengelompokan). Superset dari spec bagian 9, tidak menghapus kolom apa pun | Plan |
| D6 | `/media` di produksi: Caddy `file_server` dengan `forward_auth` ke `GET /api/media-auth` (cek visibilitas). Di dev: route FastAPI `/media/{path}` (Starlette `FileResponse` mendukung Range). Dua jalur memakai fungsi akses yang sama | Plan |
| D7 | Urutan status job tetap seperti spec: `normalizing → chunking → analyzing → merging → grounding → cutting → ready`. Karena SAM butuh keyframe, tahap `grounding` mengekstrak keyframe `best_occurrence` dulu; `cutting` membuat klip/audio/keyframe untuk semua kemunculan (keyframe yang sudah ada tidak dibuat ulang) | Plan |
| D9 | **Demo memakai video YouTube CC BY dengan atribusi**, bukan rekaman sanggar (rekam sanggar opsional). `recording` menambah `source_kind` (`own_recording`/`cc_by_video`/`internal_eval`), `source_url`, `source_creator`, `license`, `attribution`. `internal_eval` tidak pernah publik. Klaim "divalidasi oleh ahli" hanya untuk entri yang dicek kreator. Daftar video: `docs/eval/test-set.yaml` bagian `demo_cc_by` | Syafiq, 28 Okt (spec sudah diperbarui) |
| D10 | **Mode B = koreksi waktu (realign).** Muse dipanggil seperti Mode A; `evidence_quote` istilah `speech` dicocokkan (rapidfuzz `partial_ratio` ≥ 80, jendela ±30 s) ke transkrip faster-whisper per kata untuk mengganti `t_start`/`t_end`. Kolom baru `occurrence.time_source` (`asr`/`muse`). Varian transkrip-di-prompt hanya untuk ablasi. Structured output aktif (skema penuh). SAM: bbox saja, prompt deskripsi Inggris | Syafiq + Gate 0, 28 Okt |
| D8 | `speech_heard` dari Muse **tidak dipercaya** sebagai sinyal. Di uji v1, klip kontrol yang hanya musik menghasilkan `speech_heard: true` padahal transkripnya "tidak ada ucapan". Metrik halusinasi dihitung dari jumlah istilah `speech`, bukan dari `speech_heard` | Plan (dari `hasil-v1/kontrol-musik-nglorod.json`) |

---

## Peta file (akhir H7)

```
Empu/
├── .env                         # rahasia, TIDAK di-commit
├── .env.example                 # H1
├── .gitignore                   # H0
├── CLAUDE.md                    # bagian "Perintah" diisi di H1, status diperbarui tiap fase
├── README.md                    # H6
├── packs/batik_tulis.yaml       # H1 (git mv dari docs/packs/)
├── spikes/gate0/                # H0, skrip spike
├── data/                        # runtime, TIDAK di-commit
├── data-uji -> …/arsip-hidup-batik   # symlink, TIDAK di-commit
├── api/
│   ├── pyproject.toml  .python-version  uv.lock
│   ├── empu/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (satu-satunya pembaca env)
│   │   ├── enums.py             # semua StrEnum
│   │   ├── text.py              # normalize()
│   │   ├── packs.py             # CraftPack, load_pack, variant_index
│   │   ├── muse_schema.py       # MuseSegmentOutput (Pydantic), load_json_schema
│   │   ├── legacy.py            # upgrade_v1() untuk fixture uji v1
│   │   ├── meta_client.py       # MetaClient, output_text, extract_json, Detection
│   │   ├── cache.py             # ResponseCache, sha256_file
│   │   ├── resources/muse-output.schema.json
│   │   ├── db.py                # make_engine, init_db, get_session
│   │   ├── models.py            # SQLModel tables
│   │   ├── media.py             # path relatif data_dir, can_access_media
│   │   ├── visibility.py        # aturan publik
│   │   ├── review.py            # apply_review
│   │   ├── persist.py           # tulis hasil pipeline ke DB
│   │   ├── pipeline/
│   │   │   ├── ffmpeg.py        # run_ffmpeg, probe_duration
│   │   │   ├── normalize.py  chunk.py  prompts.py  analyze.py
│   │   │   ├── transcribe.py    # Mode B (kondisional)
│   │   │   ├── merge.py  process_map.py  evidence.py  ground.py
│   │   │   └── run.py           # process_recording (orkestrator)
│   │   ├── export/  common.py  json_export.py  csv_export.py  eaf_export.py  zip_export.py
│   │   ├── evaluation/  gold.py  matching.py  metrics.py  baseline.py  runner.py
│   │   ├── routes/  health.py packs.py archives.py recordings.py jobs.py entries.py
│   │   │            media.py public.py exports.py eval.py sandbox.py
│   │   ├── api_schemas.py       # model request/response API
│   │   ├── auth.py              # studio key + sandbox
│   │   ├── app.py               # create_app()
│   │   ├── worker.py            # python -m empu.worker
│   │   └── cli.py               # empu analyze | ingest | db | eval | demo
│   ├── eval/results/            # hasil evaluasi (latest.json di-commit)
│   └── tests/  fixtures/{muse,sam}/  test_*.py
├── web/                         # Next.js (H3)
│   ├── app/  components/  lib/  next.config.ts  vitest.config.ts
└── deploy/  docker-compose.yml  Caddyfile  api.Dockerfile  web.Dockerfile  (H6)
```

---

## Kontrak antarmodul (nama dan tipe yang dipakai lintas fase)

Implementer satu task hanya melihat task-nya. Tabel ini adalah kontrak yang tidak boleh diubah diam-diam. Kalau perlu berubah, ubah di sini dan di semua task yang memakainya.

### Enum (`api/empu/enums.py`, semua `StrEnum`)
| Enum | Nilai |
|---|---|
| `Category` | `tool, tool_part, material, dye, stage, technique, motif, other` |
| `Source` | `speech, on_screen_text, visual_only` |
| `VisualMatch` | `yes, no, not_visible` |
| `Confidence` | `low, medium, high` |
| `ContributorRole` | `maestro, student, documenter` |
| `ConsentStatus` | `granted, withdrawn` |
| `AccessLevel` (juga dipakai untuk `consent_scope`) | `public, community, private` |
| `JobStatus` | `queued, normalizing, chunking, analyzing, merging, grounding, cutting, ready, failed` |
| `PipelineMode` | `A, B` |
| `EntryStatus` | `proposed, accepted, edited, rejected, merged` |
| `OccurrenceStatus` | `proposed, accepted, rejected` |
| `ReviewAction` | `accept, edit, reject, merge, restore, add_manual` |
| `SamStatus` | `ok, empty, error, skipped` |
| `ChunkStatus` | `pending, done, failed` |

### Fungsi dan kelas inti
| Modul | Simbol | Tanda tangan |
|---|---|---|
| `config` | `Settings`, `get_settings()` | `get_settings() -> Settings` (lru_cache). Field: `meta_model_api_key: SecretStr\|None`, `studio_key: SecretStr\|None`, `meta_base_url`, `muse_model`, `sam_model`, `data_dir: Path`, `packs_dir: Path`, `testdata_dir: Path`, `db_url: str`, `chunk_window_s`, `chunk_overlap_s`, `analyze_concurrency`, `pipeline_mode`, `structured_output: bool`, `sam_enabled: bool`, `max_upload_mb`, `max_duration_s`, `sandbox_max_duration_s`, `sandbox_daily_quota`, `transcribe_backend` |
| `text` | `normalize` | `normalize(s: str \| None) -> str` |
| `packs` | `CraftPack`, `PackRef`, `load_pack`, `list_packs`, `PackError` | `load_pack(pack_id: str, packs_dir: Path) -> CraftPack`; `CraftPack.variant_index() -> dict[str, PackRef]`; `PackRef(kind: Literal["term","stage"], id: str)` |
| `muse_schema` | `MuseTerm`, `MuseProcessStep`, `MuseSegmentOutput`, `load_json_schema` | `MuseSegmentOutput.model_validate(dict)`; `load_json_schema() -> dict` |
| `legacy` | `upgrade_v1` | `upgrade_v1(d: dict) -> dict` |
| `meta_client` | `MetaClient`, `MetaAPIError`, `AnalyzeResult`, `Detection`, `output_text`, `extract_json` | `MetaClient.upload_file(path: Path, mime="video/mp4") -> str`; `MetaClient.analyze_video(file_id, prompt, *, model, schema=None, max_output_tokens=16000) -> AnalyzeResult`; `MetaClient.segment_image(image_path: Path, prompts: list[str], *, model) -> list[Detection]` |
| `cache` | `ResponseCache`, `sha256_file` | `ResponseCache(root: Path)`; `.key(sha, model, prompt_version, mode) -> str`; `.get(key) -> dict\|None`; `.put(key, payload: dict) -> Path` |
| `pipeline.ffmpeg` | `run_ffmpeg`, `probe_duration`, `FFmpegError` | `probe_duration(path: Path) -> float` |
| `pipeline.normalize` | `NormalizedMedia`, `normalize_recording` | `normalize_recording(src, out_dir, *, strip_audio=False) -> NormalizedMedia(analysis_path, display_path, duration_s)` |
| `pipeline.chunk` | `ChunkSpec`, `plan_chunks`, `cut_chunks` | `plan_chunks(duration_s, window_s=75, overlap_s=10) -> list[ChunkSpec]`; `ChunkSpec(idx, start_s, end_s)` |
| `pipeline.prompts` | `PROMPT_VERSION`, `prompt_version_for`, `build_prompt` | `prompt_version_for(seeds: bool) -> str`; `build_prompt(pack, *, seg_index, seg_total, seg_duration, seeds=True, transcript=None) -> str` |
| `pipeline.analyze` | `AnalyzeOptions`, `ChunkAnalysis`, `analyze_chunk`, `analyze_chunks`, `AnalysisError` | `analyze_chunks(client, cache, pack, items: list[tuple[ChunkSpec, Path]], opts, *, concurrency=3, on_done=None) -> list[ChunkAnalysis]` |
| `pipeline.process_map` | `StageMatcher`, `StepDraft`, `build_process_map`, `stage_at` | `build_process_map(analyses, pack) -> list[StepDraft]` |
| `pipeline.merge` | `Canonicalizer`, `CanonMatch`, `AbsOccurrence`, `EntryDraft`, `merge_analyses` | `merge_analyses(analyses, pack, *, steps=None, tol_s=4.0) -> list[EntryDraft]` |
| `pipeline.evidence` | `clip_window`, `make_evidence`, `extract_keyframe`, `EvidencePaths` | `make_evidence(display, t_start, t_end, duration_s, out_dir) -> EvidencePaths` |
| `pipeline.ground` | `GroundResult`, `ground_keyframe`, `sam_prompts_for` | `ground_keyframe(client, keyframe, prompts, out_dir, *, model) -> GroundResult` |
| `pipeline.run` | `JOB_STAGES`, `process_recording` | `process_recording(session, job_id: int, *, client, settings) -> None` |
| `visibility` | `recording_is_public`, `public_occurrences`, `entry_is_public`, `public_entries` | lihat H4 |
| `review` | `apply_review`, `ReviewError` | `apply_review(session, entry_id, req: ReviewIn) -> Entry` |
| `media` | `rel_to_data`, `abs_from_rel`, `can_access_media` | `can_access_media(session, rel_path: str, *, has_key: bool) -> bool` |

### Tata letak data (spec bagian 9)
```
data/empu.db
data/archives/<archive_id>/recordings/<recording_id>/
  original.<ext>  display.mp4  analysis.mp4
  chunks/<idx>.mp4
  muse/<idx>.raw.json  muse/<idx>.json
  occurrences/<occurrence_id>/{clip.mp4, audio.m4a, keyframe.jpg}
data/archives/<archive_id>/entries/<entry_id>/{crop.png, overlay.jpg}
data/cache/muse/<key>.json
data/exports/
```
Semua path media disimpan di DB sebagai **path relatif terhadap `data_dir`** (mis. `archives/1/recordings/3/display.mp4`). URL-nya `/media/<path relatif>`.

---

## Gate dan aturan potong

| Gate | Kapan | Lulus kalau | Kalau gagal |
|---|---|---|---|
| **Gate 0** | H0, paling lambat Kamis 29 Okt pagi | (1) istilah `speech` jelas turun saat audio dihapus, (2) recall ucapan v3 segmen 75 s ≥ 6/8 di #NgertiBatik, (3) SAM memotong canting dengan benar di sebagian besar frame, (4) status structured output diketahui | (1) atau (2) gagal → **Mode B wajib** (task H2-10 aktif, default `EMPU_PIPELINE_MODE=B`). (3) gagal setelah ganti prompt → `EMPU_SAM_ENABLED=false`, fallback keyframe, SAM turun prioritas. (4) ditolak → parse teks + validasi Pydantic |
| **Gate 1** | akhir H2 | Satu video uji berjalan end-to-end lewat CLI **dan** worker; DB berisi entri, klip, potongan gambar | Potong: SAM (keyframe saja), penggabungan lintas rekaman, peta tahapan sederhana (tahap dari `stage` Muse saja) |
| **Gate 2** | akhir H5 | Video demo CC BY (dan rekaman sendiri kalau ada) diproses, divalidasi, dievaluasi, atribusi tampil; aplikasi bisa diakses dari URL | Potong: ekspor ELAN, sandbox, polesan UI. **Halaman Bukti tetap wajib** |

**Urutan potong kalau waktu habis** (spec 15): 1. SAM video tracking → 2. Muse Wonder → 3. Pack stub tenun → 4. Tambah entri manual → 5. Sandbox juri → 6. Ekspor ELAN (JSON dan CSV tetap) → 7. Penggabungan lintas rekaman.

**Tidak boleh dipotong:** unggah → proses → validasi → kamus dengan klip, izin dan atribusi, angka evaluasi, demo dengan video berizin (CC BY beratribusi atau rekaman sendiri).

Stretch (spec 4) **tidak** dijadwalkan. Kerjakan hanya kalau sebuah fase selesai lebih cepat dari jadwal, dengan urutan: tambah entri manual → promosi istilah ke pack → stub pack tenun → SAM video tracking → Muse Wonder.

---

## Cara menjalankan (diisi penuh di H1; ringkasan di sini)

```bash
# Python
cd api && uv sync                         # instal
uv run pytest -q                          # tes
uv run ruff check . && uv run ruff format --check .
uv run empu analyze ../data-uji/<file>.mp4 --pack batik_tulis --out ../data/runs/<nama>
uv run empu db init
uv run python -m empu.worker              # worker
uv run uvicorn empu.app:create_app --factory --reload --port 8000   # API

# Web
cd web && pnpm install && pnpm dev        # http://localhost:3000
pnpm vitest run && pnpm lint && pnpm build
```

## Ritme kerja harian
1. Pagi: baca file fase hari itu, pastikan gate sebelumnya sudah tercatat.
2. Kerjakan task berurutan; commit di akhir setiap task.
3. Pukul 17:00 WIB: cek apakah "Selesai kalau" fase realistis tercapai. Kalau tidak, potong sekarang sesuai tabel gate, jangan tunggu malam.
4. Malam: perbarui bagian **Status** di `CLAUDE.md` (satu baris per hari).
