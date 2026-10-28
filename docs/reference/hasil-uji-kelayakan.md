# Hasil Uji Kelayakan (v1, 28 Okt 2026)

Pertanyaannya: apakah Muse Spark 1.3 bisa menangkap istilah batik yang diucapkan, kapan diucapkan, dan apa yang terlihat saat itu, langsung dari video?

Salinan bahan uji ada di `docs/reference/uji-kelayakan/`:
- `uji_muse.py`: skrip uji (prompt sudah versi v2, tapi **v2 belum dijalankan**).
- `glosarium.json`: sekitar 25 istilah beserta variannya, dipakai untuk penilaian kasar.
- `hasil-v1/`: respons mentah (`*.raw.json`), JSON hasil parse, dan `ringkasan.json`.

Video sumber ada di folder unduhan `arsip-hidup-batik/` (lihat `docs/eval/test-set.yaml`). Semua video itu milik kreatornya dan **hanya untuk uji internal**.

## Setup
- Model `muse-spark-1.3`, Responses API, `input_video` (diunggah lewat Files API), `max_output_tokens` 16000.
- Klip dikompres ke 480p, H.264 CRF 28, AAC mono 64 kbps.
- Prompt v1 meminta istilah yang diucapkan, timestamp, apa yang terlihat, dan kecocokannya. Enum masih berbahasa Indonesia.
- Kunci kasar: subtitle otomatis YouTube (bahasa Indonesia), dicocokkan dengan glosarium.

## Hasil per klip

| Klip | Durasi | Istilah dari Muse | Latensi | Token input | Catatan |
|---|---|---|---|---|---|
| `proses-lengkap-ngertibatik` (7-WQ3DKKn0w) | 241 s | 16 | 40,4 s | 65.973 | Narasi baru mulai sekitar detik 80. Banyak istilah dibaca dari diagram di layar |
| `nglowong` (rKVEysItoKY) | 132 s | 12 | 33,4 s | 36.271 | Median galat waktu **3,4 s**. Empat istilah ditandai jujur sebagai "tidak terlihat" |
| `kontrol-musik-nglorod` (J_XcGhkCRAQ) | 227 s | **0** | 37,6 s | 62.158 | Hanya musik. Tidak ada istilah karangan. Tetap menyusun 11 langkah pelorodan dari gambar saja |
| `maestro-trusmi-5menit` (8sMSLQPYNc4, 0–300 s) | 300 s | 3 | 42,4 s | 82.051 | Bagian yang diambil salah (pembukaan dan sejarah). v2 memakai menit 15–20 |

Token input konsisten sekitar **274 token per detik video** pada 480p. Output 2.200–4.800 token, dan 1.800–3.050 di antaranya token penalaran.

## Temuan penting: istilah yang diucapkan di #NgertiBatik

Subtitle menunjukkan narasi dimulai sekitar detik 82. Berikut 8 istilah teknis yang benar-benar diucapkan, dibandingkan dengan temuan Muse:

| Diucapkan (detik) | Subtitle YouTube | Muse v1 | Waktu benar? |
|---|---|---|---|
| pola (85–87) | pola | pola @89 | ✓ |
| lilin malam (109) | lilin malam | malam @57 (dari layar) | ✗ |
| spangkring (122) | *spang King* | spangkring @77,5 (dari diagram) | ✗ |
| membatik / meletakkan lilin (126–128) | membatik | membatik @124 | ✓ |
| mewarna (145–149) | mewarna | pewarnaan @148 | ✓ |
| HCl (155) | HCl | — | ✗ |
| waterglass (162–165) | *watera gelas* | — | ✗ |
| ngelorot / nglorod (173) | *ngelorot* | dilorot → pelorodan @173 | ✓ |

**Recall ucapan dengan waktu yang benar: 4 dari 8.** Angka ini lebih rendah daripada kesan awal. Penyebabnya:
1. **Teks di layar tercampur dengan ucapan.** *Malam*, *canting*, *nyamplung*, *cucuk*, *gagang*, *dingklik*, dan *spangkring* dilaporkan di detik 57–80, sebelum narasi dimulai. Kemungkinan besar Muse membacanya dari diagram dan judul. Istilahnya benar, tetapi sumber dan waktunya salah.
2. **Istilah di bagian akhir terlewat** (*HCl*, *waterglass*), kemungkinan karena klip 4 menit terlalu panjang untuk satu panggilan.

**Akibat untuk pitch:** kalimat "subtitle biasa menulis 'spang King', Empu mendengar 'spangkring'" **belum boleh dipakai.** Di v1, Muse menulis *spangkring* dengan benar karena membacanya dari diagram, bukan mendengarnya. Klaim ini baru aman kalau v2 atau rekaman sendiri menunjukkan `source=speech` di waktu yang benar.

## Yang sudah meyakinkan
- **Tidak mengarang:** klip yang hanya berisi musik menghasilkan 0 istilah.
- **Waktu tepat untuk ucapan yang jelas:** *pola*, *pewarnaan*, dan *dilorot* meleset 0–3 detik. Median klip *nglowong* 3,4 detik.
- **Menemukan istilah di luar glosarium:** *nyamplung*, *cucuk*, *gagang*, *dingklik*, *spangkring* (meskipun dari teks layar).
- **Pemahaman visual kuat:** langkah pelorodan tersusun dari gambar saja, termasuk "3 sendok makan soda abu ke ember".
- **Jujur soal gambar:** istilah yang diucapkan saat alatnya belum tampil ditandai "tidak terlihat".

## Yang belum terbukti
1. **Apakah Muse benar-benar mendengar audio.** Halaman model Muse Spark 1.3 menyebut video, gambar, dan dokumen tanpa menyebut audio. Di sisi lain, transkrip 20 detik pertama klip *nglowong* sangat rinci ("Halo teman-teman semua kenalin nama aku …"), dan klip kontrol dikenali sebagai musik gamelan. Uji dengan dan tanpa audio di Gate 0 akan menjawabnya.
2. Recall ucapan setelah perbaikan (prompt v2 dengan kolom `source` dan instruksi memeriksa sampai akhir, ditambah segmen pendek).
3. Kualitas potongan SAM 3.1 untuk canting dan alat lain.

## Perubahan di v2 (sudah ada di skrip, belum dijalankan)
- Kolom `source`: `ucapan`, `teks_layar`, atau `visual`. Hanya `ucapan` yang dinilai terhadap subtitle.
- Instruksi untuk memeriksa seluruh durasi video sampai akhir.
- Klip maestro dipindah ke menit 15–20 (900–1200 s).
- Hasil ditulis ke `hasil/muse-spark-1.3-v2/`, jadi v1 tidak tertimpa.

## Implikasi untuk desain Empu
- Segmen 75 detik dengan overlap (spec 8.3).
- `source` adalah kolom wajib di semua lapisan (spec 5, 9, 11).
- Mode B (ASR-assisted) disiapkan sebagai jalur cadangan (spec 8.4).
- Rekaman sendiri tanpa teks di layar adalah set uji utama, karena itu kondisi pemakaian nyata.
- Respons v1 di `hasil-v1/` bisa dipakai sebagai fixture tes untuk parser dan penggabungan (enum lama perlu dipetakan ke enum baru).

---

## Gate 0: hasil spike (v2, 28 Okt 2026)

Dijalankan dengan `uji_muse.py` (prompt v2, path diperbaiki ke struktur repo baru, pakai klip precut dari `arsip-hidup-batik/uji/klip/`) dan `uji_sam.py` (baru). Hasil mentah di `hasil/muse-spark-1.3-v2/` dan `hasil/sam-3.1/`.

### #1 Apakah Muse mendengar audio (klip `nglowong`)
| Versi | `speech_heard` | Istilah total | Istilah `source=ucapan` |
|---|---|---|---|
| Dengan audio | true | 22 | **13** |
| Tanpa audio (`ffmpeg -an`, diverifikasi lewat `ffprobe` — stream audio benar-benar hilang) | true | 13 | **4** |

Jumlah istilah `ucapan` turun jauh (13 → 4) tanpa audio, jadi **lolos kriteria literal Gate 0** ("audio membantu"). **Tapi ada kejanggalan**: `transcript_first_20s` di versi tanpa-audio nyaris identik kata demi kata dengan versi beraudio ("Halo teman-teman semua kenalin nama aku Zukhr… dari Universitas Negeri Surabaya…"). Kalimat pembuka ini adalah pola umum video praktikum mahasiswa Indonesia — kemungkinan Muse menebak dari konteks visual (laporan praktikum, setting kampus) atau pembacaan bibir, bukan murni "tidak bisa apa-apa tanpa audio". **Kesimpulan: audio berpengaruh secara nyata pada jumlah dan rincian istilah, tapi model juga menunjukkan kemampuan menebak konten generik dari visual saja — jangan klaim "100% butuh audio" ke juri.**

### #2 Recall ucapan pada 8 istilah kunci (#NgertiBatik, v2)
| Istilah diucapkan (detik) | Temuan Muse v2 | Waktu & sumber benar? |
|---|---|---|
| pola (85–87) | `pola` @85.0, ucapan | ✓ |
| lilin malam (109) | `mencairkan malam` @111.0, ucapan | ✓ (Δt 2 d) |
| spangkring (122) | `spangkring` @77.0, **ucapan** | ✗ — waktu tetap salah (masih dari diagram @77), dan kali ini **sumbernya pun salah** (v1 jujur menandai `teks_layar`, v2 menandai `ucapan`) |
| membatik (126–128) | `membatik` @123.0, ucapan | ✓ (Δt ~4 d) |
| mewarna (145–149) | `mewarnai` @148.0, ucapan | ✓ |
| HCl (155) | — | ✗ tidak ditemukan (sama seperti v1) |
| waterglass (162–165) | — | ✗ tidak ditemukan (sama seperti v1) |
| nglorod (173) | `melorot` @172.0, ucapan | ✓ (Δt 1 d) |

**Recall dengan waktu & sumber benar: 5 dari 8.** Naik dari v1 (4/8), tapi **masih di bawah ambang Gate 0 (≥6/8)**. Per aturan spec bagian 15: *"Kalau kurang dari 6 dari 8, Mode B menjadi default."* Satu regresi penting: akurasi label sumber untuk *spangkring* memburuk dari v1 ke v2 (true→false), bertentangan dengan tujuan v2 menambah kolom `source` yang lebih akurat. Ini jadi risiko nyata untuk metrik "akurasi label sumber ≥0,90" (spec bagian 14).

### #3 SAM 3.1 (keyframe canting dari klip `nglowong`, t=30s)
Format API (`dev.meta.ai/docs/sam/segmenting`) sudah diverifikasi: `POST /v1/responses`, `model: sam-3.1`, `input_text` berisi noun phrase pendek, `input_image` berisi `image_url` (data URL base64 untuk file lokal), `stream` boleh `false`. Hasil per prompt pada keyframe yang sama:

| Prompt | Hasil |
|---|---|
| `canting` (istilah Jawa) | 0 deteksi |
| `copper pen tool` | 0 deteksi |
| `wax pen` | 0 deteksi |
| `cloth` | **3 deteksi** (kain) |
| `pen with wooden handle` | **4 deteksi** (canting) |

**SAM 3.1 tidak mengenali istilah lokal ("canting") sama sekali** — respons kosong bukan error (sesuai dokumentasi, "zero matches" memang tampil sebagai `output_text` kosong). Begitu prompt diganti ke deskripsi Inggris yang konkret ("pen with wooden handle"), deteksi langsung muncul dan jumlahnya masuk akal (4 canting terlihat di frame). **Implikasi untuk craft pack**: kolom `sam_prompt` di `batik_tulis.yaml` wajib pakai deskripsi visual bahasa Inggris, bukan istilah asli/Jawa — istilah asli tetap ditampilkan ke pengguna, tapi prompt ke SAM harus dideskripsikan ulang.

### #4 Structured output (`text.format` json_schema)
**Diterima.** Satu panggilan ke `muse-spark-1.3` dengan skema minimal (bentuk field sesuai PROMPT v2, bukan skema produksi penuh) sukses tanpa error 400. Belum diuji: skema produksi penuh (`muse-output.schema.json`, enum Inggris) dan perilaku `strict: true`.

### Verdict Gate 0 keseluruhan
| # | Cek | Target | Hasil | Lolos? |
|---|---|---|---|---|
| 1 | Audio berpengaruh | istilah ucapan turun tanpa audio | 13 → 4 | Lolos (dengan catatan hallucinated-intro) |
| 2 | Recall ucapan #NgertiBatik | ≥ 6/8 | **5/8** | **Tidak lolos** |
| 3 | SAM 3.1 | ≥1 keyframe berhasil | 4 deteksi (prompt Inggris) | Lolos (butuh prompt Inggris) |
| 4 | Structured output | diterima API | Diterima | Lolos |

**Per aturan literal spec bagian 15, cek #2 gagal → Mode B (ASR-assisted) seharusnya menjadi default**, bukan stretch. Ini bertentangan sebagian dengan hasil cek #1 yang menunjukkan audio tetap berpengaruh signifikan — jadi gambarannya bukan "Muse tuli", tapi "Muse mendengar sebagian, namun recall istilah teknis spesifik (terutama di ujung klip panjang 241 detik dan istilah asing seperti HCl/waterglass) masih di bawah target produk, dan label sumbernya belum cukup dipercaya untuk klaim "jujur soal sumber" (prinsip produk #3)." **Keputusan Mode A vs Mode B perlu dikonfirmasi Syafiq sebelum H1**, karena ini mengubah scope pipeline (spec 8.4) secara signifikan.
