# scripts/fetch_helpers.py
import json, os, time, tempfile, shutil, sys
from urllib.parse import urlencode
import urllib.request

def http_get_json(url, retries=3, timeout=20):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gh-actions/football"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")

def read_json(path):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json_atomic(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmpfd, tmppath = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=os.path.dirname(path))
    with os.fdopen(tmpfd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    shutil.move(tmppath, path)

def now_ms():
    return int(time.time() * 1000)

def qs(base, **params):
    return f"{base}?{urlencode(params)}"
