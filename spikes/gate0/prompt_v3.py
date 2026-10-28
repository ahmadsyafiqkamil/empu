"""Prompt analyze-v3 (docs/reference/prompt-analisis.md), built from the craft pack."""

from __future__ import annotations

import json

import yaml

from common import PACK_PATH, SCHEMA_PATH

TEMPLATE = """Kamu membantu mendokumentasikan pengetahuan seorang ahli {pack_name}.
Video ini adalah segmen {seg_index}/{seg_total} dari sebuah rekaman, berdurasi {seg_duration} detik.
Semua waktu dihitung dalam detik dari AWAL SEGMEN INI.

KONTEKS KETERAMPILAN
{prompt_context}

KERANGKA TAHAPAN (urutan umum, rekaman nyata bisa berbeda):
{stages}

{seed_block}{transcript_block}TUGAS
Tonton DAN dengarkan segmen ini sampai detik terakhir.
1. Catat setiap istilah keahlian (alat, bagian alat, bahan, pewarna, tahap, teknik, motif).
   Untuk setiap istilah, tentukan sumbernya dengan tegas:
   - "speech": terdengar diucapkan di audio.
   - "on_screen_text": hanya terbaca sebagai tulisan di layar (judul, diagram, subtitle tertanam).
   - "visual_only": bendanya terlihat, tapi tidak diucapkan dan tidak tertulis.
   Kalau sebuah istilah diucapkan DAN tertulis, pakai "speech" dengan waktu saat diucapkan.
   Kalau istilah yang sama diucapkan berulang dalam 5 detik, cukup laporkan sekali.
2. Beri waktu mulai dan selesai ucapan (t_start, t_end).
3. Untuk "speech", tulis kalimat yang diucapkan di sekitar istilah itu di evidence_quote.
4. Jelaskan apa yang TERLIHAT saat itu (visible), apakah cocok dengan istilahnya (visual_match),
   dan tulis frasa benda pendek dalam bahasa Inggris (visible_object_en) kalau ada benda yang relevan.
5. Beri arti singkat dalam bahasa Indonesia (gloss_id) dan Inggris (gloss_en).
   Kalau tidak yakin artinya, katakan begitu dan turunkan confidence.
6. Susun urutan tahapan proses yang terlihat di segmen ini (process_steps).

Jangan mengarang. Kalau segmen hanya berisi musik atau tidak ada ucapan, speech_heard = false
dan jangan laporkan istilah "speech".

Jawab HANYA dengan JSON valid sesuai skema berikut, tanpa teks lain:
{schema}
"""

SEED_BLOCK = """CONTOH ISTILAH YANG MUNGKIN MUNCUL
Ini hanya contoh, BUKAN daftar yang harus ditemukan. Jangan laporkan istilah dari daftar ini
kalau tidak benar-benar diucapkan, tertulis, atau terlihat di segmen ini.
Istilah di luar daftar justru sangat penting, terutama istilah bahasa Jawa atau istilah lokal: laporkan juga.
{seeds}

"""


def _variants(label: str, variants: list[str]) -> str:
    rest = [v for v in variants if v.casefold() != label.casefold()]
    return f" (varian: {', '.join(rest)})" if rest else ""


def build(seg_index: int, seg_total: int, seg_duration: float, *, seeds: bool = True) -> str:
    pack = yaml.safe_load(PACK_PATH.read_text())
    schema = json.loads(SCHEMA_PATH.read_text())
    stages = "\n".join(
        f"- {s['id']} — {s['label']['id']}{_variants(s['id'], s.get('variants', []))}"
        for s in pack["stages"]
    )
    seed_block = ""
    if seeds:
        lines = "\n".join(
            f"- {t['label']}{_variants(t['label'], t.get('variants', []))}" for t in pack["terms"]
        )
        seed_block = SEED_BLOCK.format(seeds=lines)
    return TEMPLATE.format(
        pack_name=pack["name"]["id"],
        seg_index=seg_index,
        seg_total=seg_total,
        seg_duration=round(seg_duration),
        prompt_context=pack["prompt_context"].strip(),
        stages=stages,
        seed_block=seed_block,
        transcript_block="",
        schema=json.dumps(schema, ensure_ascii=False),
    )


if __name__ == "__main__":
    text = build(1, 4, 75)
    print(text)
    print(f"\n--- {len(text)} chars")
