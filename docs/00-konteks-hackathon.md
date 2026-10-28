# Konteks Hackathon dan Produk

## Fakta hackathon

| Item | Detail |
|---|---|
| Acara | Meta Global AI Developer Hackathon 2026 (Meta dan Cerebral Valley), remote |
| Link | https://dev.meta.ai/events/global-hackathon · https://cerebralvalley.ai/e/meta-ai-developer-hackathon |
| Masa build | 26 Okt – 4 Nov 2026. Workshop dan office hours di Discord |
| **Submission** | **4 Nov 2026, 21:00 ET = Kamis 5 Nov 2026, 09:00 WIB**. AS sudah keluar dari DST pada 1 Nov, jadi ET = UTC−5 |
| Target kirim internal | Rabu 4 Nov, 22:00 WIB |
| Penjurian | 4–8 Nov. Final dan pengumuman pemenang 9 Nov |
| Hadiah | Total USD 1.000.000 |
| Track | **Indie**, dinilai dari **kreativitas, ambisi teknis, dan apakah berfungsi** |
| Tema resmi | "Build for Your World" dan "Push the Frontier" |
| Kredit partner | Baseten USD 100, Modal USD 100, Fireworks USD 25. Kredit Meta Model API USD 150 per peserta disebut di forum, belum terkonfirmasi |
| Target | Menang, minimal masuk 5 besar |

**Belum dicek:** persyaratan isi submission (repo publik, video demo dan durasi maksimalnya, deskripsi, link aplikasi). Cek halaman submission di hari pertama build dan sesuaikan H7.

## Memenuhi kriteria Indie

| Kriteria | Cara Empu menjawabnya |
|---|---|
| Kreativitas | Bukan chatbot atau perangkum video. Empu menangkap pengetahuan tacit seorang maestro dan mengubahnya menjadi kamus yang bisa ditonton, dengan bukti asli di setiap entri |
| Ambisi teknis | Muse memahami video (dan audio) untuk menautkan istilah ke waktu dan gerakan, SAM 3.1 memotong alatnya, pipeline segmen dengan penggabungan dan kanonisasi, craft pack yang bisa ditukar, serta evaluasi dengan baseline dan ablasi |
| Berfungsi | URL publik, arsip demo yang sudah tervalidasi, sandbox untuk mencoba, dan angka evaluasi asli di halaman Bukti |

## Pembingkaian tema (pilih saat submission)
- **Build for Your World:** alat untuk komunitas pengrajin di sekitar kita, agar pengetahuan maestro tidak hilang.
- **Push the Frontier:** mempercepat dokumentasi warisan budaya takbenda dan linguistik lapangan, yang selama ini macet di tahap anotasi manual (puluhan jam kerja untuk satu jam rekaman).

Keduanya bisa dipakai. Pilihan ini tidak memengaruhi build.

## Nama dan cerita
- **Nama:** Empu, gelar Jawa untuk seorang guru ahli. Pendek, unik, mudah diucapkan juri global, dan cocok untuk cabang mana pun ke depannya.
- **Tagline:** *Capture what masters know, before it's gone.*
- **Edisi pertama:** *Empu: Batik Tulis Edition.* README menulis "Craft packs: batik tulis (live), tenun dan gamelan (planned)".
- **Arsip Hidup:** nama koleksi di dalam aplikasi, mis. *Arsip Hidup Batik Sanggar X*.
- **Visi di akhir pitch:** "Batik hari ini. Tenun dan gamelan berikutnya. Setiap keahlian yang belum pernah tertulis."
- **Cek nama (28 Okt):** tidak ditemukan produk lain bernama Empu di bidang ini. Ketersediaan domain dan merek belum dicek.
- **Hati-hati:** "empu" juga berarti pembuat keris. Jangan pakai simbol keris sebagai logo tanpa riset.

## Klaim yang aman dan yang belum
| Klaim | Status |
|---|---|
| Muse tidak mengarang istilah dari video yang hanya berisi musik | Aman (uji v1) |
| Timestamp tepat dalam beberapa detik untuk ucapan yang jelas | Aman (uji v1) |
| Muse menemukan istilah di luar glosarium | Aman, tapi di v1 istilah itu berasal dari teks di layar |
| "Subtitle biasa menulis 'spang King', Empu mendengar 'spangkring'" | **Belum.** Di v1, Muse membacanya dari diagram. Tunggu v2 atau rekaman sendiri |
| "Batik akan punah" | **Jangan pernah dipakai** |
| "Divalidasi oleh sang ahli/maestro" | **Hanya** untuk entri yang benar-benar dicek kreator atau ahli di video CC BY (atau maestro di rekaman sendiri). Selain itu: "divalidasi oleh pendokumentasi" |
| "Subtitle otomatis menulis *canting* sebagai 'cantik'/'cacing'" (video CC BY *Macam Canting dalam Batik Tulis*, Batik Education) | Fakta subtitle sudah dicek 28 Okt. Klaim bahwa **Empu** menangkapnya dengan benar baru boleh setelah hasil pipeline menunjukkan `source=speech` di waktu yang benar |

## Posisi terhadap yang sudah ada
| Yang ada | Kekurangannya | Empu |
|---|---|---|
| ELAN (alat anotasi) | Manual, berjam-jam per rekaman | Usulan otomatis, manusia tinggal memvalidasi, ekspor ke `.eaf` |
| Arsip seperti ELAR/ELDP | Menyimpan, tidak mengolah | Mengolah menjadi kamus yang bisa dicari dan ditonton |
| Subtitle atau ASR umum | Salah tulis istilah keahlian, tanpa tautan ke gerakan | Istilah, sumber, waktu, klip, dan potongan alat |
| Perangkum video umum | Tanpa izin, tanpa validasi, tanpa bukti per istilah | Izin per rekaman, level akses, atribusi maestro |

## Arah scaling (cukup satu kalimat di pitch)
| Tahap | Wujud |
|---|---|
| Hari ini | Kamus video batik tulis |
| 1 | Platform arsip warisan budaya takbenda (craft pack per keterampilan dan daerah) |
| 2 | Belajar dari maestro: murid merekam diri, dibandingkan dengan rekaman maestro, maestro mendapat bagian pendapatan |
| 3 | Paspor keaslian produk kerajinan (bukti proses pembuatan per kain) |
| 4 | Penangkap pengetahuan ahli untuk industri (teknisi senior, SOP dari video) |

Yang sulit ditiru: kepercayaan komunitas, data yang tervalidasi manusia, dan craft pack yang dibangun bersama ahlinya.
