#!/usr/bin/env python3
import json, sys, os, re
import requests
from bs4 import BeautifulSoup

URL = "https://store.steampowered.com/search/?specials=1&supportedlang=english&l=english&cc=GB"
OUT = "assets/steam_specials.json"

def main():
    try:
        r = requests.get(URL, timeout=25, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("#search_resultsRows a")
        items = []
        for a in rows[:20]:
            title = a.select_one(".title")
            disc = a.select_one(".discount_pct")
            img = a.select_one("img")
            items.append({
                "title": title.get_text(strip=True) if title else "",
                "discount": disc.get_text(strip=True) if disc else "",
                "thumb": img["src"] if img and img.has_attr("src") else "",
                "url": a["href"]
            })

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT,"w",encoding="utf-8") as f:
            json.dump({"items":items}, f, ensure_ascii=False, indent=2)
        print(f"wrote {OUT}: {len(items)} items")
    except Exception as e:
        print(f"[update_extras] Non-fatal: {e}")
        sys.exit(0)

if __name__ == "__main__":
    main()
