# Konteks Desain Empu: Kondisi Saat Ini

Snapshot per 31 Okt 2026. Dokumen ini mendeskripsikan **apa yang benar-benar ada di aplikasi sekarang** — bukan rencana, bukan cita-cita. Tujuannya: jadi bahan bagi Claude Design untuk **merapikan** tampilan yang sudah jalan, tanpa mengubah hal-hal yang sudah benar.

| | |
|---|---|
| Untuk | Claude Design (atau desainer mana pun) |
| Lampirkan | File ini + `brief-claude-design.md` + `contoh-data.json` + folder `aset/` + dua mockup `design/Empu Public.dc.html` dan `design/Empu Studio.dc.html` |
| Yang diminta | Pembaruan mockup: 4 layar lama dirapikan, 8 layar baru dibuat, sistem komponen disatukan |
| Bahasa UI | Inggris (microcopy tidak boleh diparafrase) |
| Stack | Next.js 16 App Router, React 19, Tailwind 4, TypeScript, Lucide |

---

## 1. Ringkasan: di mana kita sekarang

Empu sudah berjalan penuh. Pipeline (unggah → analisis → validasi → kamus publik → ekspor → evaluasi) terhubung ke UI, bukan mockup. Yang belum: **desainnya belum satu sistem.**

Ada tiga sumber kebenaran visual yang saling bertabrakan:

1. `docs/design/brief-claude-design.md` — brief awal, 28 Okt. Font: **Fraunces + Inter**, radius **2px**, kamus dikelompokkan **A–Z**.
2. `design/Empu Public.dc.html` dan `design/Empu Studio.dc.html` — mockup Claude Design. Font: **Newsreader + IBM Plex Sans**, radius **4/6/8px**, kamus dikelompokkan **per kategori**, ada header global.
3. `web/` — kode yang jalan. Font dan radius ikut **brief** (Fraunces, Inter, 2px), tetapi beberapa elemen memakai nilai Tailwind default (`rounded` = 4px), dan tidak ada header global sama sekali.

Hasilnya bisa dilihat di aplikasi: tiap layar benar sendiri-sendiri, tetapi tidak terasa satu produk. Contoh konkret: beranda memakai lebar `max-w-3xl`, kamus `max-w-5xl`, detail entri `max-w-5xl` dua kolom, sementara mockup memakai 1200px untuk beranda dan 1100px untuk kamus serta detail.

**Keputusan yang harus diambil di awal revisi** (rekomendasi saya di kolom kanan):

| Hal | Sekarang | Rekomendasi |
|---|---|---|
| Tipografi | Fraunces (kode) vs Newsreader (mockup) | **Newsreader + IBM Plex Sans** seperti mockup. Hurufnya lebih netral, dan mockup sudah memakainya di 4 layar yang paling penting |
| Radius | 2px dari token, 4px dari Tailwind default | Skala **4 / 6 / 8 px** seperti mockup; hapus `--radius: 2px` |
| Pengelompokan kamus | A–Z | **Per kategori** seperti mockup. Kategori adalah informasi nyata (`category`), huruf awal bukan |
| Chrome | Tidak ada header | **Satu header publik** (wordmark + Dictionary / Evidence + Documenter studio) dan satu header Studio |

---

## 2. Cakupan mockup yang ada vs layar yang benar-benar ada

| Layar | Rute | Ada di mockup? | Ada di kode? |
|---|---|---|---|
| S1 Beranda | `/` | Ya | Ya |
| S5 Kamus | `/d/[slug]` | Ya | Ya |
| S5b Detail entri | `/d/[slug]/[id]` | Ya | Ya |
| S4 Studio validasi | `/studio/recordings/[id]` | Ya | Ya |
| Gerbang kunci studio | `/studio` | Tidak | Ya |
| S2 Unggah | `/studio/upload` | Tidak | Ya |
| S3 Progres job | `/studio/jobs/[id]` | Tidak | Ya |
| S7 Ekspor | `/studio/export` | Tidak | Ya |
| Craft packs | `/studio/packs` | Tidak | Ya (fitur baru, belum ada di brief lama) |
| S6 Peta tahapan | `/d/[slug]/map/[recordingId]` | Tidak (hanya muncul sebagai link nav) | Ya |
| S8 Bukti | `/evidence` | Tidak (hanya link nav) | Ya |
| Try (sandbox juri) | `/try` | Tidak | Ya |

Mockup publik hanya mengisi 3 dari 6 layar publik + 1 dari 6 layar Studio. Jadi pekerjaan revisi bukan "poles 4 layar", tetapi **melengkapi sistem 12 layar** dengan 4 layar sebagai jangkar.

Mockup ketiga (`design/Empu iOS.dc.html`) tidak dipakai. Tidak ada aplikasi native.

---

## 3. Token dan tipografi yang benar-benar dipakai kode

Isi `web/app/globals.css` saat ini (hanya ini yang ada — tidak ada skala spasi, skala radius, skala teks, bayangan, atau durasi):

```css
:root {
  --bg: #F5F0E6;         --surface: #FBF8F2;      --fg: #1C1813;
  --muted: #665D50;      --line: #DDD4C4;         --accent: #22304F;
  --wax: #9E7330;        --src-speech: #22304F;   --src-onscreen: #8A4B22;
  --src-visual: #5E5A52; --ok: #3F6B45;           --danger: #9B3B2E;
  --font-display: "Fraunces", serif;
  --font-ui: "Inter", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --radius: 2px;
}
[data-theme="malam"] {
  --bg: #12110F; --surface: #1B1916; --fg: #ECE8DF; --muted: #A39C8E;
  --line: #2E2B26; --accent: #C9A15B; --wax: #C9A15B;
  --src-speech: #9DB0E3; --src-onscreen: #DDA272; --src-visual: #B3AC9F;
  --ok: #7FB384; --danger: #E57373;
}
```

Font dimuat lewat `next/font/google` di `web/app/layout.tsx`: `Fraunces`, `Inter`, `JetBrains_Mono`.

Token yang **ada di mockup tetapi belum ada di kode** (`design/globals.css`): `--accent-fg`, `--wax-tint #EFE3CC`, `--wax-ink #5C4214`, `--media-frame #2A2621`, `--shadow-card`, `--shadow-pop`, `--dur 150ms`, `--radius-sm/md/lg`, `--space-1…18`, skala teks `--text-*` dan `--head-*`.

Angka dari mockup, untuk referensi saat menyatukan:

| Skala | Nilai mockup |
|---|---|
| Teks isi | 12 / 13 / 15 / 18 px |
| Kata kepala | 22 / 30 / 44 / 64 / 76 px (76 hanya di detail entri desktop, 44 di mobile) |
| Spasi | 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 56 / 72 px |
| Radius | 4 badge, chip, thumbnail · 6 tombol, kartu, media · 8 dialog |
| Tinggi kontrol | 26 chip label, 34 filter, 40 tombol kecil, 44 aksi utama, 48–52 tombol hero |
| Lebar konten | 1200 (beranda), 1100 (kamus, detail), penuh (Studio ≥1280) |
| Header | 64 px publik, 56 px mobile, 64 px Studio |

---

## 4. Inventaris layar: isi sekarang dan selisihnya

Format: **isi sekarang** (urutan DOM nyata) → **selisih terhadap mockup** → **yang perlu diputuskan**.

### 4.1 Beranda `/` (mode Mori)

Berkas: `web/app/page.tsx` + `web/components/ArchivePicker.tsx`.

Isi sekarang, satu kolom `max-w-3xl`, padding `px-6 py-10`:

1. Wordmark teks `empu.` (serif, 30px, titik berwarna `--wax`).
2. Tagline 36px, `max-w-xl`.
3. Paragraf penjelasan, warna muted.
4. Baris chip arsip (satu chip per arsip publik, chip aktif = latar `--accent` + teks putih) dengan angka entri tervalidasi.
5. Tiga CTA: `Open the archive` (isi accent), `Try it with a 3-minute clip` (garis), `See the evidence` (garis).
6. Grid 2 kolom: gambar 16:9 dari entri pertama + kartu `--surface` berisi istilah, badge sumber, titik keyakinan.
7. "How it works": daftar bernomor 3 langkah, angka monospace warna `--wax`.
8. "Principles": grid 2 kolom, tiap sel bergaris.
9. Visi satu baris, serif miring 20px.
10. Footer: tiga paragraf kecil + link "Documenter studio".

Selisih terhadap S1:

- Mockup dua kolom 5:7 — teks kiri, gambar + kartu entri mengambang kanan. Kode satu kolom, kartu di bawah gambar.
- Mockup punya blok "Cara kerja" dengan gambar per langkah; kode hanya daftar teks bernomor.
- Mockup punya kartu "Living Archive · Batik Tulis" berisi 3 angka (entri / rekaman / kreator); kode punya baris chip arsip, bukan kartu.
- Mockup punya header 64px dengan nav; kode tidak punya header sama sekali.
- Lebar maksimum 768px vs 1200px.
- Pemilih arsip (chip) adalah fitur nyata yang tidak ada di mockup. Harus dipertahankan, tapi diberi tempat yang pantas (mis. di dalam kartu Living Archive atau sebagai baris di bawah hero).

### 4.2 Kamus `/d/[slug]` (Mori)

Berkas: `web/app/d/[slug]/page.tsx` + `EntryCardPublic.tsx` + `EntryRow.tsx`.

Isi sekarang, `max-w-5xl`, `px-6 py-8`:

1. Breadcrumb teks: `Home · Living Archive`.
2. Judul arsip 30px.
3. Baris angka: `{validated_count} validated terms · {recording_count} recordings · {pack} v{version}`.
4. Link `Download (ZIP)`.
5. Form pencarian: input + tombol `Search` (butuh submit).
6. Baris chip: `All` + 8 kategori + `New terms only` — semuanya `<Link>`, bukan tombol.
7. Form kedua terpisah: `Stage` select + tombol `Apply`.
8. Daftar HP: baris, thumbnail 56×56 `object-cover`, istilah, satu baris glosa, badge.
9. Desktop: dikelompokkan **A–Z**, tiap huruf judul monospace kecil, grid 2–3 kolom.

Selisih terhadap S5:

- **Pengelompokan**: A–Z → per kategori.
- **Filter**: mockup satu baris (chip + select tahap + sakelar "New terms only"); kode dua form terpisah dengan dua tombol submit.
- **Tombol arsip**: mockup `Process map` + `Download (public)` sejajar di kanan judul; kode hanya satu link teks unduh.
- **Kartu entri**: mockup thumbnail 4:5 di dalam bingkai 88px dengan `contain`; kode 16:9 `object-cover`. Ini penting: crop SAM sering 108×234, jadi `cover` memotong alatnya.
- **Header**: mockup punya header global; kode tidak.
- Sumber CC BY tidak dicantumkan di header arsip (mockup mencantumkannya).

### 4.3 Detail entri `/d/[slug]/[id]` (Mori)

Berkas: `web/app/d/[slug]/[id]/page.tsx` + `EvidenceClip` + `CropView` + `PronounceButton` + `SourceBadge` + `ConfidenceTag` + `NovelBadge` + `AttributionLine`.

Isi sekarang, `max-w-5xl`, grid 2 kolom sama besar:

- Kolom kiri: breadcrumb arsip → klip video 16:9 → crop 4:5 dengan keterangan.
- Kolom kanan: kata kepala 36px + tombol speaker **ikon saja** → chip kategori & tahap (garis polos) → badge New → "Also heard as" → kutipan (14px, garis kiri accent) + keterangan `said at 0:37` → glosa EN (serif 20px) → glosa ID dengan label "Bahasa Indonesia" → badge sumber + titik keyakinan → label validasi → atribusi → "Heard in n recordings" → link peta tahapan.

Selisih terhadap S5b:

- **Kata kepala**: 36px vs 76px desktop / 44px mobile. Mockup memakai ukuran itu untuk efek "entri kamus"; ini yang membuat halaman terasa arsip, bukan halaman detail biasa.
- **Tombol dengar**: ikon saja vs tombol berlabel `Hear it` / `Playing…` dengan latar accent.
- **Bukti**: mockup menaruh crop 260px **berdampingan** dengan kutipan 28px serif; kode menumpuk crop di bawah klip dan kutipan kecil di kolom kanan. Ini mengubah hierarki: sekarang arti lebih menonjol daripada bukti.
- **Daftar kemunculan**: mockup menampilkan `Heard in 2 recordings` dengan baris yang bisa diputar (tombol 36px, judul rekaman, waktu mono, badge sumber). Kode hanya satu baris teks jumlah.
- **Blok keyakinan + validasi**: mockup satu strip bergaris atas-bawah; kode dua elemen terpisah.
- **Kartu sumber**: mockup kartu `--surface` bergaris; kode satu baris teks muted.
- Chip kategori/tahap belum memakai gaya pill mockup (26px, `--surface`, radius 4).
- Urutan: mockup → bukti dulu, lalu arti; kode sudah mendekati tapi bobotnya terbalik.

### 4.4 Studio validasi `/studio/recordings/[id]` (Malam)

Berkas: `web/components/Studio.tsx` + `EntryCard.tsx`.

Isi sekarang:

- Header: satu baris `judul` (serif 18px) + atribusi inline; baris kedua teks kecil: `Proposed n · Accepted n · Edited n · Rejected n`, `k of n reviewed`, daftar pintasan sebagai teks, tombol `Withdraw consent` (underline).
- Grid `1.2fr / minmax(24rem, 1fr)`.
- Kiri: video 16:9 `bg-black` dengan kontrol native → timeline `h-10` berwarna `--line`/40 dengan penanda (lingkaran / persegi / segitiga) → tiga badge sumber sebagai legenda.
- Kanan: baris filter berupa dua `<select>` + checkbox `novel` + jumlah entri → `EntryCard` → daftar antrean `max-h-32` berisi baris kecil (badge + istilah).

Selisih terhadap S4:

- **Header**: mockup punya empat angka berlabel + bar progres 150px + tombol menu (Open process map / Export / Withdraw consent). Kode: teks satu baris, tanpa bar progres, tanpa menu.
- **Timeline**: mockup punya pita tahap (nglowong / nembok / medel / nglorod) dengan label, penanda yang tersusun tiga baris sesuai sumber, penggaris waktu 0:00–6:40, dan baris pintasan keyboard berbentuk `<kbd>`. Kode hanya satu baris penanda tanpa pita, tanpa penggaris.
- **Filter**: mockup chip bergaya (30px, aktif emas); kode `<select>` bawaan browser.
- **Kartu entri**: mockup menaruh klip 16:9 dan crop berdampingan di grid 1fr/128px, kata kepala 40px, baris badge, kutipan 19px dengan meta, glosa dua kolom EN/ID, tahap + catatan maestro sebagai satu baris, label status berwarna. Kode menumpuk semuanya vertikal, glosa tidak berkolom, status jadi chip kecil.
- **Aksi**: mockup `Accept` hijau padat dengan ikon + `<kbd>A</kbd>`, `Edit` bergaris, `Reject` merah bergaris, `Merge…` bergaris. Kode: Accept `bg-ok text-black`, Reject `bg-danger` penuh (bukan garis).
- **Antrean**: mockup panel daftar penuh dengan titik sumber, istilah serif 17px, label sumber, waktu mono, chip status, dan border kiri emas untuk item aktif. Kode daftar kecil 128px di dasar panel.
- Mode edit dan popover merge di kode sudah berfungsi (bukan `window.prompt`) tetapi gayanya belum mengikuti mockup (mockup memakai kotak bergaris emas berlabel `Editing`).

### 4.5 Gerbang kunci `/studio`

`StudioKeyGate`: form tengah `max-w-sm`, judul "Studio key", teks bantuan "Paste STUDIO_KEY from the server environment.", input password, pesan "Wrong key" di bawah field, tombol `Enter` (accent + teks hitam).

Selisih: berfungsi, tapi tidak ada di mockup. Saat memeriksa kunci, komponen mengembalikan `null` → layar kosong sekejap. Perlu state "checking" yang terlihat.

### 4.6 Beranda Studio `/studio`

`main` padding 32px: eyebrow `EMPU · STUDIO`, judul 30px, tiga tautan bergaris (Upload recording / Export / Craft packs).

Selisih: tidak ada di mockup. Tidak ada tautan balik ke situs publik, tidak ada daftar rekaman yang menunggu validasi — padahal itu tujuan halaman ini.

### 4.7 Unggah `/studio/upload` dan `/try`

Berkas: `web/components/UploadForm.tsx`, `variant: "studio" | "try"`.

Isi sekarang:

- Studio: judul → form arsip (jika belum ada arsip: slug / title / craft pack) → drop zone garis putus-putus → Title → Contributor name → Location → segmented `Own recording` / `CC BY video` → blok field CC BY (URL, creator, license, attribution) → fieldset **Consent** bergaris `--wax` berisi 3 radio Public/Community/Private, Consent note, checkbox wajib → tombol `Upload and process`.
- Try: judul "Try it" → catatan sandbox → drop zone → Title → checkbox izin → tombol `Process 3-minute clip`. Tanpa sisa kuota (padahal helper `tryQuota()` sudah ada di `lib/copy.ts`).

Selisih: tidak ada di mockup, jadi perlu didesain. Catatan teknis: tombol utama memakai `bg-[var(--accent)] text-black`. Di Studio (Malam) itu benar (emas + hitam). Di `/try` (Mori) accent = indigo gelap dan teks hitam → kontras ±1,7:1, gagal WCAG AA. Ini bug nyata, bukan selera.

### 4.8 Progres job `/studio/jobs/[id]`

`JobProgress`: judul "Processing" → baris mode (`Mode B · retimed with speech recognition`) + detail → daftar 7 tahap dengan ikon status (lingkaran / spinner / centang / silang), label manusiawi, lalu kolom kanan berisi **kata status mentah** (`pending`, `running`, `done`) + `seconds` + detail → bar progres 4px → tombol `Open in Studio` atau pesan error + `Retry`.

Selisih: menampilkan status mentah dua kali (ikon + kata Inggris), tidak ada kalimat penjelas per tahap seperti diminta brief, tidak ada waktu berjalan.

### 4.9 Ekspor `/studio/export`

`max-w-2xl`: judul → select arsip → fieldset format 4 kartu radio 2×2 (JSON / CSV / ELAN / ZIP) dengan satu baris penjelasan → radio scope → catatan → tombol unduh.

Selisih: kartu format berfungsi, tetapi tidak memakai radius/padding mockup; radio scope dan tombol tidak konsisten tinggi.

### 4.10 Craft packs `/studio/packs`

`max-w-4xl`: judul + deskripsi → daftar pack (istilah, id, versi, aksi "Load as example") → textarea YAML `h-96` monospace → tombol Validate / Create pack → kotak hasil valid (✓ hijau) atau tidak valid (✗ merah + pesan).

Selisih: layar baru, belum pernah didesain. Perlu satu putaran tata letak.

### 4.11 Peta tahapan `/d/[slug]/map/[recordingId]`

Desktop: satu baris pita tahap, lebar proporsional durasi, latar `--surface`, hover accent, berisi nama tahap + rentang waktu; klik → entri pertama tahap itu. Mobile: daftar vertikal (nama, waktu, tautan istilah).

Selisih: tidak ada thumbnail, tidak ada video, tidak ada penanda waktu. Mockup Studio sudah punya bahasa visual pita tahap — sebaiknya dipakai ulang di sini.

### 4.12 Bukti `/evidence`

`max-w-3xl`: judul serif 30px → subjudul → tabel 6 kolom tanpa gaya (Clip, Speech recall, Precision, Median |Δt|, Source accuracy, ASR baseline) → satu baris kontrol musik → dua paragraf batasan.

Selisih: brief meminta kartu angka utama (`7 of 8`, `4 of 8`, median galat, kontrol musik, uji tanpa audio), tabel "What generic captions heard", dan blok metode. Semua belum ada. Tabel sekarang terbaca seperti tabel admin.

---

## 5. Inventaris komponen: tampilan sekarang

| Komponen | Props | Tampilan sekarang | Selisih utama |
|---|---|---|---|
| `SourceBadge` | `source`, `size sm/md` | Ikon Lucide (`AudioLines` / huruf `T` / `Eye`) + teks, warna `--src-*`, **tanpa border** | Mockup: pill 22–24px bergaris, radius 4, teks 11–13px |
| `TimeSourceTag` | `timeSource` | Teks muted 12px + tooltip | Mockup: bagian dari baris keterangan bukti, bukan elemen sendiri |
| `StatusChip` | `status` | Border + teks berwarna, radius 2px | Mockup: latar tint (accepted `#18241A`), radius 4, teks 13px |
| `ConfidenceTag` | `confidence` | 3/2/1 titik + teks muted | Sama secara isi; pembungkus strip belum ada |
| `NovelBadge` | – | Titik `--wax` + teks muted | Mockup: pill latar `--wax-tint`, teks `--wax-ink`, tebal 600 |
| `ValidationLabel` | `variant`, `expertName?` | Centang hijau + teks 14px | Mockup: bagian strip keyakinan, warna `--ok` |
| `AttributionLine` | `variant inline/card` | Satu baris muted, atau kartu `--surface` bergaris | Mockup: kartu 13px dengan label `Source` kecil di atasnya |
| `EvidenceClip` | `clipUrl, tStart, tEnd, source, timeSource` | Video 16:9 + caption mono satu baris | Mockup: keterangan dipecah — waktu mono, pemisah, badge sumber, ikon waktu |
| `CropView` | `cropUrl, overlayUrl, keyframeUrl, samStatus` | Bingkai 4:5 `contain`, label di bawah, toggle = checkbox | Mockup: bingkai lebar tetap (260 desktop / 132 mobile / 128 studio), sakelar = dua tombol segmen `Crop` / `Show in frame` |
| `PronounceButton` | `audioUrl` | Ikon speaker saja, transparan | Mockup: tombol accent 44px berlabel `Hear it` |
| `EntryRow` | `slug`, `e` | Baris: thumb 56px cover, istilah, glosa, badge | Mockup: thumb 56px `contain` dalam bingkai `--surface`, baris badge sumber berupa ikon + label 11px |
| `EntryCardPublic` | `slug`, `e` | Kartu: gambar 16:9 `cover`, istilah 20px, glosa, badge | Mockup: grid `88px / 1fr`, thumb 4:5, istilah serif 24px, glosa 2 baris clamp |
| `EntryCard` | `entry, archiveId, editing, …` | Lihat 4.4 | Perlu disusun ulang mengikuti mockup |
| `ProcessMapBand` | `steps`, `duration`, `slug` | Pita flex, teks saja | Perlu thumbnail + bahasa visual yang sama dengan timeline Studio |
| `JobProgress` | `jobId` | Lihat 4.8 | Perlu kalimat penjelas + waktu |
| `UploadForm` | `variant` | Lihat 4.7 | Perlu desain + perbaikan kontras |
| `StudioKeyGate` | `children` | Lihat 4.5 | Perlu state checking |
| `ArchivePicker` | `archives` | Lihat 4.1 | Perlu dipecah: hero, pemilih arsip, kartu arsip |

Tidak ada komponen untuk: header publik, footer publik, header Studio, dialog konfirmasi, empty state, skeleton/loading, panel filter chip, daftar antrean Studio, kartu angka (metric).

---

## 6. Inkonsistensi yang harus dibereskan

Diurutkan dari yang paling terlihat. Semua poin di bawah bisa dicek langsung di kode.

1. **Dua sistem tipografi.** Fraunces + Inter di kode; Newsreader + IBM Plex Sans di mockup. Semua ukuran judul di kode berasal dari skala Tailwind (`text-2xl`, `text-3xl`, `text-4xl`), bukan skala desain.
2. **Radius campur.** Token `--radius` 2px dipakai di 3 tempat; `rounded` bawaan Tailwind (4px) dipakai di `Studio.tsx`, `EvidenceClip`, `StatusChip`; sisanya siku. Tidak ada radius 6px sama sekali, padahal semua kartu dan tombol di mockup 6px.
3. **Tidak ada chrome.** Tidak ada header publik, tidak ada footer bersama. Tiap halaman mulai dengan `main`-nya sendiri pada lebar berbeda (3xl, 4xl, 5xl, 2xl, xl).
4. **Navigasi putus.** `/evidence` dan `/try` hanya bisa dicapai dari CTA beranda. Dari kamus tidak ada jalan ke Bukti atau Studio. Tidak ada link balik dari Studio ke situs publik. Mockup punya nav `Dictionary / Process map / Evidence / Documenter studio`, dan "Process map" belum punya rute tingkat atas.
5. **Kontras gagal di `/try`.** Tombol `Process 3-minute clip` memakai teks hitam di atas indigo `#22304F`. Perlu `--accent-fg` per tema, bukan `text-black`/`text-white` yang di-hardcode. Pola hardcode yang sama ada di `studio/packs`, `EntryCard`, `StudioKeyGate`, dan segmented control unggah.
6. **Kamus tidak sesuai keputusan desain.** Dikelompokkan A–Z; mockup per kategori. Filter tersebar di dua form dengan dua tombol submit.
7. **Thumbnail memotong alat.** `object-cover` 16:9 pada crop SAM berukuran 108×234 memotong subjek. Mockup memakai bingkai 4:5 + `contain`.
8. **Hierarki bukti terbalik di detail entri.** Arti lebih besar daripada bukti; mockup menaruh klip + crop + kutipan 28px sebagai blok utama.
9. **Studio belum memakai bahasa visual mockup.** Filter `<select>`, timeline tanpa pita tahap, antrean 128px, header tanpa progres, tombol aksi tanpa ikon/pintasan.
10. **Status job ditampilkan dua kali** (ikon + kata Inggris mentah) dan tanpa kalimat penjelas.
11. **Empty state tidak seragam.** Semua berupa `<p>` polos dengan padding berbeda: `p-8` (404, loading), `p-3` (crop), teks muted tanpa bingkai (kamus, filter studio). Mockup memakai kotak bergaris putus-putus 40px dengan tombol aksi.
12. **Loading tidak terlihat.** "Loading…" teks polos di Studio dan Progres; `StudioKeyGate` mengembalikan `null` saat memeriksa.
13. **Tidak ada state hover/focus yang konsisten** selain `focus-visible` outline `--wax` (ini sudah benar dan harus dipertahankan). Hover kartu di mockup (`border-color: --accent`) belum ada.
14. **Mobile belum ditata.** Kamus punya varian HP, detail entri belum (mockup punya susunan HP lengkap: header 56px, judul 44px, klip full-bleed `-20px`, crop 132px + kutipan berdampingan, arti di bawah garis), beranda dan Bukti hanya menumpuk.
15. **Angka dan label campur bahasa.** "Heard in 2 recordings" (Inggris) berdampingan dengan `stage_id` mentah (`nglowong`) tanpa terjemahan; mockup menampilkan `nglowong · outlining`.
16. **Tidak ada skala spasi.** Jarak antar bagian memakai campuran `mt-2/3/4/6/8/10/12/16`, `py-8/10`, `p-3/4/6/8`.

---

## 7. Aturan yang tidak boleh berubah saat dirapikan

Ini bukan preferensi gaya — ini janji produk dan akan dinilai juri.

1. Label sumber (`Spoken` / `On-screen text` / `Visual only`) selalu terlihat, dibedakan dengan **ikon dan teks**, bukan warna saja.
2. Bukti (klip + crop asli) tampil sebelum atau setara dengan arti.
3. Gambar hanya dari frame asli video. Tidak ada ilustrasi, stok, atau gambar buatan AI.
4. Atribusi kreator selalu tampil: detail entri, header arsip, Studio, ekspor.
5. Klaim validasi jujur: `Validated by the documenter` sebagai default; `Validated by the expert · {name}` hanya bila memang dicek ahli; `Proposed by AI · not yet reviewed` di Studio.
6. Keyakinan dan status "New term" ditampilkan, bukan disembunyikan.
7. Izin adalah fitur utama: checkbox dan cakupan izin terlihat jelas di form unggah, tombol submit nonaktif sampai dicentang.
8. Tanpa motif batik klasik (parang, kawung, dan sejenisnya) dan tanpa keris. Kalau perlu tekstur: titik halus atau garis tipis dengan opasitas sangat rendah.
9. Kontras WCAG AA, semua aksi Studio bisa lewat keyboard, fokus selalu terlihat.
10. Tidak ada angka evaluasi buatan. Angka di layar Bukti berasal dari data sungguhan dan diberi label sampel bila belum final.

---

## 8. Bentuk data yang tersedia (jangan mendesain field yang tidak ada)

| Objek | Field yang bisa ditampilkan |
|---|---|
| `Archive` | `title`, `slug`, `craft_pack_id`, `description`, `recording_count`, `validated_count`, `is_demo` |
| `Recording` | `title`, `duration_s`, `display_url`, `source_kind`, `source_url`, `source_creator`, `license`, `attribution`, `contributor{name, region, sanggar}`, `status`, `consent_status` |
| `Entry` | `term`, `category`, `stage_id`, `gloss_en`, `gloss_id`, `variants[]`, `is_novel`, `status`, `access_level`, `source`, `confidence`, `crop_url`, `overlay_url`, `keyframe_url`, `clip_url`, `sam_status`, `maestro_note`, `validation_label`, `attribution`, `contributor_name`, `n_occurrences`, `best_occurrence`, `occurrences[]` |
| `Occurrence` | `recording_title`, `spoken`, `term_raw`, `source`, `t_start`, `t_end`, `time_source` (`asr`/`muse`), `evidence_quote`, `visible`, `visible_object_en`, `visual_match`, `confidence`, `clip_url`, `audio_url`, `keyframe_url` |
| `Job` | `status`, `progress`, `detail`, `mode` (`A`/`B`), `stages[]{name, status, started_at, finished_at, seconds}`, `error` |
| `Pack` | `id`, `version`, `name{id,en}`, `languages[]`, `n_stages`, `n_terms` |
| Process map | `recording_id`, `title`, `duration_s`, `steps[]{pack_stage_id, name, t_start, t_end, entries[]{id, term, keyframe_url}}` |
| Eval summary | `clips{}{speech_recall, speech_precision, median_time_error_s, source_accuracy, baseline_speech_recall, n_pred_speech}` |

Tidak ada: akun, peran pengguna, notifikasi, komentar, riwayat versi entri, pencarian semantik, atau pemutar video kustom.

Aset yang boleh dipakai: `docs/design/aset/` (6 frame asli + 2 turunan untuk mockup) dan `web/public/design/` (3 file). Semua CC BY 3.0, atribusi di `docs/design/aset/ATRIBUSI.md`.

---

## 9. Batasan teknis untuk revisi

- Tailwind 4 (`@import "tailwindcss"`), tanpa file config terpisah. Token masuk sebagai CSS variable di `web/app/globals.css`.
- Tanpa library UI baru. Ikon tetap Lucide. Tanpa animasi kompleks; transisi 150 ms.
- Video dan audio memakai elemen native (`<video controls>`, `<audio>`). Tidak ada pemutar kustom.
- Semua halaman Studio dibungkus `[data-theme="malam"]` di `web/app/studio/layout.tsx`. Halaman publik memakai `:root` Mori.
- Studio tidak punya layout HP (pesan "Studio works best on a desktop screen" di bawah 1280px). Halaman publik wajib punya versi 390px.
- Setiap layar dibangun satu orang dalam hitungan jam. Pilih grid dan flex biasa.

---

## 10. Yang diminta dari Claude Design

### 10.1 Keluaran

1. **Lembar token** dalam bentuk CSS variable, memakai nama yang sudah ada di `globals.css`, ditambah: `--accent-fg` per tema, `--wax-tint`, `--wax-ink`, `--media-frame`, `--radius-sm/md/lg`, skala spasi, skala teks, `--shadow-card`, `--shadow-pop`, `--dur`. Harus bisa ditempel apa adanya.
2. **Lembar komponen** untuk semua komponen di bagian 5, termasuk state kosong, hover, aktif, fokus, dan varian ukuran. Sertakan komponen baru: header publik, footer publik, header Studio, dialog konfirmasi, empty state, skeleton.
3. **Dua belas layar** (bagian 2). Desktop 1440px dan mobile 390px untuk enam layar publik; desktop ≥1280px untuk enam layar Studio.
4. **Daftar perubahan** per layar: apa yang berubah dari kondisi sekarang, dan token/komponen mana yang dipakai. Ini yang akan dipakai saat implementasi, jadi harus eksplisit.

Format keluaran mengikuti mockup yang sudah ada: satu file HTML bertanda `data-screen-label` per layar, sehingga bisa dibuka langsung dan dibandingkan berdampingan dengan yang lama.

### 10.2 Urutan kerja

| Urutan | Layar | Alasan |
|---|---|---|
| 1 | Token + header/footer publik | Semua layar bergantung pada ini |
| 2 | Detail entri (S5b) | Halaman yang menjual produk dan paling sering dilihat juri |
| 3 | Kamus (S5) | Pintu masuk arsip |
| 4 | Studio validasi (S4) | Inti cerita "AI proposes, a person decides" |
| 5 | Beranda (S1) | Kesan pertama |
| 6 | Progres job + Unggah + Try | Alur demo video: unggah → proses → validasi |
| 7 | Bukti (S8) + Peta tahapan (S6) | Kejujuran angka dan pemahaman proses |
| 8 | Ekspor + Craft packs + Beranda Studio + Gerbang | Sisa, cukup memakai komponen yang sama |

### 10.3 Empat keputusan yang saya serahkan ke desainer

1. **Tipografi.** Saya condong ke Newsreader + IBM Plex Sans seperti mockup. Kalau Fraunces dipertahankan, sebutkan alasan dan tunjukkan perbandingan judul 76px.
2. **Pemilih arsip di beranda.** Sekarang berupa baris chip. Mockup tidak punya tempat untuk itu. Perlu satu solusi yang tidak menghilangkan fungsinya (aplikasi akan punya lebih dari satu arsip: batik, tenun, gamelan).
3. **Peta tahapan sebagai rute tingkat atas.** Mockup menaruhnya di nav. Sekarang peta hanya per rekaman (`/d/[slug]/map/[recordingId]`). Kalau nav harus punya halaman indeks, desainkan versi ringkasnya.
4. **Header Studio.** Mockup menampilkan judul rekaman + statistik + menu. Beranda Studio, Unggah, Progres, dan Ekspor belum punya tempat untuk konteks itu. Perlu satu header Studio yang bekerja untuk lima layar.

---

## 11. Prompt siap tempel

> Saya punya aplikasi yang sudah jalan (Next.js + Tailwind), dan saya ingin merapikan tampilannya. Jangan mulai dari nol: **konteks-design-saat-ini.md** menjelaskan persis apa yang ada sekarang, layar per layar, komponen per komponen, termasuk selisihnya dengan mockup yang sudah ada. **brief-claude-design.md** berisi aturan produk dan microcopy yang tidak boleh berubah. Dua file **Empu Public.dc.html** dan **Empu Studio.dc.html** adalah mockup lama; empat layar di dalamnya (beranda, kamus, detail entri, studio validasi) sudah mendekati yang saya mau, tetapi belum konsisten satu sama lain dan belum mencakup delapan layar lain yang sudah berjalan.
>
> Tugasmu:
> 1. Tetapkan satu sistem: token warna, tipografi, skala teks, spasi, radius, dan bayangan, sebagai CSS variable dengan nama yang sudah dipakai kode (`konteks-design-saat-ini.md` bagian 3 dan 10.1).
> 2. Rapikan empat layar lama supaya memakai sistem itu, lalu buat delapan layar yang belum pernah didesain, dengan urutan di bagian 10.2.
> 3. Untuk setiap layar, beri daftar perubahan konkret dari kondisi sekarang.
>
> Jangan mengubah: label sumber Spoken / On-screen text / Visual only, urutan bukti sebelum arti, hanya frame asli, atribusi kreator, klaim validasi yang jujur, izin sebagai fitur utama, dan microcopy bahasa Inggris di brief bagian 8. Jangan memakai motif batik klasik atau keris.
>
> Mulai dari token dan halaman detail entri, lalu tunjukkan ke saya sebelum lanjut.

---

## Lampiran: peta berkas

| Layar | Berkas |
|---|---|
| Layout + font + token | `web/app/layout.tsx`, `web/app/globals.css` |
| Beranda | `web/app/page.tsx`, `web/components/ArchivePicker.tsx` |
| Kamus | `web/app/d/[slug]/page.tsx`, `EntryCardPublic.tsx`, `EntryRow.tsx` |
| Detail entri | `web/app/d/[slug]/[id]/page.tsx`, `EvidenceClip.tsx`, `CropView.tsx`, `PronounceButton.tsx` |
| Peta tahapan | `web/app/d/[slug]/map/[recordingId]/page.tsx`, `ProcessMapBand.tsx` |
| Bukti | `web/app/evidence/page.tsx` |
| Try | `web/app/try/page.tsx`, `UploadForm.tsx` |
| Studio layout | `web/app/studio/layout.tsx` |
| Beranda Studio + gerbang | `web/app/studio/page.tsx`, `StudioKeyGate.tsx` |
| Unggah | `web/app/studio/upload/page.tsx`, `UploadForm.tsx` |
| Progres | `web/app/studio/jobs/[id]/page.tsx`, `JobProgress.tsx` |
| Studio validasi | `web/app/studio/recordings/[id]/page.tsx`, `Studio.tsx`, `EntryCard.tsx` |
| Ekspor | `web/app/studio/export/page.tsx` |
| Craft packs | `web/app/studio/packs/page.tsx` |
| Copy | `web/lib/copy.ts` |
| Bentuk data | `web/lib/types.ts` |
| Token pembanding | `design/globals.css` |
