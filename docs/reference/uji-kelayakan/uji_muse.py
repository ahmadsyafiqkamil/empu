"""Uji kelayakan Empu / Gate 0: apakah Muse (video+audio native) bisa menangkap
istilah batik yang diucapkan, kapan, dan apa yang terlihat saat itu.

Langkah: pakai klip yang sudah dipotong (atau potong baru) -> unggah ke Files API
-> Responses API (input_video) -> simpan JSON -> nilai terhadap subtitle YouTube
(.vtt) sebagai kunci kasar. Hanya untuk uji internal. Kunci API dibaca dari
.env di root repo, tidak dicetak.

Mode tambahan (env var):
  AUDIO_TEST=1   -> Gate 0 #1: bandingkan klip nglowong dengan vs tanpa audio
  STRUCTURED=1   -> Gate 0 #4: coba text.format json_schema pada klip nglowong
"""
import base64, json, os, re, subprocess, sys, time
from pathlib import Path
import httpx

HERE = Path(__file__).resolve().parent          # docs/reference/uji-kelayakan/
EMPU_ROOT = HERE.parents[2]                      # Empu/
MEDIA_ROOT = EMPU_ROOT / "arsip-hidup-batik"     # video mentah + klip v1 (gitignored)
PRECUT_KLIP = MEDIA_ROOT / "uji" / "klip"        # klip 480p yang sudah ada dari uji v1
BASE = "https://api.meta.ai/v1"
MODEL = os.environ.get("MODEL", "muse-spark-1.3")
OUT = HERE / "hasil" / os.environ.get("RUN", f"{MODEL}-v2")
CLIPS = HERE / "klip"

# label skrip -> nama file klip precut (beda penamaan karena skrip lama berbeda)
PRECUT_NAME = {
    "proses-lengkap-ngertibatik": "proses-lengkap-ngertibatik.mp4",
    "nglowong": "nglowong.mp4",
    "kontrol-musik-nglorod": "kontrol-musik-nglorod.mp4",
    "maestro-trusmi-menit15-20": "maestro-trusmi-5menit.mp4",
}

# (id youtube, mulai detik, durasi detik, label)
TEST_SET = [
    ("7-WQ3DKKn0w", 0, 241, "proses-lengkap-ngertibatik"),
    ("rKVEysItoKY", 0, 132, "nglowong"),
    ("J_XcGhkCRAQ", 0, 227, "kontrol-musik-nglorod"),  # video ini hanya musik: Muse seharusnya TIDAK mengarang istilah
    ("8sMSLQPYNc4", 900, 300, "maestro-trusmi-menit15-20"),
]
AMBIGU = {"malam", "cap", "mal", "kapur", "kompor", "kuas", "motif", "pola", "jemur"}

PROMPT = """Kamu membantu mendokumentasikan pengetahuan pengrajin batik tulis.
Tonton DAN dengarkan video ini. Tugasmu:
1. Catat setiap istilah teknis batik (alat, bahan, tahap, teknik, motif) yang DIUCAPKAN
   di audio, termasuk istilah bahasa Jawa/daerah. Jangan mengarang istilah yang tidak diucapkan.
   Catat juga istilah yang hanya muncul sebagai TULISAN di layar, tapi tandai sumbernya.
   Bedakan dengan tegas: "ucapan" = terdengar di audio; "teks_layar" = hanya terbaca di layar;
   "visual" = hanya terlihat bendanya, tidak diucapkan dan tidak tertulis. Periksa seluruh durasi
   video sampai akhir, jangan berhenti di bagian awal.
2. Untuk tiap istilah beri waktu ucapan dalam detik dari awal video.
3. Jelaskan apa yang TERLIHAT di layar saat istilah itu diucapkan (alat/bahan/gerakan),
   dan apakah yang terlihat cocok dengan istilahnya.
Jawab HANYA JSON valid dengan bentuk:
{"speech_heard": true/false,
 "transcript_first_20s": "transkrip kasar 20 detik pertama",
 "terms": [{"spoken": "bentuk persis yang diucapkan/tertulis", "term": "bentuk baku", "source": "ucapan|teks_layar|visual",
            "t_start": 12.3, "t_end": 13.1, "stage": "tahap proses",
            "visible": "apa yang terlihat", "visual_match": "ya|tidak|tidak_terlihat",
            "gloss_id": "arti singkat bahasa Indonesia", "confidence": "rendah|sedang|tinggi"}],
 "process_steps": [{"step": "nama tahap", "t_start": 0, "t_end": 0, "tools": ["..."]}]}"""


def api_key() -> str:
    for line in (EMPU_ROOT / ".env").read_text().splitlines():
        if line.startswith("META_MODEL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("META_MODEL_API_KEY tidak ada di .env (root repo)")


def find_media(yt_id: str, ext: str) -> Path | None:
    hits = sorted(MEDIA_ROOT.rglob(f"*[[]{yt_id}[]]*{ext}"))
    return hits[0] if hits else None


def make_clip(src: Path, start: int, dur: int, label: str) -> Path:
    precut = PRECUT_KLIP / PRECUT_NAME.get(label, "")
    if precut.exists():
        return precut
    CLIPS.mkdir(exist_ok=True)
    dst = CLIPS / f"{label}.mp4"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-i", str(src),
                        "-t", str(dur), "-vf", "scale=-2:480", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-ac", "1",
                        "-b:a", "64k", str(dst)], check=True)
    return dst


def strip_audio(src: Path) -> Path:
    """Gate 0 #1: salinan klip tanpa audio untuk dibandingkan."""
    CLIPS.mkdir(exist_ok=True)
    dst = CLIPS / f"{src.stem}-noaudio.mp4"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                        "-an", "-c:v", "copy", str(dst)], check=True)
    return dst


def upload(client: httpx.Client, path: Path) -> str:
    with path.open("rb") as f:
        r = client.post(f"{BASE}/files", files={"file": (path.name, f, "video/mp4")},
                        data={"purpose": "user_data"}, timeout=600)
    r.raise_for_status()
    return r.json()["id"]


# Gate 0 #4: skema minimal yang cocok dengan bentuk PROMPT di atas (enum Indonesia),
# cukup untuk menguji apakah API menerima parameter ini, bukan skema produksi.
STRUCTURED_SCHEMA = {
    "type": "object",
    "properties": {
        "speech_heard": {"type": "boolean"},
        "transcript_first_20s": {"type": "string"},
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "spoken": {"type": "string"},
                    "term": {"type": "string"},
                    "source": {"type": "string", "enum": ["ucapan", "teks_layar", "visual"]},
                    "t_start": {"type": "number"},
                    "t_end": {"type": "number"},
                    "stage": {"type": "string"},
                    "visible": {"type": "string"},
                    "visual_match": {"type": "string", "enum": ["ya", "tidak", "tidak_terlihat"]},
                    "gloss_id": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["rendah", "sedang", "tinggi"]},
                },
                "required": ["spoken", "term", "source", "t_start", "t_end"],
            },
        },
        "process_steps": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["speech_heard", "terms"],
}


def ask(client: httpx.Client, video_part: dict, structured: bool = False) -> dict:
    body = {"model": MODEL, "max_output_tokens": 16000,
            "input": [{"role": "user", "content": [video_part,
                                                    {"type": "input_text", "text": PROMPT}]}]}
    if structured:
        body["text"] = {"format": {"type": "json_schema", "name": "empu_gate0_terms",
                                    "schema": STRUCTURED_SCHEMA, "strict": False}}
    r = client.post(f"{BASE}/responses", json=body, timeout=900)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:800]}")
    return r.json()


def upload_and_ask(client: httpx.Client, clip: Path, structured: bool = False) -> dict:
    """Unggah klip dan panggil Muse, dengan fallback input_file lalu data URL."""
    resp = None
    try:
        fid = upload(client, clip)
        print(f"   terunggah {fid}", flush=True)
        for part in ({"type": "input_video", "file_id": fid},
                     {"type": "input_file", "file_id": fid}):
            try:
                resp = ask(client, part, structured=structured); break
            except RuntimeError as e:
                print(f"   {part['type']} gagal: {e}", flush=True)
    except Exception as e:  # upload gagal -> coba data URL
        print(f"   upload gagal: {e}; coba data URL", flush=True)
    if resp is None:
        b64 = base64.b64encode(clip.read_bytes()).decode()
        resp = ask(client, {"type": "input_video", "video_url": f"data:video/mp4;base64,{b64}"},
                   structured=structured)
    return resp


def output_text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts = []
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts)


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    m = re.search(r"\{.*\}", text, flags=re.S)
    return json.loads(m.group(0)) if m else {}


def vtt_cues(path: Path, start: int, dur: int) -> list[tuple[float, str]]:
    cues, t = [], None
    for line in path.read_text(errors="ignore").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+) -->", line)
        if m:
            h, mi, s, ms = map(int, m.groups())
            t = h * 3600 + mi * 60 + s + ms / 1000
        elif t is not None and line.strip() and "-->" not in line:
            txt = re.sub(r"<[^>]+>", "", line).strip()
            if start <= t <= start + dur and txt:
                cues.append((t - start, txt.lower()))
    return cues


def term_ids(text: str, gloss: dict, skip_ambigu: bool) -> set[str]:
    found = set()
    low = f" {text.lower()} "
    for tid, variants in gloss.items():
        for v in variants:
            if skip_ambigu and v in AMBIGU:
                continue
            if re.search(rf"\b{re.escape(v)}", low):
                found.add(tid)
                break
    return found


def score(result: dict, cues, gloss) -> dict:
    gold_times: dict[str, list[float]] = {}
    for t, txt in cues:
        for tid in term_ids(txt, gloss, skip_ambigu=True):
            gold_times.setdefault(tid, []).append(t)
    muse_times: dict[str, list[float]] = {}
    novel = []
    for item in result.get("terms", []):
        if item.get("source", "ucapan") != "ucapan":
            continue  # hanya istilah yang benar-benar diucapkan dinilai terhadap subtitle
        text = f"{item.get('spoken','')} {item.get('term','')}"
        ids = term_ids(text, gloss, skip_ambigu=False)
        if not ids:
            novel.append(item.get("term") or item.get("spoken"))
        for tid in ids:
            try:
                muse_times.setdefault(tid, []).append(float(item.get("t_start", -1)))
            except (TypeError, ValueError):
                pass
    gold, muse = set(gold_times), set(muse_times)
    hit = gold & muse
    terr = []
    for tid in hit:
        terr.append(min(abs(a - b) for a in muse_times[tid] for b in gold_times[tid]))
    vm = [i.get("visual_match") for i in result.get("terms", [])]
    return {
        "gold_terms_from_subtitle": sorted(gold),
        "muse_terms_in_glossary": sorted(muse),
        "muse_novel_terms": [n for n in novel if n][:40],
        "recall": round(len(hit) / len(gold), 2) if gold else None,
        "precision_vs_subtitle": round(len(hit) / len(muse), 2) if muse else None,
        "median_time_error_s": round(sorted(terr)[len(terr) // 2], 1) if terr else None,
        "visual_match_counts": {k: vm.count(k) for k in set(vm)},
        "n_terms_muse": len(result.get("terms", [])),
        "source_counts": {k: [i.get("source") for i in result.get("terms", [])].count(k)
                          for k in ("ucapan", "teks_layar", "visual")},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gloss = json.loads((HERE / "glosarium.json").read_text())
    client = httpx.Client(headers={"Authorization": f"Bearer {api_key()}"})
    summary = []
    for yt_id, start, dur, label in TEST_SET:
        print(f"\n=== {label} ({MODEL})", flush=True)
        clip = PRECUT_KLIP / PRECUT_NAME.get(label, "")
        if not clip.exists():
            src = find_media(yt_id, ".mp4")
            if not src:
                print("   video tidak ditemukan, lewati"); continue
            clip = make_clip(src, start, dur, label)
        print(f"   klip {clip} ({clip.stat().st_size/1e6:.1f} MB)", flush=True)
        t0 = time.time()
        raw_path = OUT / f"{label}.raw.json"
        if raw_path.exists():
            resp = json.loads(raw_path.read_text())
        else:
            resp = upload_and_ask(client, clip)
            raw_path.write_text(json.dumps(resp, ensure_ascii=False, indent=1))
        result = parse_json(output_text(resp))
        (OUT / f"{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
        vtt = find_media(yt_id, ".id-orig.vtt") or find_media(yt_id, ".id.vtt")
        sc = score(result, vtt_cues(vtt, start, dur) if vtt else [], gloss)
        sc.update(label=label, seconds=round(time.time() - t0, 1),
                  speech_heard=result.get("speech_heard"),
                  transcript_first_20s=result.get("transcript_first_20s"),
                  usage=resp.get("usage"))
        summary.append(sc)
        print(json.dumps({k: sc[k] for k in ("recall", "precision_vs_subtitle",
              "median_time_error_s", "n_terms_muse", "speech_heard")}), flush=True)
    (OUT / "ringkasan.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"\nSelesai. Hasil di {OUT}")


def run_audio_test() -> None:
    """Gate 0 #1: klip nglowong dengan vs tanpa audio. Kalau n_terms(ucapan) sama
    banyaknya di kedua versi, Muse kemungkinan tidak benar-benar mendengar."""
    OUT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers={"Authorization": f"Bearer {api_key()}"})
    with_audio = PRECUT_KLIP / PRECUT_NAME["nglowong"]
    no_audio = strip_audio(with_audio)
    out = {}
    for tag, clip in (("with_audio", with_audio), ("no_audio", no_audio)):
        print(f"\n=== nglowong [{tag}]", flush=True)
        raw_path = OUT / f"audio-test-{tag}.raw.json"
        if raw_path.exists():
            resp = json.loads(raw_path.read_text())
        else:
            resp = upload_and_ask(client, clip)
            raw_path.write_text(json.dumps(resp, ensure_ascii=False, indent=1))
        result = parse_json(output_text(resp))
        speech_terms = [t for t in result.get("terms", []) if t.get("source") == "ucapan"]
        out[tag] = {"speech_heard": result.get("speech_heard"),
                    "transcript_first_20s": result.get("transcript_first_20s"),
                    "n_terms_total": len(result.get("terms", [])),
                    "n_terms_source_ucapan": len(speech_terms)}
        print(json.dumps(out[tag], ensure_ascii=False), flush=True)
    (OUT / "audio-test-ringkasan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    verdict = ("TIDAK MENDENGAR (Mode B wajib)"
               if out["with_audio"]["n_terms_source_ucapan"] <= out["no_audio"]["n_terms_source_ucapan"]
               else "MENDENGAR (Mode A boleh lanjut)")
    print(f"\nVerdict Gate 0 #1: {verdict}")


def run_structured_test() -> None:
    """Gate 0 #4: apakah API menerima text.format json_schema. Memakai klip
    nglowong (klip yang sudah pernah berhasil, murah dari segi durasi)."""
    OUT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers={"Authorization": f"Bearer {api_key()}"})
    clip = PRECUT_KLIP / PRECUT_NAME["nglowong"]
    print(f"\n=== structured output test ({clip.name})", flush=True)
    try:
        resp = upload_and_ask(client, clip, structured=True)
        (OUT / "structured-test.raw.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1))
        print("Verdict Gate 0 #4: DITERIMA (text.format json_schema diterima API)")
    except RuntimeError as e:
        (OUT / "structured-test.error.txt").write_text(str(e))
        print(f"Verdict Gate 0 #4: DITOLAK — {e}")


if __name__ == "__main__":
    if os.environ.get("AUDIO_TEST") == "1":
        run_audio_test()
    elif os.environ.get("STRUCTURED") == "1":
        run_structured_test()
    else:
        main()
