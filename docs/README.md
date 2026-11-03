# Dokumen Empu

Folder ini adalah konteks lengkap untuk membuat implementation plan Empu dengan Claude Code. Isinya terpisah dari proyek lain.

## Isi dan urutan baca

| # | File | Isi |
|---|---|---|
| 1 | `../CLAUDE.md` | Ringkasan, aturan emas, stack. Dibaca otomatis oleh Claude Code di setiap sesi |
| 2 | `superpowers/specs/2026-10-28-empu-design.md` | **Dokumen desain utama**: masalah, pengguna, scope, prinsip, layar, arsitektur, pipeline, model data, API, ekspor, izin, evaluasi, roadmap dan gate, risiko, keputusan terbuka |
| 3 | `reference/meta-model-api.md` | Cara memanggil Muse dan SAM: yang sudah terbukti dan yang belum |
| 4 | `reference/prompt-analisis.md` | Template prompt Muse v3 (Mode A dan B) |
| 5 | `reference/muse-output.schema.json` | Skema JSON keluaran Muse per segmen |
| 6 | `reference/hasil-uji-kelayakan.md` | Hasil uji 28 Okt, termasuk kelemahannya |
| 7 | `reference/uji-kelayakan/` | Skrip uji, glosarium, dan respons mentah v1 (bahan fixture) |
| 8 | `../packs/batik_tulis.yaml` | Craft pack draf (13 tahap, 42 istilah) |
| 9 | `eval/` | Set uji, format kunci jawaban |
| 10 | `00-konteks-hackathon.md` | Fakta hackathon, kriteria juri, nama, klaim yang aman, positioning, visi |
| 11 | `konteks-fitur.md` | Daftar lengkap fitur yang sudah ada di aplikasi (permukaan publik, Ask, Studio, pipeline, ekspor, evaluasi, batasan) |

## Cara membuat plan

Buka Claude Code di folder `Empu`, lalu kirim prompt berikut (sesuaikan kalau perlu):

```text
Baca CLAUDE.md, lalu semua dokumen di docs/ sesuai urutan di docs/README.md.
Buat implementation plan untuk Empu berdasarkan docs/superpowers/specs/2026-10-28-empu-design.md.

- Pecah per fase sesuai roadmap H0–H7 di spec bagian 15, satu file per fase,
  simpan di docs/superpowers/plans/2026-10-28-empu/.
- H0 berisi spike Gate 0 (audio, recall ucapan, SAM 3.1, structured output) sebagai
  task pertama, sebelum scaffolding apa pun.
- Setiap task: file yang disentuh, langkah TDD, perintah verifikasi, dan definisi selesai.
- Tandai setiap gate dan apa yang dipotong kalau gate gagal.
- Jangan menulis kode dulu. Tanyakan ke saya kalau ada keputusan di spec bagian 17
  yang perlu diubah.
```

Kalau kamu memakai skill penulisan plan dari superpowers, arahkan skill itu ke file spec di atas.

## Yang masih perlu kamu lakukan
1. Salin `META_MODEL_API_KEY` ke `.env` di repo Empu (jangan di-commit).
2. Pindahkan atau salin folder video uji `arsip-hidup-batik/` ke `Empu/data-uji/` (folder ini nanti di-.gitignore), atau isi `EMPU_TESTDATA_DIR` dengan lokasinya.
3. Hubungi sanggar untuk sesi rekam, paling lambat Minggu 1 Nov.
4. Tinjau keputusan terbuka di spec bagian 17. Kalau tidak diubah, default yang dipakai.
