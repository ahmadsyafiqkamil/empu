# Hasil Gate Ask: teks-saja + structured output

Tanggal: 31 Okt 2026 · Skrip: `docs/reference/uji-kelayakan/uji_ask.py` · Model: `muse-spark-1.3`
Fixture: `api/tests/fixtures/ask/probe.raw.json`

## Hasil

| Butir | Hasil |
|---|---|
| `POST /responses` tanpa `input_video` (hanya `input_text`) | **Didukung.** Status `completed`, HTTP 200 |
| `text.format` = `json_schema`, `strict: true` | **Dipatuhi.** Keluaran JSON valid, empat kunci lengkap |
| Bahasa jawaban mengikuti bahasa pertanyaan | **Ya.** Pertanyaan Indonesia → `lang: "id"`, jawaban Indonesia |
| Sitasi | **Ya.** `entry_ids: [1]`, `insufficient: false` |
| Latensi | 4,87 s (pertama), 3,43 s saat gagal |
| Token | input 224, output 917 (875 di antaranya `reasoning_tokens`), total 1141 |
| Cache prompt | `cached_tokens: 152` pada panggilan kedua — prompt pendek, dampak kecil |

Keluaran aktual:

```json
{"answer":"Canting adalah alat pena tembaga untuk menorehkan malam panas.","entry_ids":[1],"insufficient":false,"lang":"id"}
```

## Temuan yang mengubah rencana

**`max_output_tokens` harus jauh lebih besar dari perkiraan.** Percobaan pertama memakai 400 token: status `incomplete`, `output_tokens: 400` dengan `reasoning_tokens: 398`, dan **teks jawaban kosong**. Muse Spark menghabiskan budget keluaran untuk reasoning sebelum menulis jawaban.

Akibat untuk implementasi:
- Default `MetaClient.respond_text` = **2000**, bukan 800.
- `create_response` yang sudah ada menaikkan `MetaAPIError` untuk status `incomplete` — perilaku ini benar dan harus dipertahankan; route memetakannya ke 502.
- Perkiraan biaya per pertanyaan naik: ~1.100 token total, bukan ~300. Masih murah (di bawah USD 0,01 per pertanyaan pada harga `muse-spark-1.3`), tetapi batas laju tetap perlu.

## Kesimpulan

Rencana berjalan tanpa perubahan desain. Hanya angka default `max_output_tokens` yang dinaikkan, dan `RESPONSE_SCHEMA` di skrip ini sudah identik dengan yang akan dipakai `api/empu/ask/prompts.py`.

## Tindak lanjut 31 Okt: `incomplete` pada pertanyaan luas

Pertanyaan "jelaskan kepada saya bagaimana cara untuk membatik" gagal dengan 502 kira-kira satu dari tiga percobaan. Galat aslinya:

```
MetaAPIError: Meta API error 200: response status incomplete: {'reason': 'max_output_tokens'}
```

Sebabnya: Muse menghabiskan 1.327–2.075 token reasoning sebelum menulis jawaban, dan anggaran 2.000 kadang habis lebih dulu. Anggaran 2.000 cukup untuk probe dua baris, tidak untuk prompt arsip sungguhan (29 baris, 10.869 karakter).

Dua perubahan:

1. `respond_text` default 6.000 token, dan bila status `incomplete` dengan alasan `max_output_tokens`, ia mencoba **sekali** lagi dengan 12.000. Alasan `incomplete` lain (mis. `content_filter`) tidak diulang.
2. `MAX_CITATIONS = 4` (prompt `ask-v2`). Sebelumnya pertanyaan luas menyitir 24 istilah — jawaban 50 kata dengan 24 kartu bukti bukan jawaban, melainkan membuang seluruh kamus ke layar.

Hasil sesudahnya, pertanyaan yang sama lima kali berturut-turut: 5/5 `200`, 4 kartu bukti, tanpa galat di log. Pertanyaan Jawa tetap dijawab dalam Jawa (`lang: jv`), pertanyaan di luar arsip tetap `refused` tanpa bukti.

## Retrieval

Diukur pada 31 Okt dengan `empu eval retrieval` (perintah baru, lihat plan `2026-10-31-empu-retrieval-eval.md`). Angka ini mengukur **tahap retrieve saja**: berapa sering istilah yang dibutuhkan sebuah jawaban benar-benar masuk daftar yang dikirim ke model. Tidak ada panggilan model di jalur ini.

```text
cd api && uv run empu eval retrieval --archive batik-tulis \
  --questions ../docs/eval/pertanyaan-retrieval.csv --k 4
rows=18 k=4 questions=20 question_recall=1.00 term_recall=1.00
```

- **rows=18** (istilah publik setelah rekaman berlisensi standar disembunyikan), **k=4**, **questions=20**, **misses=0**.
- Komposisi daftar (`docs/eval/pertanyaan-retrieval.csv`): 5 definisi bahasa Indonesia, 5 proses/tahapan, 3 bahasa Jawa, 4 bahasa Inggris yang memakai kata lain ("wax pen", "wooden frame", "fix the dye"), 3 perbandingan dua istilah.
- Riwayat pengukuran, supaya angkanya bisa diaudit:
  - Ukuran pertama memakai `nembok` dan `paruh` sebagai jawaban yang diharapkan. Keduanya **tidak publik** (tidak punya occurrence publik), sehingga pertanyaan itu mustahil dijawab pintu publik; empat pertanyaan diganti dengan istilah publik.
  - Setelah rekaman 6 dan 7 diturunkan ke `internal_eval` (lihat plan `2026-10-31-empu-demo-data.md`), `nglorod`, `colet`, `ngiseni`, dan `finishing` ikut hilang dari kamus publik. Enam pertanyaan yang menyebutnya mustahil dijawab, jadi diganti dengan istilah yang masih publik; daftar diukur ulang dan menghasilkan angka di atas.
- Karena itu `rows` turun dari 29 ke 18. Angka 1,00 ini diukur pada daftar yang **hanya berisi istilah publik saat ini**; jangan membandingkannya dengan ukuran arsip sebelumnya.

**Keputusan (ambang di plan): `question_recall` @4 = 1,00 ≥ 0,90 → berhenti.** Retrieval leksikal cukup untuk arsip sekecil ini; jangan tambah embedding.

**Batas angka ini, harus disebut bersama hasilnya:**

- `limit` prefilter = 60 dan baris hanya 18, jadi pemotongan tidak pernah terjadi. Yang diukur adalah urutan peringkat, bukan ketahanan terhadap pemotongan. Pengukuran pada 90 baris ada di bagian berikutnya.
- 20 pertanyaan ditulis dari istilah yang ada di arsip, jadi ini bukan uji buta terhadap pertanyaan pengunjung sungguhan.

## Retrieval lintas arsip (1 Nov 2026)

Sesudah Ask menjadi satu pintu untuk semua arsip, indeks yang diranking berisi 90 baris (18 Batik + 72 Gamelan) — melewati batas prefilter 60 untuk pertama kali. Diukur ulang dengan perintah yang sama, tanpa `--archive` berarti semua arsip.

```text
cd api && uv run empu eval retrieval --questions ../docs/eval/pertanyaan-retrieval.csv --k 4
rows=90 k=4 questions=20 question_recall=0.95 term_recall=0.96
miss: how do you fix the dye so it does not fade? missing=fiksasi rank=31

cd api && uv run empu eval retrieval --questions ../docs/eval/pertanyaan-retrieval-gamelan.csv --k 4
rows=90 k=4 questions=10 question_recall=1.00 term_recall=1.00
```

Pembanding per arsip, supaya penurunan bisa diatribusikan (perintah yang dijalankan dan keluarannya):

```text
uv run empu eval retrieval --archive batik-tulis \
  --questions ../docs/eval/pertanyaan-retrieval.csv --k 4
rows=18 k=4 questions=20 question_recall=1.00 term_recall=1.00

uv run empu eval retrieval --archive gamelan \
  --questions ../docs/eval/pertanyaan-retrieval-gamelan.csv --k 4
rows=72 k=4 questions=10 question_recall=1.00 term_recall=1.00
```


| Ukuran | Baris | question_recall | term_recall |
|---|---|---|---|
| Batik, satu arsip | 18 | 1,00 | 1,00 |
| Gamelan, satu arsip | 72 | 1,00 | 1,00 |
| Batik, indeks gabungan | 90 | 0,95 | 0,96 |
| Gamelan, indeks gabungan | 90 | 1,00 | 1,00 |

- Daftar pertanyaan Gamelan: `docs/eval/pertanyaan-retrieval-gamelan.csv`, 10 pertanyaan (8 bahasa Indonesia — termasuk definisi, sebutan lain, satu teknik, dan satu perbandingan dua laras — dan 2 bahasa Inggris yang memakai kata lain). Semua istilah yang diharapkan adalah istilah publik.
- **Satu-satunya yang meleset** adalah `fiksasi` pada pertanyaan "how do you fix the dye so it does not fade?", sekarang di peringkat 31 dari 90 (sebelumnya masuk 4 besar dari 18). Sebabnya bukan pemotongan: `prefilter` mengirim 60 baris teratas, dan peringkat 31 ada di dalamnya, jadi istilah itu tetap sampai ke model. Yang berubah adalah peringkat relatif karena 72 baris Gamelan ikut bersaing.
- **Keputusan: `ask_max_entries` tetap 60.** Angka 0,95/0,96 masih di atas ambang 0,90 di bagian sebelumnya, dan menaikkan batas ke 120 tidak akan mengubah `question_recall` — metrik ini meranking seluruh baris, bukan hanya yang terkirim. Menaikkan batas hanya akan menambah token prompt tanpa memperbaiki urutan.
- **Batas angka ini:** kedua daftar pertanyaan ditulis dari istilah yang ada di arsipnya, jadi ini bukan uji buta. `question_recall` @4 adalah proksi konservatif; yang sebenarnya dikirim ke model adalah 60 baris.

