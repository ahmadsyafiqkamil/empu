# Empu: Kontrak UI (Mori & Malam)

> **Untuk implementer H3–H7.** Baca file ini bersama `00-ikhtisar.md` + file fase. Sumber: `docs/design/brief-claude-design.md`. Kalau plan fase menampilkan kode kerangka yang bertentangan dengan file ini, **file ini yang menang** untuk visual, copy, dan layout.

**Bukan mockup.** Claude Design (kalau ada) hanya referensi. Jangan menunggu mockup. Token, copy, dan layout di sini sudah cukup untuk membangun. H6 hanya 60 menit polesan — desain yang telat = kamus yang terlihat seperti admin tool.

## Sumber

| File | Pakai untuk |
|---|---|
| `docs/design/brief-claude-design.md` | Aturan, token, layout per layar, empty state, komponen |
| `docs/design/contoh-data.json` | Bentuk data UI = `web/lib/types.ts`. Jangan mendesain field yang tidak ada di sini |
| `docs/design/aset/` | Frame CC BY untuk mockup/hero statis. Atribusi: `docs/design/aset/ATRIBUSI.md` |
| `docs/design/prompt-claude-design.md` | Hanya kalau masih sempat kirim ke Claude Design (deadline Jumat 30 Okt malam) |

`contoh-data.json` **bukan** hasil pipeline. Istilah/kutipan dikira-kira. Angka `eval_summary` adalah Gate 0 sungguhan dan harus berlabel "sample" sampai `latest.json` H5 ada. Field bantu yang tidak ada di API: `recordings[].poster`, `archive.craft_pack_version` (dari `/api/packs`), `steps[].label_en` (dari pack `label.en`).

---

## Keputusan (D11)

Dua mode. **Mori** (terang, editorial) untuk halaman publik: `/`, `/d/*`, `/evidence`, `/try`. **Malam** (gelap, meja editor) untuk `/studio/*` lewat `[data-theme="malam"]` pada `web/app/studio/layout.tsx`.

Satu tema gelap untuk semua halaman **dilarang** kecuali pukul 17:00 H4 kamus belum kebaca — baru boleh jatuh ke Malam-only, catat di CLAUDE.md.

Rasa: arsip museum yang hidup, bukan aplikasi AI mengkilap. Bukti di atas penjelasan. Tanpa motif batik klasik, tanpa keris.

---

## Token (tempel ke `web/app/globals.css`)

Nama variabel **wajib** sama. Kontras sudah dicek AA di brief bagian 4.

```css
@import "tailwindcss";

:root {
  --bg: #F5F0E6;
  --surface: #FBF8F2;
  --fg: #1C1813;
  --muted: #665D50;
  --line: #DDD4C4;
  --accent: #22304F;
  --wax: #9E7330;
  --src-speech: #22304F;
  --src-onscreen: #8A4B22;
  --src-visual: #5E5A52;
  --ok: #3F6B45;
  --danger: #9B3B2E;
  --font-display: "Fraunces", serif;
  --font-ui: "Inter", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --radius: 2px;
}
[data-theme="malam"] {
  --bg: #12110F;
  --surface: #1B1916;
  --fg: #ECE8DF;
  --muted: #A39C8E;
  --line: #2E2B26;
  --accent: #C9A15B;
  --wax: #C9A15B;
  --src-speech: #9DB0E3;
  --src-onscreen: #DDA272;
  --src-visual: #B3AC9F;
  --ok: #7FB384;
  --danger: #E57373;
}
html, body {
  background: var(--bg);
  color: var(--fg);
  font-family: var(--font-ui);
}
.font-display { font-family: var(--font-display); }
.font-mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
```

Font dimuat lewat `next/font/google` di `web/app/layout.tsx`: **Fraunces** (`--font-display`, kata kepala), **Inter** (`--font-ui`), **JetBrains_Mono** (`--font-mono`, waktu/angka). Alternatif kalau Google Fonts gagal: `Newsreader` / `IBM Plex Sans` / `ui-monospace`.

Aksen Mori indigo `#22304F` — tombol utama teks putih. Aksen Malam `#C9A15B` — tombol utama teks `#12110F`. `--wax` **bukan** untuk teks (kontras Mori 3,7:1).

Ikon: `lucide-react` (garis tipis). Gerak: transisi 150 ms. Tidak ada hero animation, parallax, typing effect.

---

## Copy (`web/lib/copy.ts`)

Teks **persis** dari brief bagian 8. Jangan parafrase. Beberapa yang sering salah di kerangka plan lama:

| Salah (kerangka lama) | Benar |
|---|---|
| `spoken` / `on-screen text` | `Spoken` / `On-screen text` / `Visual only` |
| `Try the batik tulis archive` | `Open the Batik Tulis archive` |
| `new` / `new term` | `New term` |
| `validated by the documenter` | `Validated by the documenter` |
| `Not found.` | `This entry isn't public. It may still be under review, or its recording's consent was withdrawn.` |
| `prompt()` untuk edit/merge | Form inline / popover. `window.prompt` dilarang |

Ekspor objek `COPY` di `web/lib/copy.ts`. Tooltip sumber dan time-source wajib (brief bagian 8). Label tahap progres:

```
normalizing → Preparing video
chunking → Cutting 75-second segments
analyzing → Muse Spark watches and listens
merging → Matching terms to the craft pack
grounding → SAM 3.1 finds the tools
cutting → Cutting evidence clips
ready → Ready to review
```

Format waktu: `0:37` atau `2:05–2:09` (menit:detik, tabular). Helper `web/lib/time.ts`: `formatTime(s: number): string`.

Atribusi: `From "{title}" by {creator} · {license} · {url} · Trimmed by Empu`. Jangan menambah "Trimmed by Empu" kedua kali kalau API sudah memuatnya.

---

## Aturan yang tidak boleh dilanggar (implementasi)

1. `SourceBadge` memakai **ikon + teks**, bukan warna saja. Wajib di daftar, detail, Studio (termasuk mode edit), timeline (bentuk penanda), ekspor UI.
2. Bukti (klip + crop) sebelum atau setara glosa, tidak di bawah lipatan.
3. Gambar hanya dari `/media/...` atau `docs/design/aset/` (hero statis). Tidak ada stok, tidak ada AI image.
4. `CropView`: crop SAM sering 108×234. Bingkai tetap (persegi atau 4:5), `object-fit: contain` di `--surface`. Sakelar "Show in frame" memakai `overlay_url`. Kalau `sam_status !== "ok"`: keyframe utuh + "No crop found · full frame shown". **Bukan mask/siluet** — SAM Empu bbox saja.
5. Video/audio: elemen native `<video controls>` / `<audio>`. Bingkai 16:9 netral, tanpa glass/gradient di atas footage.
6. Klaim validasi: publik default `Validated by the documenter`. `Validated by the expert · {name}` hanya jika `validated_by_expert`. Studio: `Proposed by AI · not yet reviewed` untuk `proposed`.
7. Izin: checkbox menonjol, submit disabled sampai dicentang. Radio Public/Community/Private dengan satu kalimat masing-masing (brief bagian 8).
8. Studio `< 1280` px: pesan "Studio works best on a desktop screen", jangan layout HP.
9. Fokus keyboard terlihat (`outline` `--wax`). Studio: `A` accept, `E` edit, `R` reject, `J`/`K` next/prev.
10. Jangan tampilkan angka eval buatan. Gate 0 di mockup = "sample". Produksi = `latest.json`.

---

## Komponen (`web/components/`)

Bangun di **H3-6b** (bersama), dipakai ulang H4–H6. Jangan tulis ulang per halaman.

| File | Kontrak |
|---|---|
| `SourceBadge.tsx` | `source: Source \| null`; size `sm` \| `md`; ikon `AudioLines` / huruf T / `Eye`; warna `--src-*`; `title` = tooltip brief |
| `TimeSourceTag.tsx` | `asr` → "Timed by speech recognition"; `muse` → "Timed by Muse" |
| `StatusChip.tsx` | proposed / accepted / edited / rejected / merged |
| `ConfidenceTag.tsx` | high/medium/low: 3/2/1 titik + teks "High confidence" dst. |
| `NovelBadge.tsx` | "New term"; tooltip pack |
| `ValidationLabel.tsx` | documenter / expert · name / proposed by AI |
| `AttributionLine.tsx` | `variant: "inline" \| "card"` |
| `EvidenceClip.tsx` | `<video>` 16:9 + caption `{time} · {source} · {time_source}`; state loading/error "Clip unavailable" |
| `CropView.tsx` | tiga state di atas |
| `PronounceButton.tsx` | idle/playing; `<audio>` hidden, putar `audio_url` |
| `EntryCard.tsx` | Studio: view / edit inline / merge popover |
| `EntryRow.tsx` | Kamus HP: thumb 56 px, term, gloss satu baris, badge |
| `EntryCardPublic.tsx` | Kamus desktop: kartu |
| `TimelineTrack.tsx` | pita tahap + penanda: lingkaran Spoken, persegi On-screen, segitiga Visual; aktif `--wax` lebih besar |
| `JobProgress.tsx` | label manusiawi + `detail` tahap aktif |
| `UploadForm.tsx` | `variant: "studio" \| "try"` |
| `StudioKeyGate.tsx` | kartu tengah; error "Wrong key" di bawah field (cek `GET /api/archives` 401) |
| `ConfirmDialog.tsx` | cabut izin, copy berbahaya brief bagian 8 |
| `ProcessMapBand.tsx` | H4 |
| `MetricCard.tsx` / `EvalTable.tsx` | H5 |

`SourceBadge` tes unit (bukan render React): `sourceLabel("speech") === "Spoken"` exhaustive switch. `web/lib/source.ts`.

---

## Layout per layar (jangan mengarang informasi)

Urutan bangun **bukan** urutan prioritas desain. Implementasi mengikuti fase. Prioritas desain (kalau waktu H4 habis, kerjakan dari atas): S5b → S5 → S4 sudah H3 → S1 → S8 H5 → S3/S2 sudah H3 → S6 → S7.

### S4 Studio `/studio/recordings/[id]` (H3, Malam, desktop ≥ 1280)

- Top bar: judul, `AttributionLine` inline, hitungan `Proposed n · Accepted n · Edited n · Rejected n`, "k of n reviewed", pintasan, menu "Withdraw consent…" (H6).
- Kiri ±60%: video display + `TimelineTrack` (pita tahap jika process-map sudah ada; kalau H3 belum, penanda istilah saja).
- Kanan ±40%: filter status/sumber/New terms; kartu aktif (`EvidenceClip`, `CropView`, term serif, spoken miring, quote, badges, glosa, stage, maestro_note); aksi `Accept (A)` / `Edit (E)` / `Reject (R)` / `Merge…`; antrean ringkas di bawah.
- Edit **inline** di kartu: `term`, `gloss_en`, `gloss_id`, `maestro_note`. SourceBadge tetap tampil. Save edit / Cancel.
- Merge: popover cari kata kepala, preview `Merge *klowong* into *canting klowongan*?`.
- Filter kosong: "Nothing left in this filter." + saran "Show accepted".

### S2 Unggah `/studio/upload` (H3, Malam)

Area seret file. Field Archive, Title, Contributor name, Location. Segmented control "Own recording" / "CC BY video". Blok izin **di atas** tombol, bukan catatan kaki. Copy checkbox dan radio persis brief.

### S3 Progres `/studio/jobs/[id]` (H3, Malam)

Tujuh tahap label manusiawi, ikon waiting/running/done/failed, `seconds`, `detail` pada tahap aktif ("segment 3 of 4"), bar `progress`, "Mode B · retimed with speech recognition". Selesai: "Open in Studio". Gagal: `error` + Retry.

### S1 Beranda `/` (H4, Mori)

Bukan redirect ke Studio. Hero: wordmark `empu` serif + titik `--wax`, tagline, paragraf brief, CTA `Open the Batik Tulis archive` + `Try it with a 3-minute clip` + `See the evidence`. Visual: `docs/design/aset/nyanting-canting-122s.jpg` + kartu entri menempel (term `canting`, Spoken, crop). 3 langkah + 4 prinsip + kartu arsip + visi satu baris + footer atribusi + "Documenter studio".

Untuk hero statis, copy aset ke `web/public/design/` (bukan import dari `docs/`). Sertakan komentar atribusi di `web/public/design/README.md` (teks dari `aset/ATRIBUSI.md`).

### S5 Kamus `/d/[slug]` (H4, Mori)

Header: judul, `validated_count` / `recording_count`, `batik_tulis v{pack.version}`, daftar sumber CC BY singkat, tautan Process map + Download (public). Search + chip kategori (Tools, Tool parts, …) + stage + "New terms only". HP: `EntryRow`. Desktop ≥ 768: grid 3 kolom `EntryCardPublic`. Kelompok A–Z (satu skema, konsisten). Empty: brief bagian 9.

### S5b Detail `/d/[slug]/[id]` (H4, Mori) — halaman yang menjual

HP satu kolom; desktop dua kolom (bukti kiri, arti kanan). Urutan: breadcrumb → kata kepala serif + `PronounceButton` → chip kategori/tahap → "Also heard as" → `EvidenceClip` + `CropView` → kutipan (`said at` / `shown on screen at`) → `gloss_en` lalu `gloss_id` berlabel "Bahasa Indonesia" → confidence + New term → `ValidationLabel` → `AttributionLine` card → "Heard in n recordings" → tautan peta.

404 publik: copy empty state, bukan "Not found."

### S6 Peta `/d/[slug]/map/[recordingId]` (H4, Mori)

Desktop: `ProcessMapBand` horizontal. HP: daftar vertikal. Klik istilah → detail. Klik pita → seek (atau tautan ke Studio jika publik tidak punya player penuh: cukup buka klip tahap pertama).

### S7 Ekspor `/studio/export` (H3 layout Malam, diisi H4)

Empat kartu: JSON / CSV / ELAN `.eaf` / ZIP, satu kalimat per kartu. Radio "Public entries only" / "Everything except rejected (studio)". Catatan: "Every export includes creator attribution and the license."

### S8 Bukti `/evidence` (H5, Mori)

Judul: "This is the score, not the goal." Subjudul brief. `MetricCard` untuk headline Gate 2 (`latest.json`). Tabel klip. Blok "What generic captions heard": kolom Said · Auto-captions · Empu; baris `verified: false` tampil "not yet verified" (jangan klaim). Batasan + metode 4 baris (brief bagian 6 S8).

### `/try` (H6, Mori)

`UploadForm variant="try"`. Copy sandbox + sisa kuota. Izin tetap wajib. Setelah unggah → progres (tanpa StudioKeyGate) → studio sandbox.

### Gerbang `/studio`

Kartu tengah: "Studio key", password, "Enter". Cek kunci dengan request sungguhan; salah → pesan di bawah field.

---

## Aset

Hanya dua video CC BY. Frame lisensi standar **dilarang** di UI, mockup, dan demo.

| File | Pakai |
|---|---|
| `nyanting-canting-122s.jpg` | Hero S1, poster canting |
| `contoh-overlay-canting.jpg` | CropView "Show in frame" |
| `contoh-crop-canting.png` | CropView crop (uji bingkai tetap pada rasio aneh) |
| `nyanting-wajan-272s.jpg` | Visual only |
| `nyanting-caption-362s.jpg` | Footage bersubtitle (jangan disembunyikan) |
| `macamcanting-diagram-klowong-44s.jpg` | On-screen text |
| `macamcanting-canting-100s.jpg` | canting tembokan |

Kotak overlay/crop di aset **buatan manual**, pengganti SAM untuk mockup. Di app produksi keduanya dari SAM 3.1.

---

## Yang tidak dibangun

Dark mode toggle untuk publik. Akun/profil. Animasi kompleks. Library UI berat. Pemutar video kustom. Motif parang/kawung. Halaman marketing panjang.

## Kalau waktu habis

H3: token + SourceBadge + CropView + Studio keyboard + izin menonjol. Merge popover boleh jadi input id.  
H4: S5b dan S5 dulu, lalu S1. S6/S7 memakai komponen yang sama.  
H6: jangan redesign; empty state yang belum ada saja.
