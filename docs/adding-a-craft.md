# Menambah craft baru

Empu menyimpan seluruh pengetahuan keahlian di `packs/*.yaml`, bukan di kode. Untuk menambah
arsip keahlian baru (tenun, gamelan, songket, …), ikuti langkah berikut.

## 1. Buat craft pack

Salin struktur dari `packs/batik_tulis.yaml` menjadi `packs/<id>.yaml`, mis. `packs/gamelan.yaml`.

Struktur minimal:

```yaml
id: gamelan
version: 0.1.0
name:
  id: Gamelan            # nama tampilan (Bahasa Indonesia)
  en: Javanese gamelan   # nama tampilan (Inggris)
languages: [id, jv]      # bahasa yang dipakai narasumber
prompt_context: >
  Satu-dua paragraf konteks keahlian. Disisipkan ke prompt Muse agar analisis lebih akurat.

asr_error_examples: []   # opsional; contoh salah tulis ASR untuk prompt Mode B

stages:
  - id: penyiapan
    label: {id: Menyiapkan instrumen, en: Preparing the instruments}
    variants: [menyiapkan, menyetem, laras]

terms:
  - id: saron
    label: saron
    category: tool
    variants: [saron, saron barung, demung]
    stage: tabuhan            # opsional; harus merujuk id stage yang ada
    gloss_id: alat pukul perunggu berbilah
    gloss_en: bronze metallophone
    visual: true              # jika bisa dipotong SAM 3.1
    sam_prompt: bronze metallophone with wooden bars
    verified: false
```

### Kategori yang valid
`tool | tool_part | material | dye | stage | technique | motif | other`

### Aturan validasi (dicek otomatis oleh `api/empu/packs.py` dan `tests/test_packs.py`)
- `id` unik antar-term dan antar-stage.
- Satu `variant` tidak boleh dipakai dua kali (antar-istilah maupun antara istilah dan tahap).
- `stage` pada term harus merujuk `id` stage yang ada.
- `visual: true` wajib punya `sam_prompt` (deskripsi Inggris, pendek).

## 2. Buat archive yang menunjuk ke pack

Archive adalah wadah rekaman + entri, terhubung ke satu `craft_pack_id`.

**Via UI Studio** (`/studio/upload`, butuh studio key): jika belum ada arsip, form "Create archive"
meminta *slug*, *title*, dan *craft pack*.

**Via API**:
```bash
curl -X POST http://127.0.0.1:8000/api/archives \
  -H "Content-Type: application/json" \
  -H "X-Studio-Key: <STUDIO_KEY>" \
  -d '{"slug":"gamelan","title":"Living Archive · Gamelan","craft_pack_id":"gamelan"}'
```

**Via CLI** (langsung bikin arsip + ingest video):
```bash
cd api && uv run empu ingest <video.mp4> \
  --archive gamelan --archive-title "Living Archive · Gamelan" \
  --pack gamelan --contributor "Nama Maestro" --consent-confirmed
```

## 3. Unggah, verifikasi, dan buka arsip

1. Unggah rekaman ke arsip baru via `/studio/upload`.
2. Verifikasi entri di `/studio/recordings/<id>` (Accept / Edit / Reject).
3. Arsip publik muncul di `/d/<slug>` (mis. `/d/gamelan`).

## Catatan

- **Jangan** menaruh file template `.yaml` selain pack asli di `packs/` — `list_packs()` akan
  meng-glob semua `*.yaml` dan mencoba memuatnya sebagai pack.
- Nama craft di frontend diambil dari `GET /api/packs/{id}` → `name.id` dan `version`.