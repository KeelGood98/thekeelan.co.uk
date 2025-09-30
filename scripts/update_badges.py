#!/usr/bin/env python3
# Build assets/badges.json by looking at teams in assets/table.json and
# fetching the club crest from Wikipedia REST summary.

import json, os, sys, urllib.request, urllib.parse, time

TABLE = "assets/table.json"
OUT   = "assets/badges.json"

WIKI_EXACT = {
  "Arsenal":"Arsenal_F.C.",
  "Aston Villa":"Aston_Villa_F.C.",
  "AFC Bournemouth":"AFC_Bournemouth",
  "Bournemouth":"AFC_Bournemouth",
  "Brentford":"Brentford_F.C.",
  "Brighton and Hove Albion":"Brighton_%26_Hove_Albion_F.C.",
  "Brighton & Hove Albion":"Brighton_%26_Hove_Albion_F.C.",
  "Burnley":"Burnley_F.C.",
  "Chelsea":"Chelsea_F.C.",
  "Crystal Palace":"Crystal_Palace_F.C.",
  "Everton":"Everton_F.C.",
  "Fulham":"Fulham_F.C.",
  "Leeds United":"Leeds_United_F.C.",
  "Liverpool":"Liverpool_F.C.",
  "Manchester City":"Manchester_City_F.C.",
  "Manchester United":"Manchester_United_F.C.",
  "Newcastle United":"Newcastle_United_F.C.",
  "Nottingham Forest":"Nottingham_Forest_F.C.",
  "Tottenham Hotspur":"Tottenham_Hotspur_F.C.",
  "West Ham United":"West_Ham_United_F.C.",
  "Wolverhampton Wanderers":"Wolverhampton_Wanderers_F.C.",
  "Sunderland":"Sunderland_A.F.C."
}

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"GH-Actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def crest_from_wiki(title):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    try:
        j = json.loads(fetch(url).decode("utf-8"))
        # Prefer originalimage if there; fallback to thumbnail
        src = (j.get("originalimage") or {}).get("source") or (j.get("thumbnail") or {}).get("source")
        if src:
            return src.replace("http://","https://")
    except Exception as e:
        print("wiki fail:", title, e, file=sys.stderr)
    return None

def main():
    os.makedirs("assets", exist_ok=True)
    try:
        with open(TABLE,"r") as f:
            table = json.load(f)
    except Exception as e:
        print("missing assets/table.json:", e, file=sys.stderr)
        sys.exit(0)

    teams = [r.get("team","") for r in table.get("standings",[])]
    out = {}
    for t in teams:
        title = WIKI_EXACT.get(t) or (t.replace(" ","_")+"_F.C.")
        crest = crest_from_wiki(title)
        if crest: out[t.lower()] = crest

    with open(OUT,"w") as f:
        json.dump({"updated":int(time.time()*1000),"badges":out}, f)
    print("wrote", OUT, "with", len(out), "entries")

if __name__ == "__main__":
    main()
