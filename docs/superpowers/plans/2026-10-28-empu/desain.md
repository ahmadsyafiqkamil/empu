# Empu: Kontrak UI (Modernist)

> **Untuk implementer H3–H7.** Baca file ini bersama `00-ikhtisar.md` + file fase. Sumber: `docs/design/brief-claude-design.md`. Kalau plan fase menampilkan kode kerangka yang bertentangan dengan file ini, **file ini yang menang** untuk visual, copy, dan layout.

**Bukan mockup.** Claude Design (kalau ada) hanya referensi. Jangan menunggu mockup. Token, copy, dan layout di sini sudah cukup untuk membangun. H6 hanya 60 menit polesan — desain yang telat = kamus yang terlihat seperti admin tool.

## Sumber

| File | Pakai untuk |
|---|---|
| `Empu web aplikasi redesign/` | **Mockup terkini (Modernist).** Sumber visual utama: `Empu Public.dc.html` dan `Empu Studio.dc.html`, plus `_ds/modernist-*/styles.css` untuk token dan kelas komponen |
| `docs/design/konteks-design-saat-ini.md` | Kondisi UI per layar dan komponen saat ini, beserta selisihnya |
| `docs/design/brief-claude-design.md` | Aturan produk dan microcopy (tetap berlaku). Token warna dan tipografi di dalamnya **sudah digantikan** bagian Token di file ini |
| `docs/design/contoh-data.json` | Bentuk data UI = `web/lib/types.ts`. Jangan mendesain field yang tidak ada di sini |
| `docs/design/aset/` | Frame CC BY untuk hero statis. Atribusi: `docs/design/aset/ATRIBUSI.md` |

`contoh-data.json` **bukan** hasil pipeline. Istilah/kutipan dikira-kira. Angka `eval_summary` adalah Gate 0 sungguhan dan harus berlabel "sample" sampai `latest.json` H5 ada. Field bantu yang tidak ada di API: `recordings[].poster`, `archive.craft_pack_version` (dari `/api/packs`), `steps[].label_en` (dari pack `label.en`).

---

## Keputusan (D11)

> **Diperbarui 31 Okt 2026.** Arah visual diganti ke sistem **Modernist** (lihat
> `docs/design/konteks-design-saat-ini.md` dan `Empu web aplikasi redesign/`). Satu tema
> terang untuk semua halaman; Studio dibedakan oleh header bar gelap, bukan oleh tema gelap.
> Token, tipografi, dan radius di bawah sudah yang baru. Aturan produk (label sumber, bukti
> dulu, frame asli, atribusi, klaim validasi, izin) tidak berubah sama sekali.

Satu mode. **Terang** untuk semua halaman. Studio tetap terasa berbeda karena header bar
hitam dan kepadatan tabelnya, bukan karena latar gelap.

Rasa: arsip museum yang hidup, bukan aplikasi AI mengkilap. Bukti di atas penjelasan.
Tanpa motif batik klasik, tanpa keris. Struktur dibentuk oleh grid dan garis 2px, bukan
oleh kartu dan bayangan.

---

## Token (tempel ke `web/app/globals.css`)

Nama variabel **wajib** sama. Kontras sudah dicek AA di brief bagian 4.

```css
:root {
  --color-bg: #f3f2f2;
  --color-surface: #eae9e9;
  --color-text: #201e1d;
  --color-accent: #ec3013;          /* brand: wordmark, tautan, nav aktif, banner */
  --color-action: #ae1800;          /* isi tombol utama — 6.5:1 dengan --color-bg */
  --color-action-hover: #7c1405;
  --color-divider: color-mix(in srgb, #201e1d 40%, transparent);
  --color-neutral-100 … --color-neutral-900;
  --color-accent-100 … --color-accent-900;
  --font-heading: Archivo 800;
  --font-body: Archivo 400;
  --font-mono: ui-monospace, "SF Mono", Menlo;
  --space-1: 4px … --space-8: 32px;
  --radius-sm/md/lg: 0;
}
```

Font dimuat lewat `next/font/google` di `web/app/layout.tsx`: **Archivo 400 / 600 / 800**
sebagai `--font-archivo`. Tidak ada serif. Tidak ada sudut membulat.

Tombol utama memakai `--color-action`, bukan `--color-accent`: teks `#f3f2f2` di atas
`#ec3013` hanya 3,2:1 dan gagal AA untuk label 14px. `--color-accent` tetap dipakai untuk
wordmark, tautan, nav aktif, dan banner visi. **Accept di Studio memakai tinta
`--color-text`**, bukan merah, supaya tidak tertukar dengan Reject.

Ikon: `lucide-react` (garis). Gerak: transisi 150 ms. Tidak ada hero animation, parallax,
typing effect.

Foto: **berwarna**. Kelas `.grayscale` dari sistem Modernist tidak dipakai — batik identik
dengan warna, dan menghapusnya melemahkan klaim "bukti asli".

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
9. Fokus keyboard terlihat (`outline` 2px `--color-accent`). Studio: `A` accept, `E` edit, `R` reject, `J`/`K` next/prev.
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
| Timeline di `Studio.tsx` | pita tahap di atas, lalu satu lajur per sumber (Spoken, On-screen, Visual); penanda aktif pakai `--color-accent` dengan cincin |
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

### S4 Studio `/studio/recordings/[id]` (H3, Studio, desktop ≥ 1280)

- Top bar: judul, `AttributionLine` inline, hitungan `Proposed n · Accepted n · Edited n · Rejected n`, "k of n reviewed", pintasan, menu "Withdraw consent…" (H6).
- Kiri ±60%: video display + `TimelineTrack` (pita tahap jika process-map sudah ada; kalau H3 belum, penanda istilah saja).
- Kanan ±40%: filter status/sumber/New terms; kartu aktif (`EvidenceClip`, `CropView`, term serif, spoken miring, quote, badges, glosa, stage, maestro_note); aksi `Accept (A)` / `Edit (E)` / `Reject (R)` / `Merge…`; antrean ringkas di bawah.
- Edit **inline** di kartu: `term`, `gloss_en`, `gloss_id`, `maestro_note`. SourceBadge tetap tampil. Save edit / Cancel.
- Merge: popover cari kata kepala, preview `Merge *klowong* into *canting klowongan*?`.
- Filter kosong: "Nothing left in this filter." + saran "Show accepted".

### S2 Unggah `/studio/upload` (H3, Studio)

Area seret file. Field Archive, Title, Contributor name, Location. Segmented control "Own recording" / "CC BY video". Blok izin **di atas** tombol, bukan catatan kaki. Copy checkbox dan radio persis brief.

### S3 Progres `/studio/jobs/[id]` (H3, Studio)

Tujuh tahap label manusiawi, ikon waiting/running/done/failed, `seconds`, `detail` pada tahap aktif ("segment 3 of 4"), bar `progress`, "Mode B · retimed with speech recognition". Selesai: "Open in Studio". Gagal: `error` + Retry.

### S1 Beranda `/` (H4, publik)

Bukan redirect ke Studio. Hero: wordmark `empu` Archivo 800 + titik `--color-accent`, tagline, paragraf brief, CTA `Open the Batik Tulis archive` + `Try it with a 3-minute clip` + `See the evidence`. Visual: `docs/design/aset/nyanting-canting-122s.jpg` + kartu entri menempel (term `canting`, Spoken, crop). Baris arsip berisi sel yang bisa diklik, 3 langkah bergambar, 4 prinsip sebagai sel grid, banner visi merah, footer atribusi + "Documenter studio".

Untuk hero statis, copy aset ke `web/public/design/` (bukan import dari `docs/`). Sertakan komentar atribusi di `web/public/design/README.md` (teks dari `aset/ATRIBUSI.md`).

### S5 Kamus `/d/[slug]` (H4, publik)

Header: judul, `validated_count` / `recording_count`, `batik_tulis v{pack.version}`, daftar sumber CC BY singkat, tautan Process map + Download (public). Search + chip kategori (Tools, Tool parts, …) + stage + "New terms only". HP: `EntryRow`. Desktop ≥ 768: grid 3 kolom `EntryCardPublic`. Kelompok per kategori, bukan A–Z: kategori adalah informasi nyata, huruf awal bukan. Empty: brief bagian 9.

### S5b Detail `/d/[slug]/[id]` (H4, publik) — halaman yang menjual

HP satu kolom; desktop dua kolom (bukti kiri, arti kanan). Urutan: breadcrumb → kata kepala serif + `PronounceButton` → chip kategori/tahap → "Also heard as" → `EvidenceClip` + `CropView` → kutipan (`said at` / `shown on screen at`) → `gloss_en` lalu `gloss_id` berlabel "Bahasa Indonesia" → confidence + New term → `ValidationLabel` → `AttributionLine` card → "Heard in n recordings" → tautan peta.

404 publik: copy empty state, bukan "Not found."

### S6 Peta `/d/[slug]/map/[recordingId]` (H4, publik)

Desktop: `ProcessMapBand` horizontal. HP: daftar vertikal. Klik istilah → detail. Klik pita → seek (atau tautan ke Studio jika publik tidak punya player penuh: cukup buka klip tahap pertama).

### S7 Ekspor `/studio/export` (H3 layout Studio, diisi H4)

Empat kartu: JSON / CSV / ELAN `.eaf` / ZIP, satu kalimat per kartu. Radio "Public entries only" / "Everything except rejected (studio)". Catatan: "Every export includes creator attribution and the license."

### S8 Bukti `/evidence` (H5, publik)

Judul: "This is the score, not the goal." Subjudul brief. `MetricCard` untuk headline Gate 2 (`latest.json`). Tabel klip. Blok "What generic captions heard": kolom Said · Auto-captions · Empu; baris `verified: false` tampil "not yet verified" (jangan klaim). Batasan + metode 4 baris (brief bagian 6 S8).

### `/try` (H6, publik)

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
