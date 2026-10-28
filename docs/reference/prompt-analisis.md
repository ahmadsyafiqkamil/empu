# Prompt Analisis Muse

`PROMPT_VERSION = "analyze-v3"`. Simpan template ini di kode (`api/empu/pipeline/prompts.py`), bukan di dokumen. Setiap perubahan prompt wajib menaikkan versi, karena versi menjadi bagian dari kunci cache dan dicatat di hasil evaluasi.

Riwayat:
- **v1** (uji 28 Okt): istilah yang diucapkan, timestamp, apa yang terlihat. Enum berbahasa Indonesia.
- **v2** (skrip uji, belum dijalankan): menambah `source` (`ucapan`/`teks_layar`/`visual`) dan instruksi memeriksa sampai akhir video.
- **v3** (Empu): enum berbahasa Inggris, konteks dari craft pack, info segmen, `evidence_quote`, `visible_object_en`, `gloss_en`, dan `category`.

## Template v3 (Mode A)

Bagian dalam `{…}` diisi dari craft pack dan metadata segmen.

```text
Kamu membantu mendokumentasikan pengetahuan seorang ahli {pack.name.id}.
Video ini adalah segmen {seg_index}/{seg_total} dari sebuah rekaman, berdurasi {seg_duration} detik.
Semua waktu dihitung dalam detik dari AWAL SEGMEN INI.

KONTEKS KETERAMPILAN
{pack.prompt_context}

KERANGKA TAHAPAN (urutan umum, rekaman nyata bisa berbeda):
{daftar: stage.id — stage.label.id (varian: …)}

CONTOH ISTILAH YANG MUNGKIN MUNCUL
Ini hanya contoh, BUKAN daftar yang harus ditemukan. Jangan laporkan istilah dari daftar ini
kalau tidak benar-benar diucapkan, tertulis, atau terlihat di segmen ini.
Istilah di luar daftar justru sangat penting, terutama istilah bahasa Jawa atau istilah lokal: laporkan juga.
{daftar: term.label (varian: …)}

TUGAS
Tonton DAN dengarkan segmen ini sampai detik terakhir.
1. Catat setiap istilah keahlian (alat, bagian alat, bahan, pewarna, tahap, teknik, motif).
   Untuk setiap istilah, tentukan sumbernya dengan tegas:
   - "speech": terdengar diucapkan di audio.
   - "on_screen_text": hanya terbaca sebagai tulisan di layar (judul, diagram, subtitle tertanam).
   - "visual_only": bendanya terlihat, tapi tidak diucapkan dan tidak tertulis.
   Kalau sebuah istilah diucapkan DAN tertulis, pakai "speech" dengan waktu saat diucapkan.
   Kalau istilah yang sama diucapkan berulang dalam 5 detik, cukup laporkan sekali.
2. Beri waktu mulai dan selesai ucapan (t_start, t_end).
3. Untuk "speech", tulis kalimat yang diucapkan di sekitar istilah itu di evidence_quote.
4. Jelaskan apa yang TERLIHAT saat itu (visible), apakah cocok dengan istilahnya (visual_match),
   dan tulis frasa benda pendek dalam bahasa Inggris (visible_object_en) kalau ada benda yang relevan.
5. Beri arti singkat dalam bahasa Indonesia (gloss_id) dan Inggris (gloss_en).
   Kalau tidak yakin artinya, katakan begitu dan turunkan confidence.
6. Susun urutan tahapan proses yang terlihat di segmen ini (process_steps).

Jangan mengarang. Kalau segmen hanya berisi musik atau tidak ada ucapan, speech_heard = false
dan jangan laporkan istilah "speech".

Jawab HANYA dengan JSON valid sesuai skema berikut, tanpa teks lain:
{muse-output.schema.json, atau contoh bentuknya kalau structured output tidak didukung}
```

## Tambahan untuk Mode B (ASR-assisted)

Sisipkan sebelum TUGAS:

```text
TRANSKRIP OTOMATIS (dengan timestamp, dari awal segmen)
Transkrip ini dibuat mesin pengenal suara umum dan SERING SALAH menulis istilah keahlian
(contoh: "spangkring" ditulis "spang King", "waterglass" ditulis "watera gelas").
Pakai timestamp-nya sebagai jangkar waktu, lalu perbaiki ejaan istilah berdasarkan apa yang
kamu dengar dan lihat di video.
{[t_start–t_end] teks}
```

## Catatan
- Ablasi "tanpa istilah benih": hapus seluruh bagian CONTOH ISTILAH, sisanya tetap sama. Ini memakai versi prompt yang berbeda (`analyze-v3-noseed`).
- Jangan menaruh glosa dari pack di prompt. Arti harus datang dari ucapan maestro dan video, supaya validasi maestro bermakna.
