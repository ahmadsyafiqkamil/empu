# Rapikan Data Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Arsip demo hanya menampilkan rekaman yang boleh dan layak dilihat juri — tidak ada lagi rekaman berjudul "tes" di `/d/batik-tulis`, dan tidak ada risiko menampilkan video berlisensi standar.

**Architecture:** Tambah satu perintah CLI yang mengubah metadata rekaman secara aman (`empu recording edit`), lalu pakai perintah itu untuk mengganti judul dan menurunkan rekaman yang bukan untuk publik menjadi `source_kind=internal_eval` (yang otomatis menyembunyikannya lewat `empu.visibility.recording_is_public`). Tidak ada file media yang dihapus, jadi keputusan ini bisa dibalik.

**Tech Stack:** Python 3.12, Typer, SQLModel, pytest, typer.testing.CliRunner.

**Spec:** `docs/superpowers/specs/2026-10-28-empu-design.md` bagian 13 (Izin dan akses) dan `CLAUDE.md` aturan data/hak cipta.

## Global Constraints

- **Jangan hapus file media atau baris DB.** Menyembunyikan, bukan menghapus: `source_kind=internal_eval` adalah mekanisme yang sudah ada dan bisa dibalik.
- **Video berlisensi standar tidak pernah publik**, tidak boleh muncul di demo, kamus, maupun ekspor. Hanya `internal_eval`.
- Perubahan data ini terjadi di `data/empu.db` yang **tidak di-commit**; perintah yang sama harus dijalankan juga di server setelah deploy.
- Kode dan identifier bahasa Inggris; dokumen bahasa Indonesia.
- Jangan menyentuh `data-uji/` atau `arsip-hidup-batik/`.

## Review Focus

1. **Rekaman "tes" lolos ke publik.** Dua rekaman berjudul `Tes`/`tes` di arsip `batik-tulis` lolos `recording_is_public` dan menjadi sumber 11 dari 29 entri publik — termasuk untuk sitasi Ask Empu. (Task 2)
2. **Lisensi.** Kalau rekaman itu potongan video YouTube berlisensi standar, mempublikasikannya melanggar aturan proyek sendiri. (Task 2, keputusan eksplisit)
3. **Kamus menipis setelah disembunyikan.** Menyembunyikan kedua rekaman menurunkan `validated_count`; pastikan angkanya masih pantas dan tidak ada entri yang kehilangan semua bukti publik. (Task 4)
4. **Judul gamelan belum layak.** Arsip `gamelan` tampil publik sebagai "Living Archive - Gamelan" dengan rekaman bernama `tes gamelan`, `Gamelan 2`, `Gamelan part 2`. (Task 3)
5. **Perubahan hanya di lokal.** DB di server tidak ikut berubah; tanpa menjalankan ulang perintahnya di sana, juri tetap melihat "tes". (Task 5)

---

## File Map

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/cli.py` | Modify | sub-app `recording`, perintah `edit` |
| `api/tests/test_recording_cli.py` | Create | Tes `recording edit` |
| `data/empu.db` | Modify (tidak di-commit) | Metadata rekaman 6, 7, 8, 9, 10 |

---

### Task 1: Perintah `empu recording edit`

**Files:**
- Modify: `api/empu/cli.py` (dekat `reprocess`, setelah `process_cmd`)
- Test: `api/tests/test_recording_cli.py`

**Interfaces:**
- Produces:
  - `recording_app = typer.Typer(...)`; `app.add_typer(recording_app, name="recording")`
  - `empu recording edit <recording_id> [--title TEXT] [--source-kind own_recording|cc_by_video|internal_eval]`
  - Mencetak `recording <id>: title=… source_kind=…` setelah berhasil.

Aturan validasi (dipin):
- Rekaman tidak ada → `error: recording <id> not found`, exit 2.
- Tidak ada opsi yang diberikan → exit 2 dengan `error: nothing to change`.
- `--source-kind cc_by_video` ditolak (exit 2, `error: cc_by_video needs source_url, source_creator, license and attribution`) bila salah satu dari empat kolom itu kosong. Empat kolom itu **tidak** diubah perintah ini.
- Kolom lain (`status`, `consent_*`, path media) tidak disentuh.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_recording_edit_changes_title(session):
    rec = make_recording(session, make_archive(session), title="tes")
    r = CliRunner().invoke(cli.app, ["recording", "edit", str(rec.id), "--title", "Latihan"])
    assert r.exit_code == 0
    session.refresh(rec)
    assert rec.title == "Latihan"


def test_recording_edit_can_hide_a_recording(session):
    rec = make_recording(session, make_archive(session))
    r = CliRunner().invoke(
        cli.app, ["recording", "edit", str(rec.id), "--source-kind", "internal_eval"]
    )
    assert r.exit_code == 0
    session.refresh(rec)
    assert rec.source_kind is SourceKind.internal_eval
    assert recording_is_public(rec) is False


def test_recording_edit_refuses_cc_by_without_attribution(session):
    rec = make_recording(session, make_archive(session))
    r = CliRunner().invoke(
        cli.app, ["recording", "edit", str(rec.id), "--source-kind", "cc_by_video"]
    )
    assert r.exit_code == 2
    assert "attribution" in r.output


def test_recording_edit_unknown_id(session):
    assert CliRunner().invoke(cli.app, ["recording", "edit", "9999", "--title", "x"]).exit_code == 2


def test_recording_edit_requires_a_change(session):
    rec = make_recording(session, make_archive(session))
    assert CliRunner().invoke(cli.app, ["recording", "edit", str(rec.id)]).exit_code == 2
```

Tes memakai `settings` + DB sementara lewat fixture yang sudah ada di `api/tests/conftest.py`; CLI membaca `get_settings()` sehingga tes harus meng-override settings seperti tes CLI lain di `api/tests/test_cli.py`.

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_recording_cli.py -v`
Expected: FAIL — `No such command 'recording'`.

- [ ] **Step 3: Implementasikan**

`--title` bertipe `str | None`, `--source-kind` bertipe `SourceKind | None` (Typer memakai nilai enum sebagai pilihan). Terapkan perubahan, `session.add`, `session.commit()`.

- [ ] **Step 4: Jalankan tesnya dan seluruh suite**

Run: `cd api && uv run pytest tests/test_recording_cli.py -v && uv run pytest -q`
Expected: PASS; suite tetap hijau.

- [ ] **Step 5: Commit**

```bash
git add api/empu/cli.py api/tests/test_recording_cli.py
git commit -m "feat(cli): edit a recording's title and source kind"
```

---

### Task 2: Putuskan dan terapkan nasib dua rekaman "tes"

**Files:**
- Modify: `data/empu.db` (lokal, tidak di-commit)

**Interfaces:**
- Consumes: `empu recording edit` dari Task 1

Rekaman yang dimaksud: **id 6 (`Tes`) dan id 7 (`tes`)**, keduanya di arsip 1 (`batik-tulis`), `own_recording`, `source_url` kosong, durasi 180 s.

- [ ] **Step 1: Jawab satu pertanyaan (Syafiq)**

> Rekaman 6 dan 7 itu videonya apa — potongan video YouTube, rekaman sendiri, atau video uji sintetis?

- [ ] **Step 2: Terapkan cabangnya**

**Kalau potongan YouTube berlisensi standar, atau video uji sintetis** (bukan rekaman asli yang boleh dipublikasikan):

```bash
cd api
uv run empu recording edit 6 --source-kind internal_eval
uv run empu recording edit 7 --source-kind internal_eval
```

**Kalau rekaman sendiri yang layak tampil:** ganti judulnya, jangan disembunyikan.

```bash
cd api
uv run empu recording edit 6 --title "<judul yang menjelaskan isinya>"
uv run empu recording edit 7 --title "<judul yang menjelaskan isinya>"
```

- [ ] **Step 3: Verifikasi efeknya**

Run:

```bash
curl -s http://127.0.0.1:8000/api/public/archives/batik-tulis/recordings | python3 -m json.tool | grep '"title"'
```

Expected (cabang sembunyikan): hanya `Macam Canting dalam Batik Tulis` dan `Proses nyanting batik tulis`.

---

### Task 3: Ganti judul rekaman gamelan

**Files:**
- Modify: `data/empu.db` (lokal, tidak di-commit)

- [ ] **Step 1: Lihat judul sekarang**

Run: `sqlite3 data/empu.db "select id,title from recording where archive_id=3;"`

Expected: `8|tes gamelan`, `9|Gamelan 2`, `10|Gamelan part 2`.

- [ ] **Step 2: Ganti dengan judul yang menjelaskan isi**

Gunakan nama yang menyebut apa yang direkam, bukan nomor urut. Contoh bentuk (isi sesuai isi videonya):

```bash
cd api
uv run empu recording edit 8 --title "Kendang dan gending — sesi 1"
uv run empu recording edit 9 --title "Kendang dan gending — sesi 2"
uv run empu recording edit 10 --title "Kendang dan gending — sesi 3"
```

- [ ] **Step 3: Verifikasi**

Run: `curl -s http://127.0.0.1:8000/api/public/archives/gamelan/recordings | grep '"title"'`
Expected: tiga judul baru, tanpa kata "tes".

---

### Task 4: Periksa dampaknya pada kamus dan Ask Empu

**Files:** tidak ada (verifikasi)

- [ ] **Step 1: Hitung ulang entri publik**

Run:

```bash
curl -s http://127.0.0.1:8000/api/public/archives/batik-tulis | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['validated_count'], 'terms ·', d['recording_count'], 'recordings')"
```

Expected: angka yang jujur. Kalau cabang Task 2 adalah "sembunyikan", `validated_count` turun; catat angka barunya. **Jangan** menambal dengan entri karangan.

- [ ] **Step 2: Pastikan Ask Empu tidak menyitir entri yang hilang**

Run:

```bash
curl -s -X POST http://127.0.0.1:8000/api/public/archives/batik-tulis/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"apa itu canting"}' | python3 -m json.tool | head -30
```

Expected: `refused: false`, setiap `evidence[].entry.id` masih publik, dan setiap `occurrence.recording_id` termasuk rekaman yang tersisa di daftar Step 1.

- [ ] **Step 3: Hapus cache jawaban lama**

Cache Ask menyimpan id entri; entri yang baru disembunyikan akan dibuang saat hidrasi, tetapi jawabannya bisa jadi menyebut istilah yang sudah tidak tampil. Bersihkan agar demo tidak memutar jawaban lama:

```bash
rm -rf data/cache/ask
```

---

### Task 5: Terapkan hal yang sama di server

**Files:** tidak ada (operasional)

- [ ] **Step 1: Setelah deploy, jalankan perintah yang sama di server**

Run (di dalam container API):

```bash
docker compose exec api uv run empu recording edit 6 --source-kind internal_eval
docker compose exec api uv run empu recording edit 7 --source-kind internal_eval
docker compose exec api rm -rf /data/cache/ask
```

- [ ] **Step 2: Verifikasi dari luar**

Run: `curl -s https://<domain>/api/public/archives/batik-tulis/recordings | grep '"title"'`
Expected: sama dengan hasil Task 2 Step 3.
