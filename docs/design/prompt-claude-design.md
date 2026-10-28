# Prompt pembuka untuk Claude Design

Lampirkan: `brief-claude-design.md`, `contoh-data.json`, dan semua gambar di `aset/`. Lalu tempel teks di bawah.

---

Tolong desain UI web **Empu: Batik Tulis Edition**, kamus keahlian yang bisa ditonton. Setiap istilah batik terhubung ke ucapan asli sang ahli, klip gerakannya, dan potongan alat dari frame asli video. AI (Muse Spark 1.3 + SAM 3.1) mengusulkan, manusia memutuskan.

Semua konteks ada di **brief-claude-design.md** (terlampir). Ikuti terutama:
- **Aturan yang tidak boleh dilanggar** di bagian 3: label sumber Spoken / On-screen text / Visual only selalu terlihat dengan ikon dan teks, hanya frame asli, atribusi kreator selalu tampil, dan klaim validasi yang jujur.
- **Arah visual "Mori & Malam"** di bagian 4: mode terang untuk halaman publik, mode gelap untuk Studio, dengan token warna yang sudah dicek kontrasnya. Pakai nama CSS variable yang sama.
- **Microcopy bahasa Inggris** di bagian 8. Pakai persis.
- **Batasan teknis** di bagian 10: Next.js + Tailwind, elemen video dan audio native, dan harus bisa dibangun satu orang dalam sekitar 2 hari. Pilih yang sederhana.

Isi semua layar dengan data dari **contoh-data.json** dan gambar dari folder **aset/**. Jangan membuat gambar atau ilustrasi baru, dan jangan memakai motif batik klasik atau simbol keris sebagai dekorasi.

Urutan kerja:
1. Token desain (warna kedua mode, tipografi, spasi) sebagai CSS variable.
2. Lembar komponen (bagian 7), dengan semua state.
3. Layar sesuai prioritas: **Detail entri** (HP 390 px dan desktop 1440 px) → **Kamus** → **Studio validasi** (desktop) → **Beranda** → **Bukti** → Progres → Unggah dan Try → Peta tahapan → Ekspor.

Mulai dari token dan Detail entri dulu, lalu tunjukkan ke saya sebelum lanjut ke layar lain.
