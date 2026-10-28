# Rujukan Meta Model API untuk Empu

Semua panggilan ke Meta lewat satu modul: `api/empu/meta_client.py`. Bagian "Terverifikasi" sudah dipakai dan berhasil di uji kelayakan 28 Okt 2026 (`docs/reference/uji-kelayakan/uji_muse.py`). Bagian "Belum terverifikasi" wajib dicek di spike Gate 0 sebelum kodenya dianggap selesai.

Dokumentasi resmi (baca dari Mac kalau bisa diakses; dari workspace cloud halaman ini diblokir):
- https://dev.meta.ai/docs/video-understanding
- https://dev.meta.ai/docs/sam/segmenting
- https://dev.meta.ai/docs/models

## Dasar
- Base URL: `https://api.meta.ai/v1`
- Auth: `Authorization: Bearer $META_MODEL_API_KEY`
- Kunci disimpan di `.env` (`META_MODEL_API_KEY=...`). **Jangan pernah dicetak, di-log, atau di-commit.**
- API kompatibel dengan OpenAI SDK (`/chat/completions`, `/responses`) dan format Anthropic Messages (`/messages`). Empu memakai `/responses` karena itulah yang terbukti untuk video.

## Terverifikasi

### Unggah file
```http
POST /v1/files
Content-Type: multipart/form-data
file=@segment.mp4 (video/mp4)
purpose=user_data
```
Respons: `{"id": "<file_id>", ...}`. Timeout yang dipakai: 600 detik. Ukuran klip uji 7–17 MB (480p, 2–5 menit).

### Analisis video
```json
POST /v1/responses
{
  "model": "muse-spark-1.3",
  "max_output_tokens": 16000,
  "input": [{
    "role": "user",
    "content": [
      {"type": "input_video", "file_id": "<file_id>"},
      {"type": "input_text", "text": "<prompt>"}
    ]
  }]
}
```
- Timeout yang dipakai: 900 detik. Latensi nyata 33–42 detik untuk klip 2–5 menit.
- Bentuk respons: objek `response` dengan `status`, `output[]`, dan `usage`. Item `output` bisa bertipe `reasoning` dan `message`. Teks jawaban ada di `content[].type == "output_text"`. Ambil `output_text` di tingkat atas kalau ada, kalau tidak gabungkan dari `output[]` (lihat fungsi `output_text()` di skrip uji).
- `usage`: `input_tokens`, `output_tokens`, `output_tokens_details.reasoning_tokens`. Simpan per panggilan.
- Biaya token: sekitar **274 token input per detik video** pada 480p.
- Jawaban kadang dibungkus pagar ```` ```json ````. Bersihkan dulu, lalu ambil objek `{...}` terluar.

### Fallback yang sudah ada di skrip uji
Kalau `input_video` dengan `file_id` gagal, coba `{"type": "input_file", "file_id": ...}`. Kalau unggah gagal, kirim `{"type": "input_video", "video_url": "data:video/mp4;base64,..."}`. Di v1, jalur utama berhasil.

## Terverifikasi di Gate 0 (28 Okt), detail di `hasil-gate0.md`
- **Audio:** Muse memakai audio. Tanpa audio, istilah `speech` turun dari 7 ke 0 pada video tanpa subtitle tertanam. Waktu bisa bergeser 14–23 s pada segmen yang diawali jeda musik → Mode B (faster-whisper sebagai jangkar waktu).
- **Structured output:** `"text": {"format": {"type": "json_schema", "name": "empu_terms", "schema": <muse-output.schema.json penuh>, "strict": true}}` diterima, keluaran lolos validasi skema. Tanpa structured output, Muse kadang menyalin skema dari prompt sebelum jawaban; parser harus mengambil objek pertama yang `terms`-nya list.
- **SAM 3.1:** `POST /responses`, `{"model": "sam-3.1", "stream": false, "input": [{"role": "user", "content": [{"type": "input_text", "text": "<frasa Inggris>"}, {"type": "input_image", "image_url": "data:image/jpeg;base64,..."}]}]}`. Keluaran teks: `<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;x=..;y=..;data=...|>` per instance (piksel terhadap `w`×`h`). Mask berencoding khusus, belum dipecahkan; Empu memakai bbox saja. Istilah lokal ("canting") tidak dikenali; deskripsi Inggris ("wooden stick with copper tip") berhasil. Token 0, `usage.images_processed` = 1.
- **Transkripsi Meta:** `muse-voice-transcribe-1.0` muncul di `GET /models`, tetapi `/audio/transcriptions` → 404 dan `/responses` → `model_not_found`. Pakai faster-whisper lokal.
- **Daftar model** (`GET /models`): muse-image-1.0, muse-spark-1.1, muse-spark-1.2(-contributor), muse-spark-1.3(-contributor), muse-voice-transcribe-1.0, muse-wonder-1.0, sam-3.1.

## Belum terverifikasi (catatan awal sebelum Gate 0, dipertahankan untuk riwayat)

| Hal | Status | Cara cek |
|---|---|---|
| Muse memakai **audio** dari video | Bertentangan: halaman model tidak menyebut audio, tetapi hasil uji menunjukkan transkrip ucapan | Klip yang sama dengan audio dan tanpa audio (`ffmpeg -an`), lalu bandingkan istilah `speech` |
| **Structured output** | Disebut didukung untuk Muse Spark, tapi bentuk parameternya di `/responses` belum dicoba | Kirim `"text": {"format": {"type": "json_schema", "name": "empu_terms", "schema": <muse-output.schema.json>, "strict": true}}`. Kalau ditolak, parse teks dan validasi dengan Pydantic |
| **SAM 3.1** | Model id `sam-3.1`. Menurut ringkasan sekunder, aksesnya lewat Responses API, input teks pendek ("canting"), dan keluarannya semua instance yang cocok dengan bbox dan mask. Video di-stream per frame. Format request, encoding mask, dan batasnya belum diketahui | Baca `dev.meta.ai/docs/sam/segmenting`, lalu kirim 1 keyframe dengan prompt "canting" dan simpan respons mentahnya sebagai fixture |
| **Muse Voice Transcribe** (untuk Mode B) | Disebut ada di daftar model, tapi model id dan apakah ada timestamp per kata belum diketahui | Cek di `/docs/models`. Fallback: faster-whisper lokal |
| **Muse Wonder** | Id `muse-wonder-1.0` menurut listing gateway pihak ketiga | Hanya untuk ablasi stretch |

## Harga (menurut listing gateway pihak ketiga, belum dicek di halaman resmi)
| Model | Input / 1 juta token | Output / 1 juta token |
|---|---|---|
| `muse-spark-1.3` | USD 1,25 | USD 4,25 |
| `muse-wonder-1.0` | USD 4,00 | USD 20,00 |

Perkiraan: video 5 menit sekitar 82 ribu token input ditambah sekitar 5 ribu token output per putaran, kira-kira USD 0,12. Harga SAM belum diketahui.

## Panduan implementasi `meta_client.py`
- Fungsi:
  - `upload_file(path) -> file_id`
  - `analyze_video(file_id, prompt, schema=None) -> (parsed: dict, raw: dict, usage: dict, latency_s: float)`
  - `segment_image(image_path, prompts: list[str]) -> list[Detection]`, dengan `Detection = {label, score, bbox_xyxy, mask_png_bytes | None}`
  - `transcribe(audio_path) -> list[Segment]` (Mode B)
- Retry dengan backoff eksponensial untuk 429 dan 5xx, maksimal 4 kali (`tenacity`). Jangan retry untuk 4xx lain.
- Cache respons mentah di `data/cache/muse/<sha256(segment)+model+prompt_version+mode>.json`. Kalau cache ada, jangan panggil API.
- Simpan `usage` dan latensi ke tabel `chunk` atau `job`.
- Tes unit **tidak boleh** memanggil API sungguhan. Pakai fixture dari `docs/reference/uji-kelayakan/hasil-v1/` dan dari respons mentah spike Gate 0.
- Satu-satunya tempat yang membaca `META_MODEL_API_KEY` adalah `config.py`.
