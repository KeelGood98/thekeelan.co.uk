#!/usr/bin/env python3
import json
from pathlib import Path
import requests

OUT = Path("assets/steam_specials.json")
API = "https://store.steampowered.com/api/featuredcategories/?cc=GB"

def main():
    r = requests.get(API, timeout=30); r.raise_for_status()
    js = r.json()
    specials = (js.get("specials") or {}).get("items") or []
    out = []
    for it in specials:
        out.append({
            "title": it.get("name",""),
            "discount_percent": it.get("discount_percent",0),
            "final_price": round((it.get("final_price",0) or 0)/100,2),
            "header_image": it.get("header_image",""),
            "url": f"https://store.steampowered.com/app/{it.get('id')}"
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(out)} specials)")

if __name__=="__main__":
    main()
