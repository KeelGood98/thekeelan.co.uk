#!/usr/bin/env python3
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone

OUT_DIR = "assets"
os.makedirs(OUT_DIR, exist_ok=True)

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "keelan-actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def norm(s: str) -> str:
    return (s or "").lower().replace("&", "and").replace(".", "").replace("-", " ").strip()

# ----- work out current PL season (e.g. "2025-2026")
now = datetime.now(timezone.utc)
start = now.year if now.month >= 7 else now.year - 1
season = f"{start}-{start+1}"

# ----- THESPORTSDB: league 4328 = English Premier League
table_url = f"https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4328&s={urllib.parse.quote(season)}"
teams_url = "https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=English%20Premier%20League"

# ----- build table (20 rows expected)
rows = []
try:
    data = json.loads(fetch(table_url).decode("utf-8"))
    for t in data.get("table") or []:
        rows.append({
            "pos":  int(t.get("intRank") or 0),
            "team": t.get("strTeam") or "",
            "played": int(t.get("intPlayed") or 0),
            "won":    int(t.get("intWin") or 0),
            "drawn":  int(t.get("intDraw") or 0),
            "lost":   int(t.get("intLoss") or 0),
            "gf":     int(t.get("intGoalsFor") or 0),
            "ga":     int(t.get("intGoalsAgainst") or 0),
            "gd":     int(t.get("intGoalDifference") or 0),
            "pts":    int(t.get("intPoints") or 0),
        })
    rows.sort(key=lambda r: r["pos"] or 999)
except Exception as e:
    raise SystemExit(f"[table] ERROR: {e}")

if len(rows) < 10:
    raise SystemExit(f"[table] ERROR: fetched only {len(rows)} rows")

# ----- build crest/badge map (used by index)
badges = {}
try:
    tdata = json.loads(fetch(teams_url).decode("utf-8"))
    for t in (tdata.get("teams") or []):
        name = t.get("strTeam") or ""
        badge = t.get("strTeamBadge") or ""
        if name and badge:
            badges[norm(name)] = badge.replace("http://", "https://")
except Exception as e:
    print("[badges] warn:", e)

# ----- write assets
with open(os.path.join(OUT_DIR, "table.json"), "w", encoding="utf-8") as f:
    json.dump({
        "season": season,
        "source": "TheSportsDB",
        "updated": int(time.time() * 1000),
        "standings": rows
    }, f)

with open(os.path.join(OUT_DIR, "badges.json"), "w", encoding="utf-8") as f:
    json.dump({"badges": badges, "updated": int(time.time() * 1000)}, f)

print(f"Wrote table.json ({len(rows)} rows) + badges.json ({len(badges)} crests)")
