# Konteks Fitur Empu

Dokumen ini merangkum **seluruh fitur yang ada di aplikasi Empu hari ini**, bukan rencana.
Isinya disusun dari kode di `api/empu/` dan `web/`, jadi kalau kode berubah, dokumen ini
yang perlu diperbarui. Untuk latar belakang produk dan keputusan desain, baca
`docs/superpowers/specs/2026-10-28-empu-design.md`.

- **Produk:** Empu mengubah video seorang ahli yang bekerja sambil bercerita menjadi kamus
  keahlian yang bisa ditonton dan ditelusuri buktinya.
- **Edisi aktif:** Batik Tulis (`packs/batik_tulis.yaml`). Gamelan sudah punya pack draf
  (`packs/gamelan.yaml`).
- **Prinsip yang mengikat semua fitur:**
  1. AI mengusulkan, manusia memutuskan.
  2. Bukti selalu terlihat (klip, timestamp, sumber, keyakinan).
  3. Label sumber (`speech` / `on_screen_text` / `visual_only`) tidak boleh hilang.
  4. Gambar hanya dari frame asli; tidak ada gambar buatan AI.
  5. Izin dulu; izin bisa dicabut dan pencabutan langsung menyembunyikan turunannya.
  6. Pengetahuan keahlian hanya tinggal di craft pack, tidak di kode pipeline.

---

## 1. Peta permukaan aplikasi

| Permukaan | Akses | Route utama | Status |
|---|---|---|---|
| Beranda publik | Tanpa kunci | `/` | Jalan |
| Kamus per arsip | Tanpa kunci | `/d/[slug]` | Jalan |
| Detail entri | Tanpa kunci | `/d/[slug]/[id]` | Jalan |
| Peta tahapan | Tanpa kunci | `/map`, `/d/[slug]/map/[recordingId]` | Jalan |
| Ask Empu (publik) | Tanpa kunci, rate limit | `/ask` | Jalan |
| Halaman Bukti | Tanpa kunci | `/evidence` | Jalan |
| Coba / sandbox | Tanpa kunci, kuota harian | `/try` | Jalan |
| Studio | `STUDIO_KEY` | `/studio/*` | Jalan |
| API publik | Tanpa kunci | `/api/public/*`, `/api/packs*`, `/api/health`, `/api/eval/summary`, `/media/*` (publik) | Jalan |
| API studio | `X-Studio-Key` | `/api/archives/*`, `/api/entries/*`, `/api/jobs/*`, `/api/recordings/*` | Jalan |
| CLI | Lokal | `empu ...` | Jalan |
| Worker | Proses terpisah | `python -m empu.worker` | Jalan |

---

## 2. Fitur publik

### 2.1 Beranda (`/`)
- Menampilkan daftar arsip publik beserta sampel entri (keyframe atau crop) sebagai kartu.
- Blok "How it works" tiga langkah dengan gambar dari frame asli rekaman.
- Blok prinsip produk dan blok visi.
- CTA menuju kamus, Ask, halaman Bukti, dan `/try`.
- Arsip sandbox tidak pernah muncul di daftar publik.

### 2.2 Kamus per arsip (`/d/[slug]`)
- Hanya menampilkan entri yang lolos aturan visibilitas publik (lihat bagian 9).
- Pencarian teks (`q`) dan filter:
  - kategori: `tool`, `tool_part`, `material`, `dye`, `stage`, `technique`, `motif`, `other`;
  - tahap proses dari craft pack;
  - badge "istilah baru" (`is_novel=1`).
- Entri dikelompokkan per kategori dengan urutan tetap.
- Nama dan versi craft pack diambil dari `GET /api/packs/{id}`.
- Empty state yang mengarahkan ke halaman Bukti bila arsip belum punya entri publik.

### 2.3 Detail entri (`/d/[slug]/[id]`)
- Klip bukti dengan audio, diputar dari `/media/...` (mendukung Range/seek).
- Audio pengucapan terpisah (`.m4a`) dan tombol dengar pengucapan.
- Crop hasil SAM (`crop.png`) dan overlay (`overlay.jpg`), atau keyframe utuh bila SAM gagal.
- Istilah baku, bentuk yang diucapkan, varian ejaan.
- Glosa bahasa Indonesia dan Inggris.
- Badge sumber (`speech` / `on_screen_text` / `visual_only`), badge keyakinan, dan penanda
  sumber waktu (`asr` atau `muse`).
- Nama maestro/kontributor dan label validasi:
  - "Validated by the expert · <nama>" hanya bila ada `review_event` dari aktor non-dokumenter;
  - selain itu "Validated by the documenter".
- Daftar kemunculan istilah yang sama di rekaman lain, masing-masing menuju timestamp-nya.
- Atribusi lengkap untuk rekaman `cc_by_video` (kreator, URL, lisensi, keterangan dipotong).

### 2.4 Peta tahapan (`/map`, `/d/[slug]/map/[recordingId]`)
- Indeks semua rekaman publik per arsip.
- Timeline horizontal tahap proses untuk satu rekaman.
- Setiap tahap menampilkan istilah dan thumbnail; klik untuk melompat ke video.
- Tahap yang tidak cocok dengan pack masuk ke `other`.

### 2.5 Ask Empu publik (`/ask`)
- Satu pintu untuk **semua arsip non-sandbox** dalam satu pertanyaan.
- Route lama `/d/[slug]/ask` dialihkan ke `/ask`.
- Jawaban wajib menyitir `entry_ids`. Bila model tidak bisa menautkan jawaban ke entri yang
  boleh tampil, jawaban menjadi `refused` dan tidak menampilkan klaim tanpa bukti.
- Bukti dihidrasi ulang dari database setiap kali, sehingga pencabutan izin atau penolakan
  kemunculan langsung berlaku walau teks jawaban berasal dari cache.
- Setiap bukti membawa `archive_slug` dan `archive_title`; kartu bukti menautkan ke arsipnya.
- Maksimal 4 sitasi per jawaban (`MAX_CITATIONS=4`).
- Rate limit per IP: `EMPU_ASK_PER_HOUR` (default 40/jam). Di belakang Caddy, limit memakai
  hop pertama `X-Forwarded-For`.
- Cache jawaban di `data/cache/ask`; prompt `ask-v5`.
- Saran pertanyaan diambil dari istilah tiap arsip.
- Tombol melayang (`AskLauncher`) dan sheet `<dialog>` tersedia di seluruh layout publik.
- Catatan: pertanyaan yang tidak tercakup arsip dijawab jujur bahwa arsip tidak memuatnya.

### 2.6 Halaman Bukti (`/evidence`)
- Membaca `GET /api/eval/summary` (dari `api/eval/results/latest.json`).
- Menampilkan per klip: recall ucapan, presisi, median galat waktu, akurasi label sumber,
  baseline ASR, dan jumlah temuan `speech`.
- Ringkasan: jumlah klip diukur, rata-rata recall, rata-rata presisi, dan hasil klip kontrol
  musik (target 0 istilah `speech`).
- Menampilkan pack, mode pipeline, dan waktu evaluasi.
- Bila belum ada hasil, halaman menampilkan empty state, bukan angka palsu.

### 2.7 Coba / sandbox (`/try`)
- Unggah tanpa kunci studio ke arsip privat `sandbox`.
- Batas: 3 menit, maksimal 80 MB, kuota harian `EMPU_SANDBOX_DAILY_QUOTA` (default 30 job/hari).
- Izin wajib dicentang.
- Isi sandbox tidak tampil di daftar arsip publik, kamus, maupun Ask publik.

---

## 3. Fitur Studio (butuh `STUDIO_KEY`)

### 3.1 Key gate
- Semua halaman `/studio/*` dibungkus `StudioKeyGate`.
- Kunci disimpan di browser (localStorage) dan dikirim sebagai header `X-Studio-Key`.
- Untuk elemen media (`<video>`, `<img>`) yang tidak bisa mengirim header, kunci juga
  disimpan sebagai cookie `empu_studio_key`.
- `GET /api/media-auth` dipakai untuk memeriksa akses file sebelum ditampilkan.

### 3.2 Studio home (`/studio`)
- Daftar arsip dan rekaman dengan statistik entri dan status job terakhir.
- Pintu masuk ke unggah, validasi, ekspor, pack, dan Ask studio.

### 3.3 Unggah rekaman (`/studio/upload`)
- Membuat arsip baru bila belum ada: slug, judul, craft pack.
- Metadata rekaman di UI: file video, judul, maestro/kontributor, lokasi, jenis sumber, level
  akses. API juga menerima tanggal rekam, bahasa (default `id,jv`), catatan izin, dan bukti izin.
- **Izin wajib**: `consent_confirmed=true`, scope (`public` / `community` / `private`), dan
  catatan izin. Bukti izin (mis. "izin lisan di 00:05") tersedia lewat API dan CLI.
- Jenis sumber:
  - `own_recording` (default);
  - `cc_by_video` — wajib `source_url`, `source_creator`, `license`, `attribution`;
  - `internal_eval` — wajib `consent_scope=private`, tidak boleh publik.
- Batas unggah: `EMPU_MAX_UPLOAD_MB` (default 500 MB) dan `EMPU_MAX_DURATION_S`
  (default 20 menit).
- Respons: `recording_id` dan `job_id`.

### 3.4 Progres job (`/studio/jobs/[id]`)
- Polling status job setiap 2 detik.
- Tahap: `queued → normalizing → chunking → analyzing → merging → grounding → cutting → ready`
  atau `failed`.
- Menampilkan progres, detail ("segmen 3/5"), daftar tahap dengan waktu mulai/selesai, dan error.
- Tombol coba lagi lewat reprocess.

### 3.5 Studio validasi (`/studio/recordings/[id]`)
- Pemutar video dengan penanda istilah di timeline.
- Daftar entri dengan filter status (`proposed`, `accepted`, `edited`, `rejected`), `all`,
  dan istilah baru (`novel`).
- Kartu entri: klip, crop, istilah baku, bentuk diucapkan, kutipan kalimat, badge sumber,
  keyakinan, glosa ID/EN, tahap.
- Aksi review:
  - **Accept** — entri masuk kamus bila `access_level=public`;
  - **Edit** — ubah istilah, glosa ID/EN, dan catatan maestro di UI; API juga menerima
    kategori, tahap, level akses, dan varian;
  - **Reject** — sembunyikan entri;
  - **Merge** — gabungkan ke entri lain;
  - **Restore** — kembalikan entri yang ditolak.
- Setiap aksi menulis `review_event` (before/after, aktor, waktu).
- Pintasan keyboard: `A` accept, `E` edit, `R` reject, `J`/`K` entri berikut/sebelumnya,
  `Esc` menutup dialog.
- Menampilkan progres review (proposed vs reviewed).
- **Withdraw consent**: satu tombol per rekaman; seluruh kemunculan dan media turunannya
  langsung hilang dari kamus, Ask, dan ekspor.

### 3.6 Ask studio (`/studio/ask`)
- Tanya satu arsip dengan cakupan `proposed` (entri yang belum divalidasi).
- Berguna untuk memeriksa apakah pipeline menangkap istilah tertentu sebelum dipublikasikan.
- Tetap memakai aturan sitasi dan hidrasi bukti yang sama.

### 3.7 Ekspor (`/studio/export`)
- Pilih arsip, format, dan cakupan.
- Format: JSON, CSV, ELAN (`.eaf`), ZIP.
- Cakupan: `public` (tanpa kunci tambahan) atau `all` (butuh `STUDIO_KEY`).
- ELAN hanya bisa untuk satu rekaman; kalau cakupan berisi lebih dari satu rekaman, gunakan ZIP.

### 3.8 Craft pack (`/studio/packs`)
- Melihat daftar pack dan detailnya.
- Menempel YAML lalu **Validate** tanpa menulis file.
- Membuat pack baru (`POST /api/packs`) setelah validasi.
- Memuat pack yang sudah ada sebagai template (`GET /api/packs/{id}/source`).
- Validasi menolak id ganda, varian ganda, stage yang tidak ada, dan `visual: true` tanpa
  `sam_prompt`.

---

## 4. Pipeline pemrosesan

Status job: `queued → normalizing → chunking → analyzing → merging → grounding → cutting → ready`
atau `failed`. Antrean memakai tabel `job`; worker mengambil satu job `queued` pada satu waktu.
Job yang tertinggal saat worker restart di-requeue.

### 4.1 Intake
- Menolak rekaman tanpa izin.
- Menyimpan file asli tanpa diubah.
- Membuat `recording` dan `job` dalam satu transaksi.

### 4.2 Normalisasi (ffmpeg/ffprobe)
- `analysis.mp4`: 480p, H.264 CRF 28 preset veryfast, AAC mono 64 kbps — untuk Muse.
- `display.mp4`: 720p, H.264, AAC, `-movflags +faststart` — untuk klip, audio, dan keyframe.
- Durasi dicatat lewat ffprobe.

### 4.3 Pemotongan segmen
- Jendela default 75 detik, overlap 10 detik (`EMPU_CHUNK_WINDOW_S`, `EMPU_CHUNK_OVERLAP_S`).
- Video 5 menit menjadi 5 segmen (0, 65, 130, 195, 260 detik).
- Segmen diproses paralel dengan semaphore `EMPU_ANALYZE_CONCURRENCY` (default 3).

### 4.4 Analisis Muse per segmen
- Cache key: `sha256(segmen) + model + prompt_version + mode`. Respons mentah disimpan di
  `data/cache/muse/`; kalau cache ada, API tidak dipanggil.
- Upload ke Files API (`purpose=user_data`), lalu Responses API dengan `input_video` + prompt.
- Prompt berisi konteks craft pack: deskripsi keahlian, kerangka tahapan, dan istilah benih.
  Istilah benih adalah contoh, bukan daftar wajib.
- Structured output (`text.format` json_schema) dengan fallback parse teks + validasi Pydantic
  dan satu kali retry dengan pesan galat.
- Menyimpan respons mentah, JSON hasil parse, usage, dan latensi per segmen.
- Retry dengan backoff untuk 429/5xx (maksimal 4 kali).
- `PROMPT_VERSION` saat ini `analyze-v3`.

### 4.5 Mode A dan Mode B
- **Mode A:** video + audio langsung ke Muse.
- **Mode B (default):** faster-whisper lokal menghasilkan timestamp per kata; waktu Muse
  di-*realign* secara fuzzy ke jendela transkrip ±30 detik. Bila `partial_ratio ≥ 80`, waktu
  diganti waktu kata dan `time_source=asr`; kalau tidak, waktu Muse dipakai (`time_source=muse`).
  Ejaan istilah tetap dari Muse.
- Mode bisa dipilih per job (`reprocess --mode A|B`).

### 4.6 Penggabungan dan normalisasi istilah
- Timestamp segmen digeser ke waktu rekaman.
- Deduplikasi di zona overlap: istilah sama dan `|Δt| ≤ 4 detik` digabung; yang keyakinannya
  lebih tinggi dipertahankan.
- Kanonisasi ke pack: cocokkan `term`/`spoken` dengan varian pack (casefold, tanpa tanda baca),
  lalu fuzzy match `rapidfuzz` rasio ≥ 90.
- Istilah yang tidak cocok ditandai `is_novel=true`.
- Satu entri per istilah baku per arsip; kemunculan dari rekaman baru ditambahkan ke entri lama.
- `best_occurrence` dipilih dengan prioritas: `speech`, lalu `visual_match=yes`, lalu
  keyakinan tertinggi, lalu durasi terlama.

### 4.7 Peta tahapan
- `process_steps` dari semua segmen digabung.
- Nama tahap dicocokkan ke `stages` pack lewat id, label, atau varian.
- Tahap yang tidak cocok masuk ke `other`.
- Entri ditautkan ke tahap berdasarkan waktu dan `stage` dari Muse.

### 4.8 Media bukti
- **Klip:** `t_start − 1,0 s` sampai `t_end + 1,5 s`, minimal 3 detik, maksimal 8 detik,
  MP4 H.264 dengan audio.
- **Audio pengucapan:** rentang yang sama, `.m4a`.
- **Keyframe:** JPG di titik tengah ucapan.

### 4.9 Potongan gambar (SAM 3.1)
- Hanya untuk istilah pack dengan `visual: true`, atau istilah baru yang `visible`-nya
  menyebut benda.
- Masukan: keyframe `best_occurrence` + `sam_prompt` berbahasa Inggris.
- Keluaran: `crop.png` (bbox + padding 15%), `overlay.jpg` (mask di atas frame),
  `sam_status` (`ok` / `empty` / `error` / `skipped`).
- Fallback: keyframe utuh, ditandai di Studio.

### 4.10 Cache dan biaya
- Respons Muse dan Ask di-cache di disk.
- Perubahan prompt wajib menaikkan versi prompt karena versi ikut jadi cache key.

---

## 5. Ekspor

JSON dan ZIP mencantumkan nama arsip, craft pack + versi, model, versi prompt, scope, dan
tanggal ekspor. CSV mencantumkan maestro per baris. Untuk `cc_by_video`, JSON dan ZIP
menyertakan `source_creator`, `source_url`, `license`, dan keterangan bahwa video dipotong;
`README.txt` di ZIP memuat atribusi lengkap.

| Format | Isi |
|---|---|
| JSON (`empu-dataset.json`) | `{manifest, contributors, recordings, entries:[{…, occurrences:[…]}], process_maps}`; path media relatif terhadap ZIP |
| CSV (`entries.csv`) | Satu baris per kemunculan: term, category, stage, gloss_id, gloss_en, variants, is_novel, status, access_level, maestro, recording, t_start, t_end, source, confidence, clip_path |
| ELAN (`.eaf`) | Satu file per rekaman; media `display.mp4`; tier time-aligned: `term`, `spoken`, `gloss-id`, `gloss-en`, `source`, `stage` |
| ZIP | JSON + CSV + `.eaf` + `media/` (klip, audio, crop) + `README.txt` berisi atribusi dan ketentuan pemakaian |

Lisensi dataset tidak ditentukan aplikasi; kolom `license` diisi pemilik arsip.

---

## 6. Evaluasi

- `empu eval run` mencetak metrik per klip dan agregat ke `api/eval/results/<run>.json`.
- `empu eval draft-gold <clip_id>` menyusun draf kunci jawaban dari kemunculan di DB
  (`annotator=DRAFT`) untuk dikoreksi manusia.
- `empu eval retrieval` mengukur berapa sering entri yang dibutuhkan sebuah pertanyaan
  bertahan di ranking Ask (question recall dan term recall pada top-k).
- `empu ask warm` menjawab pertanyaan demo lebih dulu agar cache server sudah terisi.
- Metrik: recall ucapan, presisi, median galat waktu, akurasi label sumber, istilah karangan
  di klip kontrol musik, istilah baru valid, ketepatan crop SAM, tingkat penerimaan, dan
  waktu yang dihemat.
- Baseline: subtitle otomatis/Whisper dicocokkan ke varian pack.
- Ablasi: segmen 75 detik vs klip utuh; dengan vs tanpa istilah benih; video dengan vs tanpa
  audio.
- `latest.json` dibaca halaman `/evidence`.
- Tes tidak pernah memanggil API sungguhan; fixture ada di `api/tests/fixtures/`.

---

## 7. Craft pack

- Semua pengetahuan keahlian tinggal di `packs/*.yaml`.
- Struktur: `id`, `version`, `name{id,en}`, `languages`, `prompt_context`,
  `asr_error_examples`, `stages[]`, `terms[]`.
- Kategori valid: `tool`, `tool_part`, `material`, `dye`, `stage`, `technique`, `motif`, `other`.
- Aturan validasi: id unik, varian tidak boleh dipakai dua kali, `stage` harus merujuk stage
  yang ada, `visual: true` wajib punya `sam_prompt`.
- Menambah keahlian baru: lihat `docs/adding-a-craft.md`.
- Pack aktif: `batik_tulis`, `gamelan`.

---

## 8. Izin, visibilitas, dan atribusi

Entri tampil publik hanya bila **semua** syarat berikut terpenuhi:

1. `entry.status ∈ {accepted, edited}`;
2. `entry.access_level = public`;
3. rekaman sumber `consent_status = granted`;
4. `consent_scope = public`;
5. `source_kind ≠ internal_eval`;
6. untuk `cc_by_video`: `source_url`, `source_creator`, `license`, `attribution` terisi;
7. entri punya minimal satu kemunculan publik yang tidak ditolak.

Aturan tambahan:
- Kemunculan dari rekaman yang izinnya dicabut tidak pernah ditampilkan.
- Bila kemunculan publik sebuah entri habis, entri ikut tersembunyi.
- Arsip sandbox tidak pernah masuk daftar arsip publik, kamus, atau Ask publik.
- Label validasi dihitung dari `review_event`: aktor selain `documenter`/`syafiq` yang
  melakukan `accept`/`edit` menghasilkan "Validated by the expert".
- Data tetap milik maestro dan komunitas (prinsip CARE). Tidak ada penjualan data atau
  pelatihan model pihak ketiga tanpa izin.

---

## 9. Model data ringkas

| Tabel | Isi |
|---|---|
| `archive` | slug, title, craft_pack_id, description, owner_name, license, default_access, is_demo, is_sandbox |
| `contributor` | nama, peran (`maestro`/`student`/`documenter`), region, sanggar, bio |
| `recording` | arsip, kontributor, judul, tanggal, lokasi, bahasa, durasi, path media, consent, source kind, lisensi, atribusi, status |
| `job` | rekaman, status, progress, detail, error, mode, model, prompt_version, usage, timings |
| `chunk` | rekaman, idx, start/end, path, sha256, file_id, status, raw/parsed path, usage, latency |
| `entry` | arsip, term, kategori, stage, glosa ID/EN, varian, pack_term_id, is_novel, status, access_level, best_occurrence, crop/overlay, sam_status, catatan maestro |
| `occurrence` | entri, rekaman, chunk, spoken, term_raw, source, t_start/t_end, stage_raw, visible, visible_object_en, visual_match, glosa, kutipan, keyakinan, path klip/audio/keyframe, status |
| `process_step` | rekaman, pack_stage_id, nama, waktu, tools, urutan |
| `review_event` | entri, kemunculan, aksi, before/after, aktor, waktu |

Tata letak media:

```
data/archives/<archive_id>/recordings/<recording_id>/
  original.<ext>  display.mp4  analysis.mp4
  chunks/<idx>.mp4
  muse/<idx>.raw.json  muse/<idx>.json
  occurrences/<occurrence_id>/{clip.mp4, audio.m4a, keyframe.jpg}
data/archives/<archive_id>/entries/<entry_id>/{crop.png, overlay.jpg}
data/cache/muse/<cache_key>.json
data/cache/ask/<cache_key>.json
data/exports/
```

---

## 10. API

### Publik (tanpa kunci)
| Metode | Path |
|---|---|
| GET | `/api/health` |
| GET | `/api/packs`, `/api/packs/{id}` |
| GET | `/api/public/archives` |
| GET | `/api/public/archives/{slug}` |
| GET | `/api/public/archives/{slug}/entries` |
| GET | `/api/public/archives/{slug}/recordings` |
| GET | `/api/public/entries/{id}` |
| GET | `/api/public/recordings/{id}/process-map` |
| POST | `/api/public/ask` |
| POST | `/api/public/archives/{slug}/ask` |
| POST | `/api/sandbox/recordings` |
| GET | `/api/eval/summary` |
| GET | `/media/{path}` |
| GET | `/api/media-auth` |

### Studio (`X-Studio-Key`)
| Metode | Path |
|---|---|
| GET/POST | `/api/archives` |
| GET | `/api/archives/{id}` |
| GET | `/api/archives/{id}/recordings` |
| POST | `/api/archives/{id}/recordings` |
| GET | `/api/recordings/{id}` |
| GET | `/api/recordings/{id}/entries` |
| GET | `/api/recordings/{id}/process-map` |
| POST | `/api/recordings/{id}/reprocess` |
| POST | `/api/recordings/{id}/withdraw-consent` |
| GET | `/api/jobs/{id}` |
| GET | `/api/archives/{id}/entries` |
| GET | `/api/entries/{id}` |
| POST | `/api/entries/{id}/review` |
| GET | `/api/archives/{id}/export` |
| POST | `/api/archives/{id}/ask` |
| GET | `/api/packs/{id}/source` |
| POST | `/api/packs/validate` |
| POST | `/api/packs` |

Catatan: aksi `add_manual` (tambah istilah manual) sudah ada di enum tetapi belum
diimplementasikan; API review menolaknya dengan pesan "add_manual is not available".
Menambah istilah yang terlewat masih dilakukan lewat craft pack atau rekaman ulang.

---

## 11. CLI

```bash
empu analyze <video> --pack <id> --out <dir>     # normalisasi + segmen + analisis Muse
empu db init [--reset]                            # siapkan SQLite
empu ingest <video> --archive <slug> ...          # daftarkan rekaman + job
empu reprocess <recording_id> [--mode A|B]        # antre ulang
empu process <job_id>                             # jalankan satu job (debug)
empu status [--archive <slug>]                    # ringkasan arsip/rekaman/entri
empu recording edit <id> [--title ...] [--source-kind ...]
empu eval run --set ... --gold ... --out ...      # evaluasi
empu eval draft-gold <clip_id>                    # draf kunci jawaban
empu eval retrieval --questions ... [--archive ...] [--scope public|studio] [--k ...]
empu ask warm --questions ... [--archive ...] [--scope ...]
```

---

## 12. Konfigurasi

| Env | Default | Fungsi |
|---|---|---|
| `META_MODEL_API_KEY` | — | Kunci Meta Model API (wajib untuk pipeline/Ask) |
| `STUDIO_KEY` | — | Kunci studio |
| `META_BASE_URL` | `https://api.meta.ai/v1` | Base URL Meta API |
| `MUSE_MODEL` | `muse-spark-1.3` | Model analisis |
| `SAM_MODEL` | `sam-3.1` | Model crop |
| `EMPU_DATA_DIR` | `<repo>/data` | Data, media, cache, DB |
| `EMPU_PACKS_DIR` | `<repo>/packs` | Lokasi craft pack |
| `EMPU_DB_URL` | `sqlite:///<data>/empu.db` | Database |
| `EMPU_CHUNK_WINDOW_S` | `75` | Jendela segmen |
| `EMPU_CHUNK_OVERLAP_S` | `10` | Overlap segmen |
| `EMPU_ANALYZE_CONCURRENCY` | `3` | Paralelisme analisis |
| `EMPU_PIPELINE_MODE` | `B` | Mode pipeline default |
| `EMPU_STRUCTURED_OUTPUT` | `true` | Structured output |
| `EMPU_STRUCTURED_SCHEMA_VARIANT` | `full` | Varian skema |
| `EMPU_SAM_ENABLED` | `true` | Aktifkan crop SAM |
| `EMPU_TRANSCRIBE_BACKEND` | `whisper` | Backend ASR Mode B |
| `EMPU_TRANSCRIBE_MODEL` | — | Model faster-whisper |
| `EMPU_MAX_UPLOAD_MB` | `500` | Batas unggah |
| `EMPU_MAX_DURATION_S` | `1200` | Batas durasi |
| `EMPU_SANDBOX_MAX_DURATION_S` | `180` | Batas durasi sandbox |
| `EMPU_SANDBOX_DAILY_QUOTA` | `30` | Kuota job sandbox per hari |
| `EMPU_ASK_PER_HOUR` | `40` | Rate limit Ask per IP |
| `EMPU_ASK_MAX_ENTRIES` | `60` | Entri maksimum per prompt Ask |
| `EMPU_DOMAIN` | — | Domain Caddy saat deploy |
| `EMPU_API_ORIGIN` | `http://127.0.0.1:8000` | Alamat API untuk web |

---

## 13. Peta kode

| Area | Lokasi |
|---|---|
| API & pipeline | `api/empu/` |
| Route | `api/empu/routes/` |
| Pipeline | `api/empu/pipeline/` |
| Ask | `api/empu/ask/` |
| Evaluasi | `api/empu/evaluation/` |
| Ekspor | `api/empu/export/` |
| Worker | `api/empu/worker.py` |
| CLI | `api/empu/cli.py` |
| Craft pack | `packs/*.yaml` |
| Web | `web/app/`, `web/components/`, `web/lib/` |
| Deploy | `deploy/` |
| Dokumen | `docs/` |

---

## 14. Batasan dan yang belum ada

- Belum ada akun multi-pengguna dan peran; akses tulis memakai satu kunci studio.
- Belum ada antrean terdistribusi (Redis); worker memakai tabel `job` dan berjalan satu job
  pada satu waktu.
- Database SQLite satu file; belum ada Postgres.
- Belum ada editor crop manual di UI; crop hanya dari SAM atau fallback keyframe.
- Belum ada video tracking SAM (mask bergerak); crop masih per keyframe.
- Belum ada unggah rekaman langsung dari kamera/perangkat mobile.
- Belum ada pencarian semantik lintas bahasa; pencarian kamus berbasis teks/filter.
- Belum ada halaman pengaturan consent terpusat; pencabutan izin per rekaman.
- Belum ada hasil evaluasi final yang dipublikasikan sampai `latest.json` dibuat.
- URL publik bergantung pada deploy VPS; konfigurasi ada di `deploy/`.
