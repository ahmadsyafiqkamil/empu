# Empu

Empu mengubah video seorang ahli yang bekerja sambil bercerita menjadi kamus keahlian yang bisa ditonton. Setiap istilah terhubung ke ucapan, klip, dan potongan gambar alatnya, lalu divalidasi oleh sang ahli. Edisi pertama: **Batik Tulis**. Dibangun solo oleh Syafiq untuk Meta Global AI Developer Hackathon 2026 (track Indie).

**Deadline submission: Kamis 5 Nov 2026, 09:00 WIB. Target kirim: Rabu 4 Nov, 22:00 WIB.**

## Baca dulu
1. `docs/superpowers/specs/2026-10-28-empu-design.md`: sumber kebenaran (scope, pipeline, data, API, evaluasi, roadmap, gate).
2. `docs/reference/meta-model-api.md`: sebelum menulis kode apa pun yang memanggil Meta API.
3. `docs/reference/prompt-analisis.md` dan `docs/reference/muse-output.schema.json`.
4. `packs/batik_tulis.yaml`: craft pack draf.
5. `docs/reference/hasil-uji-kelayakan.md`: apa yang sudah dan belum terbukti.
6. `docs/00-konteks-hackathon.md`: kriteria juri dan klaim yang boleh dipakai.

Plan implementasi disimpan di `docs/superpowers/plans/`.

## Aturan emas
- **Ikuti gate di spec bagian 15.** Kalau gate gagal, potong fitur sesuai urutan di sana, jangan memperpanjang jadwal.
- **Pengetahuan keterampilan hanya di craft pack.** Jangan hardcode istilah batik di kode pipeline.
- **AI mengusulkan, manusia memutuskan.** Tidak ada yang tampil publik kecuali entri `accepted`/`edited`, `access_level=public`, dan izin rekamannya `granted` + `public`.
- **Label sumber (`speech`/`on_screen_text`/`visual_only`) tidak boleh hilang** di DB, API, UI, maupun ekspor.
- **Gambar hanya dari frame asli.** Jangan pernah membuat gambar dengan AI.
- **Semua panggilan Meta API lewat `api/empu/meta_client.py`.** Cache respons mentah (kunci: hash segmen + model + versi prompt + mode). Jangan memanggil API kalau cache sudah ada.
- **Rahasia:** `META_MODEL_API_KEY` dan `STUDIO_KEY` ada di `.env`. Jangan dicetak, di-log, atau di-commit.
- **Data dan hak cipta:** jangan commit video, `data/`, `data-uji/`, atau `arsip-hidup-batik/`. Video YouTube **berlisensi standar** hanya untuk evaluasi internal dan tidak boleh muncul di demo, repo, atau ekspor publik. Video YouTube **CC BY** (daftar `demo_cc_by` di `docs/eval/test-set.yaml`) boleh tampil di demo, kamus publik, dan ekspor, **dengan atribusi** (kreator, URL, lisensi, keterangan "dipotong").
- **Klaim validasi:** "divalidasi oleh sang ahli" hanya untuk entri yang benar-benar dicek kreator/ahli. Selain itu "divalidasi oleh pendokumentasi".
- **Tes tidak boleh memanggil API sungguhan.** Pakai fixture di `api/tests/fixtures/` (sumber awal: `docs/reference/uji-kelayakan/hasil-v1/`, enum lama perlu dipetakan).
- Kalau spec ambigu soal izin, akses publik, atau klaim ke juri, **tanya Syafiq**, jangan menebak.

## Stack (rencana)
- `api/`: Python 3.11+, FastAPI, SQLModel (SQLite), Pydantic v2, httpx, tenacity, rapidfuzz, pympi-ling, PyYAML. ffmpeg/ffprobe dipanggil lewat subprocess. Tes dengan pytest.
- `web/`: Next.js (App Router), TypeScript, Tailwind.
- `deploy/`: Docker Compose (web, api, worker, caddy). Caddy menyajikan `/media` dengan dukungan Range.
- Satu paket Python `empu` berisi pustaka pipeline, API, worker (`python -m empu.worker`), dan CLI (`empu analyze`, `empu eval`).

## Perintah
Diisi saat scaffolding (H1): instalasi, menjalankan api, worker, dan web, tes, lint, dan CLI.

## Konvensi
- Kode, identifier, nama tabel, enum, dan pesan commit dalam bahasa Inggris.
- Teks UI dalam bahasa Inggris. Istilah keahlian tetap dalam bentuk aslinya. Glosa tersedia dalam bahasa Indonesia dan Inggris.
- Dokumen di `docs/` dalam bahasa Indonesia.
- Setiap perubahan prompt menaikkan `PROMPT_VERSION`.

## Status
- H0 (Rab 28 Okt): dokumen konteks selesai. Plan di `docs/superpowers/plans/2026-10-28-empu/` (ikhtisar, H0, H1 sebagian). Keputusan: demo pakai video YouTube CC BY dengan atribusi (spec diperbarui). Gate 0 selesai (`docs/reference/hasil-gate0.md`): audio lulus, recall 4/8 dengan waktu (7/8 isi) → **Mode B** (faster-whisper sebagai jangkar waktu), SAM lulus dengan prompt deskriptif Inggris + bbox saja, structured output skema penuh didukung. Berikutnya: hubungi kreator CC BY, lalu H1.
