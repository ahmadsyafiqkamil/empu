# Eval Retrieval Ask Empu — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menghasilkan angka nyata untuk tahap *retrieve* Ask Empu — berapa sering entri yang seharusnya muncul benar-benar masuk daftar yang dikirim ke model — sehingga keputusan "perlu semantic/embedding atau tidak" diambil dari bukti, bukan selera.

**Architecture:** `prefilter` sekarang mencampur dua hal: memberi peringkat dan memotong. Pisahkan menjadi `rank_rows(question, rows) -> list[IndexEntry]` (murni, memberi peringkat seluruh baris) dan `prefilter` (memotong + mengurutkan ulang berdasarkan id, perilaku lama). Di atas `rank_rows`, modul evaluasi baru menghitung recall@k terhadap daftar pertanyaan yang punya jawaban yang diharapkan. Tidak ada perubahan pada jalur jawaban; ini pengukuran.

**Tech Stack:** Python 3.12, Typer, SQLModel, pytest, `typer.testing.CliRunner`, CSV.

**Spec:** `docs/superpowers/specs/2026-10-31-ask-empu-design.md` bagian 7 (pendekatan A) dan 9.3 (alur), serta `docs/superpowers/specs/2026-10-28-empu-design.md` bagian 14 (budaya evaluasi).

## Global Constraints

- **Tidak ada angka buatan.** Laporan retrieval hanya dari menjalankan `rank_rows` pada data nyata.
- **Jangan mengubah jalur jawaban** di plan ini. `prefilter` harus berperilaku identik setelah refactor (diuji).
- Pengetahuan keahlian hanya di craft pack / berkas data; tidak boleh ada istilah batik di `api/empu/**`.
- Tes tidak memanggil API sungguhan.
- Kode dan identifier bahasa Inggris; dokumen bahasa Indonesia.

## Review Focus

1. **Refactor mengubah perilaku.** `prefilter` mengembalikan baris urut id; kalau refactor mengembalikan urut skor, prompt menjadi tidak deterministik dan tes cache bisa goyah. (Task 1)
2. **Pertanyaan tanpa entri yang diharapkan.** Pertanyaan di luar arsip tidak boleh dihitung sebagai kegagalan retrieval — ia memang harus ditolak. (Task 2)
3. **Sinonim antar-bahasa.** Pertanyaan Inggris tentang istilah Jawa (mis. "wax pen" untuk entri yang gloss_en-nya "copper pen for hot wax") adalah kasus yang paling mungkin meleset; harus ada di daftar pertanyaan. (Task 3)
4. **Skala kecil menipu.** Dengan 29 entri publik dan batas 60, `prefilter` tidak memotong apa pun, jadi recall@4 akan selalu 1,0 dan tidak mengukur apa pun. Angka harus dilaporkan bersama `n_rows` dan `limit`. (Task 2)
5. **Laporan tanpa keputusan.** Angka recall yang tidak diikuti keputusan (tambah alias / tambah embedding / biarkan) tidak berguna. (Task 4)

---

## File Map

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/empu/ask/index.py` | Modify | `rank_rows`; `prefilter` memakainya |
| `api/tests/test_ask_index.py` | Modify | tes `rank_rows`, tes `prefilter` tetap sama |
| `api/empu/evaluation/retrieval.py` | Create | `RetrievalQuestion`, `load_questions`, `evaluate_retrieval`, `RetrievalReport` |
| `api/empu/cli.py` | Modify | `empu eval retrieval` |
| `api/tests/test_eval_retrieval.py` | Create | tes hitungan recall dan parsing CSV |
| `docs/eval/pertanyaan-retrieval.csv` | Create | 20 pertanyaan + entri yang diharapkan |

---

### Task 1: Pisahkan peringkat dari pemotongan

**Files:**
- Modify: `api/empu/ask/index.py`
- Test: `api/tests/test_ask_index.py`

**Interfaces:**
- Produces: `rank_rows(question: str, rows: list[IndexEntry]) -> list[IndexEntry]` — seluruh baris, urut skor menurun lalu `id` menaik.
- `prefilter(question, rows, limit=60)` tetap dengan tanda tangan dan perilaku yang sama (≤limit → urut id; >limit → ambil `limit` teratas dari `rank_rows`, lalu urut id).

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_rank_rows_orders_by_score_then_id(session):
    # bangun baris dengan build_index, pola yang sudah dipakai di file ini
    rows = [
        build_index([(_entry(session, a, "mori"), [])])[0],
        build_index([(_entry(session, a, "canting"), [])])[0],
        build_index([(_entry(session, a, "nembok"), [])])[0],
    ]
    ranked = rank_rows("apa itu canting?", rows)
    assert [r.term for r in ranked] == ["canting", "mori", "nembok"]


def test_rank_rows_keeps_every_row(session):
    rows = [build_index([(_entry(session, a, f"t{i}"), [])])[0] for i in range(10)]
    assert len(rank_rows("t3", rows)) == 10
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_ask_index.py -k rank_rows -v`
Expected: FAIL — `ImportError: cannot import name 'rank_rows'`.

- [ ] **Step 3: Implementasikan**

Pindahkan badan penskoran `_score`/`_blob` ke `rank_rows` (tanpa memotong). `prefilter` menjadi pemanggil tipis. Jangan mengubah bobot atau ambang.

- [ ] **Step 4: Jalankan tesnya, termasuk tes `prefilter` yang lama**

Run: `cd api && uv run pytest tests/test_ask_index.py -v && uv run pytest -q`
Expected: PASS semuanya — terutama lima tes `prefilter` yang sudah ada.

- [ ] **Step 5: Commit**

```bash
git add api/empu/ask/index.py api/tests/test_ask_index.py
git commit -m "refactor(ask): separate ranking from truncation"
```

---

### Task 2: Modul evaluasi retrieval

**Files:**
- Create: `api/empu/evaluation/retrieval.py`
- Test: `api/tests/test_eval_retrieval.py`

**Interfaces:**
- Consumes: `rank_rows`, `IndexEntry`
- Produces:
  - `@dataclass(frozen=True) RetrievalQuestion: question: str; expected: tuple[str, ...]`
  - `load_questions(path: Path) -> list[RetrievalQuestion]` — CSV berheader `question,expected`; `expected` dipisah `|`; baris dengan `expected` kosong dilewati.
  - `@dataclass(frozen=True) RetrievalReport: n_questions: int; n_rows: int; k: int; question_recall: float; term_recall: float; misses: list[dict]`
  - `evaluate_retrieval(questions, rows, *, k: int = 4) -> RetrievalReport`

Definisi angka (dipin):
- `question_recall` = fraksi pertanyaan yang **semua** `expected`-nya ada di `k` baris teratas.
- `term_recall` = fraksi seluruh pasangan (pertanyaan, expected term) yang ditemukan di `k` teratas.
- `misses` hanya memuat pertanyaan yang gagal, dengan `{"question", "missing", "rank"}` di mana `rank` = posisi 1-based expected pertama yang tidak masuk `k` (dari `rank_rows`), atau `null` bila tidak ditemukan sama sekali.
- Perbandingan term memakai `casefold()` pada `IndexEntry.term` dan pada `expected`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def _rows(session, a, terms: list[str]):
    # pola yang sama dengan test_ask_index.py: entri lalu build_index
    return [build_index([(_entry(session, a, t), [])])[0] for t in terms]


def test_evaluate_counts_a_full_hit(session):
    a = make_archive(session)
    rows = _rows(session, a, ["canting", "mori"])
    qs = [RetrievalQuestion("apa itu canting?", ("canting",))]
    rep = evaluate_retrieval(qs, rows, k=1)
    assert rep.question_recall == 1.0 and rep.term_recall == 1.0
    assert rep.misses == []


def test_evaluate_reports_the_rank_of_a_miss(session):
    a = make_archive(session)
    rows = _rows(session, a, ["mori", "canting"])
    qs = [RetrievalQuestion("apa itu canting?", ("canting",))]
    rep = evaluate_retrieval(qs, rows, k=1)
    assert rep.question_recall == 0.0
    assert rep.misses[0]["missing"] == ["canting"]


def test_load_questions_parses_pipe_separated_expected(tmp_path):
    p = tmp_path / "q.csv"
    p.write_text("question,expected\napa itu canting?,canting\n,\n")
    assert load_questions(p) == [RetrievalQuestion("apa itu canting?", ("canting",))]
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_eval_retrieval.py -v`
Expected: FAIL — `No module named 'empu.evaluation.retrieval'`.

- [ ] **Step 3: Implementasikan `retrieval.py`**

- [ ] **Step 4: Jalankan tesnya**

Run: `cd api && uv run pytest tests/test_eval_retrieval.py -v`
Expected: PASS (3 tes).

- [ ] **Step 5: Commit**

```bash
git add api/empu/evaluation/retrieval.py api/tests/test_eval_retrieval.py
git commit -m "feat(eval): measure retrieval recall for Ask Empu"
```

---

### Task 3: Perintah `empu eval retrieval`

**Files:**
- Modify: `api/empu/cli.py`
- Test: `api/tests/test_eval_retrieval.py`

**Interfaces:**
- Produces: `empu eval retrieval --archive <slug> --questions <path> [--scope public|studio] [--k 4]`
- Mencetak `rows=N k=K questions=Q question_recall=… term_recall=…`, lalu satu baris per miss.

- [ ] **Step 1: Tulis tes yang gagal**

```python
def test_eval_retrieval_cli_reports_numbers(session, tmp_path, monkeypatch):
    ...  # satu arsip publik, dua entri, satu pertanyaan yang cocok
    r = CliRunner().invoke(cli.app, ["eval", "retrieval", "--archive", "uji",
                                     "--questions", str(qfile), "--k", "1"])
    assert r.exit_code == 0
    assert "question_recall=1.00" in r.output
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd api && uv run pytest tests/test_eval_retrieval.py -k cli -v`
Expected: FAIL — `No such command 'retrieval'`.

- [ ] **Step 3: Implementasikan**

Arsip di-resolve per slug; baris dibangun dari `collect_entries(session, archive.id, scope)` → `build_index(...)`. Arsip kosong → exit 2 dengan pesan jelas.

- [ ] **Step 4: Jalankan seluruh suite dan ruff**

Run: `cd api && uv run pytest -q && uv run ruff check .`
Expected: hijau dan bersih.

- [ ] **Step 5: Commit**

```bash
git add api/empu/cli.py api/tests/test_eval_retrieval.py
git commit -m "feat(cli): empu eval retrieval"
```

---

### Task 4: Daftar pertanyaan dan keputusan

**Files:**
- Create: `docs/eval/pertanyaan-retrieval.csv`
- Modify: `docs/reference/hasil-gate-ask.md`

**Interfaces:**
- Consumes: `empu eval retrieval`

- [ ] **Step 1: Tulis 20 pertanyaan (Syafiq)**

Kolom `question,expected`. `expected` = istilah baku (`entry.term`) yang **harus** muncul agar jawabannya benar, dipisah `|` bila lebih dari satu. Wajib memuat:
- 5 pertanyaan definisi berbahasa Indonesia;
- 5 pertanyaan proses/tahapan;
- 3 pertanyaan berbahasa Jawa;
- 4 pertanyaan berbahasa Inggris yang menyebut istilah dengan kata lain (mis. "wax pen", "remove the wax");
- 3 pertanyaan perbandingan dua istilah (`a|b`).

Jangan masukkan pertanyaan di luar arsip.

- [ ] **Step 2: Ukur**

Run:

```bash
cd api && uv run empu eval retrieval --archive batik-tulis \
  --questions ../docs/eval/pertanyaan-retrieval.csv --k 4
```

Expected: mencetak `rows=N k=4 questions=20 question_recall=… term_recall=…`.

- [ ] **Step 3: Putuskan, dengan ambang tertulis**

| `question_recall` @4 | Keputusan |
|---|---|
| ≥ 0.90 | **Berhenti.** Retrieval leksikal cukup; jangan tambah embedding. Catat angkanya sebagai bukti. |
| 0.75–0.89 | **Alias dulu.** Tambahkan sinonim ke `packs/batik_tulis.yaml` (`variants` sudah ada; tambah istilah Inggris/lokal yang wajar), ukur ulang. Embedding hanya kalau masih < 0.90 sesudahnya. |
| < 0.75 | **Semantic layak dipertimbangkan.** Bawa angkanya ke Syafiq sebelum menulis kode apa pun. |

Tulis hasil dan keputusannya di `docs/reference/hasil-gate-ask.md` bagian baru "Retrieval", termasuk `rows`, `k`, dan daftar miss.

- [ ] **Step 4: Commit**

```bash
git add docs/eval/pertanyaan-retrieval.csv docs/reference/hasil-gate-ask.md
git commit -m "docs(eval): retrieval questions and their measured recall"
```
