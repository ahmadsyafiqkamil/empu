# H5 (Sen 2 Nov): Evaluasi Terukur dan Halaman Bukti

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Angka evaluasi jujur (recall, presisi, galat waktu, label sumber, kontrol musik, baseline ASR) tersimpan di `api/eval/results/latest.json` dan tampil di halaman Bukti. Gate 2.

**Architecture:** Kunci jawaban CSV per klip. Pencocokan greedy: `canon_key` sama dan |Δt| ≤ 5 s. CLI `empu eval run|draft-gold`. S8 membaca `GET /api/eval/summary` (publik). Baseline: subtitle YouTube vs varian pack. Halaman Bukti mode Mori; copy dan kartu angka: `desain.md` S8.

**Tech Stack:** csv, Canonicalizer H2-3, rapidfuzz, Next.js.

## Global Constraints

Semua butir `00-ikhtisar.md`. Khusus:
- Laporkan angka asli, termasuk yang gagal target.
- Video lisensi standar = `internal_eval`, tidak masuk demo/ekspor/kamus.
- D8: `speech_heard` tidak dipakai. Istilah karangan = jumlah prediksi `source=speech` di klip kontrol.
- Tes evaluasi tidak memanggil Meta.

## Prasyarat
- H4 kamus hidup. Arsip demo punya entri accepted.
- File `.vtt` untuk klip uji ada di `data-uji/`.

## File yang disentuh di fase ini

| File | Aksi | Tanggung jawab |
|---|---|---|
| `api/tests/fixtures/eval/tiny.csv` | Create | fixture gold |
| `api/empu/evaluation/gold.py` | Create | parser CSV |
| `api/empu/evaluation/matching.py` | Create | greedy match |
| `api/empu/evaluation/metrics.py` | Create | metrik spec 14 |
| `api/empu/evaluation/baseline.py` | Create | VTT → Pred pack |
| `api/empu/evaluation/runner.py` | Create | satu run |
| `api/empu/cli.py` | Modify | `empu eval` |
| `api/empu/routes/eval.py` | Create | `GET /api/eval/summary` |
| `docs/eval/kunci-jawaban/*.csv` | Create | gold manusia |
| `api/eval/results/latest.json` | Create | angka (di-commit) |
| `web/app/evidence/page.tsx` | Create | S8 |

---

### Task H5-1: Parser kunci jawaban

**Files:**
- Create: `api/empu/evaluation/__init__.py`, `gold.py`
- Create: `api/tests/fixtures/eval/tiny.csv`
- Test: `api/tests/test_eval_gold.py`

**Interfaces:**
- `GoldRow` frozen dataclass: `clip_id, t_start, t_end, spoken, term, category, source, stage, visible_object, note, annotator`
- `load_gold(path: Path) -> list[GoldRow]` — abaikan `annotator=contoh`

tiny.csv:

```csv
clip_id,t_start,t_end,spoken,term,category,source,stage,visible_object,note,annotator
demo,85,88,pola,pola,stage,speech,memola,pensil,ok,syafiq
demo,66,68,nyamplung,nyamplung,tool_part,on_screen_text,,diagram,bukan ucapan,syafiq
demo,1,2,x,x,tool,speech,,,contoh,contoh
```

- [ ] **Step 1: Tes**

```python
# api/tests/test_eval_gold.py
from conftest import FIXTURES
from empu.evaluation.gold import load_gold


def test_skips_example_rows():
    rows = load_gold(FIXTURES / "eval/tiny.csv")
    assert [r.term for r in rows] == ["pola", "nyamplung"]
    assert rows[0].source.value == "speech"
    assert rows[1].source.value == "on_screen_text"
```

- [ ] **Step 2:** Fail `ModuleNotFoundError`.

- [ ] **Step 3: Implementasi**

```python
# api/empu/evaluation/gold.py
import csv
from dataclasses import dataclass
from pathlib import Path

from empu.enums import Category, Source


@dataclass(frozen=True)
class GoldRow:
    clip_id: str
    t_start: float
    t_end: float
    spoken: str
    term: str
    category: Category
    source: Source
    stage: str
    visible_object: str
    note: str
    annotator: str


def load_gold(path: Path) -> list[GoldRow]:
    rows: list[GoldRow] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            if (raw.get("annotator") or "").strip().lower() == "contoh":
                continue
            if not (raw.get("term") or "").strip():
                continue
            cat = raw.get("category") or "other"
            category = Category(cat) if cat in {c.value for c in Category} else Category.other
            rows.append(GoldRow(
                clip_id=raw["clip_id"], t_start=float(raw["t_start"]), t_end=float(raw["t_end"]),
                spoken=raw.get("spoken") or raw["term"], term=raw["term"],
                category=category, source=Source(raw["source"]),
                stage=raw.get("stage") or "", visible_object=raw.get("visible_object") or "",
                note=raw.get("note") or "", annotator=raw.get("annotator") or "",
            ))
    return rows
```

- [ ] **Step 4:** pytest lulus. Commit `feat(eval): gold CSV loader skipping template examples`.

---

### Task H5-2: Pencocokan dan metrik

**Files:**
- Create: `matching.py`, `metrics.py`
- Test: `api/tests/test_eval_matching.py`

**Interfaces:**
- `Pred(term, t_start, t_end, source, spoken, pack_term_id)`
- `Match(gold, pred, delta)`
- `match_mentions(gold, pred, pack, *, tol_s=5.0) -> list[Match]` — canon_key sama, |mid Δt|≤5, greedy
- `compute_metrics(matches, pred, gold) -> dict` dengan kunci `speech_recall`, `speech_precision`, `median_time_error_s`, `source_accuracy`, `n_gold_speech`, `n_pred_speech`, `n_matched_speech`, `n_gold`, `n_pred`, `n_matched`

- [ ] **Step 1: Tes**

```python
# api/tests/test_eval_matching.py
from empu.enums import Category, Source
from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Pred, match_mentions
from empu.evaluation.metrics import compute_metrics


def G(term, t, source=Source.speech):
    return GoldRow("c", t, t + 1, term, term, Category.tool, source, "", "", "", "s")


def P(term, t, source=Source.speech):
    return Pred(term=term, t_start=t, t_end=t + 1, source=source, spoken=term, pack_term_id=None)


def test_match_within_tol(pack):
    gold = [G("canting", 10), G("malam", 20)]
    pred = [P("tjanting", 12), P("malam", 40)]
    matches = match_mentions(gold, pred, pack, tol_s=5)
    by_term = {m.gold.term: m for m in matches}
    assert by_term["canting"].pred is not None and abs(by_term["canting"].delta) == 2
    assert by_term["malam"].pred is None


def test_metrics_speech(pack):
    gold = [G("canting", 10), G("malam", 20), G("nyamplung", 30, source=Source.on_screen_text)]
    pred = [P("canting", 11), P("hcl", 50)]
    m = compute_metrics(match_mentions(gold, pred, pack), pred, gold)
    assert m["n_gold_speech"] == 2
    assert m["speech_recall"] == 0.5
    assert m["speech_precision"] == 0.5
```

- [ ] **Step 2: Implementasi**

```python
# api/empu/evaluation/matching.py
from dataclasses import dataclass

from empu.enums import Source
from empu.evaluation.gold import GoldRow
from empu.packs import CraftPack
from empu.pipeline.merge import Canonicalizer


@dataclass(frozen=True)
class Pred:
    term: str
    t_start: float
    t_end: float
    source: Source
    spoken: str
    pack_term_id: str | None


@dataclass
class Match:
    gold: GoldRow
    pred: Pred | None
    delta: float | None


def _mid(a: float, b: float) -> float:
    return (a + b) / 2


def match_mentions(gold: list[GoldRow], pred: list[Pred], pack: CraftPack, *,
                   tol_s: float = 5.0) -> list[Match]:
    canon = Canonicalizer(pack)
    gkeys = [canon.match(g.term, g.spoken).canon_key for g in gold]
    pkeys = [canon.match(p.term, p.spoken).canon_key for p in pred]
    pairs: list[tuple[float, int, int]] = []
    for i, g in enumerate(gold):
        gm = _mid(g.t_start, g.t_end)
        for j, p in enumerate(pred):
            if gkeys[i] != pkeys[j]:
                continue
            d = abs(gm - _mid(p.t_start, p.t_end))
            if d <= tol_s:
                pairs.append((d, i, j))
    pairs.sort()
    used_g: set[int] = set()
    used_p: set[int] = set()
    found: dict[int, tuple[Pred, float]] = {}
    for d, i, j in pairs:
        if i in used_g or j in used_p:
            continue
        used_g.add(i)
        used_p.add(j)
        found[i] = (pred[j], d)
    return [Match(g, found[i][0], found[i][1]) if i in found else Match(g, None, None)
            for i, g in enumerate(gold)]
```

```python
# api/empu/evaluation/metrics.py
import statistics

from empu.enums import Source
from empu.evaluation.gold import GoldRow
from empu.evaluation.matching import Match, Pred


def compute_metrics(matches: list[Match], pred: list[Pred], gold: list[GoldRow]) -> dict:
    gold_speech = [m for m in matches if m.gold.source is Source.speech]
    hit_speech = [m for m in gold_speech if m.pred is not None]
    pred_speech = [p for p in pred if p.source is Source.speech]
    used = {id(m.pred) for m in matches if m.pred is not None}
    pred_speech_hit = sum(1 for p in pred_speech if id(p) in used)
    deltas = [m.delta for m in matches if m.delta is not None]
    n_matched = sum(1 for m in matches if m.pred is not None)
    source_ok = sum(1 for m in matches if m.pred is not None and m.pred.source is m.gold.source)
    return {
        "n_gold_speech": len(gold_speech),
        "n_pred_speech": len(pred_speech),
        "n_matched_speech": len(hit_speech),
        "speech_recall": (len(hit_speech) / len(gold_speech)) if gold_speech else None,
        "speech_precision": (pred_speech_hit / len(pred_speech)) if pred_speech else None,
        "median_time_error_s": statistics.median(deltas) if deltas else None,
        "source_accuracy": (source_ok / n_matched) if n_matched else None,
        "n_gold": len(gold),
        "n_pred": len(pred),
        "n_matched": n_matched,
    }
```

Hapus impor `Source` di matching.py kalau tidak terpakai.

- [ ] **Step 3:** pytest lulus. Commit `feat(eval): greedy mention matching and speech metrics`.

---

### Task H5-3: Baseline ASR dari VTT

**Files:**
- Create: `baseline.py`
- Test: `api/tests/test_eval_baseline.py`

**Interfaces:** `parse_vtt(path) -> list[Pred]`; `baseline_against_pack(cues, pack) -> list[Pred]` (buang yang `method=="novel"`).

- [ ] **Step 1: Tes**

```python
# api/tests/test_eval_baseline.py
from empu.evaluation.baseline import baseline_against_pack, parse_vtt


def test_parse_vtt(tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nspang King\n")
    cues = parse_vtt(p)
    assert cues[0].spoken == "spang King"
    assert abs(cues[0].t_start - 1.0) < 0.01


def test_spang_king_is_novel(pack, tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text("WEBVTT\n\n00:02:02.000 --> 00:02:04.000\nspang King\n")
    assert baseline_against_pack(parse_vtt(p), pack) == []
```

- [ ] **Step 2: Implementasi**

```python
# api/empu/evaluation/baseline.py
import re
from pathlib import Path

from empu.enums import Source
from empu.evaluation.matching import Pred
from empu.packs import CraftPack
from empu.pipeline.merge import Canonicalizer

TS = re.compile(r"(\d+):(\d+):(\d+[.,]\d+)\s-->\s(\d+):(\d+):(\d+[.,]\d+)")


def _sec(h: str, m: str, s: str) -> float:
    return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))


def parse_vtt(path: Path) -> list[Pred]:
    text = Path(path).read_text(encoding="utf-8")
    cues: list[Pred] = []
    for block in re.split(r"\n\s*\n", text):
        match = TS.search(block)
        if not match:
            continue
        t0 = _sec(*match.group(1, 2, 3))
        t1 = _sec(*match.group(4, 5, 6))
        lines = [
            ln.strip() for ln in block.splitlines()
            if ln.strip() and "-->" not in ln and ln.strip() != "WEBVTT" and not ln.strip().isdigit()
        ]
        spoken = " ".join(lines)
        if not spoken or spoken.startswith("NOTE"):
            continue
        cues.append(Pred(term=spoken, t_start=t0, t_end=t1, source=Source.speech,
                         spoken=spoken, pack_term_id=None))
    return cues


def baseline_against_pack(cues: list[Pred], pack: CraftPack) -> list[Pred]:
    canon = Canonicalizer(pack)
    out: list[Pred] = []
    for cue in cues:
        hit = canon.match(cue.term, cue.spoken)
        if hit.method == "novel":
            continue
        out.append(Pred(term=hit.term, t_start=cue.t_start, t_end=cue.t_end, source=Source.speech,
                        spoken=cue.spoken, pack_term_id=hit.pack_term_id))
    return out
```

- [ ] **Step 3:** pytest. Commit `feat(eval): YouTube VTT baseline against pack variants`.

---

### Task H5-4: Runner + CLI

**Files:**
- Create: `api/empu/evaluation/runner.py`
- Modify: `cli.py`
- Test: `api/tests/test_eval_runner.py`

**Interfaces:**
- `pred_from_db(session, recording_id) -> list[Pred]`
- `run_clip(gold, pred, pack, *, baseline=None) -> dict` (metrics + `baseline_speech_recall`)
- `write_results(path, payload) -> None`
- CLI typer group `eval`: `run`, `draft-gold`

```python
# api/empu/evaluation/runner.py
import json
from pathlib import Path

from sqlmodel import Session, select

from empu.evaluation.gold import GoldRow, load_gold
from empu.evaluation.matching import Pred, match_mentions
from empu.evaluation.metrics import compute_metrics
from empu.models import Entry, Occurrence
from empu.packs import CraftPack


def pred_from_db(session: Session, recording_id: int) -> list[Pred]:
    occs = session.exec(select(Occurrence).where(Occurrence.recording_id == recording_id)).all()
    out = []
    for o in occs:
        e = session.get(Entry, o.entry_id)
        if e is None:
            continue
        out.append(Pred(term=e.term, t_start=o.t_start, t_end=o.t_end, source=o.source,
                        spoken=o.spoken, pack_term_id=e.pack_term_id))
    return out


def run_clip(gold: list[GoldRow], pred: list[Pred], pack: CraftPack,
             *, baseline: list[Pred] | None = None) -> dict:
    matches = match_mentions(gold, pred, pack)
    metrics = compute_metrics(matches, pred, gold)
    if baseline is not None:
        b = compute_metrics(match_mentions(gold, baseline, pack), baseline, gold)
        metrics["baseline_speech_recall"] = b["speech_recall"]
    return metrics


def write_results(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
```

Tes: gold tiny + Pred canting di t=86 (kalau tiny pakai pola/nyamplung, buat gold in-memory).

CLI:

```python
eval_app = typer.Typer()
app.add_typer(eval_app, name="eval")


@eval_app.command("run")
def eval_run(
    set_path: Path = typer.Option(..., "--set"),
    gold_dir: Path = typer.Option(..., "--gold"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    ...
```

`draft-gold CLIP_ID` menulis CSV dengan annotator=`DRAFT` dari occurrence DB atau muse JSON. Manusia wajib ganti annotator.

Commit: `feat(cli): empu eval run and draft-gold`.

---

### Task H5-5: Kunci jawaban manusia

Syafiq menonton. Urutan:
1. `docs/eval/kunci-jawaban/ccby-macam-canting.csv`
2. `docs/eval/kunci-jawaban/ngertibatik-proses.csv` (8 istilah Gate 0 + diagram `on_screen_text`)
3. Kontrol: tanpa CSV; runner cek `n_pred_speech`

```bash
cd api && uv run empu eval draft-gold ccby-macam-canting
```

Jangan commit `annotator=contoh` atau `DRAFT`. Commit setelah koreksi: `docs: gold annotations for demo and ngertibatik`.

---

### Task H5-6: Jalankan eval

```bash
cd api
uv run empu eval run --set ../docs/eval/test-set.yaml \
  --gold ../docs/eval/kunci-jawaban \
  --out eval/results/$(date -u +%Y%m%dT%H%M).json
cp eval/results/<stamp>.json eval/results/latest.json
```

Bentuk `latest.json`:

```json
{
  "created_at": "2026-11-02T12:00:00Z",
  "pack": "batik_tulis@0.1.1",
  "mode": "B",
  "clips": {
    "ccby-macam-canting": {},
    "ngertibatik-proses": {},
    "kontrol-musik-nglorod": {"n_pred_speech": 0}
  },
  "aggregate": {},
  "notes": []
}
```

Tulis `docs/reference/hasil-gate2.md` dengan angka asli. Commit `latest.json`.

---

### Task H5-7: API + halaman Bukti

**Files:**
- Create: `api/empu/routes/eval.py`
- Modify: `app.py` (tanpa studio key)
- Create: `web/app/evidence/page.tsx`
- Test: `api/tests/test_api_eval.py`

```python
# api/empu/routes/eval.py
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from empu.config import REPO_ROOT

router = APIRouter()
LATEST = REPO_ROOT / "api" / "eval" / "results" / "latest.json"


@router.get("/api/eval/summary")
def eval_summary() -> dict:
    if not LATEST.is_file():
        raise HTTPException(404, "no eval results")
    return json.loads(LATEST.read_text())
```

Tes: tulis file temp, monkeypatch `LATEST`.

Layout S8: `desain.md`. Judul dan subjudul **persis** brief. Headline cards (`speech_terms_found_content` berdampingan dengan `_with_timing`, median |Δt|, musik = 0, audio-off `7 → 0`). Tabel klip. Blok captions: baris `verified !== true` → "not yet verified", jangan klaim. Metode 4 baris. Jangan angka Gate 0 tanpa label jika `latest.json` sudah ada.

```tsx
// web/app/evidence/page.tsx
const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";
export const dynamic = "force-dynamic";

export default async function EvidencePage() {
  const data = await fetch(`${API}/api/eval/summary`, { cache: "no-store" }).then((r) => r.json());
  const clips = data.clips ?? {};
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="font-display text-3xl">This is the score, not the goal.</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Measured against human-checked answer keys. We publish the real numbers, including the misses.
      </p>
      <table className="mt-8 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--line)]">
            <th className="py-2">Clip</th>
            <th>Speech recall</th>
            <th>Precision</th>
            <th>Median |Δt|</th>
            <th>Source acc.</th>
            <th>ASR baseline</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(clips as Record<string, Record<string, number | null>>).map(([id, m]) => (
            <tr key={id} className="border-b border-[var(--line)]">
              <td className="py-2">{id}</td>
              <td>{fmt(m.speech_recall)}</td>
              <td>{fmt(m.speech_precision)}</td>
              <td>{m.median_time_error_s ?? "—"}</td>
              <td>{fmt(m.source_accuracy)}</td>
              <td>{fmt(m.baseline_speech_recall)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-6 text-sm">
        Music-only control: {String((clips as Record<string, { n_pred_speech?: number }>)["kontrol-musik-nglorod"]?.n_pred_speech ?? "—")} spoken terms (target 0).
      </p>
      <p className="mt-4 text-xs text-[var(--muted)]">
        Source labels are weaker when captions are burnt into the video. Timestamps are realigned with local speech recognition; spelling still comes from Muse. Demo clips are CC BY videos, already edited, not field recordings.
      </p>
      <p className="mt-2 text-xs text-[var(--muted)]">
        Method: 75-second segments · structured output · faster-whisper as the time anchor · SAM bounding boxes.
      </p>
    </main>
  );
}

function fmt(v: number | null | undefined) {
  return v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(2);
}
```

Taut dari `web/app/page.tsx`: Evidence.

Commit: `feat: public Evidence page from latest.json`.

---

### Task H5-8: Gate 2 + Status

`docs/reference/hasil-gate2.md`: video CC BY diproses+divalidasi+dievaluasi; atribusi tampil; URL masih lokal sampai H6; tabel angka.

CLAUDE.md: `H5 (Sen 2 Nov): Gate 2 — eval di halaman Bukti. Berikutnya: H6 izin, sandbox, deploy.`

Jangan mengulang pipeline semalaman kalau recall rendah. Tulis angka itu.

## Selesai kalau (Gate 2)
- [ ] `latest.json` ter-commit dari gold manusia
- [ ] `/evidence` merender tabel
- [ ] Kontrol musik tercantum
- [ ] Baseline ASR tercantum

## Kalau gagal
Potong sandbox dan polesan. Halaman Bukti **wajib**.
