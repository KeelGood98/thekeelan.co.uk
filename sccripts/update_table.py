#!/usr/bin/env python3
import json, time, urllib.request, urllib.parse, os
from datetime import datetime

API = "https://www.thesportsdb.com/api/v1/json/3"
PL  = "4328"  # Premier League

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"thekeelan-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def season_now():
    now = datetime.utcnow()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{start}-{start+1}"

def main():
    os.makedirs("assets", exist_ok=True)
    s = season_now()

    # Full 20-team table
    data  = get(f"{API}/lookuptable.php?l={PL}&s={urllib.parse.quote(s)}")
    table = data.get("table") or []
    rows=[]
    for t in table:
        rows.append({
            "pos":    int(t.get("intRank") or 0),
            "team":   t.get("strTeam") or "",
            "played": int(t.get("intPlayed") or 0),
            "won":    int(t.get("intWin") or 0),
            "drawn":  int(t.get("intDraw") or 0),
            "lost":   int(t.get("intLoss") or 0),
            "gf":     int(t.get("intGoalsFor") or 0),
            "ga":     int(t.get("intGoalsAgainst") or 0),
            "gd":     int(t.get("intGoalDifference") or 0),
            "pts":    int(t.get("intPoints") or 0)
        })
    rows.sort(key=lambda r: r["pos"] or 999)
    with open("assets/table.json","w") as f:
        json.dump({"season":s,"updated":int(time.time()*1000),"standings":rows}, f)

    # Badges
    badges={}
    teams = get(f"{API}/search_all_teams.php?l=English%20Premier%20League").get("teams") or []
    for tm in teams:
        name=(tm.get("strTeam") or "").strip()
        badge=(tm.get("strTeamBadge") or "").replace("http://","https://")
        if name: badges[name]=badge
    with open("assets/badges.json","w") as f:
        json.dump({"updated":int(time.time()*1000),"badges":badges}, f)

if __name__=="__main__":
    main()
