# H0 (Rab 28 Okt): Init Repo dan Spike Gate 0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menjawab empat pertanyaan Gate 0 dengan panggilan API sungguhan (apakah Muse mendengar audio, recall ucapan prompt v3 pada segmen 75 detik, apakah SAM 3.1 bisa memotong alat, apakah structured output diterima), lalu mencatat keputusan Mode A/B dan SAM sebelum satu baris kode produk pun ditulis.

**Architecture:** Skrip spike sekali pakai di `spikes/gate0/` (Python 3.12 lewat `uv run --with …`, tanpa paket `empu`). Semua keluaran mentah ditulis ke `data/spikes/gate0/` (tidak di-commit). Respons mentah yang berguna sebagai fixture disalin ke `docs/reference/uji-kelayakan/hasil-gate0/`. Hasil dan keputusan ditulis ke `docs/reference/hasil-gate0.md`.

**Tech Stack:** Python 3.12, httpx, PyYAML, Pillow, jsonschema, ffmpeg/ffprobe.

## Global Constraints

Semua butir di `00-ikhtisar.md` bagian "Global Constraints" berlaku. Yang paling relevan untuk fase ini:
- `META_MODEL_API_KEY` dibaca dari `.env` root repo. Jangan dicetak, di-log, atau di-commit. Jangan pernah `cat .env`.
- Video uji YouTube hanya untuk evaluasi internal. Jangan commit video, `data/`, `data-uji/`.
- Setiap respons mentah disimpan ke disk sebelum diproses, dan skrip **tidak memanggil API lagi** kalau file hasilnya sudah ada (biaya dan waktu).
- Gate 0 butir 2 memakai **prompt v3** (keputusan D2).
- Batas waktu Gate 0: paling lambat Kamis 29 Okt pagi. Kalau satu probe macet lebih dari 45 menit, catat sebagai "tidak terjawab", ambil default konservatif (Mode B untuk audio/recall, fallback keyframe untuk SAM, parse teks untuk structured output), dan lanjut.

## Anggaran
- Waktu: sekitar 3–4 jam termasuk menonton hasil.
- Biaya Muse: sekitar 2 × 36 ribu (audio) + 4 × 20 ribu (recall) + 1 × 8 ribu (structured) ≈ 160 ribu token input ≈ USD 0,25. SAM: 7–14 panggilan, harga belum diketahui.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `.gitignore` | Modify | Mengecualikan rahasia, data, video, artefak build |
| `docs/eval/lisensi/*.json` | Create | Bukti lisensi CC BY per video (metadata YouTube, tanpa video) |
| `data-uji` | Create (symlink) | Menunjuk ke folder video uji yang sudah ada |
| `spikes/gate0/common.py` | Create | Helper bersama: kunci API, klien httpx, cari video, potong klip, unggah, panggil, parse |
| `spikes/gate0/prompt_v3.py` | Create | Builder prompt v3 dari craft pack (sumber teks untuk `prompts.py` di H1) |
| `spikes/gate0/probe_models.py` | Create | Daftar model yang tersedia (SAM, transkripsi, Wonder) |
| `spikes/gate0/probe_structured.py` | Create | Gate 0.4: `text.format` json_schema |
| `spikes/gate0/probe_audio.py` | Create | Gate 0.1: dengan vs tanpa audio |
| `spikes/gate0/probe_recall.py` | Create | Gate 0.2: recall ucapan 8 istilah, segmen 75 s |
| `spikes/gate0/probe_sam.py` | Create | Gate 0.3: SAM 3.1 pada 7 keyframe |
| `docs/reference/hasil-gate0.md` | Create | Angka, keputusan, bentuk request/response yang terbukti |
| `docs/reference/uji-kelayakan/hasil-gate0/` | Create | Respons mentah terpilih sebagai fixture H1/H2 |
| `docs/reference/meta-model-api.md` | Modify | Pindahkan butir yang terbukti ke "Terverifikasi" |
| `docs/superpowers/specs/2026-10-28-empu-design.md` | Modify | Bagian 15 Gate 0 butir 2: "prompt v3" (D2); bagian 17 #6 hasil mode |
| `CLAUDE.md` | Modify | Status H0 |

---

### Task H0-1: Init repo, `.gitignore`, symlink video uji

**Files:**
- Modify: `.gitignore` (sudah ada di root repo; pastikan memuat semua baris di bawah)
- Create: `data-uji` (symlink)

**Interfaces:**
- Consumes: folder video uji `arsip-hidup-batik/` yang sudah disalin ke root repo (23 file `.mp4`, subfolder `1-proses-lengkap`, `2-closeup-per-tahap`, `3-sejarah-lisan-maestro`, `4-pembanding-inggris`). Folder ini ter-ignore git.
- Produces: `data-uji/` yang bisa di-`rglob`, repo git dengan commit pertama berisi `docs/` dan `CLAUDE.md`.

- [ ] **Step 1: Pastikan `.gitignore` memuat baris berikut** (tambahkan yang belum ada; `arsip-hidup-batik/` dan `*.vtt` sudah ada di file sekarang)

```gitignore
# Rahasia
.env
.env.*
!.env.example

# Data dan media (hak cipta, ukuran)
arsip-hidup-batik/
data/
data-uji
data-uji/
*.vtt
*.mp4
*.mov
*.mkv
*.m4a
*.wav
*.webm

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
*.db
*.db-journal

# Node / Next
node_modules/
.next/
out/
web/.env*
!web/.env.example
*.tsbuildinfo
next-env.d.ts

# OS / editor
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 2: Buat symlink video uji**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
ln -s arsip-hidup-batik data-uji
find -L data-uji -name '*.mp4' | wc -l
find -L data-uji \( -name '*\[rKVEysItoKY\]*.mp4' -o -name '*\[7-WQ3DKKn0w\]*.mp4' \)
```
Expected: angka `23`, lalu dua path (video *nglowong* dan *#NgertiBatik*). Kalau salah satu tidak ditemukan, cari dengan `find -L data-uji -name '*rKVEysItoKY*'` dan catat nama filenya.

- [ ] **Step 3: Pastikan rahasia dan data ter-ignore**

```bash
git check-ignore -v .env data-uji arsip-hidup-batik/x.mp4 data/x.mp4
git status --porcelain
```
Expected: empat baris `check-ignore` (masing-masing menunjuk aturan di `.gitignore`). `git status` hanya menampilkan `.gitignore`, `CLAUDE.md`, `docs/` (dan `.cursor/` kalau ada; tambahkan `.cursor/` ke `.gitignore` kalau tidak ingin di-commit). **Tidak boleh** ada `.env`, `data-uji`, atau `arsip-hidup-batik`.

- [ ] **Step 4: Pindai rahasia sebelum commit pertama**

```bash
grep -rIl "META_MODEL_API_KEY=" docs CLAUDE.md || echo "bersih"
grep -rIlE "sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,}" docs CLAUDE.md || echo "bersih"
```
Expected: `bersih` dua kali.

- [ ] **Step 5: Commit**

```bash
git add .gitignore CLAUDE.md docs
git commit -m "chore: initial docs, spec, and gitignore"
```

---

### Task H0-2: Video CC BY, kontak kreator, persyaratan submission (30 menit)

Dikerjakan sekarang karena jawaban kreator butuh waktu, dan video CC BY prioritas 1 adalah bahan demo dan set uji utama (keputusan D9).

**Files:**
- Modify: `docs/00-konteks-hackathon.md`
- Create: `docs/eval/lisensi/<youtube_id>.json` (bukti lisensi per video, metadata saja)

- [ ] **Step 1: Unduh tiga video CC BY prioritas 1 dan simpan bukti lisensinya**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
mkdir -p data-uji/cc-by docs/eval/lisensi
for id in FodqwNTWOrQ zyscgcTHtq8 FRIKA7rTFGw; do
  yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 \
    --write-subs --write-auto-subs --sub-langs "id,id-orig" \
    -o "data-uji/cc-by/%(title)s [%(id)s].%(ext)s" "https://www.youtube.com/watch?v=$id"
  yt-dlp -J --skip-download "https://www.youtube.com/watch?v=$id" | python3 -c "
import json,sys,datetime; d=json.load(sys.stdin)
keep={k:d.get(k) for k in ('id','title','channel','channel_url','uploader','license','upload_date','duration','webpage_url')}
keep['verified_at']=datetime.date.today().isoformat()
print(json.dumps(keep,ensure_ascii=False,indent=1))" > docs/eval/lisensi/$id.json
done
grep -h '"license"' docs/eval/lisensi/*.json
```
Expected: tiga file `.mp4` di `data-uji/cc-by/` (ter-ignore git) dan tiga baris `"license": "Creative Commons Attribution license (reuse allowed)"`. Kalau YouTube membalas HTTP 429, tunggu 10 menit lalu ulangi video yang gagal saja. Jangan unduh semua 11 video sekarang; prioritas 2 dan 3 diunduh di H3 kalau dibutuhkan.

- [ ] **Step 2: Tonton sekilas ketiga video (10 menit total).** Untuk tiap video catat: ada narasi yang jelas (ya/tidak), ada musik latar di bawah narasi (ya/tidak), ada teks di layar (ya/tidak), dan siapa yang bicara (ahli atau presenter). Kalau salah satu ternyata hampir tanpa narasi, ganti dengan video prioritas 2 dari `docs/eval/test-set.yaml`.

- [ ] **Step 3: Hubungi kreator untuk izin dan validasi jarak jauh.** Prioritas: **TEBAK teras batik kaindra** (sanggar aktif, Batik Pajampangan), lalu **Batik Education**. Cari kontak di bagian "About" channel YouTube, Instagram, atau WhatsApp. Isi pesan: Empu adalah proyek hackathon nirlaba yang membuat kamus istilah batik dari video mereka (CC BY, dengan atribusi); minta (a) restu memakai video itu di demo, dan (b) kesediaan 20–30 menit video call pada 1–3 Nov untuk mengecek 10–15 istilah dan artinya. Catat di `docs/00-konteks-hackathon.md` di bawah tabel "Fakta hackathon":

```markdown
## Status kontak kreator video CC BY
| Kreator | Kontak | Dihubungi | Restu demo | Validasi | Catatan |
|---|---|---|---|---|---|
| TEBAK teras batik kaindra | (WA/IG) | 28 Okt | menunggu | menunggu | |
| Batik Education | (email/IG) | 28 Okt | menunggu | menunggu | |
```

Tanpa balasan, demo tetap jalan (lisensi CC BY sudah cukup secara hukum), tetapi semua entri disebut "divalidasi oleh pendokumentasi".

- [ ] **Step 4: Cek persyaratan submission** di https://dev.meta.ai/events/global-hackathon dan https://cerebralvalley.ai/e/meta-ai-developer-hackathon. Ganti baris "**Belum dicek:** …" di `docs/00-konteks-hackathon.md` dengan daftar yang ditemukan: repo publik (ya/tidak), video demo (durasi maksimal, platform), deskripsi (panjang maksimal), link aplikasi, kewajiban memakai model Meta tertentu, form/platform submission. Kalau halaman belum memuat info, tulis "belum diumumkan per 28 Okt" dan cek ulang di awal H3.

- [ ] **Step 5: Commit**

```bash
git add docs/00-konteks-hackathon.md docs/eval/lisensi
git commit -m "docs: CC BY license evidence, creator outreach, submission requirements"
```

---

### Task H0-3: Helper spike dan daftar model

**Files:**
- Create: `spikes/gate0/common.py`
- Create: `spikes/gate0/probe_models.py`

**Interfaces:**
- Produces (dipakai semua probe):
  - `REPO: Path`, `OUT: Path` (= `data/spikes/gate0`), `TESTDATA: Path`, `SCHEMA_PATH`, `PACK_PATH`
  - `client() -> httpx.Client` (base_url Meta, header auth)
  - `find_video(yt_id: str) -> Path`
  - `make_clip(src: Path, start: float, dur: float, dst: Path, *, strip_audio: bool = False) -> Path`
  - `extract_frame(src: Path, t: float, dst: Path) -> Path`
  - `upload(c, path: Path, mime: str = "video/mp4") -> str`
  - `post_json(c, path: str, body: dict) -> tuple[int, dict | str]` (tidak melempar error untuk status ≥ 400)
  - `video_body(file_id, prompt, *, model="muse-spark-1.3", text_format=None) -> dict`
  - `output_text(resp: dict) -> str`, `parse_json(text: str) -> dict`
  - `once(name: str, fn: Callable[[], dict]) -> dict` (memanggil `fn` hanya kalau `OUT/name` belum ada)

- [ ] **Step 1: Tulis `spikes/gate0/common.py`**

```python
"""Shared helpers for the Gate 0 spike.

Throwaway code. Production code lives in api/empu/ and must not import this.
Never print the API key or request headers.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
BASE = "https://api.meta.ai/v1"
OUT = REPO / "data" / "spikes" / "gate0"
TESTDATA = Path(os.environ.get("EMPU_TESTDATA_DIR", REPO / "data-uji")).resolve()
SCHEMA_PATH = REPO / "docs" / "reference" / "muse-output.schema.json"
PACK_PATH = REPO / "docs" / "packs" / "batik_tulis.yaml"


def _api_key() -> str:
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("META_MODEL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("META_MODEL_API_KEY missing in .env")


def client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE,
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=httpx.Timeout(900, connect=30),
    )


def find_video(yt_id: str) -> Path:
    hits = sorted(p for p in TESTDATA.rglob("*.mp4") if f"[{yt_id}]" in p.name)
    if not hits:
        raise SystemExit(f"video [{yt_id}] not found under {TESTDATA}")
    return hits[0]


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def make_clip(src: Path, start: float, dur: float, dst: Path, *, strip_audio: bool = False) -> Path:
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    audio = ["-an"] if strip_audio else ["-c:a", "aac", "-ac", "1", "-b:a", "64k"]
    _ffmpeg(
        "-ss", str(start), "-i", str(src), "-t", str(dur),
        "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        *audio, str(dst),
    )
    return dst


def extract_frame(src: Path, t: float, dst: Path) -> Path:
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg("-ss", str(t), "-i", str(src), "-frames:v", "1", "-q:v", "2", str(dst))
    return dst


def upload(c: httpx.Client, path: Path, mime: str = "video/mp4") -> str:
    with path.open("rb") as f:
        r = c.post("/files", files={"file": (path.name, f, mime)},
                   data={"purpose": "user_data"}, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError(f"upload {r.status_code}: {r.text[:500]}")
    return r.json()["id"]


def post_json(c: httpx.Client, path: str, body: dict) -> tuple[int, dict | str]:
    r = c.post(path, json=body)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text[:2000]


def video_body(file_id: str, prompt: str, *, model: str = "muse-spark-1.3",
               text_format: dict | None = None) -> dict:
    body: dict = {
        "model": model,
        "max_output_tokens": 16000,
        "input": [{"role": "user", "content": [
            {"type": "input_video", "file_id": file_id},
            {"type": "input_text", "text": prompt},
        ]}],
    }
    if text_format is not None:
        body["text"] = {"format": text_format}
    return body


def output_text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts = []
    for item in resp.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts)


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    m = re.search(r"\{.*\}", text, flags=re.S)
    return json.loads(m.group(0)) if m else {}


def save(name: str, obj: object) -> Path:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    return path


def once(name: str, fn: Callable[[], dict]) -> dict:
    path = OUT / name
    if path.exists():
        return json.loads(path.read_text())
    result = fn()
    save(name, result)
    return result
```

- [ ] **Step 2: Tulis `spikes/gate0/probe_models.py`**

```python
"""List available model ids. Answers: exact SAM id, transcription model, Muse Wonder."""

from common import client, once


def main() -> None:
    with client() as c:
        data = once("models.json", lambda: c.get("/models").json())
    ids = sorted(m.get("id", "") for m in data.get("data", []))
    print("all:", ids)
    for kw in ("sam", "transcri", "voice", "whisper", "wonder", "muse"):
        print(f"{kw}:", [i for i in ids if kw in i.lower()])


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Jalankan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
uv run --python 3.12 --with httpx python probe_models.py
```
Expected: baris `all: [...]` lalu satu baris per kata kunci. Catat id persis untuk SAM (diharapkan `sam-3.1`), model transkripsi (kalau ada), dan Wonder. Kalau `/models` mengembalikan error, hapus `data/spikes/gate0/models.json`, tulis "tidak ada endpoint /models", dan pakai id dari dokumentasi.

- [ ] **Step 4: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/common.py spikes/gate0/probe_models.py
git commit -m "spike(gate0): shared helpers and model listing"
```

---

### Task H0-4: Builder prompt v3

**Files:**
- Create: `spikes/gate0/prompt_v3.py`

**Interfaces:**
- Consumes: `docs/packs/batik_tulis.yaml`, `docs/reference/muse-output.schema.json`
- Produces: `TEMPLATE: str`, `SEED_BLOCK: str`, `build(seg_index: int, seg_total: int, seg_duration: float, *, seeds: bool = True) -> str`. Teks `TEMPLATE` dan `SEED_BLOCK` disalin **verbatim** ke `api/empu/pipeline/prompts.py` di H1-8. Kalau teksnya diubah selama Gate 0, catat perubahannya di `hasil-gate0.md`.

- [ ] **Step 1: Tulis `spikes/gate0/prompt_v3.py`**

```python
"""Prompt analyze-v3 (docs/reference/prompt-analisis.md), built from the craft pack."""

from __future__ import annotations

import json

import yaml

from common import PACK_PATH, SCHEMA_PATH

TEMPLATE = """Kamu membantu mendokumentasikan pengetahuan seorang ahli {pack_name}.
Video ini adalah segmen {seg_index}/{seg_total} dari sebuah rekaman, berdurasi {seg_duration} detik.
Semua waktu dihitung dalam detik dari AWAL SEGMEN INI.

KONTEKS KETERAMPILAN
{prompt_context}

KERANGKA TAHAPAN (urutan umum, rekaman nyata bisa berbeda):
{stages}

{seed_block}{transcript_block}TUGAS
Tonton DAN dengarkan segmen ini sampai detik terakhir.
1. Catat setiap istilah keahlian (alat, bagian alat, bahan, pewarna, tahap, teknik, motif).
   Untuk setiap istilah, tentukan sumbernya dengan tegas:
   - "speech": terdengar diucapkan di audio.
   - "on_screen_text": hanya terbaca sebagai tulisan di layar (judul, diagram, subtitle tertanam).
   - "visual_only": bendanya terlihat, tapi tidak diucapkan dan tidak tertulis.
   Kalau sebuah istilah diucapkan DAN tertulis, pakai "speech" dengan waktu saat diucapkan.
   Kalau istilah yang sama diucapkan berulang dalam 5 detik, cukup laporkan sekali.
2. Beri waktu mulai dan selesai ucapan (t_start, t_end).
3. Untuk "speech", tulis kalimat yang diucapkan di sekitar istilah itu di evidence_quote.
4. Jelaskan apa yang TERLIHAT saat itu (visible), apakah cocok dengan istilahnya (visual_match),
   dan tulis frasa benda pendek dalam bahasa Inggris (visible_object_en) kalau ada benda yang relevan.
5. Beri arti singkat dalam bahasa Indonesia (gloss_id) dan Inggris (gloss_en).
   Kalau tidak yakin artinya, katakan begitu dan turunkan confidence.
6. Susun urutan tahapan proses yang terlihat di segmen ini (process_steps).

Jangan mengarang. Kalau segmen hanya berisi musik atau tidak ada ucapan, speech_heard = false
dan jangan laporkan istilah "speech".

Jawab HANYA dengan JSON valid sesuai skema berikut, tanpa teks lain:
{schema}
"""

SEED_BLOCK = """CONTOH ISTILAH YANG MUNGKIN MUNCUL
Ini hanya contoh, BUKAN daftar yang harus ditemukan. Jangan laporkan istilah dari daftar ini
kalau tidak benar-benar diucapkan, tertulis, atau terlihat di segmen ini.
Istilah di luar daftar justru sangat penting, terutama istilah bahasa Jawa atau istilah lokal: laporkan juga.
{seeds}

"""


def _variants(label: str, variants: list[str]) -> str:
    rest = [v for v in variants if v.casefold() != label.casefold()]
    return f" (varian: {', '.join(rest)})" if rest else ""


def build(seg_index: int, seg_total: int, seg_duration: float, *, seeds: bool = True) -> str:
    pack = yaml.safe_load(PACK_PATH.read_text())
    schema = json.loads(SCHEMA_PATH.read_text())
    stages = "\n".join(
        f"- {s['id']} — {s['label']['id']}{_variants(s['id'], s.get('variants', []))}"
        for s in pack["stages"]
    )
    seed_block = ""
    if seeds:
        lines = "\n".join(
            f"- {t['label']}{_variants(t['label'], t.get('variants', []))}" for t in pack["terms"]
        )
        seed_block = SEED_BLOCK.format(seeds=lines)
    return TEMPLATE.format(
        pack_name=pack["name"]["id"],
        seg_index=seg_index,
        seg_total=seg_total,
        seg_duration=round(seg_duration),
        prompt_context=pack["prompt_context"].strip(),
        stages=stages,
        seed_block=seed_block,
        transcript_block="",
        schema=json.dumps(schema, ensure_ascii=False),
    )


if __name__ == "__main__":
    text = build(1, 4, 75)
    print(text)
    print(f"\n--- {len(text)} chars")
```

- [ ] **Step 2: Cek keluarannya**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
uv run --python 3.12 --with pyyaml --with httpx python prompt_v3.py | head -40
uv run --python 3.12 --with pyyaml --with httpx python -c "
import prompt_v3, yaml
p = prompt_v3.build(1, 4, 75)
pack = yaml.safe_load(open(prompt_v3.PACK_PATH))
print('gloss leaks:', [t['id'] for t in pack['terms'] if t['gloss_id'] in p])
noseed = prompt_v3.build(1, 4, 75, seeds=False)
print('noseed has seed block:', 'CONTOH ISTILAH' in noseed)
"
```
Expected: header prompt berisi `segmen 1/4`, `berdurasi 75 detik`, daftar tahap `- persiapan_kain — Persiapan kain (varian: …)`. `gloss leaks: []` (glosa pack tidak boleh masuk prompt). `noseed has seed block: False`.

- [ ] **Step 3: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/prompt_v3.py
git commit -m "spike(gate0): prompt analyze-v3 builder from craft pack"
```

---

### Task H0-5: Gate 0.4, structured output

Dijalankan pertama karena paling murah (klip 30 detik), dan hasilnya menentukan bentuk panggilan probe berikutnya.

**Files:**
- Create: `spikes/gate0/probe_structured.py`

**Interfaces:**
- Consumes: `common.*`, `prompt_v3.build`
- Produces: `data/spikes/gate0/structured.json` berisi `{file_id, attempts: [{variant, status, error|null, valid_json, schema_valid, raw}]}`; keputusan `EMPU_STRUCTURED_OUTPUT=true|false` dan varian skema yang diterima (`full` atau `stripped`).

- [ ] **Step 1: Tulis `spikes/gate0/probe_structured.py`**

```python
"""Gate 0.4: does /responses accept text.format json_schema for muse-spark-1.3?

Tries the full schema first, then a stripped schema without keywords that strict
modes often reject (maxLength, minimum, $schema, $id, title, description).
"""

from __future__ import annotations

import copy
import json

import jsonschema

from common import (OUT, SCHEMA_PATH, client, find_video, make_clip, once, output_text,
                    parse_json, post_json, upload, video_body)
from prompt_v3 import build

STRIP = {"maxLength", "minimum", "$schema", "$id", "title", "description"}


def stripped(node):
    if isinstance(node, dict):
        return {k: stripped(v) for k, v in node.items() if k not in STRIP}
    if isinstance(node, list):
        return [stripped(v) for v in node]
    return node


def attempt(c, file_id: str, prompt: str, name: str, schema: dict) -> dict:
    fmt = {"type": "json_schema", "name": "empu_terms", "schema": schema, "strict": True}
    status, resp = post_json(c, "/responses", video_body(file_id, prompt, text_format=fmt))
    result = {"variant": name, "status": status, "error": None, "valid_json": False,
              "schema_valid": False, "raw": resp}
    if status >= 400:
        result["error"] = resp if isinstance(resp, str) else json.dumps(resp)[:1500]
        return result
    try:
        parsed = json.loads(output_text(resp))
        result["valid_json"] = True
    except ValueError:
        parsed = parse_json(output_text(resp))
    try:
        jsonschema.validate(parsed, json.loads(SCHEMA_PATH.read_text()))
        result["schema_valid"] = True
    except jsonschema.ValidationError as e:
        result["error"] = f"schema: {e.message}"
    return result


def main() -> None:
    full = json.loads(SCHEMA_PATH.read_text())
    clip = make_clip(find_video("rKVEysItoKY"), 0, 30, OUT / "clips" / "nglowong-30s.mp4")
    prompt = build(1, 1, 30)

    def run() -> dict:
        with client() as c:
            fid = upload(c, clip)
            attempts = [attempt(c, fid, prompt, "full", copy.deepcopy(full))]
            if attempts[0]["status"] >= 400:
                attempts.append(attempt(c, fid, prompt, "stripped", stripped(full)))
            return {"file_id": fid, "attempts": attempts}

    data = once("structured.json", run)
    for a in data["attempts"]:
        print(a["variant"], a["status"], "json:", a["valid_json"], "schema:", a["schema_valid"],
              "err:", (a["error"] or "")[:300])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Jalankan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
uv run --python 3.12 --with httpx --with pyyaml --with jsonschema python probe_structured.py
```
Expected, salah satu:
- `full 200 json: True schema: True` → structured output **didukung** dengan skema penuh.
- `full 400 …` lalu `stripped 200 json: True …` → didukung dengan skema tanpa `maxLength`/`minimum`. H1 memakai skema stripped untuk `text.format`; batas panjang tetap ditegakkan Pydantic.
- Keduanya ≥ 400 → **tidak didukung**: `EMPU_STRUCTURED_OUTPUT=false`. Pipeline memakai parse teks, validasi Pydantic, dan satu kali ulang.

- [ ] **Step 3: Catat hasil sementara** di catatan kerja (ditulis ke `hasil-gate0.md` di H0-9): status, varian yang diterima, pesan error persis.

- [ ] **Step 4: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/probe_structured.py
git commit -m "spike(gate0): structured output probe"
```

---

### Task H0-6: Gate 0.1, apakah Muse mendengar audio

**Files:**
- Create: `spikes/gate0/probe_audio.py`

**Interfaces:**
- Consumes: `common.*`, `prompt_v3.build`, hasil H0-5 (env `STRUCTURED=1` kalau skema penuh diterima)
- Produces: `data/spikes/gate0/audio-with.raw.json`, `audio-without.raw.json`, `audio.summary.json`; keputusan "Muse mendengar: ya/tidak".

- [ ] **Step 1: Tulis `spikes/gate0/probe_audio.py`**

```python
"""Gate 0.1: same 132 s nglowong clip with and without audio (ffmpeg -an).

Pass: speech terms without audio <= 50% of speech terms with audio, AND the
no-audio transcript does not reproduce the presenter's spoken intro.
"""

from __future__ import annotations

import json
import os

from common import (OUT, SCHEMA_PATH, client, find_video, make_clip, once, output_text,
                    parse_json, post_json, upload, video_body)
from prompt_v3 import build

USE_STRUCTURED = os.environ.get("STRUCTURED", "0") == "1"
INTRO_WORDS = ("kenalin", "teman-teman", "praktikum")


def run_one(clip, name: str) -> dict:
    def call() -> dict:
        with client() as c:
            fid = upload(c, clip)
            fmt = None
            if USE_STRUCTURED:
                schema = json.loads(SCHEMA_PATH.read_text())
                fmt = {"type": "json_schema", "name": "empu_terms", "schema": schema, "strict": True}
            status, resp = post_json(c, "/responses", video_body(fid, build(1, 1, 132), text_format=fmt))
            if status >= 400:
                raise RuntimeError(f"{status}: {str(resp)[:500]}")
            return resp

    raw = once(f"{name}.raw.json", call)
    return parse_json(output_text(raw))


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
    src = find_video("rKVEysItoKY")
    with_audio = make_clip(src, 0, 132, OUT / "clips" / "nglowong-132s.mp4")
    no_audio = make_clip(src, 0, 132, OUT / "clips" / "nglowong-132s-noaudio.mp4", strip_audio=True)
    a = summarize(run_one(with_audio, "audio-with"))
    b = summarize(run_one(no_audio, "audio-without"))
    intro_leak = any(w in b["transcript_excerpt"].lower() for w in INTRO_WORDS)
    ratio = (b["n_speech"] / a["n_speech"]) if a["n_speech"] else None
    verdict = bool(a["n_speech"]) and ratio is not None and ratio <= 0.5 and not intro_leak
    summary = {"with": a, "without": b, "speech_ratio": ratio, "intro_leak": intro_leak,
               "muse_hears_audio": verdict}
    (OUT / "audio.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Jalankan** (`STRUCTURED=1` hanya kalau H0-5 lulus dengan skema penuh)

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
STRUCTURED=0 uv run --python 3.12 --with httpx --with pyyaml python probe_audio.py
```
Expected: JSON ringkasan. Bandingkan `with.n_speech` dengan `without.n_speech`.

- [ ] **Step 3: Putuskan**
  - `muse_hears_audio: true` → Gate 0.1 **lulus**.
  - `false` karena `without.n_speech` mendekati `with.n_speech`, atau `intro_leak: true` → Muse tidak benar-benar mendengar. **Mode B wajib.**
  - Kasus abu-abu (rasio 0,5–0,8): baca `without.speech_terms`. Kalau semuanya juga tertulis di layar (judul "Langkah-Langkah Proses Ngelowong"), Muse salah label sumber tetapi tetap mendengar di klip beraudio. Catat sebagai "lulus dengan catatan: label sumber tidak bisa dipercaya tanpa audio", lalu biarkan Gate 0.2 yang menentukan.

- [ ] **Step 4: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/probe_audio.py
git commit -m "spike(gate0): audio vs no-audio probe"
```

---

### Task H0-7: Gate 0.2, recall ucapan prompt v3 pada segmen 75 detik

**Files:**
- Create: `spikes/gate0/probe_recall.py`

**Interfaces:**
- Consumes: `common.*`, `prompt_v3.build`
- Produces: `data/spikes/gate0/recall-seg<idx>.raw.json` (4 file), `recall-seg<idx>.json`, `recall.summary.json` berisi `hits`, `recall`, `pass`, `median_dt`, `speech_before_80s`. Respons mentah per segmen menjadi fixture penggabungan di H2.

Kunci 8 istilah (dari `docs/reference/hasil-uji-kelayakan.md`, detik dari awal video 7-WQ3DKKn0w):

| # | Istilah | Detik | Varian yang diterima |
|---|---|---|---|
| 1 | pola | 85–87 | pola, memola, molani |
| 2 | lilin malam | 109 | malam, lilin, lilin malam |
| 3 | spangkring | 122 | spangkring, spang kring, sangkring |
| 4 | membatik / meletakkan lilin | 126–128 | membatik, mencanting, canting, nyanting |
| 5 | mewarna | 145–149 | mewarna, mewarnai, pewarnaan, warna |
| 6 | HCl | 155 | hcl, asam klorida |
| 7 | waterglass | 162–165 | waterglass, water glass, natrium silikat |
| 8 | nglorod | 173 | nglorod, ngelorod, ngelorot, lorod, lorot, dilorot, dilorod, pelorodan |

Aturan cocok: istilah Muse dengan `source == "speech"`, `term` atau `spoken` (lowercase) mengandung salah satu varian sebagai kata utuh, dan jarak waktu absolut ke rentang kunci ≤ 5 detik.

- [ ] **Step 1: Tulis `spikes/gate0/probe_recall.py`**

```python
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
```

- [ ] **Step 2: Jalankan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
uv run --python 3.12 --with httpx --with pyyaml python probe_recall.py
```
Expected: 4 segmen (`seg0` 0–75, `seg1` 65–140, `seg2` 130–205, `seg3` 195–241), lalu ringkasan dengan `recall: "n/8"`.

- [ ] **Step 3: Baca dua angka tambahan**
  - `speech_before_80s`: istilah berlabel `speech` sebelum narasi dimulai. Idealnya kosong. Kalau berisi istilah dari diagram (*nyamplung*, *cucuk*, *gagang*), label sumber masih tidak bisa dipercaya. Catat, karena ini memengaruhi klaim ke juri dan metrik akurasi label sumber.
  - `nearest_any_source` pada istilah yang meleset: apakah istilahnya ditemukan tetapi berlabel `on_screen_text`, atau waktunya meleset lebih dari 5 detik?

- [ ] **Step 4: Putuskan**
  - `recall ≥ 6/8` **dan** Gate 0.1 lulus → **Mode A** default.
  - `recall < 6/8` → **Mode B** default (spec 15). Mode A tetap dijalankan sebagai pembanding di ablasi H5.

- [ ] **Step 5: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/probe_recall.py
git commit -m "spike(gate0): spoken-term recall probe on 75 s segments"
```

---

### Task H0-8: Gate 0.3, SAM 3.1 pada keyframe

**Files:**
- Create: `spikes/gate0/probe_sam.py`
- Create (kalau perlu): `spikes/gate0/sam_body.json` (template request kalau dokumentasi menunjukkan bentuk lain)

**Interfaces:**
- Consumes: `common.*`, id model SAM dari H0-3
- Produces: `data/spikes/gate0/sam/<frame>.p<i>.raw.json`, `<frame>.p<i>.boxes.jpg` (frame asli + kotak deteksi untuk dinilai manusia), `sam.summary.json`. Bentuk request dan response yang terbukti dicatat di `hasil-gate0.md` dan dipakai untuk `MetaClient.segment_image` dan `parse_sam_response` di H2-6.

- [ ] **Step 1: Baca dokumentasi SAM** di https://dev.meta.ai/docs/sam/segmenting dan https://dev.meta.ai/docs/models (dari Mac, dengan browser). Catat: endpoint (Responses API atau endpoint khusus), bentuk input gambar (`input_image` dengan `image_url` data URL, `file_id`, atau field lain), cara memberi prompt teks, bentuk keluaran (format bbox `xyxy` atau `xywh`, piksel atau ternormalisasi; encoding mask PNG base64, RLE, atau polygon), dan batas ukuran gambar. Kalau bentuk request berbeda dari varian default di skrip, tulis template ke `spikes/gate0/sam_body.json` dengan placeholder `{{MODEL}}`, `{{IMAGE_DATA_URL}}`, `{{FILE_ID}}`, `{{PROMPT}}`.

- [ ] **Step 2: Tulis `spikes/gate0/probe_sam.py`**

```python
"""Gate 0.3: SAM 3.1 on 7 keyframes (3 canting + wajan + kain + malam + spangkring).

Default request shape (unverified, from secondary sources) is the Responses API with an
input_image data URL and an input_text prompt. If docs show a different shape, put it in
sam_body.json with {{MODEL}}, {{IMAGE_DATA_URL}}, {{FILE_ID}}, {{PROMPT}} placeholders.
Draws every box found anywhere in the response so a human can judge it.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw

from common import OUT, client, extract_frame, find_video, once, post_json, upload

MODEL = os.environ.get("SAM_MODEL", "sam-3.1")
HERE = Path(__file__).parent
TEMPLATE = HERE / "sam_body.json"
SAM_OUT = OUT / "sam"
CANTING = ["canting", "small copper wax pen", "hand holding small copper pen"]
# (name, youtube_id, seconds, prompt variants). Open the JPGs; adjust seconds if the object is not in frame.
FRAMES = [
    ("canting-1", "rKVEysItoKY", 30.6, CANTING),
    ("canting-2", "rKVEysItoKY", 45.0, CANTING),
    ("canting-3", "rKVEysItoKY", 60.0, CANTING),
    ("wajan", "rKVEysItoKY", 26.0, ["small black wok with melted wax"]),
    ("kain", "rKVEysItoKY", 28.5, ["white cloth"]),
    ("malam", "rKVEysItoKY", 29.6, ["melted brown wax", "block of dark wax"]),
    ("spangkring", "7-WQ3DKKn0w", 122.0, ["wooden hoop frame holding cloth", "wooden rack holding cloth"]),
]
BOX_KEYS = ("bbox", "box", "bounding_box", "bbox_xyxy", "xyxy")


def body_for(image: Path, prompt: str, file_id: str | None) -> dict:
    data_url = "data:image/jpeg;base64," + base64.b64encode(image.read_bytes()).decode()
    if TEMPLATE.exists():
        text = (TEMPLATE.read_text().replace("{{MODEL}}", MODEL)
                .replace("{{IMAGE_DATA_URL}}", data_url).replace("{{PROMPT}}", prompt)
                .replace("{{FILE_ID}}", file_id or ""))
        return json.loads(text)
    return {"model": MODEL, "input": [{"role": "user", "content": [
        {"type": "input_image", "image_url": data_url},
        {"type": "input_text", "text": prompt},
    ]}]}


def find_boxes(node, out: list) -> list:
    if isinstance(node, dict):
        for k in BOX_KEYS:
            v = node.get(k)
            if isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
                out.append({"box": v, "score": node.get("score") or node.get("confidence"),
                            "label": node.get("label") or node.get("text")})
        for v in node.values():
            find_boxes(v, out)
    elif isinstance(node, list):
        for v in node:
            find_boxes(v, out)
    elif isinstance(node, str) and node.lstrip().startswith(("{", "[")):
        try:
            find_boxes(json.loads(node), out)
        except ValueError:
            pass
    return out


def draw(image: Path, boxes: list, dst: Path) -> None:
    im = Image.open(image).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    for b in boxes:
        x0, y0, x1, y1 = b["box"]
        if max(x0, y0, x1, y1) <= 1.0:  # normalized coordinates
            x0, x1, y0, y1 = x0 * w, x1 * w, y0 * h, y1 * h
        d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=4)
        d.text((x0 + 4, y0 + 4), f"{b.get('label')} {b.get('score')}", fill=(255, 0, 0))
    im.save(dst, quality=90)


def main() -> None:
    SAM_OUT.mkdir(parents=True, exist_ok=True)
    needs_file = TEMPLATE.exists() and "{{FILE_ID}}" in TEMPLATE.read_text()
    summary = []
    with client() as c:
        for name, yt, t, prompts in FRAMES:
            frame = extract_frame(find_video(yt), t, SAM_OUT / f"{name}.jpg")
            for i, prompt in enumerate(prompts):
                tag = f"{name}.p{i}"

                def call(frame=frame, prompt=prompt) -> dict:
                    file_id = upload(c, frame, mime="image/jpeg") if needs_file else None
                    status, resp = post_json(c, "/responses", body_for(frame, prompt, file_id))
                    return {"status": status, "response": resp}

                raw = once(f"sam/{tag}.raw.json", call)
                boxes = find_boxes(raw.get("response"), [])
                draw(frame, boxes, SAM_OUT / f"{tag}.boxes.jpg")
                summary.append({"frame": name, "prompt": prompt, "status": raw["status"],
                                "n_boxes": len(boxes), "top": boxes[:3]})
                print(tag, raw["status"], len(boxes), str(raw.get("response"))[:200])
    (OUT / "sam.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
```

Catatan: kalau dokumentasi menyebut endpoint selain `/responses`, ganti argumen pertama `post_json(c, "/responses", …)` dengan path dari dokumentasi.

- [ ] **Step 3: Jalankan**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu/spikes/gate0
SAM_MODEL=sam-3.1 uv run --python 3.12 --with httpx --with pillow python probe_sam.py
open ../../data/spikes/gate0/sam/
```
Expected: satu baris per (frame, prompt) dengan status HTTP dan jumlah kotak. Kalau status 400/404, baca pesan error, perbaiki `sam_body.json` atau path sesuai dokumentasi, **hapus** `data/spikes/gate0/sam/*.raw.json` yang gagal (supaya `once` memanggil ulang), lalu jalankan lagi. Maksimal 3 iterasi format (45 menit). Kalau tetap gagal, Gate 0.3 = **gagal** (fallback keyframe).

- [ ] **Step 4: Nilai secara manual.** Buka setiap `*.boxes.jpg`. Untuk tiap frame catat apakah kotak teratas menutupi benda yang benar. Kalau `find_boxes` tidak menemukan kotak padahal status 200, buka `.raw.json`, cari bentuk keluarannya (mis. `polygon`, `masks` RLE), lalu catat bentuknya di `hasil-gate0.md`.

- [ ] **Step 5: Putuskan**
  - Canting benar di ≥ 2 dari 3 frame canting (dengan prompt mana pun) → **SAM aktif**. Catat prompt terbaik. Kalau prompt terbaik bukan `canting, small copper wax pen`, perbarui `sam_prompt` istilah canting di pack pada H1-3.
  - Canting benar di < 2 dari 3 frame → **`EMPU_SAM_ENABLED=false`**. Studio dan Kamus menampilkan keyframe utuh; task SAM di H2 dikerjakan terakhir, hanya kalau waktu tersisa.
  - Sebuah benda dianggap gagal hanya setelah semua varian prompt-nya dicoba.

- [ ] **Step 6: Commit**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git add spikes/gate0/probe_sam.py
[ -f spikes/gate0/sam_body.json ] && git add spikes/gate0/sam_body.json
git commit -m "spike(gate0): SAM 3.1 keyframe probe"
```

---

### Task H0-9: Catat hasil Gate 0, salin fixture, perbarui dokumen

**Files:**
- Create: `docs/reference/hasil-gate0.md`
- Create: `docs/reference/uji-kelayakan/hasil-gate0/` (salinan respons mentah terpilih)
- Modify: `docs/reference/meta-model-api.md`
- Modify: `docs/superpowers/specs/2026-10-28-empu-design.md` (bagian 15 Gate 0 butir 2, bagian 17 #6)
- Modify: `CLAUDE.md` (Status)

**Interfaces:**
- Produces untuk H1/H2:
  - Nilai env awal: `EMPU_PIPELINE_MODE=A|B`, `EMPU_STRUCTURED_OUTPUT=true|false`, `EMPU_SAM_ENABLED=true|false`, `SAM_MODEL=<id>`, `EMPU_TRANSCRIBE_BACKEND=muse|whisper`.
  - Fixture: `hasil-gate0/structured.raw.json`, `hasil-gate0/recall-seg0..3.raw.json`, `hasil-gate0/sam-canting.raw.json`, `hasil-gate0/audio-with.raw.json`, ringkasan `*.summary.json`, `models.json`.

- [ ] **Step 1: Salin fixture** (respons JSON saja, bukan video atau gambar)

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
mkdir -p docs/reference/uji-kelayakan/hasil-gate0
cp data/spikes/gate0/recall-seg{0,1,2,3}.raw.json docs/reference/uji-kelayakan/hasil-gate0/
cp data/spikes/gate0/audio-with.raw.json docs/reference/uji-kelayakan/hasil-gate0/
cp data/spikes/gate0/*.summary.json data/spikes/gate0/models.json docs/reference/uji-kelayakan/hasil-gate0/
python3 -c "
import json; d=json.load(open('data/spikes/gate0/structured.json'))
ok=[a for a in d['attempts'] if a['status']<400]
json.dump(ok[0]['raw'] if ok else d['attempts'][-1], open('docs/reference/uji-kelayakan/hasil-gate0/structured.raw.json','w'), ensure_ascii=False, indent=1)"
# SAM: pilih SATU respons canting terbaik dari H0-8 (ganti nama file sesuai hasil)
cp data/spikes/gate0/sam/canting-1.p1.raw.json docs/reference/uji-kelayakan/hasil-gate0/sam-canting.raw.json
du -sh docs/reference/uji-kelayakan/hasil-gate0/*
```
Expected: semua file < 1 MB. Kalau respons SAM > 1 MB karena mask base64, sisakan satu deteksi saja di JSON sebelum di-commit.

- [ ] **Step 2: Tulis `docs/reference/hasil-gate0.md`** dengan struktur berikut, diisi angka asli dari `*.summary.json`:

```markdown
# Hasil Gate 0 (28–29 Okt 2026)

Skrip: `spikes/gate0/`. Respons mentah terpilih: `docs/reference/uji-kelayakan/hasil-gate0/`.
Prompt: analyze-v3 (keputusan D2), dibangun dari `docs/packs/batik_tulis.yaml` v0.1.0.

## Ringkasan keputusan
| Butir | Hasil | Keputusan | Env |
|---|---|---|---|
| 0.1 Audio | with: n speech, without: n speech, rasio r, intro_leak ya/tidak | lulus / gagal | – |
| 0.2 Recall | n/8, median Δt x s, speech sebelum detik 80: [...] | Mode A / Mode B | `EMPU_PIPELINE_MODE=` |
| 0.3 SAM | canting benar k/3, prompt terbaik "...", wajan/kain/malam/spangkring ya/tidak | aktif / fallback keyframe | `EMPU_SAM_ENABLED=`, `SAM_MODEL=` |
| 0.4 Structured | status full/stripped, error | didukung (full/stripped) / tidak | `EMPU_STRUCTURED_OUTPUT=` |
| Model lain | transkripsi: id atau tidak ada; Wonder: id | Mode B pakai Muse transcribe / faster-whisper | `EMPU_TRANSCRIBE_BACKEND=` |

## Bentuk request/response yang terbukti
### SAM 3.1
(body request persis tanpa data gambar; contoh respons dengan satu deteksi; format bbox; encoding mask)

### Structured output
(body `text.format` yang diterima, atau pesan error persis)

## Detail per butir
(tabel 8 istilah dari recall.summary.json; daftar speech_terms with/without audio; catatan label sumber)

## Implikasi untuk klaim ke juri
(apakah "subtitle menulis 'spang King', Empu mendengar 'spangkring'" sudah boleh dipakai: hanya kalau spangkring @122 ditemukan dengan source=speech)

## Biaya dan latensi
(token input/output dan latensi per panggilan dari usage di raw.json)
```

- [ ] **Step 3: Perbarui `docs/reference/meta-model-api.md`.** Pindahkan butir yang terbukti dari tabel "Belum terverifikasi" ke bagian "Terverifikasi" dengan bentuk request dan respons persis (audio, structured output, SAM, model transkripsi). Butir yang gagal tetap di tabel dengan status "gagal di Gate 0, lihat hasil-gate0.md".

- [ ] **Step 4: Perbarui spec.** Di `docs/superpowers/specs/2026-10-28-empu-design.md`:
  - Bagian 15, Gate 0 butir 2: ganti "jalankan prompt v2" menjadi "jalankan prompt v3 (keputusan 28 Okt)".
  - Bagian 17 baris #6: ganti default dengan hasil Gate 0, mis. "Mode A (Gate 0 lulus 28 Okt: audio terbukti, recall 7/8)".

- [ ] **Step 5: Perbarui `CLAUDE.md`** bagian Status:

```markdown
- H0 (Rab 28 Okt): dokumen dan plan selesai. Gate 0: mode A|B, SAM aktif|fallback, structured ya|tidak. Lihat docs/reference/hasil-gate0.md. Berikutnya: H1.
```

- [ ] **Step 6: Commit**

```bash
git add docs/reference/hasil-gate0.md docs/reference/uji-kelayakan/hasil-gate0 docs/reference/meta-model-api.md docs/superpowers/specs/2026-10-28-empu-design.md CLAUDE.md
git commit -m "docs: record Gate 0 results and decisions"
```

## Selesai kalau
- [ ] `docs/reference/hasil-gate0.md` berisi keempat keputusan dengan angka asli.
- [ ] Nilai env awal (`EMPU_PIPELINE_MODE`, `EMPU_STRUCTURED_OUTPUT`, `EMPU_SAM_ENABLED`, `SAM_MODEL`, `EMPU_TRANSCRIBE_BACKEND`) sudah diketahui.
- [ ] Fixture respons mentah ada di `docs/reference/uji-kelayakan/hasil-gate0/`.
- [ ] Tiga video CC BY prioritas 1 terunduh, bukti lisensinya ada di `docs/eval/lisensi/`, dan kedua kreator sudah dihubungi.
- [ ] `git status` bersih (kecuali `.env`, `data/`, `data-uji` yang ter-ignore).

## Kalau Gate 0 gagal
| Butir gagal | Dampak ke plan |
|---|---|
| 0.1 atau 0.2 | H2-10 (Mode B) **wajib** dan dikerjakan sebelum H2-8 (orkestrator). `EMPU_PIPELINE_MODE=B`. H5 menjalankan Mode A sebagai pembanding |
| 0.3 | `EMPU_SAM_ENABLED=false`. H2-6 dikerjakan paling akhir di H2, hanya kalau waktu ada. UI memakai keyframe. Metrik "ketepatan potongan SAM" dilaporkan "tidak dijalankan" |
| 0.4 | `EMPU_STRUCTURED_OUTPUT=false`. Tidak ada perubahan task; `analyze_chunk` sudah menangani parse teks + satu kali ulang |
