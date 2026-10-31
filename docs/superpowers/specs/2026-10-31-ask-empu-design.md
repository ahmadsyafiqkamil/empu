# Ask Empu: Dokumen Desain

Tanggal: 31 Okt 2026 · Pemilik: Syafiq · Status: menunggu persetujuan

## 1. Niat dan alasan

Kamus Empu hari ini hanya bisa **dibaca**: orang mencari istilah, lalu menonton buktinya. Yang belum bisa dilakukan pembaca adalah **bertanya**. Pertanyaan seperti "kenapa kain harus dibolak-balik saat ngelorod?" atau "alat yang ujungnya seperti paruh itu namanya apa?" tidak punya kotak pencarian yang cocok, karena jawabannya tersebar di beberapa entri dan bergantung pada apa yang diucapkan maestro.

Ask Empu menambahkan satu pintu tanya-jawab di dalam aplikasi. Setiap jawaban **wajib bersandar pada entri yang sudah ada**, dan setiap klaim menampilkan buktinya: klip maestro, potongan gambar alat, kutipan ucapan, label sumber, dan waktu. Ini bukan chatbot yang tahu banyak tentang batik; ini **kamus yang bisa ditanya**.

Manfaat untuk hackathon: kriteria penilaian memuat Impact (30%), Demo (25%), dan Technical Depth (20%). Ask Empu menyentuh ketiganya dengan risiko kecil, karena seluruh bahannya (entri, klip, crop, kutipan, label sumber) sudah ada di `data/empu.db` dan `/media`.

## 2. Pengguna dan dua pintu

| Pintu | Pengguna | Cakupan data | Bentuk jawaban |
|---|---|---|---|
| **Publik** | Pembaca, murid, juri | Hanya entri yang lolos aturan visibilitas publik | Menjelaskan, lalu menunjuk klip + crop + kutipan |
| **Studio** | Pendokumentasi, maestro | Entri `proposed`/`accepted`/`edited` (bukan `rejected`), izin rekaman masih `granted` | Sama, ditambah status entri; untuk memeriksa apa yang sistem pikir maestro katakan |

Satu mesin, dua cakupan. Pintu publik lebih dulu (yang dinilai juri); pintu Studio memakai mesin yang sama dengan satu parameter berbeda.

**Bahasa jawaban mengikuti bahasa pertanyaan.** Maestro bertanya dalam Jawa atau Indonesia dan dijawab begitu; pembaca asing bertanya dalam Inggris. Ini klaim yang bisa dipamerkan: kamus yang bisa ditanya dalam bahasa ahlinya.

## 3. Tujuan

1. Pembaca bisa mengajukan pertanyaan bebas (ID/EN/JV) dan mendapat jawaban ≤90 kata yang disusun dari entri yang ada.
2. Setiap jawaban menampilkan minimal satu bukti yang bisa ditonton: klip, crop, kutipan, label sumber, waktu.
3. Kalau arsip tidak memuat jawabannya, agen **bilang tidak ada**. Tidak menebak, tidak menambah pengetahuan luar.
4. Pendokumentasi bisa memakai pintu yang sama untuk memeriksa entri yang belum divalidasi.
5. Biaya terkendali: satu panggilan model teks per pertanyaan baru, di-cache, ada batas laju.

## 4. Bukan tujuan

- Percakapan multi-giliran dengan memori panjang. Tiap pertanyaan berdiri sendiri; UI boleh menampilkan riwayat pertanyaan sebelumnya, tapi model tidak menerima riwayat.
- Aksi tulis lewat obrolan (menerima/mengubah entri). Itu tetap di Studio.
- Menjawab dari pengetahuan umum, Wikipedia, atau video di luar arsip.
- Membuat gambar, merangkum video, atau mengirim video ke model.
- Suara (TTS/STT) di versi ini.

## 5. Anti-tujuan (gagal walau secara teknis jalan)

- Jawaban yang menyebut istilah yang tidak ada di arsip.
- Jawaban yang mengarang timestamp atau kutipan.
- Jawaban yang menampilkan bukti dari entri `proposed` atau `private` di pintu publik.
- Jawaban yang menampilkan bukti dari rekaman yang izinnya dicabut, atau dari arsip sandbox.
- Jawaban yang membuat juri perlu memverifikasi manual untuk tahu apakah itu benar.

Batas kejujuran yang bisa dijamin: **bukti** dan **sitasi** sepenuhnya dikendalikan server. Kalimat jawaban dibatasi oleh prompt dan daftar yang dikirim, tetapi tidak bisa dibuktikan secara mekanis; karena itu setiap jawaban selalu tampil bersama buktinya, dan jawaban tanpa sitasi sah ditolak.

## 6. Kendala

- Target kirim internal 4 Nov 2026, 22:00 WIB. Fitur ini harus selesai dalam 1,5 hari kerja dan tidak boleh memotong H6/H7.
- Prinsip produk yang tidak boleh dilanggar: AI mengusulkan manusia memutuskan, bukti selalu terlihat, jujur soal sumber, gambar hanya dari frame asli, izin dulu.
- Semua panggilan Meta lewat `api/empu/meta_client.py`; respons mentah di-cache.
- Tes tidak boleh memanggil API sungguhan.
- Pengetahuan keterampilan tidak boleh di-hardcode di `api/empu/**` (ada tes yang menjaga ini). Prompt Ask Empu tidak boleh menyebut istilah batik; konteks datang dari baris data.
- Tidak menambah dependensi baru (rapidfuzz sudah ada). Tidak menambah tabel DB.
- UI bahasa Inggris, istilah keahlian tetap asli.

## 7. Pendekatan yang dipertimbangkan

**A. Satu panggilan model teks dengan daftar entri terpilih + sitasi id (dipilih).**
Ambil entri yang lolos cakupan, saring dengan kemiripan leksikal (rapidfuzz) ke ≤60 baris, kirim daftar ringkas + pertanyaan ke Muse dengan structured output `{answer, lang, entry_ids, insufficient}`. Validasi id, lalu hidrasi bukti dari DB. Murah (≈6 ribu token input), satu putaran, mudah diuji karena model bisa diganti fungsi palsu.
Tukar: kualitas retrieval bergantung pada leksikal; pertanyaan yang memakai sinonim jauh bisa meleset. Mitigasi: daftar ≤60 baris mencakup seluruh kamus demo (104 entri, tapi publik 84), jadi penyaringan jarang memotong apa pun di skala sekarang.

**B. Pencarian leksikal saja, tanpa model.**
Kirim entri teratas, UI menyusun kalimat dari glosa. Nol biaya, nol latensi, nol risiko halusinasi.
Tukar: tidak menjawab pertanyaan, hanya menampilkan hasil pencarian. Untuk juri ini terasa seperti fitur pencarian biasa, bukan agen. Ditolak sebagai fitur utama; tetap dipakai sebagai lapisan penyaring di dalam A.

**C. Agen multi-turn dengan tool-calling (cari entri, buka entri, cari kemunculan).**
Paling "agentic", bisa menelusuri beberapa langkah.
Tukar: lebih banyak bagian bergerak (loop, batas langkah, penanganan galat per langkah), latensi 3–5× lipat, lebih sulit diuji dan dijelaskan dalam demo 2 menit, dan risiko model memanggil tool berulang tanpa henti. Dalam 1,5 hari ini terlalu mahal. A bisa tumbuh ke C setelah submission.

**Keputusan: A**, dengan penyaring leksikal dari B di dalamnya.

## 8. Keputusan yang sudah diambil

| # | Keputusan | Alasan |
|---|---|---|
| A1 | Dua pintu, satu mesin; parameter `scope` = `public` \| `studio` | Menghindari dua implementasi yang bisa menyimpang aturan visibilitas |
| A2 | Sitasi wajib: model mengembalikan `entry_ids`; id di luar daftar dibuang | Jawaban tanpa bukti tidak bisa tampil; ini yang menjaga kejujuran || A3 | `insufficient=true` atau tidak ada id valid → `refused=true`, bukti kosong, UI menampilkan keadaan "belum ada di arsip" | Menutup jalur halusinasi paling umum |
| A4 | Bahasa jawaban mengikuti bahasa pertanyaan (`lang` dari model) | Maestro & pembaca global |
| A5 | Satu pertanyaan = satu panggilan; tanpa riwayat ke model | Sederhana, dapat di-cache, dapat diuji |
| A6 | Cache `ResponseCache` di `data/cache/ask/`, kunci `sha256(scope+archive_id+pertanyaan ternormalisasi) + model + ASK_PROMPT_VERSION + scope` | Memakai ulang kelas cache yang sudah ada; juri yang mengulang pertanyaan tidak membayar dua kali |
| A7 | Bukti dihidrasi ulang dari DB setiap kali (cache hanya menyimpan teks + id) | URL media dan visibilitas selalu segar; entri yang kemudian disembunyikan otomatis hilang |
| A8 | Batas laju per IP: `ask_per_hour` (default 40), in-memory, satu proses | Endpoint publik tanpa kunci membakar kredit Meta kalau dibiarkan |
| A9 | Tanpa streaming; satu respons JSON | Latensi 3–8 detik masih wajar untuk demo; streaming menambah kompleksitas |
| A10 | Model hanya menerima teks (bukan video/gambar) | 274 token per detik video; mahal, lambat, dan tidak perlu karena bukti sudah terpotong |
| A11 | Pintu Studio menyertakan `proposed` dan `private`, mengecualikan `rejected`/`merged`, menyembunyikan rekaman yang izinnya dicabut | Sejalan dengan ekspor `scope=all` (D3): Studio adalah tempat entri belum publik ditinjau, tapi izin yang dicabut tetap tidak boleh muncul di mana pun |

## 9. Bentuk teknis

### 9.1 API

| Metode | Path | Kunci | Cakupan |
|---|---|---|---|
| POST | `/api/public/archives/{slug}/ask` | tidak | publik; arsip sandbox → 404 |
| POST | `/api/archives/{id}/ask` | `X-Studio-Key` | studio |

Body: `{"question": str}` — 3–500 karakter setelah `strip`, spasi berlebih dirapatkan di server.

Respons (200):

```json
{
  "answer": "…",
  "lang": "id",
  "refused": false,
  "evidence": [
    {
      "entry": { "…EntryListItem…" },
      "occurrence": { "…OccurrenceOut…" }
    }
  ],
  "model": "muse-spark-1.3",
  "prompt_version": "ask-v1",
  "cached": false
}
```

Galat: 404 arsip tidak ada / sandbox (publik), 422 pertanyaan terlalu pendek/panjang, 429 batas laju, 502 model gagal atau keluarannya tidak bisa diparse.

### 9.2 Modul

```
api/empu/ask/__init__.py      # ekspor answer_question, AskResult, AskError
api/empu/ask/index.py         # IndexEntry, build_index, prefilter
api/empu/ask/prompts.py       # ASK_PROMPT_VERSION, RESPONSE_SCHEMA, build_prompt
api/empu/ask/engine.py        # collect_entries, answer_question, hidrasi bukti
api/empu/ask/ratelimit.py     # RateLimiter
api/empu/routes/ask.py        # dua route + dependency model
```

`MetaClient` mendapat satu metode baru `respond_text(...)` — teks saja, tanpa unggah file.

### 9.3 Alur satu pertanyaan

1. Normalisasi pertanyaan (`" ".join(q.split())`).
2. `collect_entries(session, archive_id, scope)` → daftar `(Entry, [Occurrence])`.
3. `build_index` → `IndexEntry` (id, term, kategori, tahap, glosa ID/EN, varian, ≤2 kutipan).
4. `prefilter` → ≤`ask_max_entries` (default 60) baris; kalau jumlah entri ≤ batas, semua ikut, urut id.
5. Cache: kalau ada, lompat ke 8.
6. `build_prompt` → `ask_model(prompt)` → `AnalyzeResult`.
7. Validasi keluaran: `insufficient` → tolak; id di luar daftar dibuang; sisa kosong → tolak. `parse_error` → `AskError`.
8. Hidrasi tiap id menjadi `(EntryListItem, OccurrenceOut)` memakai serializer yang ada; simpan payload ke cache.
9. Kembalikan `AskResult`.

### 9.4 Aturan utama prompt (verbatim di `prompts.py`)

Jawab dalam bahasa penanya; pakai hanya istilah di daftar; setiap klaim menunjuk id; kalau tidak ada, `insufficient=true` dan katakan terus terang; hormati label sumber (jangan bilang "dia bilang" untuk yang hanya terlihat); jangan mengarang timestamp atau kutipan; maksimal 90 kata.

### 9.5 UI

- `/d/[slug]/ask` — pintu publik. Header publik, judul "Ask the archive", panel tanya, chip contoh pertanyaan dari tiga istilah pertama, riwayat tanya-jawab dalam satu halaman.
- Kartu bukti: istilah + kategori + glosa (+ EN), klip video dengan kontrol, crop/overlay sebagai gambar, kutipan, badge sumber, waktu, tautan "Open entry".
- `/studio/ask` — pintu Studio di dalam `StudioKeyGate`, dengan pemilih arsip dan badge status entri.
- Keadaan kosong dan galat memakai kelas yang sudah ada (`.empty`, `.btn`), tanpa `window.alert`.

### 9.6 Yang diserahkan ke builder

- Susunan visual kartu bukti dan panel (dalam batasan token `desain.md`).
- Pemilihan contoh pertanyaan.
- Nada copy Inggris untuk keadaan menolak dan galat.
- Detail penyaringan leksikal (bobot, ambang) selama tes yang ditetapkan lulus.

## 10. Dampak dan risiko

| Risiko | Mitigasi |
|---|---|
| Model menyitir id yang tidak ada | Validasi ketat; id asing dibuang; bila habis → `refused` |
| Model menjawab dari pengetahuan luar | Prompt melarang; UI selalu menampilkan bukti; `refused` bila kosong |
| Pertanyaan di luar kamus dijawab seolah ada | `insufficient` wajib diisi; tidak ada id → refused |
| Kredit Meta terbakar oleh endpoint publik | Cache + batas laju per IP + batas panjang pertanyaan |
| Latensi >10 detik saat demo | Daftar ≤60 baris, `max_output_tokens` 800; uji waktu nyata di Task 1 |
| Istilah batik masuk ke kode | Prompt hanya berisi baris data; tes `test_no_hardcoded_craft_terms` tetap hijau |
| Fitur memotong waktu deploy | Pintu publik = wajib; pintu Studio boleh dipotong tanpa menyentuh mesin |
