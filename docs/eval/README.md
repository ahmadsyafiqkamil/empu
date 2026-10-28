# Evaluasi Empu

Rencana lengkap ada di spec bagian 14. Folder ini berisi bahan uji dan format kunci jawaban.

- `test-set.yaml`: daftar klip uji. YouTube hanya untuk internal; rekaman sendiri adalah set utama.
- `kunci-jawaban-template.csv`: format kunci jawaban. Tiga baris di dalamnya **hanya contoh** (`annotator=contoh`) dan tidak boleh dipakai sebagai kunci sungguhan.
- `kunci-jawaban/<clip_id>.csv`: kunci per klip (belum dibuat).

## Format kunci jawaban
Satu baris per **penyebutan**, bukan per istilah unik.

| Kolom | Isi |
|---|---|
| `clip_id` | Sama dengan `id` di `test-set.yaml` |
| `t_start`, `t_end` | Detik dari awal klip (bukan dari awal video YouTube) |
| `spoken` | Bentuk persis yang diucapkan atau tertulis |
| `term` | Bentuk baku. Pakai `id` atau `label` dari craft pack kalau ada, atau tulis istilah baru apa adanya |
| `category` | `tool`, `tool_part`, `material`, `dye`, `stage`, `technique`, `motif`, atau `other` |
| `source` | `speech`, `on_screen_text`, atau `visual_only` |
| `stage` | id tahap dari pack, boleh kosong |
| `visible_object` | Benda yang terlihat, untuk menilai potongan SAM |
| `note` | Catatan bebas |
| `annotator` | Siapa yang membuat dan mengoreksi baris ini |

## Cara membuat kunci dengan cepat
1. Draf otomatis dari subtitle dan hasil Muse (`empu eval draft-gold <clip_id>`).
2. Tonton klipnya dan koreksi setiap baris. Tambahkan yang terlewat dan hapus yang salah.
3. Catat nama annotator dan lama waktu mengoreksi. Waktu ini juga dipakai untuk metrik "waktu yang dihemat".
