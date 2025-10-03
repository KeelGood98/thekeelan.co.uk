#!/usr/bin/env python3
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("assets/table.json")
BBC_TABLE_URL = "https://www.bbc.co.uk/sport/football/premier-league/table"

def badge_from_name(name: str) -> str:
    special = {
        "Manchester United": "MU", "Manchester City": "MC", "Newcastle United": "NU",
        "Brighton & Hove Albion": "B&A", "Brighton and Hove Albion":"B&A",
        "AFC Bournemouth": "AB", "Nottingham Forest": "NF", "West Ham United": "WH",
        "Tottenham Hotspur": "TH", "Crystal Palace": "CP", "Sheffield United":"SU",
        "Wolverhampton Wanderers":"WW"
    }
    if name in special: return special[name]
    parts = re.split(r"\s+|&", name.strip())
    letters = [p[0].upper() for p in parts if p]
    return (letters[0]+(letters[1] if len(letters)>1 else "")) or "??"

def fetch_table():
    r = requests.get(BBC_TABLE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table: raise RuntimeError("BBC table not found")

    body = table.find("tbody")
    rows = body.find_all("tr") if body else table.find_all("tr")

    data=[]
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all(["th","td"])]
        if len(cols) < 10: continue
        try: pos = int(cols[0])
        except: continue
        team = cols[1]
        p,w,d,l,gf,ga,gd,pts = [int(x) for x in cols[2:10]]
        data.append({
            "pos":pos,"team":team,"p":p,"w":w,"d":d,"l":l,"gf":gf,"ga":ga,"gd":gd,"pts":pts,
            "badge": badge_from_name(team)
        })
    data.sort(key=lambda x:x["pos"])
    if len(data)<18: raise RuntimeError(f"Only {len(data)} rows scraped")
    return data

def main():
    data=fetch_table()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8") as f:
        json.dump({"league":"Premier League","rows":data}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} with {len(data)} teams")

if __name__=="__main__":
    main()
