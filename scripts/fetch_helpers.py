#!/usr/bin/env python3
import json, os, sys, time, urllib.request, datetime

def http_get_json(url, timeout=30, tries=3, sleep_base=1.0):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(sleep_base * (i + 1))
    if last:
        raise last

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
