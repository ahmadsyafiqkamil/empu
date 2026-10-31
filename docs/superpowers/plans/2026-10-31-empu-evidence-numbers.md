# Isi Halaman Bukti dengan Angka Asli — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Halaman `/evidence` berhenti menampilkan "—", dan angka di dalamnya berasal dari gold annotation yang benar-benar dicek manusia — bukan dari keluaran model itu sendiri.

**Architecture:** `empu eval run` sudah menghitung metrik dari DB + gold CSV. Yang kurang: (a) penjaga yang menolak gold berstatus `DRAFT`, karena `draft-gold` membuat gold **dari prediksi model** sehingga recall akan mendekati 1,0 secara melingkar; (b) filter `--only` supaya klip uji internal yang tidak ada di DB tidak muncul sebagai baris kosong di halaman publik; (c) gold untuk dua klip demo, direview manusia; (d) `api/eval/results/latest.json` yang dibaca `GET /api/eval/summary`.

**Tech Stack:** Python 3.12, Typer, SQLModel, pytest, typer.testing.CliRunner, YAML, CSV. Next.js 16 (halaman Bukti sudah ada, tidak diubah).

**Spec:** `docs/superpowers/specs/2026-10-28-empu-design.md` bagian 14 (Evaluasi) dan bagian 6 layar S8.

## Global Constraints

- **Tes tidak boleh memanggil API sungguhan.**
- **Tidak ada angka evaluasi buatan.** Angka di layar Bukti hanya dari `latest.json` hasil `empu eval run`. Jangan pernah menulis angka ke JSON dengan tangan.
- Gold yang belum dicek manusia berstatus `annotator=DRAFT` dan **tidak boleh** menghasilkan `latest.json`.
- Kode dan identifier bahasa Inggris; dokumen bahasa Indonesia.
- Jangan menyentuh `data/`, `data-uji/`, `arsip-hidup-batik/` selain membaca.
- `api/eval/results/latest.json` **boleh** di-commit (tidak ada di `.gitignore`); `data/` tidak.

## Review Focus

1. **Gold melingkar.** `empu eval draft-gold` menyalin prediksi model menjadi gold. Kalau file itu dipakai apa adanya, `speech_recall` akan ≈1,0 dan angkanya bohong. (Task 1)
2. **Klip tanpa rekaman.** `test-set.yaml` memuat klip `internal_eval` yang videonya tidak ada di DB; tanpa filter, halaman publik menampilkan baris penuh "—". (Task 2)
3. **Klip tanpa gold.** `ccby-nyanting` belum punya CSV; `_gold_path` mengembalikan `None` dan runner menulis `n_pred` saja — halaman menampilkan "—" seolah gagal. (Task 4)
4. **Baseline ASR hilang.** `_find_vtt` mencari di `EMPU_TESTDATA_DIR`; kalau tidak ada, kolom baseline kosong. Bukan bug, tapi harus jujur di halaman. (Task 5)
5. **Angka tanpa mode pipeline.** `latest.json` mencatat `mode` (A/B) dan `pack`, tetapi halaman Bukti tidak menampilkannya; juri tidak bisa tahu angka itu dari mode apa. (Task 5)

---

## File Map

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/evaluation/gold.py` | Modify | `has_draft_rows(rows)` |
| `api/empu/cli.py` | Modify | `eval run --only`, penjaga DRAFT, `--allow-draft` |
| `api/tests/test_eval_cli.py` | Create | Tes filter, penjaga DRAFT, penulisan hasil |
| `docs/eval/kunci-jawaban/ccby-macam-canting.csv` | Modify | Review manusia, `annotator` diisi nama |
| `docs/eval/kunci-jawaban/ccby-nyanting.csv` | Create | Draft lalu review manusia |
| `api/eval/results/latest.json` | Create | Keluaran `empu eval run` |
| `web/app/evidence/page.tsx` | Modify | Menampilkan pack, mode, dan tanggal ukur |

---

### Task 1: Tolak gold yang belum dicek manusia

**Files:**
- Modify: `api/empu/evaluation/gold.py`
- Modify: `api/empu/cli.py:380-421`
- Test: `api/tests/test_eval_cli.py`

**Interfaces:**
- Produces:
  - `has_draft_rows(rows: list[GoldRow]) -> bool` — `True` bila ada `annotator == "DRAFT"`
  - `empu eval run … [--allow-draft]` — tanpa flag itu, keluar dengan kode 2 dan pesan yang menyebut file yang masih DRAFT

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_eval_run_refuses_draft_gold(tmp_path):
    # gold CSV berisi satu baris annotator=DRAFT, satu rekaman di DB,
    # test set berisi satu klip yang youtube_id-nya cocok dengan rekaman itu
    r = CliRunner().invoke(app, [
        "eval", "run",
        "--set", str(set_path),
        "--gold", str(gold_dir),
        "--out", str(out),
    ])
    assert r.exit_code == 2
    assert "DRAFT" in r.output
    assert not out.exists()


def test_eval_run_accepts_checked_gold(tmp_path):
    # gold yang sama, annotator="syafiq"
    r = CliRunner().invoke(app, [
        "eval", "run",
        "--set", str(set_path),
        "--gold", str(gold_dir),
        "--out", str(out),
    ])
    assert r.exit_code == 0
    assert out.exists()
```

Gunakan pola `CliRunner` + `settings` yang sudah ada di `api/tests/test_cli.py`.

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_eval_cli.py -k draft -v`
Expected: FAIL — tes pertama dapat `exit_code == 0`, atau `has_draft_rows` belum ada.

- [ ] **Step 3: Implementasikan**

`has_draft_rows` memeriksa `row.annotator.strip().upper() == "DRAFT"`. Di `eval_run`, kumpulkan `gold_path` per klip lebih dulu; bila `has_draft_rows(...)` dan bukan `--allow-draft`, cetak `error: gold still marked DRAFT: <path>` ke stderr lalu `raise typer.Exit(2)` **sebelum** menulis `out`.

- [ ] **Step 4: Jalankan tesnya**

Run: `cd api && uv run pytest tests/test_eval_cli.py -v`
Expected: PASS (2 tes).

- [ ] **Step 5: Commit**

```bash
git add api/empu/evaluation/gold.py api/empu/cli.py api/tests/test_eval_cli.py
git commit -m "feat(eval): refuse to publish numbers from draft gold"
```

---

### Task 2: Filter klip dengan `--only`

**Files:**
- Modify: `api/empu/cli.py:380-421`
- Test: `api/tests/test_eval_cli.py`

**Interfaces:**
- Produces: `empu eval run --only <clip-id>` (boleh diulang). Tanpa `--only`, semua klip diproses seperti sekarang.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_eval_run_only_limits_clips(tmp_path):
    # test set berisi dua klip; hanya satu yang punya rekaman + gold
    r = CliRunner().invoke(app, [
        "eval", "run",
        "--set", str(set_path),
        "--gold", str(gold_dir),
        "--out", str(out),
        "--only", "ccby-macam-canting",
    ])
    assert r.exit_code == 0
    payload = json.loads(out.read_text())
    assert list(payload["clips"]) == ["ccby-macam-canting"]
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_eval_cli.py -k only -v`
Expected: FAIL — Typer menolak opsi yang tidak dikenal.

- [ ] **Step 3: Implementasikan**

`only: list[str] = typer.Option([], "--only")`. Saring `_clips_from_set(set_path)` dengan `if only and item["id"] not in only: continue`. Id yang tidak ada di set → `error: unknown clip ids: […]`, exit 2.

- [ ] **Step 4: Jalankan tesnya**

Run: `cd api && uv run pytest tests/test_eval_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/empu/cli.py api/tests/test_eval_cli.py
git commit -m "feat(eval): score only the clips you ask for"
```

---

### Task 3: Draft gold untuk klip kedua

**Files:**
- Create: `docs/eval/kunci-jawaban/ccby-nyanting.csv`

**Interfaces:**
- Consumes: `empu eval draft-gold ccby-nyanting`
- Produces: CSV 11 kolom yang sama dengan `ccby-macam-canting.csv`, semua baris `annotator=DRAFT`.

- [ ] **Step 1: Hasilkan draft**

Run: `cd api && uv run empu eval draft-gold ccby-nyanting`
Expected: menulis `docs/eval/kunci-jawaban/ccby-nyanting.csv` dan mencetak jumlah baris.

- [ ] **Step 2: Review manusia (Syafiq, bukan otomatis)**

Tonton rekaman `Proses nyanting batik tulis` (508 s) sambil membuka CSV. Untuk **setiap** baris, periksa tiga hal dan perbaiki bila salah:
1. Istilahnya benar-benar **diucapkan** di `t_start`–`t_end` itu (bukan hanya terlihat).
2. `source` sesuai: `speech` hanya bila terdengar; `visual_only` bila hanya terlihat; `on_screen_text` bila hanya terbaca.
3. Ejaan `term` mengikuti bentuk baku, bukan bentuk salah dengar.

Tambahkan baris yang **terlewat** (istilah yang diucapkan tapi tidak ada di draft). Hapus baris yang tidak ada di video. Setiap baris yang sudah dicek: isi `annotator` dengan nama Anda.

- [ ] **Step 3: Verifikasi tidak ada DRAFT tersisa**

Run: `grep -c DRAFT docs/eval/kunci-jawaban/ccby-nyanting.csv || true`
Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add docs/eval/kunci-jawaban/ccby-nyanting.csv
git commit -m "docs(eval): gold answer key for the nyanting clip"
```

---

### Task 4: Review gold klip pertama

**Files:**
- Modify: `docs/eval/kunci-jawaban/ccby-macam-canting.csv`

**Interfaces:**
- Produces: file yang sama dengan `annotator` terisi dan tanpa baris `DRAFT`.

- [ ] **Step 1: Review manusia (Syafiq)**

26 baris, semua bertanda `DRAFT`. Kriteria identik dengan Task 3 Step 2. Perhatikan khusus baris `source=visual_only` (25,5–28,0 dan 195–218): pastikan memang tidak diucapkan.

- [ ] **Step 2: Verifikasi**

Run: `grep -c DRAFT docs/eval/kunci-jawaban/ccby-macam-canting.csv || true`
Expected: `0`.

- [ ] **Step 3: Commit**

```bash
git add docs/eval/kunci-jawaban/ccby-macam-canting.csv
git commit -m "docs(eval): check the macam-canting gold answer key"
```

---

### Task 5: Hasilkan dan publikasikan angkanya

**Files:**
- Create: `api/eval/results/latest.json`

**Interfaces:**
- Consumes: `empu eval run`, gold dari Task 3 dan 4
- Produces: `latest.json` dengan `clips`, `aggregate`, `notes` yang dibaca `GET /api/eval/summary`

- [ ] **Step 1: Jalankan evaluasi untuk dua klip demo**

Run:

```bash
cd api && uv run empu eval run \
  --set ../docs/eval/test-set.yaml \
  --gold ../docs/eval/kunci-jawaban \
  --out eval/results/latest.json \
  --only ccby-macam-canting --only ccby-nyanting
```

Expected: `wrote eval/results/latest.json: 2 clips`.

- [ ] **Step 2: Periksa angkanya masuk akal**

Run: `cd api && python -c "import json; d=json.load(open('eval/results/latest.json')); print(json.dumps(d['aggregate'], indent=1)); print(d['notes'])"`

Expected: `aggregate` berisi angka 0–1, bukan `null` semua. `notes` kosong atau hanya menjelaskan baseline yang tidak tersedia. **Kalau `speech_recall` ≥ 0,95, curigai gold belum benar-benar direview** — hentikan dan kembali ke Task 3/4.

- [ ] **Step 3: Verifikasi halaman Bukti**

Jalankan API dan web (`uv run uvicorn empu.app:create_app --factory --port 8000`, `pnpm dev`), buka `http://localhost:3000/evidence`.
Expected: empat kartu angka terisi, tabel berisi dua baris klip, tidak ada "—" di kolom yang datanya ada. Kalau baseline ASR kosong, biarkan "—" — itu jujur, bukan bug.

- [ ] **Step 4: Commit**

```bash
git add api/eval/results/latest.json
git commit -m "docs(eval): publish the first honest numbers on the evidence page"
```
---

### Task 6: Sebutkan mode, pack, dan tanggal pada halaman Bukti

**Files:**
- Modify: `web/app/evidence/page.tsx`

**Interfaces:**
- Consumes: `GET /api/eval/summary` → `{created_at, pack, mode, clips, aggregate, notes}`
- Produces: satu baris metadata di bawah subjudul: `pack · mode · created_at`

Tanpa ini, angka di halaman tidak bisa dipertanggungjawabkan: juri tidak tahu apakah itu Mode A atau B, pack versi apa, dan kapan diukur.

- [ ] **Step 1: Implementasikan**

Baca `data?.pack`, `data?.mode`, `data?.created_at`. Render baris `mono` berukuran 12px, warna `var(--color-neutral-700)`, tepat di bawah `<p>` subjudul. Bila `data` null, jangan render apa pun (halaman sudah punya keadaan kosong yang jujur).

- [ ] **Step 2: Verifikasi**

Run: `cd web && pnpm lint && pnpm build`
Expected: lolos.

Manual: buka `/evidence` dengan `latest.json` dari Task 5 → tampil mis. `batik_tulis@1.0 · mode B · 2026-11-01T…Z`. Hapus sementara `latest.json` → baris hilang, keadaan kosong tetap tampil.

- [ ] **Step 3: Commit**

```bash
git add web/app/evidence/page.tsx
git commit -m "feat(evidence): say which pack and mode the numbers come from"
```
