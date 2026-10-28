"""Muse analysis prompt (docs/reference/prompt-analisis.md).

Any change to TEMPLATE, SEED_BLOCK, TRANSCRIPT_BLOCK or analyze.RETRY_SUFFIX must bump the
version constants: they are part of the cache key and of every evaluation result.
"""

from __future__ import annotations

import json

from empu.meta_client import TranscriptSegment
from empu.muse_schema import load_json_schema
from empu.packs import CraftPack

PROMPT_VERSION = "analyze-v3"
NOSEED_VERSION = "analyze-v3-noseed"
ASR_VERSION = "analyze-v3-asr"

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

TRANSCRIPT_BLOCK = """TRANSKRIP OTOMATIS (dengan timestamp, dari awal segmen)
Transkrip ini dibuat mesin pengenal suara umum dan SERING SALAH menulis istilah keahlian
(contoh: {examples}).
Pakai timestamp-nya sebagai jangkar waktu, lalu perbaiki ejaan istilah berdasarkan apa yang
kamu dengar dan lihat di video.
{lines}

"""


def prompt_version_for(seeds: bool, *, transcript: bool = False) -> str:
    base = ASR_VERSION if transcript else PROMPT_VERSION
    if seeds:
        return base
    return NOSEED_VERSION if not transcript else f"{ASR_VERSION}-noseed"


def _variants(label: str, variants: list[str]) -> str:
    rest = [v for v in variants if v.casefold() != label.casefold()]
    return f" (varian: {', '.join(rest)})" if rest else ""


def _transcript_block(pack: CraftPack, transcript: list[TranscriptSegment]) -> str:
    examples = ", ".join(f'"{e.correct}" ditulis "{e.heard}"' for e in pack.asr_error_examples)
    lines = "\n".join(f"[{s.t_start:.1f}–{s.t_end:.1f}] {s.text.strip()}" for s in transcript)
    return TRANSCRIPT_BLOCK.format(examples=examples, lines=lines)


def build_prompt(pack: CraftPack, *, seg_index: int, seg_total: int, seg_duration: float,
                 seeds: bool = True, transcript: list[TranscriptSegment] | None = None) -> str:
    stages = "\n".join(f"- {s.id} — {s.label.id}{_variants(s.id, s.variants)}" for s in pack.stages)
    seed_block = ""
    if seeds:
        seed_block = SEED_BLOCK.format(
            seeds="\n".join(f"- {t.label}{_variants(t.label, t.variants)}" for t in pack.terms))
    return TEMPLATE.format(
        pack_name=pack.name.id,
        seg_index=seg_index,
        seg_total=seg_total,
        seg_duration=round(seg_duration),
        prompt_context=pack.prompt_context.strip(),
        stages=stages,
        seed_block=seed_block,
        transcript_block=_transcript_block(pack, transcript) if transcript else "",
        schema=json.dumps(load_json_schema(), ensure_ascii=False),
    )
