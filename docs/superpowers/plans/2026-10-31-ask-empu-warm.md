# `empu ask warm` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pertanyaan yang akan dipakai di video demo sudah terjawab dan tersimpan di cache sebelum kamera menyala, sehingga demo tidak pernah menampilkan tunggu 6–9 detik — tanpa memalsukan data.

**Architecture:** Cache jawaban Ask sudah ada (`ResponseCache` di `data/cache/ask`, kunci memuat scope + archive + revisi arsip + pertanyaan ternormalisasi). Yang ditambahkan hanya fungsi `warm_questions` yang memanggil `answer_question` untuk daftar pertanyaan, dan satu perintah CLI tipis di atasnya. Karena jalurnya sama persis dengan permintaan pengguna sungguhan, jawaban yang dihasilkan tetap nyata dan buktinya tetap divalidasi.

**Tech Stack:** Python 3.12, Typer, SQLModel, pytest, `typer.testing.CliRunner`.

**Spec:** `docs/superpowers/specs/2026-10-31-ask-empu-design.md` bagian 9.3 (alur) dan A6 (cache).

## Global Constraints

- **Jangan memalsukan jawaban.** `warm` hanya mengisi cache lewat jalur produksi `answer_question`; tidak boleh menulis payload cache dengan tangan.
- Semua panggilan Meta lewat `MetaClient`; tes tidak boleh memanggil jaringan.
- Jalur cache harus sama dengan server: `settings.data_dir / "cache" / "ask"`. Menjalankan `warm` dengan `EMPU_DATA_DIR` berbeda menghasilkan cache yang tidak terpakai.
- Kode dan identifier bahasa Inggris; dokumen bahasa Indonesia.
- Jangan menaruh istilah keahlian di `api/empu/**` (ada tes penjaga); daftar pertanyaan hidup di berkas data.

## Review Focus

1. **Cache tidak terpakai.** `warm` dijalankan dengan `EMPU_DATA_DIR` lain → server tidak melihat cache dan demo tetap lambat. (Task 1, verifikasi Task 3)
2. **Arsip berubah setelah warm.** Revisi arsip adalah bagian dari kunci cache, jadi menerima satu entri membatalkan seluruh cache. Perilaku ini sudah diuji di `api/tests/test_ask_engine.py` (`test_cached_refusal_is_not_served_after_the_entry_is_accepted`); konsekuensinya operasional: `warm` harus dijalankan **ulang** setelah review terakhir sebelum rekaman. (Task 3)
3. **Satu pertanyaan gagal menghentikan semuanya.** Model bisa gagal untuk satu pertanyaan; sisanya harus tetap diproses. (Task 1)
4. **Pertanyaan kosong atau komentar di berkas.** Berkas daftar pertanyaan akan memuat baris kosong dan `#`. (Task 1)
5. **Warm membakar kredit tanpa disadari.** Setiap pertanyaan = satu panggilan model sungguhan; perintah harus mencetak berapa panggilan yang terjadi. (Task 1)

---

## File Map

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/ask/warm.py` | Create | `WarmResult`, `warm_questions`, `read_questions` |
| `api/empu/ask/__init__.py` | Modify | ekspor `warm_questions` |
| `api/empu/cli.py` | Modify | sub-app `ask`, perintah `warm` |
| `api/tests/test_ask_warm.py` | Create | Tes pemrosesan daftar, kegagalan sebagian, cache terisi |
| `docs/demo/questions.txt` | Create | Pertanyaan yang dipakai di video |

---

### Task 1: Fungsi `warm_questions`

**Files:**
- Create: `api/empu/ask/warm.py`
- Modify: `api/empu/ask/__init__.py`
- Test: `api/tests/test_ask_warm.py`

**Interfaces:**
- Consumes: `answer_question(session, *, archive_id, question, scope, ask_model, cache, model, pack_name, max_entries=60) -> AskResult` dan `AskError` dari `empu.ask.engine`
- Produces:
  - `@dataclass(frozen=True) WarmResult: question: str; refused: bool; cached: bool; n_evidence: int; error: str | None`
  - `read_questions(path: Path) -> list[str]` — satu pertanyaan per baris, buang baris kosong dan yang diawali `#`, buang duplikat dengan mempertahankan urutan
  - `warm_questions(session, *, archive_id: int, questions: list[str], ask_model, cache, model: str, pack_name: str, scope: str = "public") -> list[WarmResult]`

Aturan (dipin): setiap pertanyaan diproses berurutan; `AskError`, `MetaAPIError`, dan `httpx.HTTPError` ditangkap **per pertanyaan** dan dicatat di `WarmResult.error`, lalu lanjut ke pertanyaan berikutnya. `cached` diambil dari `AskResult.cached` — jadi menjalankan `warm` dua kali menunjukkan `cached=True` pada putaran kedua.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_read_questions_skips_blanks_comments_and_duplicates(tmp_path):
    p = tmp_path / "q.txt"
    p.write_text("apa itu canting\n\n# catatan\n  apa itu canting  \ncara nglorod\n")
    assert read_questions(p) == ["apa itu canting", "cara nglorod"]


def test_warm_fills_the_cache_and_reports_it(session, tmp_path):
    a, ids = seed_two_public_entries(session)
    calls: list[str] = []
    model = fake_model([{"answer": "Canting.", "lang": "id",
                         "entry_ids": [ids[0]], "insufficient": False}], calls)
    cache = ResponseCache(tmp_path / "cache")

    first = warm_questions(session, archive_id=a.id, questions=["apa itu canting"],
                           ask_model=model, cache=cache, model="muse-test",
                           pack_name="batik tulis")
    second = warm_questions(session, archive_id=a.id, questions=["apa itu canting"],
                            ask_model=model, cache=cache, model="muse-test",
                            pack_name="batik tulis")

    assert len(calls) == 1
    assert first[0].cached is False and first[0].refused is False
    assert second[0].cached is True


def test_one_failure_does_not_stop_the_rest(session, tmp_path):
    a, ids = seed_two_public_entries(session)
    def model(prompt: str):
        if "GAGAL" in prompt:
            raise MetaAPIError(500, "boom")
        return AnalyzeResult(raw={}, text="", parsed={"answer": "ok", "lang": "id",
                               "entry_ids": [ids[0]], "insufficient": False},
                             parse_error=None, usage={}, latency_s=0.0)

    out = warm_questions(session, archive_id=a.id,
                         questions=["apa itu GAGAL", "apa itu canting"],
                         ask_model=model, cache=ResponseCache(tmp_path / "c"),
                         model="muse-test", pack_name="batik tulis")

    assert out[0].error is not None
    assert out[1].error is None and out[1].refused is False
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_ask_warm.py -v`
Expected: FAIL — `No module named 'empu.ask.warm'`.

- [ ] **Step 3: Implementasikan `warm.py`**

Jangan menduplikasi logika jawaban: panggil `answer_question` apa adanya. Tangkap `(AskError, MetaAPIError, httpx.HTTPError)` per pertanyaan.

- [ ] **Step 4: Ekspor dari `__init__.py`** (`WarmResult`, `read_questions`, `warm_questions`).

- [ ] **Step 5: Jalankan tesnya dan seluruh suite**

Run: `cd api && uv run pytest tests/test_ask_warm.py -v && uv run pytest -q`
Expected: PASS; suite hijau.

- [ ] **Step 6: Commit**

```bash
git add api/empu/ask/warm.py api/empu/ask/__init__.py api/tests/test_ask_warm.py
git commit -m "feat(ask): warm the answer cache ahead of a demo"
```

---

### Task 2: Perintah `empu ask warm`

**Files:**
- Modify: `api/empu/cli.py`
- Test: `api/tests/test_ask_warm.py`

**Interfaces:**
- Produces:
  - `ask_app = typer.Typer(...)`; `app.add_typer(ask_app, name="ask")`
  - `empu ask warm --archive <slug> --questions <path> [--scope public|studio]`
  - Mencetak satu baris per pertanyaan: `<cached?> <refused?> <n_evidence> <question>`, lalu ringkasan `warmed N of M (K model calls)`.

Aturan: arsip tidak ada → exit 2. Berkas pertanyaan tidak ada → exit 2. `--scope studio` butuh `STUDIO_KEY`? Tidak — CLI berjalan di server sendiri, jadi scope studio diizinkan tanpa kunci. Semua panggilan model memakai `MetaClient.from_settings`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_ask_warm_reports_per_question(session, tmp_path, monkeypatch):
    # arsip "uji" dengan dua entri publik; qfile berisi dua pertanyaan;
    # monkeypatch klien Meta supaya mengembalikan payload tetap (tanpa jaringan)
    r = CliRunner().invoke(cli.app, ["ask", "warm", "--archive", "uji",
                                     "--questions", str(qfile)])
    assert r.exit_code == 0
    assert "warmed 2 of 2" in r.output
    assert "model calls" in r.output


def test_ask_warm_unknown_archive(tmp_path):
    qfile = tmp_path / "q.txt"
    qfile.write_text("apa itu canting\n")
    r = CliRunner().invoke(cli.app, ["ask", "warm", "--archive", "tidak-ada",
                                     "--questions", str(qfile)])
    assert r.exit_code == 2
    assert "not found" in r.output
```

Tes meng-override factory klien dengan `monkeypatch` pada fungsi yang dipakai CLI (mis. `make_client`), bukan memanggil jaringan.

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_ask_warm.py -k cli -v`
Expected: FAIL — `No such command 'ask'`.

- [ ] **Step 3: Implementasikan perintah**

Resolusi arsip lewat `select(Archive).where(Archive.slug == slug)`; `pack_name` dari `load_pack(archive.craft_pack_id, settings.packs_dir).name.en` dengan fallback ke id pack (sama seperti `_pack_name` di `routes/ask.py` — jangan duplikasi: pindahkan helper itu ke `empu/ask/engine.py` sebagai `pack_display_name(archive, settings)` dan pakai dari kedua tempat).

- [ ] **Step 4: Jalankan seluruh suite dan ruff**

Run: `cd api && uv run pytest -q && uv run ruff check .`
Expected: hijau dan bersih.

- [ ] **Step 5: Commit**

```bash
git add api/empu/cli.py api/empu/ask/engine.py api/empu/routes/ask.py api/tests/test_ask_warm.py
git commit -m "feat(cli): empu ask warm"
```

---

### Task 3: Daftar pertanyaan demo dan verifikasi

**Files:**
- Create: `docs/demo/questions.txt`

**Interfaces:**
- Consumes: `empu ask warm`

- [ ] **Step 1: Tulis daftar pertanyaan demo**

Buat `docs/demo/questions.txt`, satu pertanyaan per baris, isinya **persis** pertanyaan yang akan diucapkan/diketik di video. Sertakan minimal: satu pertanyaan definisi (Indonesia), satu pertanyaan proses, satu pertanyaan bahasa Jawa, satu pertanyaan Inggris. Jangan sertakan pertanyaan yang di luar arsip — itu untuk ditunjukkan langsung, bukan di-warm.

- [ ] **Step 2: Warm pada data lokal**

Run:

```bash
cd api && uv run empu ask warm --archive batik-tulis \
  --questions ../docs/demo/questions.txt
```

Expected: setiap baris `cached=False` pada putaran pertama, ringkasan `warmed N of N`.

- [ ] **Step 3: Pastikan cache benar-benar terpakai**

Run perintah yang sama sekali lagi.
Expected: semua baris `cached=True`, dan ringkasan menunjukkan `0 model calls`.

- [ ] **Step 4: Verifikasi di UI**

Buka `/d/batik-tulis`, klik **Ask**, ketik salah satu pertanyaan dari berkas, kirim.
Expected: jawaban muncul hampir seketika (tanpa jeda 6–9 detik). Respons jaringan membawa `"cached": true`.

- [ ] **Step 5: Ulangi di server sebelum rekaman**

Run (di dalam container API):

```bash
docker compose exec api uv run empu ask warm --archive batik-tulis \
  --questions /app/docs/demo/questions.txt
```

Catatan: berkas harus ikut ke image atau disalin ke container. Kalau tidak, jalankan dengan `--questions` yang menunjuk path di dalam container.

- [ ] **Step 6: Commit**

```bash
git add docs/demo/questions.txt
git commit -m "docs(demo): the questions the demo will ask"
```
