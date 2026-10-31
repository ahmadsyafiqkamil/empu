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
