"""Gate 0 #3: uji kelayakan SAM 3.1 — kirim 1 keyframe + prompt teks pendek,
simpan respons mentahnya sebagai fixture. Format request/response SAM belum
diverifikasi sebelumnya (lihat docs/reference/meta-model-api.md), jadi ini
spike eksploratif, bukan parser produksi.

Kunci API dibaca dari .env di root repo, tidak dicetak.
"""
import base64, json, sys
from pathlib import Path
import httpx

HERE = Path(__file__).resolve().parent
EMPU_ROOT = HERE.parents[2]
BASE = "https://api.meta.ai/v1"
MODEL = "sam-3.1"
import os

OUT = HERE / "hasil" / "sam-3.1"
KEYFRAME = HERE / "klip" / "canting-keyframe.jpg"
# "canting" (istilah Jawa) kosong di percobaan pertama — SAM 3.1 kemungkinan
# cuma kenal kosakata Inggris. Fallback sesuai spec: deskripsi Inggris.
PROMPT = os.environ.get("SAM_PROMPT", "copper pen tool")


def api_key() -> str:
    for line in (EMPU_ROOT / ".env").read_text().splitlines():
        if line.startswith("META_MODEL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("META_MODEL_API_KEY tidak ada di .env (root repo)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    slug = PROMPT.replace(" ", "-")
    b64 = base64.b64encode(KEYFRAME.read_bytes()).decode()
    body = {
        "model": MODEL,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": PROMPT},
            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
        ]}],
        "stream": False,
    }
    client = httpx.Client(headers={"Authorization": f"Bearer {api_key()}"})
    print(f"=== SAM 3.1 test: prompt='{PROMPT}' keyframe={KEYFRAME.name}", flush=True)
    r = client.post(f"{BASE}/responses", json=body, timeout=180)
    (OUT / f"{slug}.status.txt").write_text(str(r.status_code))
    if r.status_code >= 400:
        (OUT / f"{slug}.error.txt").write_text(r.text[:4000])
        print(f"Verdict Gate 0 #3: GAGAL — HTTP {r.status_code}: {r.text[:500]}")
        return
    resp = r.json()
    (OUT / f"{slug}.raw.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1))
    text = resp.get("output_text") or ""
    if not text:
        for item in resp.get("output", []):
            for c in item.get("content", []) or []:
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    text += c["text"]
    (OUT / f"{slug}.output_text.txt").write_text(text)
    n_box = text.count("<|box;")
    n_mask = text.count("<|mask;")
    print(f"   {n_box} token box, {n_mask} token mask ditemukan di output")
    verdict = "OK (ada deteksi)" if n_box > 0 else "KOSONG (0 deteksi, cek prompt/fallback keyframe)"
    print(f"Verdict Gate 0 #3: {verdict}")


if __name__ == "__main__":
    main()
