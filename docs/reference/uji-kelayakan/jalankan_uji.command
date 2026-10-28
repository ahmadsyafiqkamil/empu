#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")"
PY="../../backend/.venv/bin/python"
"$PY" uji_muse.py 2>&1 | tee log-uji.txt
echo; echo "SELESAI. Jendela ini boleh ditutup."
