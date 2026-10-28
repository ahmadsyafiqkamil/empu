# Brief Desain Empu untuk Claude Design

| | |
|---|---|
| Tanggal | 28 Okt 2026 |
| Lampirkan ke Claude Design | File ini, `contoh-data.json`, dan semua gambar di `aset/` |
| Desain final paling lambat | **Jumat 30 Okt malam.** Web dibangun Sabtu–Minggu (plan H3–H4), dan plan hanya memberi 60 menit polesan UI di H6, jadi desain tidak bisa menyusul |
| Sumber | Spec `docs/superpowers/specs/2026-10-28-empu-design.md`, plan H3–H7, `docs/reference/hasil-gate0.md` |

Teks UI di aplikasi berbahasa **Inggris**, karena jurinya global. Brief ini berbahasa Indonesia, tetapi semua microcopy ditulis dalam bahasa Inggris persis seperti yang akan tampil.

---

## 1. Produk dalam satu paragraf

**Empu** mengubah video seorang ahli yang bekerja sambil bercerita menjadi **kamus keahlian yang bisa ditonton**. Setiap istilah (misalnya *canting klowongan*, *nembok*, *nglorod*) terhubung ke ucapan aslinya, klip 3–8 detik dari gerakannya, dan potongan gambar alatnya yang diambil dari frame asli. AI mengusulkan istilah: Muse Spark 1.3 menonton dan mendengar video, lalu SAM 3.1 menemukan alatnya di frame. Setelah itu manusia memutuskan, dan tidak ada yang tampil publik sebelum seseorang menerimanya. Edisi pertama: **Batik Tulis**. Keterampilan lain (tenun, gamelan) cukup ditambahkan sebagai *craft pack* YAML.

- **Nama:** Empu, gelar Jawa untuk guru ahli. Tulis "Empu", atau wordmark huruf kecil "empu".
- **Tagline:** *Capture what masters know, before it's gone.*
- **Edisi:** *Batik Tulis Edition*
- **Nama koleksi publik:** *Living Archive · Batik Tulis* (slug `hidup-batik`)
- **Konteks:** Meta Global AI Developer Hackathon 2026, track Indie. Juri menilai kreativitas, ambisi teknis, dan apakah aplikasinya berfungsi.

## 2. Siapa yang melihat, dan apa yang harus mereka tangkap

| Pengguna | Perangkat | Dalam 10 detik pertama, mereka harus paham bahwa… |
|---|---|---|
| **Juri** (paling penting) | Laptop, kadang HP | Ini kamus yang setiap katanya punya bukti asli (klip, suara, alat), dan AI-nya jujur soal sumber dan keyakinannya |
| **Pembaca publik / murid** | HP | Bisa mencari istilah, mendengar maestro mengucapkannya, dan melihat alatnya |
| **Pendokumentasi** (Syafiq, sanggar, peneliti) | Desktop | Bisa memvalidasi puluhan usulan AI dengan cepat lewat keyboard, tanpa kehilangan konteks video |
| **Maestro / kreator video** | Didampingi pendokumentasi | Namanya dihormati, dan karyanya diatribusikan dengan benar |

Rasa yang dituju: **arsip museum yang hidup, bukan aplikasi AI yang mengkilap.** Tenang, teliti, hormat pada pembuatnya. Bukti lebih menonjol daripada teknologi.

---

## 3. Aturan UI yang tidak boleh dilanggar

1. **Label sumber selalu terlihat** di setiap entri, setiap kemunculan, setiap penanda timeline, dan saat mode edit. Ada tiga jenis: `Spoken` (diucapkan), `On-screen text` (tertulis di layar), dan `Visual only` (hanya terlihat). Bedakan dengan **ikon dan teks**, bukan hanya warna.
2. **Bukti di atas penjelasan.** Klip dan potongan frame asli tampil sebelum atau setara dengan arti kata, bukan tersembunyi di bawah.
3. **Gambar hanya dari frame asli video.** Tidak ada ilustrasi, foto stok, atau gambar buatan AI, baik di aplikasi maupun di mockup. Untuk mockup, pakai gambar di `aset/`.
4. **Atribusi kreator selalu tampil** di detail entri, header arsip, dan Studio. Formatnya ada di bagian 8.
5. **Klaim validasi harus jujur.** Default publik: "Validated by the documenter". "Validated by the expert · {nama}" hanya untuk entri yang benar-benar dicek kreator. Di Studio, entri yang belum ditinjau berlabel "Proposed by AI · not yet reviewed".
6. **Tingkat keyakinan dan istilah baru ditampilkan**, bukan disembunyikan.
7. **Izin itu fitur utama**, bukan teks kecil di bawah. Checkbox izin dan cakupan izin harus jelas terlihat di form unggah.
8. **Tanpa motif batik klasik sebagai dekorasi** (parang, kawung, dan sejenisnya punya makna dan aturan pemakaian), dan **tanpa simbol keris**. Kalau perlu tekstur, pakai titik halus ala *cecek* (isen-isen titik) atau garis tipis canting, dengan opasitas sangat rendah.
9. **Kontras minimal WCAG AA.** Semua aksi Studio bisa dilakukan dengan keyboard, dan fokus selalu terlihat.
10. **Jangan menampilkan angka evaluasi buatan.** Angka di mockup halaman Bukti diambil dari `contoh-data.json` (hasil Gate 0 yang sungguhan) dan diberi tanda "sample".

---

## 4. Arah visual (usulan): "Mori & Malam"

Dua bahan dasar batik tulis menjadi dua mode:

- **Mori** (kain katun putih gading) untuk **halaman publik**: Beranda, Kamus, Detail entri, Peta tahapan, Bukti, dan Try. Terang dan editorial, seperti leksikon atau buku panduan lapangan. Teksnya mirip tinta indigo dan soga.
- **Malam** (lilin batik, cokelat gelap keemasan) untuk **Studio**: Unggah, Progres, Validasi, dan Ekspor. Gelap seperti meja kerja editor video, supaya mata tidak lelah saat meninjau video berjam-jam. Plan H3 sudah memakai tema gelap dengan aksen emas.

Kalau Claude Design atau kamu lebih suka satu tema saja, pakai **mode Malam untuk semua halaman**, karena token itu sudah ada di plan. Tapi saran saya tetap dua mode, karena kamus publik lebih enak dibaca dalam mode terang.

### Token warna (sudah dicek kontrasnya)

Nama variabel sengaja dibuat sama dengan `web/app/globals.css` di plan, supaya hasil desain bisa langsung dipakai. Token tambahan diberi awalan baru.

| Token | Mori (terang) | Malam (gelap, Studio) | Dipakai untuk |
|---|---|---|---|
| `--bg` | `#F5F0E6` | `#12110F` | Latar halaman |
| `--surface` | `#FBF8F2` | `#1B1916` | Kartu, panel |
| `--fg` | `#1C1813` (15,5:1) | `#ECE8DF` (15,4:1) | Teks utama |
| `--muted` | `#665D50` (5,7:1) | `#A39C8E` (6,9:1) | Teks sekunder, metadata |
| `--line` | `#DDD4C4` | `#2E2B26` | Garis, border |
| `--accent` | `#22304F` indigo (11,5:1; teks putih di atasnya 13:1) | `#C9A15B` malam (teks `#12110F` di atasnya 7,9:1) | Tombol utama, tautan, penanda aktif |
| `--wax` | `#9E7330` (3,7:1, hanya untuk elemen non-teks) | `#C9A15B` | Sorotan: penanda timeline aktif, cincin fokus, badge "New term" |
| `--src-speech` | `#22304F` | `#9DB0E3` | Badge `Spoken` (ikon gelombang suara) |
| `--src-onscreen` | `#8A4B22` soga | `#DDA272` | Badge `On-screen text` (ikon huruf "T") |
| `--src-visual` | `#5E5A52` | `#B3AC9F` | Badge `Visual only` (ikon mata) |
| `--ok` | `#3F6B45` | `#7FB384` | Accepted / Edited |
| `--danger` | `#9B3B2E` | `#E57373` | Rejected, cabut izin, error |

`Spoken` sengaja memakai warna yang sama dengan aksen, karena suara sang ahli adalah inti produk. Ketiga badge sumber tetap dibedakan lewat ikon dan teks.

### Tipografi (Google Fonts, dimuat lewat `next/font`)
- **Kata kepala dan judul:** serif berkarakter, misalnya *Fraunces* (alternatif *Newsreader*). Istilah seperti **nyamplung** harus terasa seperti entri kamus.
- **UI dan isi:** *Inter* (alternatif *IBM Plex Sans*).
- **Timestamp dan angka:** monospace dengan angka tabular, misalnya *JetBrains Mono*. Format waktu `0:37` atau `2:05–2:09`.
- Istilah lokal ditulis apa adanya, huruf kecil, tanpa diterjemahkan di judul. Ejaan bentuk yang diucapkan (`spoken`) boleh dicetak miring.

### Gambar dan video (penting: bahannya tidak ideal)
- Footage asli berupa video YouTube amatir: cahaya kurang, warna hangat, kadang ada **subtitle tertanam** (lihat `aset/nyanting-caption-362s.jpg`) atau logo channel. Desain harus terlihat baik dengan bahan seperti ini. Bingkai video dengan latar netral, jangan beri efek kaca atau gradien di atasnya.
- **Potongan SAM bisa kecil dan sangat tinggi atau lebar** (contoh `aset/contoh-crop-canting.png` berukuran 108×234 piksel). Tampilkan di **bingkai berukuran tetap** (misalnya persegi atau 4:5) dengan `object-fit: contain` di atas `--surface`, plus label "Original frame". Sediakan sakelar "Show in frame" yang menampilkan keyframe utuh dengan kotak bbox, seperti `aset/contoh-overlay-canting.jpg`.
- SAM di Empu hanya menghasilkan **kotak (bbox), bukan mask**. Jangan mendesain siluet atau mask berwarna.
- Rasio video 16:9 (sumber 1280×720, tampilan 720p).

### Ikon, gerak, dan logo
- Ikon garis tipis (Lucide cukup). Ikon wajib: gelombang suara (Spoken), "T" (On-screen text), mata (Visual only), centang, pensil, silang, gabung, gembok (studio), unduh, putar, speaker.
- Gerak minimal: transisi 150 ms. Tidak ada animasi hero, parallax, atau efek mengetik.
- Logo: wordmark "empu" dengan font serif kata kepala. Boleh ditambah satu titik kecil berwarna `--wax`, seperti tetesan malam atau *cecek*. Jangan memakai keris, wayang, atau motif klasik.

---

## 5. Peta layar dan rute

Prioritas desain diurutkan dari yang paling penting untuk juri dan video demo. Kerjakan berurutan.

| Prioritas | Kode | Rute | Layar | Mode | Perangkat utama |
|---|---|---|---|---|---|
| 1 | S5b | `/d/hidup-batik/[id]` | **Detail entri** | Mori | HP dan desktop |
| 2 | S5 | `/d/hidup-batik` | **Kamus** (daftar dan pencarian) | Mori | HP dan desktop |
| 3 | S4 | `/studio/recordings/[id]` | **Studio validasi** | Malam | Desktop ≥ 1280 px |
| 4 | S1 | `/` | **Beranda** | Mori | Desktop dan HP |
| 5 | S8 | `/evidence` | **Bukti** (evaluasi) | Mori | Desktop dan HP |
| 6 | S3 | `/studio/jobs/[id]` | Progres pemrosesan | Malam | Desktop |
| 7 | S2 | `/studio/upload` dan `/try` | Unggah (studio) dan Coba (sandbox juri) | Malam / Mori | Desktop |
| 8 | S6 | `/d/hidup-batik/map/[recordingId]` | Peta tahapan | Mori | Desktop dan HP |
| 9 | S7 | `/studio/export` | Ekspor | Malam | Desktop |
| 10 | – | `/studio` | Gerbang kunci studio dan beranda studio | Malam | Desktop |

Urutan di video demo (naskah H7): Unggah → Progres → Studio (terima satu, ubah satu glosa) → Kamus → ketuk satu istilah, dengar klip, lihat potongan alat → Peta tahapan → Ekspor → Bukti.

---

## 6. Spesifikasi per layar

Semua nama field mengikuti `contoh-data.json` (bentuknya sama dengan `web/lib/types.ts`). **Jangan mendesain informasi yang tidak ada di data.**

### S5b Detail entri (prioritas 1)
Halaman inilah yang menjual produknya. Susunan dari atas (HP: satu kolom; desktop: dua kolom, bukti di kiri dan arti di kanan):
1. **Breadcrumb:** `Living Archive · Batik Tulis` → kategori.
2. **Kata kepala:** `term` dalam serif besar, misalnya **canting klowongan**. Di sebelahnya tombol **dengar pengucapan** (speaker) yang memutar `best_occurrence.audio_url`. Di bawahnya chip kategori (`tool`, `tool_part`, `material`, `dye`, `stage`, `technique`, `motif`, `other`, ditampilkan sebagai "Tool", "Tool part", dan seterusnya) dan chip tahap (`stage_id`, mis. "nglowong · outlining").
3. **Varian:** "Also heard as: *klowongan, ngengreng*" (`variants`).
4. **Blok bukti:**
   - Klip video 16:9 (`clip_url`) dengan keterangan: `0:37–0:42 · Spoken · Timed by speech recognition`.
   - Potongan frame asli (`crop_url`), dengan label "Original frame · cropped with SAM 3.1" dan sakelar "Show in frame" (`overlay_url`). Kalau `sam_status` bukan `ok`: tampilkan keyframe utuh dengan label "No crop found · full frame shown".
5. **Kutipan:** `evidence_quote` (kalimat sang ahli) dalam blok kutipan, dengan "said at 0:37". Untuk `On-screen text`, tulis "shown on screen at 0:44" tanpa tanda kutip ucapan.
6. **Arti:** `gloss_en` sebagai teks utama, `gloss_id` di bawahnya dengan label "Bahasa Indonesia".
7. **Badge keyakinan dan istilah baru:** "High confidence", dan "New term" kalau `is_novel`.
8. **Validasi:** `validation_label` dengan ikon centang.
9. **Atribusi:** kartu kecil berisi judul video, kreator, lisensi, tautan, dan "Trimmed by Empu".
10. **Kemunculan lain:** "Heard in 2 recordings". Daftar `occurrences`: judul rekaman · waktu · badge sumber. Tiap baris bisa diputar.
11. Tautan ke peta tahapan rekaman sumber.

### S5 Kamus (prioritas 2)
- **Header arsip:** judul, jumlah entri tervalidasi dan rekaman, versi craft pack (`batik_tulis v0.1.0`), daftar sumber (2 video CC BY dengan atribusi singkat), tautan "Process map" dan "Download (public)".
- **Pencarian** di atas, lalu **chip filter** kategori (Tools, Tool parts, Materials, Dyes, Stages, Techniques, Motifs), filter tahap, dan sakelar "New terms only".
- **Daftar entri:** di HP berupa baris (thumbnail 56 px, kata kepala, `gloss_en` satu baris, badge sumber, badge New). Di desktop berupa kartu 3 kolom. Kelompokkan berdasarkan huruf A–Z atau kategori (pilih salah satu dan tampilkan konsisten).
- Kosong: lihat bagian 9.

### S4 Studio validasi (prioritas 3, desktop ≥ 1280 px, mode Malam)
Inti cerita "AI proposes. A human decides." Harus cepat dipakai dengan keyboard.
- **Top bar:** judul rekaman, atribusi singkat, hitungan status (`Proposed 18 · Accepted 9 · Edited 2 · Rejected 2`), progres tinjauan "13 of 31 reviewed", petunjuk pintasan (`A` accept, `E` edit, `R` reject, `J/K` next/previous), menu rekaman (berisi "Withdraw consent…", bergaya berbahaya).
- **Kiri (±60%):** pemutar video (`display_url`). Di bawahnya **timeline** dengan:
  - pita tahap proses (rentang berwarna tipis berlabel, mis. *nglowong*);
  - penanda istilah per kemunculan, yang bentuknya mengikuti sumber (lingkaran untuk Spoken, persegi untuk On-screen text, segitiga untuk Visual only) dan warnanya mengikuti token sumber. Penanda terpilih memakai `--wax` dan lebih besar. Klik penanda untuk loncat ke waktunya.
- **Kanan (±40%):**
  - bar filter (status, sumber, New terms);
  - **kartu entri aktif:** klip, potongan frame dengan sakelar "Show in frame", kata kepala, bentuk ucapan (miring), kutipan, deretan badge (sumber, waktu dari ASR atau Muse, keyakinan, New), glosa ID dan EN, tahap, catatan maestro, label status;
  - **baris aksi:** `Accept (A)` hijau, `Edit (E)` netral, `Reject (R)` merah, `Merge…` netral;
  - di bawahnya **antrean ringkas** entri lain (baris kecil: kata kepala, badge sumber, waktu, status).
- **Mode edit inline** (bukan dialog bawaan browser): field `term`, `gloss_en`, `gloss_id`, `maestro_note`. Badge sumber tetap tampil saat mengedit. Tombol "Save edit" dan "Cancel".
- **Merge:** popover pencarian entri tujuan berdasarkan kata kepala, dengan pratinjau "Merge *klowong* into *canting klowongan*?".
- Di bawah 1280 px: tampilkan pesan "Studio works best on a desktop screen", tanpa layout HP.

### S1 Beranda (prioritas 4)
- **Hero:** wordmark, tagline, satu paragraf penjelasan (microcopy bagian 8), lalu tombol utama "Open the Batik Tulis archive" dan dua tombol sekunder, "Try it with a 3-minute clip" dan "See the evidence". Visual hero: satu frame asli (`aset/nyanting-canting-122s.jpg`) dengan satu kartu entri nyata yang "menempel" di sampingnya (kata kepala, badge Spoken, potongan alat). Ini menunjukkan produknya, bukan dekorasi.
- **Cara kerja, 3 langkah dengan frame asli:**
  1. "A master works and explains."
  2. "Muse Spark 1.3 watches and listens; SAM 3.1 finds the tool." Kalimat ini satu-satunya tempat nama model ditonjolkan.
  3. "A person accepts, edits, or rejects. Only accepted terms go public."
- **Prinsip (4 butir pendek):** bukti di setiap istilah; sumber selalu dilabeli; tidak ada yang publik tanpa persetujuan manusia; hanya frame asli.
- **Kartu arsip:** *Living Archive · Batik Tulis*, berisi jumlah entri, rekaman, dan kreator.
- **Visi (satu baris):** "Batik today. Weaving and gamelan next. Every craft that was never written down."
- **Footer:** atribusi video, kredit hackathon, dan tautan "Documenter studio".

### S8 Bukti (prioritas 5)
- Judul: **"This is the score, not the goal."** Subjudul: "Measured against human-checked answer keys. We publish the real numbers, including the misses."
- **Kartu angka utama:** recall istilah ucapan (isi dan dengan waktu, ditampilkan berdampingan, mis. `7 of 8` dan `4 of 8`), median galat waktu, kontrol musik (`0 spoken terms`), uji tanpa audio (`7 → 0`).
- **Tabel per klip** (kolom dari `eval_summary.clips`): Clip, Speech recall, Precision, Median |Δt|, Source accuracy, ASR baseline.
- **"What generic captions heard"**: tabel kecil dengan kolom *Said* · *Auto-captions* · *Empu*. Kesalahan subtitle-nya nyata (`spangkring` → *spang King*, `canting` → *cantik*, `canting klowong` → *cacing cowok*, `waterglass` → *watera gelas*). Tapi kolom *Empu* baru terbukti untuk `spangkring` (`verified: true` di `contoh-data.json`). Baris lain harus diberi state "pending" (mis. teks abu-abu + "not yet verified") sampai hasil pipeline membuktikannya. Ini blok konten statis.
- **Batasan (jujur):** label sumber lebih lemah kalau ada subtitle tertanam; waktu disejajarkan ulang dengan ASR lokal sementara ejaan tetap dari Muse; video demo adalah video CC BY yang sudah diedit, bukan rekaman lapangan.
- **Metode singkat:** 4 baris (segmen 75 detik, structured output, faster-whisper sebagai jangkar waktu, SAM bbox).

### S3 Progres
- Daftar 7 tahap dengan label manusiawi (bagian 8), ikon status (menunggu, berjalan, selesai, gagal), dan durasi per tahap (`seconds`). Tahap aktif menampilkan `detail` (mis. "segment 3 of 4").
- Bar progres keseluruhan (`progress`), waktu berjalan, dan mode ("Mode B · retimed with speech recognition").
- Kalimat penjelas di bawah tiap tahap supaya juri paham tanpa narasi, mis. "Muse Spark watches and listens to each 75-second segment."
- **Selesai:** tombol "Open in Studio". **Gagal:** pesan `error` dan tombol "Retry".

### S2 Unggah (studio) dan `/try` (sandbox juri)
- **Area seret file** (video, maks 500 MB atau 20 menit; di `/try` maks 3 menit).
- Field: Archive, Title, Contributor name, Location.
- **Source:** segmented control "Own recording" / "CC BY video". Kalau CC BY: Source URL, Creator, License (default `CC BY 3.0`), Attribution text, semuanya wajib.
- **Blok izin yang menonjol:** checkbox wajib (tombol unggah nonaktif sebelum dicentang), radio cakupan izin (Public / Community / Private) dengan penjelasan satu baris masing-masing, dan field "Consent note" (mis. "verbal consent at 0:05").
- **Versi `/try`** (mode Mori, untuk juri): lebih ringkas, pemberitahuan sandbox, sisa kuota hari ini, dan tetap ada izin wajib. Setelah unggah langsung masuk ke Progres, lalu Studio sandbox.

### S6 Peta tahapan
- Desktop: timeline horizontal satu rekaman, dengan pita tahap berurutan (label istilah lokal dan terjemahan Inggris, rentang waktu), dan di dalamnya thumbnail istilah yang muncul di tahap itu. HP: daftar vertikal.
- Klik istilah membuka detail entri. Klik pita tahap memutar video dari awal tahap.

### S7 Ekspor
- Empat kartu format: **JSON** (dataset lengkap), **CSV** (tabel entri), **ELAN `.eaf`** (untuk ahli bahasa), dan **ZIP** (semuanya, plus klip, crop, dan README atribusi). Satu baris penjelasan per kartu.
- Radio cakupan: "Public entries only" / "Everything except rejected (studio)".
- Catatan: "Every export includes creator attribution and the license."

### Gerbang kunci studio
Kartu kecil di tengah: "Studio key", field password, dan tombol "Enter". Tanpa login dan tanpa akun.

---

## 7. Komponen

Nama mengikuti komponen di plan (`web/components/`), supaya hasil desain gampang dipetakan ke kode.

| Komponen | Varian dan state |
|---|---|
| `SourceBadge` | speech / on_screen_text / visual_only; ukuran sm dan md; dengan tooltip |
| `TimeSourceTag` | asr ("Timed by speech recognition") / muse ("Timed by Muse") |
| `StatusChip` | proposed / accepted / edited / rejected / merged |
| `ConfidenceTag` | high / medium / low (titik 3/2/1 plus teks) |
| `NovelBadge` | "New term" |
| `ValidationLabel` | documenter / expert · {name} / proposed by AI |
| `AttributionLine` | ringkas (satu baris) / lengkap (kartu) |
| `EvidenceClip` | video 16:9 + keterangan waktu, sumber, dan time source; state loading dan error |
| `CropView` | crop ok (bingkai tetap, contain) / show in frame (keyframe + bbox) / no crop (keyframe utuh) |
| `PronounceButton` | idle / playing |
| `EntryRow` (Kamus HP) dan `EntryCardPublic` (Kamus desktop) | dengan atau tanpa thumbnail, novel |
| `EntryCard` (Studio) | view / edit inline / merge popover |
| `TimelineTrack` | pita tahap + penanda per sumber, aktif, hover |
| `JobProgress` | per tahap: waiting / running / done / failed |
| `UploadForm` | studio / try; own / CC BY; izin belum atau sudah dicentang |
| `MetricCard`, `EvalTable` | angka utama + keterangan "sample" di mockup |
| `ProcessMapBand` | tahap + thumbnail istilah |
| `StudioKeyGate` | default / salah kunci |
| `ConfirmDialog` | cabut izin (berbahaya) |

---

## 8. Microcopy (bahasa Inggris, pakai persis)

| Tempat | Teks |
|---|---|
| Tagline | Capture what masters know, before it's gone. |
| Paragraf beranda | Empu turns a master's narrated work video into a watchable craft dictionary. Every term links to the original speech, a short clip of the movement, and the real tool, cropped from the original frame. AI proposes; a person decides. |
| Tombol beranda | Open the Batik Tulis archive · Try it with a 3-minute clip · See the evidence |
| Badge sumber | Spoken · On-screen text · Visual only |
| Tooltip sumber | Heard in the recording's audio. · Read from text shown in the video, not spoken. · Seen in the video; not spoken or written. |
| Time source | Timed by speech recognition · Timed by Muse |
| Tooltip time source | Muse found the term; the timestamp was aligned to a word-level transcript. · Timestamp from Muse; no transcript match. |
| Keyakinan | High confidence · Medium confidence · Low confidence |
| Istilah baru | New term (tooltip: Not in the Batik Tulis craft pack yet. Check with the maker.) |
| Validasi | Validated by the documenter · Validated by the expert · {name} · Proposed by AI · not yet reviewed |
| Crop | Original frame · cropped with SAM 3.1 · Show in frame · No crop found · full frame shown |
| Atribusi | From "{title}" by {creator} · {license} · {url} · Trimmed by Empu |
| Kutipan | said at {0:37} · shown on screen at {0:44} |
| Varian | Also heard as: {variants} |
| Kemunculan | Heard in {n} recordings |
| Aksi Studio | Accept (A) · Edit (E) · Reject (R) · Merge… · Next (J) · Previous (K) · Save edit · Cancel |
| Cabut izin | Withdraw consent for this recording |
| Konfirmasi cabut izin | All entries from this recording will disappear from the public dictionary and from exports. Files are kept but hidden. Withdraw consent? |
| Checkbox izin | I confirm the contributor granted permission to process this recording, and I recorded that consent. |
| Cakupan izin | Public: accepted entries can appear in the public dictionary. · Community: kept out of the public dictionary; visible in the studio. · Private: restricted knowledge; never public. |
| Tahap progres | Preparing video · Cutting 75-second segments · Muse Spark watches and listens · Matching terms to the craft pack · SAM 3.1 finds the tools · Cutting evidence clips · Ready to review |
| Try | Your clip goes to a private sandbox. It is not listed publicly. · Up to 3 minutes. {n} uploads left today. |
| Bukti | This is the score, not the goal. · Measured against human-checked answer keys. We publish the real numbers, including the misses. |
| Batasan di Bukti | Source labels are weaker when captions are burnt into the video. · Timestamps are realigned with local speech recognition; spelling still comes from Muse. |
| Prinsip AI | AI proposes. A person decides. |
| Footer | Built for the Meta Global AI Developer Hackathon 2026 with Muse Spark 1.3 and SAM 3.1. Demo clips are CC BY videos, credited on every entry. |

---

## 9. State kosong dan error

| Situasi | Tampilan |
|---|---|
| Kamus belum ada entri publik | "No public entries yet. Terms appear here after a person accepts them." + tautan ke Bukti |
| Pencarian tanpa hasil | "No terms match '{q}'." + tombol hapus filter |
| Entri tidak publik / izin dicabut (404) | "This entry isn't public. It may still be under review, or its recording's consent was withdrawn." |
| Crop SAM kosong | Keyframe utuh + "No crop found · full frame shown" |
| Klip gagal dimuat | Bingkai 16:9 netral + "Clip unavailable" |
| Job gagal | Pesan error + Retry |
| Kuota sandbox habis | "Today's sandbox uploads are used up. The archive is still open to explore." |
| Video sandbox > 3 menit | Validasi di form sebelum unggah |
| Filter Studio kosong | "Nothing left in this filter." + saran "Show accepted" |
| Kunci studio salah | Pesan di bawah field |

---

## 10. Batasan teknis untuk desain

- **Stack:** Next.js 16 (App Router), React 19, Tailwind 4, TypeScript. Token warna ditaruh sebagai CSS variable di `globals.css` (nama variabel di bagian 4). Mode Malam memakai `[data-theme="malam"]` pada layout `/studio`.
- **Video dan audio memakai elemen native** (`<video controls>`, `<audio>`). Tidak ada pemutar kustom yang rumit. Kontrol tambahan (tombol dengar, loncat ke waktu) cukup tombol biasa.
- **Waktu bangun sangat terbatas:** semua layar dibangun dalam sekitar 2 hari oleh satu orang. Pakai layout standar (grid, flex), komponen sederhana, tanpa ilustrasi kustom, tanpa animasi kompleks, tanpa library UI berat. Kalau ada pilihan, pilih yang lebih sederhana.
- **Data yang tersedia** ada di `contoh-data.json`. Kalau sebuah ide desain butuh data yang tidak ada di sana, tandai sebagai "nanti", jangan jadikan bagian utama.
- **Tidak ada akun pengguna.** Studio memakai satu kunci. Tidak perlu desain login atau profil.
- Media disajikan dari `/media/...` (path relatif). Gambar crop berformat PNG dengan ukuran bervariasi.
- Lebar konten Kamus dan Detail sekitar 720–1100 px. Studio memakai lebar penuh.

## 11. Tidak perlu didesain
Aplikasi native, dark mode untuk halaman publik, pengaturan akun, notifikasi, pembayaran, kursus, paspor produk, dashboard admin, halaman marketing panjang, dan pemilih craft pack selain dropdown sederhana.

## 12. Yang diharapkan dari Claude Design
1. **Token desain** (warna kedua mode, tipografi, spasi, radius, bayangan) dalam bentuk CSS variable yang siap ditempel ke `globals.css`.
2. **Lembar komponen** dari bagian 7, dengan semua state.
3. **Layar sesuai urutan prioritas** di bagian 5: HP (390 px) dan desktop (1440 px) untuk layar publik, dan desktop saja untuk Studio. Isi dengan data dari `contoh-data.json` dan gambar dari `aset/`.
4. Kalau waktu terbatas: S5b, S5, S4, dan S1 dulu. Sisanya cukup memakai komponen yang sama.

---

## Lampiran A: Aset
Lihat `aset/ATRIBUSI.md`. Semua frame berasal dari dua video YouTube berlisensi CC BY 3.0 dan **wajib** diberi atribusi kalau tampil di desain yang dibagikan.

| File | Isi | Cocok untuk |
|---|---|---|
| `nyanting-canting-122s.jpg` | Tangan memegang canting di atas kain berpola | Hero beranda, klip entri *canting* |
| `contoh-overlay-canting.jpg` | Frame yang sama dengan kotak bbox | State "Show in frame" |
| `contoh-crop-canting.png` | Potongan canting (108×234 px, sangat tinggi) | `CropView` |
| `nyanting-wajan-272s.jpg` | Wajan berisi malam, kotak canting, alas kain | Entri *wajan* (Visual only) |
| `nyanting-caption-362s.jpg` | Canting dengan subtitle tertanam "cek hasil berkala" | Contoh footage bersubtitle |
| `macamcanting-diagram-klowong-44s.jpg` | Gambar canting berlabel "KLOWONG" | Entri sumber On-screen text |
| `macamcanting-canting-100s.jpg` | Canting dipakai di kain warna | Entri *canting tembokan* |

Catatan: kotak di `contoh-overlay-canting.jpg` dan crop `contoh-crop-canting.png` **dibuat manual sebagai pengganti hasil SAM** untuk mockup. Di aplikasi, keduanya berasal dari SAM 3.1.

## Lampiran B: Ringkasan model data untuk desain

| Objek | Field yang tampil di UI |
|---|---|
| Archive | `title`, `slug`, `craft_pack_id`, `recording_count`, `validated_count`, `is_demo` |
| Recording | `title`, `duration_s`, `display_url`, `source_kind` (own_recording / cc_by_video), `attribution`, `status` |
| Entry | `term`, `category`, `stage_id`, `gloss_en`, `gloss_id`, `variants`, `is_novel`, `status`, `access_level`, `source` (dari kemunculan terbaik), `confidence`, `crop_url`, `overlay_url`, `keyframe_url`, `clip_url`, `sam_status`, `maestro_note`, `validation_label`, `attribution`, `contributor_name`, `n_occurrences` |
| Occurrence | `recording_title`, `spoken`, `source`, `t_start`, `t_end`, `time_source`, `evidence_quote`, `visible`, `visual_match`, `confidence`, `clip_url`, `audio_url`, `keyframe_url` |
| Job | `status`, `progress`, `detail`, `mode`, `stages[]` (name, status, seconds), `error` |
| Process map | `steps[]` (pack_stage_id, name, t_start, t_end, entries[] {id, term, keyframe_url}) |
| Eval summary | `clips{}` (speech_recall, speech_precision, median_time_error_s, source_accuracy, baseline_speech_recall, n_pred_speech) |
