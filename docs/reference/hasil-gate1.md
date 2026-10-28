# Hasil Gate 1 (30 Okt 2026)

| Butir | Hasil |
|---|---|
| CLI end-to-end (*Macam Canting*, 246 s, Mode B) | ready; entri 15 (baru 15); kemunculan 26; klip 26/26 |
| Worker end-to-end (*Proses nyanting*, 508 s, Mode B) | ready; waktu total 205,3 s (normalizing 53,1; chunking 15,9; analyzing 85,7; merging 0,0; grounding 11,3; cutting 39,3) |
| Penggabungan lintas rekaman | entri dengan kemunculan dari 2 rekaman: batik tulis, canting, malam, mori, nglowong (5) |
| SAM | ok/empty/error/skipped = 4/9/0/8; prompt yang diganti (pack 0.1.1): canting tembokan, cucuk, mori, malam |
| Mode B | `asr_retimed` 18 dari 18 kemunculan speech (rek. 1); rek. 2 tanpa retime (0); model whisper `small`, transkripsi ~53 s (normalizing rek. 2) |
| Biaya | token Muse (job awal): in 84359+176336, out 18658+28482; `cached_chunks` 0 pada ingest pertama (chunk hash ≠ cache H1); reprocess: 4+8 cache penuh, Muse 0 token; SAM dipanggil ulang hanya untuk prompt baru (~grounding 12,9 s + 3,5 s) |

## Keputusan
- Gate 1 **lulus** dengan catatan SAM: 9 entri `empty` (termasuk istilah novel `paruh` tanpa `sam_prompt` pack). SAM tetap aktif; UI fallback keyframe jika perlu di H5.

## Temuan untuk H3
- Ingest CC BY + atribusi otomatis dari `docs/eval/lisensi/*.json` lancar; kontributor default = channel (`documenter`).
- Worker + poll `empu status` cukup untuk demo; reprocess `--run` cepat saat Muse cache penuh.
- Pack 0.1.1: SAM canting tembokan/cucuk/mori/malam perlu verifikasi overlay di studio.
- `asr_retimed` hanya rek. 1 (Macam Canting); rek. 2 perlu dicek apakah speech cukup untuk retime di run berikutnya.
