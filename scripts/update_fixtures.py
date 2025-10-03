#!/usr/bin/env python3
"""
Builds assets/fixtures.json from ESPN team schedule (Premier League).
We use ESPN team id for Manchester United (id=360).

Produces:
{
  "upcoming": [ ... ],
  "results":  [ ... ]
}
"""

import datetime as dt
import json
import pathlib
import sys
import urllib.request

OUT = pathlib.Path("assets/fixtures.json")
TEAM_ID = 360  # Manchester United on ESPN
URL = (
    f"https://site.api.espn.com/apis/v2/sports/soccer/eng.1/teams/{TEAM_ID}/schedule"
    "?region=gb&lang=en"
)

def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

def parse_event(ev):
    comp = ev["competitions"][0]
    date_iso = ev["date"]
    # ESPN ISO → cut to minutes
    date = dt.datetime.fromisoformat(date_iso.replace("Z","+00:00")).strftime("%Y-%m-%d")
    time_uk = dt.datetime.fromisoformat(date_iso.replace("Z","+00:00")).strftime("%H:%M")

    # identify home/away and scores
    home, away = None, None
    for c in comp.get("competitors", []):
        name = c["team"]["displayName"]
        if c.get("homeAway") == "home":
            home = name
            home_score = c.get("score")
        else:
            away = name
            away_score = c.get("score")

    # competition name (EPL / FA Cup / etc.)
    comp_text = comp.get("notes", [{}])[0].get("headline") or ev.get("shortName") or "Match"

    status = ev.get("status", {}).get("type", {}).get("state", "").lower()
    is_final = status in ("post", "final")
    is_pre   = status in ("pre", "scheduled")

    score = None
    if is_final and home_score is not None and away_score is not None:
        score = f"{home_score}–{away_score}"

    tv = None
    # ESPN broadcast sometimes in competitions[0].broadcasts → list
    for b in comp.get("broadcasts", []):
        if b.get("market") == "uk" and b.get("names"):
            tv = b["names"][0]
            break

    return {
        "date": date,
        "time_uk": time_uk,
        "comp": comp_text,
        "home": home,
        "away": away,
        "tv": tv,
        "score": score,
        "state": "final" if is_final else ("upcoming" if is_pre else "inplay")
    }

def main():
    data = fetch_json(URL)
    events = data.get("events", [])
    parsed = [parse_event(ev) for ev in events]

    upcoming = [e for e in parsed if e["state"] == "upcoming"]
    results  = [e for e in parsed if e["state"] == "final"]

    # sort: upcoming by date/time asc, results desc
    key = lambda e: (e["date"], e["time_uk"])
    upcoming.sort(key=key)
    results.sort(key=key, reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump({"upcoming": upcoming[:10], "results": results[:12]}, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(upcoming)} upcoming / {len(results)} results")

if __name__ == "__main__":
    sys.exit(main())
