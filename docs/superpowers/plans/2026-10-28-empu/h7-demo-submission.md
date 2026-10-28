# H7 (Rab 4 Nov): Video Demo, Teks Submission, Kirim

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Submission hackathon terkirim sebelum Rabu 4 Nov 2026, 22:00 WIB, dengan video 2–3 menit, teks jujur, dan tiga tautan publik yang terbuka.

**Architecture:** Tidak ada kode fitur baru. H7 menghasilkan artefak: naskah, video, teks form, pemeriksaan repo, unggah. Kalau form resmi minta field yang belum ada di produk, isi dari `docs/00-konteks-hackathon.md` dan halaman `/evidence` — jangan menambah fitur. Kalau pukul 17:00 WIB naskah belum direkam, kirim dengan rekaman satu-take dari walkthrough produksi; polesan editing dipotong.

**Tech Stack:** OBS atau QuickTime (1080p 16:9), ffmpeg/ffprobe, git, form Cerebral Valley (`https://cerebralvalley.ai/e/meta-ai-developer-hackathon`), YouTube unlisted atau field unggah resmi.

## Global Constraints

- Spec `docs/superpowers/specs/2026-10-28-empu-design.md` bagian 19 adalah kerangka shot. UI di video berbahasa Inggris; istilah keahlian tetap asli.
- Video YouTube berlisensi standar **tidak** boleh muncul di demo, repo, atau ekspor publik.
- CC BY yang boleh: daftar `demo_cc_by` di `docs/eval/test-set.yaml`. Atribusi di layar: kreator, judul, URL, lisensi, keterangan "trimmed".
  - Hook: `zyscgcTHtq8` — *Proses nyanting batik tulis* — TEBAK teras batik kaindra — CC BY 3.0 — https://www.youtube.com/watch?v=zyscgcTHtq8
  - Masalah (hanya jika Empu `source=speech` di waktu benar): `FodqwNTWOrQ` — *Macam Canting dalam Batik Tulis* — Batik Education — CC BY 3.0 — https://www.youtube.com/watch?v=FodqwNTWOrQ
- "Validated by the expert" hanya jika `review_event.actor` bukan documenter (`DOCUMENTER_ACTORS = {documenter, syafiq}` dari H3). Selain itu "Validated by the documenter".
- Jangan klaim "batik will vanish" / "Batik akan punah".
- Jangan klaim recall tunggal. Tampilkan tabel `/evidence`. Salin angka dari `api/eval/results/latest.json`, bukan dari ingatan Gate 0, kecuali file itu belum ada.
- Klaim *canting* vs subtitle "cantik"/"cacing" hanya jika Empu menangkap `canting` dengan `source=speech` di waktu benar pada rekaman `FodqwNTWOrQ`.
- Repo: jangan berisi `.env`, video, `data/`, `data-uji/`, `arsip-hidup-batik/`. File video demo di `~/Movies/empu-demo.mp4`, **tidak** di-commit.
- Track: **Indie**. Tema default: **Build for Your World**. Ganti ke Push the Frontier hanya jika form memaksa satu tema teknis dan menolak dunia-nyata.
- Deadline resmi: Kamis 5 Nov 2026, 09:00 WIB (4 Nov 21:00 ET). Target internal: Rabu 4 Nov 22:00 WIB.

## Prasyarat

- H6 selesai: URL HTTPS hidup, `/d/hidup-batik` 200, `/evidence` 200, `/api/health` 200, README memuat domain produksi.
- H0-2 Step 4: kalau `docs/00-konteks-hackathon.md` masih berisi "Belum dicek", **H7-1 adalah task pertama hari ini** (maks 20 menit), bukan di menit terakhir.
- Jangan mulai H7-3 sebelum H7-1 selesai: durasi video mengikuti max resmi kalau sudah diumumkan.

## File yang disentuh di fase ini

| File | Aksi | Task |
|---|---|---|
| `docs/00-konteks-hackathon.md` | Modify | H7-1 |
| `docs/submission/script.md` | Create | H7-2 |
| `docs/submission/text.md` | Create | H7-4 |
| `docs/submission/receipt.png` | Create (setelah kirim) | H7-6 |
| `README.md` | Modify (URL final, tautan video) | H7-5 |
| `CLAUDE.md` | Modify (status terkirim) | H7-6 |
| `~/Movies/empu-demo.mp4` | Create di disk lokal, tidak di-git | H7-3 |

---

### Task H7-1: Baca form submission sungguhan

**Files:**
- Modify: `docs/00-konteks-hackathon.md`

**Interfaces:**
- Consumes: tautan resmi di `docs/00-konteks-hackathon.md` (Fakta hackathon).
- Produces: tabel `## Persyaratan submission` yang menggantikan kalimat "Belum dicek". H7-3 dan H7-4 membaca tabel itu untuk durasi video, batas karakter, dan field wajib.

- [ ] **Step 1: Buka tiga sumber, catat apa yang tertulis, bukan apa yang diharapkan**

```bash
# 28 Okt: /submit 404. Cek ulang pada 4 Nov pagi.
curl -sI https://cerebralvalley.ai/e/meta-ai-developer-hackathon/submit | head -n 1
# Expected 4 Nov: HTTP/2 200 atau 302 ke login, BUKAN 404.

# Halaman acara (sudah hidup 28 Okt):
# https://dev.meta.ai/events/global-hackathon
# https://cerebralvalley.ai/e/meta-ai-developer-hackathon
# Official Rules: cari tautan "Official Rules" / PDF di halaman acara, Discord office hours, dan email penerimaan.
```

Fakta yang **sudah** diketahui 28 Okt (jangan dibuang, jangan ditambah tebakan):

| Item | Isi per 28 Okt 2026 |
|---|---|
| Platform | Cerebral Valley, event `meta-ai-developer-hackathon`. Halaman `/submit` masih 404. |
| Deadline resmi | 4 Nov 2026, 21:00 ET = 5 Nov 2026, 09:00 WIB |
| Track | Indie (satu track per proyek) |
| Tema | "Build for Your World" dan "Push the Frontier" — pilih satu |
| Model Meta | Muse Spark dan SAM 3.1 disebut di halaman acara; pakai keduanya di teks |
| Video demo | Durasi resmi **belum diumumkan**. Spec Empu: 2–3 menit. Cap kerja: **≤ 2:50** sampai form menyebut max lain |
| Repo publik | **belum diumumkan**. Siapkan repo publik + README; unggah URL kalau field ada |
| Deskripsi | batas karakter **belum diumumkan**. Siapkan versi 500 karakter dan versi 1500 karakter |
| URL aplikasi | wajib secara substansi (juri menilai apakah berfungsi). Siapkan HTTPS dari H6 |
| Tim | solo; satu submitter; tidak ada anggota lain yang perlu dicantumkan |

Kalau Official Rules sudah terbit, salin field wajib ke tabel di bawah. Kalau belum: tulis "belum diumumkan per {tanggal jam WIB}" di sel yang kosong, lalu lanjut H7-2 dengan cap 2:50.

- [ ] **Step 2: Ganti baris "Belum dicek" di `docs/00-konteks-hackathon.md`**

Hapus:

```markdown
**Belum dicek:** persyaratan isi submission (repo publik, video demo dan durasi maksimalnya, deskripsi, link aplikasi). Cek halaman submission di hari pertama build dan sesuaikan H7.
```

Ganti dengan (isi sel dari Step 1; contoh di bawah memakai fakta 28 Okt — perbarui tanggal dan sel yang berubah):

```markdown
## Persyaratan submission (dicek 4 Nov 2026)

Sumber: https://dev.meta.ai/events/global-hackathon · https://cerebralvalley.ai/e/meta-ai-developer-hackathon · Official Rules (tautan yang ditemukan) · Discord bila form belum buka.

| Item | Isi |
|---|---|
| Platform | Cerebral Valley (satu submitter Indie) |
| Repo | (ya wajib / tidak wajib / belum diumumkan) |
| Video demo | durasi max … ; unggah ke (YouTube unlisted / field form) |
| Deskripsi | batas pendek … ; batas panjang … |
| URL aplikasi | wajib |
| Model Meta | Muse Spark 1.3 + SAM 3.1 (sebut di teks) |
| Track | Indie |
| Tema | Build for Your World |
| Form buka | (ya / belum, cek ulang jam …) |
```

Jangan mengisi sel dengan tebakan. Sel kosong = "belum diumumkan".

- [ ] **Step 3: Commit**

```bash
git add docs/00-konteks-hackathon.md
git commit -m "$(cat <<'EOF'
docs: official submission requirements

EOF
)"
```

---

### Task H7-2: Naskah dan shot list (spec 19)

**Files:**
- Create: `docs/submission/script.md`

**Interfaces:**
- Consumes: kerangka spec bagian 19; lisensi `docs/eval/lisensi/{zyscgcTHtq8,FodqwNTWOrQ}.json`; angka `/evidence`.
- Produces: naskah yang dibaca 2:20–2:50. H7-3 merekam persis urutan ini.

- [ ] **Step 1: Tulis file utuh**

```markdown
# Demo script (target 2:30, hard cap 2:50 unless Official Rules say otherwise)

VO in English. Craft terms stay in original form (canting, nyanting, malam).
Lower-thirds: Inter / system UI font, white on 60% black bar, 16:9 safe area. Di dalam app: Fraunces untuk kata kepala (`desain.md`). Jangan overlay motif batik.

## Gate before recording
Open production URL. Confirm:
- `/api/health` 200
- `/d/hidup-batik` shows ≥1 accepted public entry with clip + crop + source badge + CC BY line
- `/evidence` table has numbers from `api/eval/results/latest.json`
- Studio login works (or skip Studio shot and say "validator already accepted these entries")

Canting-vs-captions shot (0:15–0:35): ONLY if this SQL (or Studio filter) is true
on the Macam Canting recording (`source_url` contains `FodqwNTWOrQ`):

```sql
SELECT e.term, o.source, o.t_start, o.t_end
FROM occurrence o JOIN entry e ON e.id = o.entry_id
JOIN recording r ON r.id = o.recording_id
WHERE r.source_url LIKE '%FodqwNTWOrQ%'
  AND o.source = 'speech'
  AND lower(e.term) LIKE '%canting%';
```

If empty: use fallback VO in 0:15–0:35. Do not fake the comparison.

## 0:00–0:15 Hook
Picture: B-roll from Empu dictionary clip of nyanting (TEBAK), not a raw YouTube tab.
Lower-third (stay 15s):
`TEBAK teras batik kaindra · Proses nyanting batik tulis · CC BY 3.0 · trimmed`
`https://www.youtube.com/watch?v=zyscgcTHtq8`

VO: "This knowledge has never been written down."

On-screen title, last 3s: `Empu — Batik Tulis Edition`

## 0:15–0:35 Problem
Preferred (only if the SQL above returned a row):
Split: YouTube auto-captions saying "cantik" or "cacing" | Empu entry `canting` with source badge `speech` and the matching timestamp.
VO: "Recording is easy. Turning a master's speech into a dictionary is not. Captions hear 'cantik'. Empu hears canting — and shows you the tool."

Fallback (if SQL empty):
Studio list of proposed terms with source badges `speech` / `on_screen_text` / `visual_only`.
VO: "Recording is easy. Turning it into a dictionary is not. Empu keeps the source label: spoken, on-screen, or visual-only. A human still decides what goes public."

## 0:35–2:05 Product (90s)
Cursor large. Click slowly. Address bar shows the production domain.

1. Upload (12s). `/try` sandbox or Studio upload. Consent checkbox visible (`public` + granted). Do not skip the checkbox.
2. Progress (10s). Stages: normalizing → chunking → analyzing → merging → grounding → cutting → ready. Do not speed-ramp so fast the labels vanish.
3. Studio (25s). Accept one entry (A). Edit one English gloss (E). Source badge stays visible. Say: "AI proposes. A human decides."
4. Dictionary (25s). `/d/hidup-batik`. Tap one term. Hear the clip. See the SAM crop from the original frame. Attribution line visible.
5. Process map (10s). Stages of nyanting in order.
6. Export (8s). Download ZIP or ELAN. Three seconds of the file list is enough.

If sandbox was cut in H6: skip shot 1 on `/try`; start from Studio on a prepared recording. Say one sentence: "Judges can still walk the live dictionary."

## 2:05–2:25 Evidence
Full-screen `/evidence`.
VO, reading the real cells, not a target:
"This is the score, not the goal. Speech recall with tight timing: N of M. Music-only control: K spoken terms."
If control is not 0, say the real K. Do not round.

## 2:25–2:40 Vision
Full-screen `packs/batik_tulis.yaml` (term keys only, no secrets).
VO: "Batik today. Weaving and gamelan next. Every unwritten craft."
End card (3s):
`empu` production URL
`Dictionary /d/hidup-batik`
`Evidence /evidence`
```

- [ ] **Step 2: Cek durasi naskah**

Baca naskah keras sekali sambil timer. Target 2:20–2:50. Kalau &gt; 2:50, potong shot process map dulu, lalu export, jangan potong Evidence.

- [ ] **Step 3: Commit naskah**

```bash
git add docs/submission/script.md
git commit -m "$(cat <<'EOF'
docs: demo shot list

EOF
)"
```

---

### Task H7-3: Rekam dan encode

**Files:**
- Create (lokal, tidak di-git): `~/Movies/empu-demo-raw.mov`, `~/Movies/empu-demo.mp4`

**Interfaces:**
- Consumes: `docs/submission/script.md`; max durasi dari tabel H7-1.
- Produces: file MP4 ≤ max resmi (default ≤ 170 s) siap unggah.

- [ ] **Step 1: Set rekaman**

OBS atau QuickTime:
- Display 1920×1080, 30 fps, 16:9.
- Capture browser window (bukan seluruh desktop dengan notifikasi).
- Cursor besar (macOS Accessibility → Pointer).
- Tutup tab YouTube berlisensi standar. Tutup `.env`. Tutup Discord.
- Audio: VO terpisah (mikrofon) dicampur belakangan, atau VO live. Jangan pakai musik stok.

- [ ] **Step 2: Satu take jalan**

Rekam sesuai shot list. Kalau salah klik, lanjut dan sisipkan cut di encode; jangan 12 take.

Lower-third CC BY harus terbaca ≥ 3 detik per klip.

- [ ] **Step 3: Encode**

```bash
mkdir -p "$HOME/Movies"
ffmpeg -y -i "$HOME/Movies/empu-demo-raw.mov" \
  -c:v libx264 -crf 20 -preset medium \
  -c:a aac -b:a 192k -ac 2 -ar 48000 \
  -movflags +faststart \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30" \
  "$HOME/Movies/empu-demo.mp4"

ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$HOME/Movies/empu-demo.mp4"
# Expected: 120..170 (or official max from H7-1, whichever is smaller)
ls -lh "$HOME/Movies/empu-demo.mp4"
```

Kalau durasi di atas max: potong Vision dulu (sisakan 8 detik YAML + end card), bukan Evidence.

- [ ] **Step 4: Unggah video**

YouTube **unlisted** (judul `Empu — Batik Tulis Edition`, deskripsi memuat atribusi CC BY kedua klip) **atau** field unggah di form H7-1.

Deskripsi YouTube (salin utuh):

```text
Empu turns a master's narrated work video into a watchable craft dictionary.

Trimmed clips under CC BY 3.0:
- TEBAK teras batik kaindra, "Proses nyanting batik tulis", https://www.youtube.com/watch?v=zyscgcTHtq8
- Batik Education, "Macam Canting dalam Batik Tulis", https://www.youtube.com/watch?v=FodqwNTWOrQ
  (only if that shot appears)

Not affiliated with the original creators. Clips are trimmed.
```

Simpan URL di `docs/submission/text.md` pada H7-4. **Jangan** `git add` file MP4.

Tidak ada commit di task ini (artefak di luar repo).

---

### Task H7-4: Teks submission

**Files:**
- Create: `docs/submission/text.md`

**Interfaces:**
- Consumes: tabel H7-1; `api/eval/results/latest.json`; URL video H7-3; domain H6.
- Produces: copy siap tempel ke form. Angka di paragraf jujur = angka di `/evidence`.

- [ ] **Step 1: Baca angka evaluasi**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("api/eval/results/latest.json")
print(p.read_text() if p.exists() else "MISSING latest.json — use /evidence screenshot, not Gate 0 memory")
PY
```

- [ ] **Step 2: Tulis `docs/submission/text.md`**

Ganti `N/M`, `K`, `https://DOMAIN`, dan URL video dengan nilai nyata. Jangan biarkan placeholder sudut.

```markdown
# Empu submission copy

## Tagline
Capture what masters know, before it's gone.

## Track
Indie

## Theme
Build for Your World

Reason: a tool for workshops around me, not a model demo. Switch to Push the Frontier only if the form forbids a real-world theme.

## Models used
- muse-spark-1.3 — spoken / on-screen / visual-only craft terms from video
- sam-3.1 — bounding-box crops from original frames (no generated images)
- faster-whisper (local) — timestamp repair after Gate 0 (Mode B). Not a Meta model; say so if the form asks "only Meta?"

## Short description (≤500 characters)
Empu turns a master's narrated work video into a watchable craft dictionary. Muse Spark finds terms, timestamps, and whether they were spoken, on-screen, or visual-only. SAM crops the real tool from the original frame. A human validator accepts every public entry. Demo: batik tulis, CC BY videos with attribution.

## Long description (≤1500 characters, trim to the official cap)
Masters already record their work. The knowledge still dies in unlabeled files.

Empu is a pipeline plus a human gate. A consented video is chunked, analyzed with Muse Spark, and aligned in time (Mode B: local ASR as the clock after Muse timestamps drifted across music). Each term keeps a source label: speech, on-screen text, or visual-only. SAM 3.1 crops the tool from the original frame. Nothing is public until a validator accepts or edits it. Consent can be withdrawn; public clips disappear with it.

The first edition is batik tulis. Knowledge lives in a YAML craft pack, not in hardcoded terms. The live dictionary is CC BY source material with on-screen credit (creator, URL, license, trimmed).

We publish the eval table, not a target. Speech recall with tight timing, a YouTube-captions baseline, and a music-only control are on /evidence.

## Honesty paragraph (paste if the form asks "did it work")
Gate 0: Muse hears audio (0 spoken terms on a caption-free music/silence control) but timestamps drift after music gaps, so Mode B realigns to local ASR. Copy the current cells from /evidence here. Do not write "validated by batik masters" as a blanket. Expert-validated means the recording's maker checked that entry.

## Links
- App: https://DOMAIN
- Dictionary: https://DOMAIN/d/hidup-batik
- Evidence: https://DOMAIN/evidence
- Try (if H6 shipped sandbox): https://DOMAIN/try
- Repo: REPO_URL
- Demo video: VIDEO_URL

## Attribution block (paste into any "third-party content" field)
Demo media is trimmed from YouTube videos under CC BY 3.0:
- TEBAK teras batik kaindra, Proses nyanting batik tulis, https://www.youtube.com/watch?v=zyscgcTHtq8
- Batik Education, Macam Canting dalam Batik Tulis, https://www.youtube.com/watch?v=FodqwNTWOrQ
```

Hitung karakter versi pendek:

```bash
python3 - <<'PY'
from pathlib import Path
text = Path("docs/submission/text.md").read_text()
# extract the short paragraph between the heading and the next ##
start = text.index("## Short description")
chunk = text[start:text.index("## Long description")]
body = "\n".join(line for line in chunk.splitlines() if not line.startswith("#") and line.strip())
print(len(body))
PY
```

Kalau form max &lt; 500, potong kalimat SAM dulu, lalu kalimat CC BY, jangan potong "A human validator accepts every public entry."

- [ ] **Step 3: Commit**

```bash
git add docs/submission/text.md
git commit -m "$(cat <<'EOF'
docs: submission copy

EOF
)"
```

---

### Task H7-5: Pemeriksaan akhir repo dan URL

**Files:**
- Modify: `README.md` (tautan video + domain final)

**Interfaces:**
- Consumes: domain H6, `VIDEO_URL` dari H7-3.
- Produces: tree git tanpa rahasia/media; README yang sama dengan form.

- [ ] **Step 1: Rahasia dan media tidak ter-track**

```bash
cd /Users/ahmadsyafiqkamil/Documents/Project/Empu
git ls-files | grep -E '(^|/)\.env$|data-uji|arsip-hidup|\.mp4$|^data/' && echo FAIL || echo clean
git grep -n 'META_MODEL_API_KEY\|STUDIO_KEY' -- ':!.env.example' ':!docs/**' ':!*.md' && echo FAIL || echo keys-ok
```

Expected stdout: `clean` lalu `keys-ok`. Kalau FAIL: `git rm --cached` file itu, **jangan** `git rm` salinan lokal.

- [ ] **Step 2: Tiga tautan juri**

```bash
# Ganti DOMAIN. Harus dari jaringan publik, bukan localhost.
DOMAIN=https://DOMAIN
curl -sf -o /dev/null -w "%{http_code}\n" "$DOMAIN/api/health"
curl -sf -o /dev/null -w "%{http_code}\n" "$DOMAIN/d/hidup-batik"
curl -sf -o /dev/null -w "%{http_code}\n" "$DOMAIN/evidence"
```

Expected: `200` tiga kali.

Walkthrough klik (satu kali, 3 menit): beranda → `/d/hidup-batik` → satu entri (klip + crop + source + atribusi) → `/evidence` → `/try` atau Studio. Kalau klip 416/403: perbaiki Range/auth H3/H6 **hanya** jika media putus; jangan poles UI.

- [ ] **Step 3: README**

Di `README.md` (dibuat H6), pastikan blok Live memuat URL video:

```markdown
**Live:** https://DOMAIN
**Dictionary:** /d/hidup-batik · **Evidence:** /evidence · **Try (3 min):** /try
**Demo video:** VIDEO_URL
```

Kalau sandbox dipotong di H6, hapus `Try` dari baris itu.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: final live and demo URLs

EOF
)"
```

Push hanya jika user meminta, atau jika H7-6 butuh URL commit publik dan remote sudah di-set di H6. Jangan `git push --force`.

---

### Task H7-6: Kirim

**Files:**
- Create: `docs/submission/receipt.png`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `docs/submission/text.md`, `VIDEO_URL`, repo URL, domain.
- Produces: konfirmasi form + status CLAUDE.md.

- [ ] **Step 1: Tempel, jangan improvisasi klaim**

Buka form Cerebral Valley. Salin field dari `docs/submission/text.md`. Cek tiga tautan sekali lagi di tab penyamaran.

Solo Indie: jangan mencantumkan anggota fiktif.

- [ ] **Step 2: Submit sebelum 22:00 WIB**

Klik submit. Screenshot halaman konfirmasi → `docs/submission/receipt.png`.

Kalau form gagal (5xx, kuota, login):

1. Simpan draft.
2. Coba browser kedua.
3. Discord office hours.
4. Jangan nambah fitur. Deadline resmi masih 09:00 WIB Kamis.

- [ ] **Step 3: Status repo**

Di `CLAUDE.md` bagian Status, ganti kalimat "Berikutnya: H7" dengan:

```markdown
- H7 (Rab 4 Nov): submitted {HH:MM WIB}. App https://DOMAIN · video VIDEO_URL · repo REPO_URL
```

```bash
git add docs/submission/receipt.png CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: submission sent

EOF
)"
```

## Selesai kalau

- [ ] Form resmi terkirim (bukan hanya draft)
- [ ] App, video, repo terbuka dari jaringan publik
- [ ] Klaim di teks = sel di `/evidence`
- [ ] `git ls-files` tidak memuat `.env`, `.mp4`, `data/`

## Kalau pukul 17:00 WIB belum

| Belum | Potong |
|---|---|
| Naskah belum direkam | Satu take walkthrough: kamus → satu entri → evidence. Tanpa split captions, tanpa export |
| VO belum rapi | VO live, jangan tunda unggah |
| Sandbox `/try` rusak | Jangan perbaiki. Kamus + evidence cukup |
| Form belum buka | Isi draft lokal `docs/submission/text.md`, cek Discord, kirim menit pertama form hidup. Jangan nambah fitur sambil menunggu |

Tidak boleh dipotong: tiga tautan hidup, atribusi CC BY di video, angka jujur, submit.

## Jangan dilakukan pada H7

Fitur baru, retraining prompt, "satu video lagi", polesan warna, ganti tagline, rewrite pack YAML. Opportunity cost: submission telat. Stretch spec bagian 4 tidak masuk H7.
