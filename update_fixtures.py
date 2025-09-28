#!/usr/bin/env python3
import json, time, urllib.request, urllib.parse, os

os.makedirs("assets", exist_ok=True)

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent":"thekeelan-actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def tsdb_team_id(team_name="Manchester United"):
    q = urllib.parse.quote(team_name)
    data = json.loads(get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={q}").decode("utf-8"))
    teams = data.get("teams") or []
    return teams[0].get("idTeam") if teams else None

def next_events(team_id):
    d = json.loads(get(f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}").decode("utf-8"))
    return d.get("events") or []

def last_events(team_id):
    d = json.loads(get(f"https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={team_id}").decode("utf-8"))
    return d.get("results") or []

tid = tsdb_team_id("Manchester United")
matches = []

if tid:
    # Upcoming
    for e in next_events(tid):
        dt = (e.get("dateEvent") or "") + " " + (e.get("strTimeLocal") or e.get("strTime") or "00:00:00")
        matches.append({
            "date": dt.strip(),
            "comp": e.get("strLeague"),
            "home": e.get("strHomeTeam"),
            "away": e.get("strAwayTeam"),
            "status": "SCHEDULED",
            "tv": None,
            "score": None
        })

    # Recent
    for e in last_events(tid):
        dt = (e.get("dateEvent") or "") + " " + (e.get("strTimeLocal") or e.get("strTime") or "00:00:00")
        hs = e.get("intHomeScore"); as_ = e.get("intAwayScore")
        score = None
        if hs is not None and as_ is not None:
            try:
                score = {"home": int(hs), "away": int(as_)}
            except:
                score = None

        # Work out W/D/L from the MUFC perspective
        outcome = None
        if score:
            if e.get("strHomeTeam") == "Manchester United":
                if score["home"] > score["away"]: outcome = "W"
                elif score["home"] == score["away"]: outcome = "D"
                else: outcome = "L"
            elif e.get("strAwayTeam") == "Manchester United":
                if score["away"] > score["home"]: outcome = "W"
                elif score["away"] == score["home"]: outcome = "D"
                else: outcome = "L"

        matches.append({
            "date": dt.strip(),
            "comp": e.get("strLeague"),
            "home": e.get("strHomeTeam"),
            "away": e.get("strAwayTeam"),
            "status": "FINISHED" if score else "FINISHED",
            "tv": None,
            "score": score,
            "outcome": outcome
        })

# Sort by date ascending; keep reasonable amount
def sort_key(m):
    return m.get("date","")
matches = sorted(matches, key=sort_key)

out = {"updated": int(time.time()*1000), "matches": matches}
with open("assets/fixtures.json","w",encoding="utf-8") as f:
    json.dump(out, f)
print(f"Wrote assets/fixtures.json ({len(matches)} matches)")
