# Hasil Gate 0 (28 Okt 2026)

Skrip: `spikes/gate0/`. Respons mentah terpilih: `docs/reference/uji-kelayakan/hasil-gate0/`.
Hasil uji sebelumnya dari sesi lain (prompt v2, klip utuh, SAM awal): `docs/reference/uji-kelayakan/hasil/`.
Prompt: analyze-v3 (keputusan D2), dibangun dari `docs/packs/batik_tulis.yaml` v0.1.0. Model `muse-spark-1.3`.

## Ringkasan keputusan

| Butir | Hasil | Keputusan | Env |
|---|---|---|---|
| 0.1 Audio | #NgertiBatik 80–155 s: **7 istilah `speech` dengan audio, 0 tanpa audio**; tanpa audio `speech_heard=false`, transkrip "[musik, tanpa ucapan]" (kemiripan transkrip 0,09) | **Lulus.** Muse benar-benar mendengar | – |
| 0.2 Recall | **4/8** dengan aturan ketat (\|Δt\| ≤ 5 s). Secara isi **7/8** tertangkap sebagai `speech` dengan kutipan yang benar; HCl, waterglass, nglorod meleset 18–23 s karena waktu di segmen 130–205 s bergeser | **Gagal menurut aturan gate → Mode B default.** Masalahnya waktu, bukan pendengaran | `EMPU_PIPELINE_MODE=B` |
| 0.3 SAM | Canting di 3 close-up: 3/3 benar. Deretan 4 canting: 4/4 dengan "wooden stick with copper tip". Istilah "canting" sendiri: kosong | **Lulus.** Prompt harus deskripsi Inggris; pakai bbox saja (keputusan 28 Okt) | `EMPU_SAM_ENABLED=true`, `SAM_MODEL=sam-3.1` |
| 0.4 Structured | `text.format` json_schema dengan **skema v3 penuh**: 200, JSON valid, lolos validasi skema | **Didukung, skema penuh** | `EMPU_STRUCTURED_OUTPUT=true`, `EMPU_STRUCTURED_SCHEMA_VARIANT=full` |
| Transkripsi Meta | `muse-voice-transcribe-1.0` ada di `GET /models`, tetapi `/audio/transcriptions` → 404 dan `/responses` → `model_not_found` | Mode B memakai **faster-whisper lokal** | `EMPU_TRANSCRIBE_BACKEND=whisper` |
| Model lain | `/models`: muse-image-1.0, muse-spark-1.1/1.2/1.3 (+contributor), muse-wonder-1.0, sam-3.1 | Muse Wonder tersedia untuk ablasi stretch | – |

## 0.1 Audio (diulang)
Uji pertama pada klip *nglowong* (sesi lain) **tidak sah**: video itu punya subtitle karaoke tertanam, sehingga tanpa audio Muse tetap "membaca" perkenalan presenter dari layar (13 → 4 istilah `speech`, transkrip hampir sama). Diulang pada #NgertiBatik detik 80–155 (narasi, hampir tanpa teks di layar):

| | Dengan audio | Tanpa audio |
|---|---|---|
| `speech_heard` | true | **false** |
| Istilah `speech` | 7 (persiapan_kain @83, memola @87, malam @112, koran @117, spangkring @121, nglowong @127, pewarnaan @143) | **0** |
| Istilah lain | 5 `visual_only` | 1 `on_screen_text`, 9 `visual_only` |

Waktu di jendela ini tepat terhadap subtitle (memola 85–87, malam 109, spangkring 122/126, pewarnaan 145).

**Catatan untuk label sumber:** di klip *nglowong*, tanpa audio Muse tetap memberi label `speech` pada 4 istilah yang sebenarnya dibaca dari subtitle tertanam. Label `speech` tidak bisa dipercaya penuh kalau ada teks ucapan di layar. Ini disebut jujur di halaman Bukti.

## 0.2 Recall (prompt v3, segmen 75 s, overlap 10 s)

| # | Kunci (detik) | Muse | Waktu Muse | Status |
|---|---|---|---|---|
| 1 | pola (85–87) | memola, `speech` | 87,0 | ✓ |
| 2 | lilin malam (109) | malam, `speech` | 111,0 | ✓ |
| 3 | spangkring (122) | spangkring, `speech` | 123,0 | ✓ (subtitle YouTube: "spang King") |
| 4 | membatik (126–128) | – (hanya `on_screen_text`/`visual_only`) | – | ✗ |
| 5 | mewarna (145–149) | cocok lewat varian "warna" (fiksasi @143,5); pewarnaan `speech` @132 | 143,5 | ✓ secara aturan, perlu dicek ulang di kunci jawaban resmi |
| 6 | HCl (155) | HCl, `speech`, kutipan benar | 137,0 | ✗ waktu (Δ 18 s) |
| 7 | waterglass (162–165) | waterglass, `speech`, kutipan benar | 142,0 | ✗ waktu (Δ 20 s). Subtitle YouTube: "watera gelas" |
| 8 | nglorod (173) | nglorod ("nglorot"), `speech`, kutipan benar | 150,0 | ✗ waktu (Δ 23 s) |

- Median Δt untuk yang cocok: 1,2 s. `speech` sebelum detik 80 (diagram di layar): **0**. Ini perbaikan dari v1, di mana istilah dari diagram dilabeli ucapan.
- Sebaran sumber 4 segmen: 14 `speech`, 20 `on_screen_text`, 10 `visual_only`.
- **Diagnosis pergeseran waktu:** segmen 2 (130–205 s) diawali jeda musik 13 detik (132–145 s). Muse menaruh ucapan pertama di +2 s dan memampatkan sisanya, sehingga semua waktu di segmen itu terlalu awal 14–23 s. Di jendela 80–155 s (uji audio) waktu yang sama tepat. Jadi pergeseran muncul pada segmen yang diawali bagian tanpa ucapan.

### Implikasi
- Gate menyatakan Mode B default. Bentuk Mode B yang paling murah: **transkrip faster-whisper dengan timestamp per kata sebagai jangkar waktu**. Dua cara, diputuskan di H2: (a) transkrip disisipkan ke prompt (spec 8.4, prompt sudah siap di H1-8), atau (b) Muse tetap Mode A, lalu `evidence_quote` tiap istilah dicocokkan (fuzzy) ke transkrip ber-timestamp untuk mengoreksi `t_start`/`t_end`. Cara (b) tidak mengubah prompt maupun cache, dan cocok dengan temuan bahwa kutipan Muse akurat.
- Mode A tetap dijalankan sebagai pembanding di ablasi H5.

## 0.3 SAM 3.1

Request yang terbukti (`spikes/gate0/probe_sam.py`):
```json
POST /v1/responses
{"model": "sam-3.1", "stream": false, "input": [{"role": "user", "content": [
  {"type": "input_text", "text": "wooden stick with copper tip"},
  {"type": "input_image", "image_url": "data:image/jpeg;base64,<...>"}]}]}
```
Respons: `status: completed`, `usage.images_processed: 1`, token 0. Teks keluaran (`output[].content[].text`) berisi satu pasang token per instance:
```text
<|box;x1=702;y1=203;x2=853;y2=290;w=854;h=480|><|mask;x=0;y=0;data=88,152,~!!!5`...|>
```
`x1..y2` dalam piksel terhadap `w`×`h` (ukuran gambar yang dikirim). Mask memakai encoding khusus yang belum diketahui; **diputuskan memakai bbox saja** untuk crop (bbox + padding 15%) dan overlay (garis kotak). Pecahkan mask = stretch.

| Frame | Prompt | Kotak | Benar? |
|---|---|---|---|
| Close-up canting (Tholo Thili, 50 s) | pen with wooden handle | 1 | ya |
| Close-up canting (100 s) | wooden stick with copper tip | 1 | ya |
| Close-up canting (125 s) | pen with wooden handle | 1 | ya |
| Deretan 4 canting (keyframe *nglowong*) | wooden stick with copper tip | 4 | ya, keempatnya |
| Deretan 4 canting | pen with wooden handle (uji sesi lain) | 1 | ya, 1 dari 4 |
| Sama | canting / copper pen tool / wax pen / small copper cup on a wooden stick | 0 | – |
| Kain (keyframe *nglowong*) | cloth (uji sesi lain) | 1 | ya |
| "Wajan" #NgertiBatik 100 s | small black wok / small stove | 0 | **uji tidak sah**: frame itu berisi sketsa pensil, bukan wajan |

### Implikasi untuk pack dan pipeline
- `sam_prompt` di pack harus deskripsi visual dalam bahasa Inggris, **tanpa** istilah lokal. Untuk keempat jenis canting: `wooden stick with copper tip, pen with wooden handle`. Pipeline mencoba prompt berurutan dan berhenti pada prompt pertama yang menghasilkan kotak.
- Prompt alat lain (wajan, kompor, gawangan, spangkring) belum teruji. Uji pada keyframe nyata dari video demo di H2.

## 0.4 Structured output
`text.format = {"type": "json_schema", "name": "empu_terms", "schema": <muse-output.schema.json penuh>, "strict": true}` diterima. Keluaran adalah JSON murni dan lolos validasi skema. Uji sesi lain dengan skema sederhana juga diterima.

**Temuan terkait:** tanpa structured output, di satu segmen Muse **menyalin skema JSON dari prompt** dulu, baru memberi jawabannya, dalam satu teks. Parser "ambil dari `{` pertama sampai `}` terakhir" gagal. Dua akibat untuk H1:
1. Pakai structured output (`EMPU_STRUCTURED_OUTPUT=true`).
2. `extract_json` tetap harus tahan banting: ambil objek JSON pertama yang lengkap dengan `terms` berupa list (pakai `json.JSONDecoder.raw_decode`), bukan potongan dari `{` pertama sampai `}` terakhir.

## Implikasi untuk klaim ke juri
- **Boleh:** "Subtitle otomatis YouTube menulis 'spang King'; Empu menangkap *spangkring* sebagai ucapan di waktu yang benar" (@123 s, ucapan 122–126 s).
- **Belum:** klaim yang sama untuk *waterglass* ("watera gelas"). Istilah dan kutipannya benar, tetapi waktunya baru tepat setelah koreksi Mode B. Pakai hanya setelah Mode B diuji.
- **Boleh:** "Tanpa audio, Muse tidak melaporkan satu pun istilah ucapan" (0 dari 7, pada video tanpa subtitle tertanam).
- **Boleh:** "Klip yang hanya berisi musik menghasilkan 0 istilah ucapan" (v1 dan v2).
- **Jangan dulu:** angka recall tunggal. Laporkan recall isi (7/8) dan recall dengan waktu (4/8) berdampingan, sampai kunci jawaban resmi H5 ada.

## Biaya dan latensi (perkiraan)
Sekitar 7 panggilan Muse yang berbayar (4 recall, 2 audio, 1 structured; 2 percobaan transkripsi ditolak tanpa biaya) dan 13 panggilan SAM (0 token). Latensi Muse per segmen 75 s sekitar 25–45 s. Total di bawah USD 0,20.

## Catatan H1
(diisi saat H1-10)
