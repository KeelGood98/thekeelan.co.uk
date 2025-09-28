#!/usr/bin/env python3
import json, time, urllib.request, os

os.makedirs("assets", exist_ok=True)

def get(u, timeout=45):
    req = urllib.request.Request(u, headers={"User-Agent":"thekeelan-actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

MUFC_ID = "133612"  # TheSportsDB id for Manchester United (hard-coded to avoid wrong team)

def eventsnext(team_id):
    d = json.loads(get(f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}").decode("utf-8"))
    return d.get("events") or []

def eventslast(team_id):
    d = json.loads(get(f"https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={team_id}").decode("utf-8"))
    return d.get("results") or []

def tidy_date(e):
    date = (e.get("dateEvent") or "").strip()
    time_ = (e.get("strTimeLocal") or e.get("strTime") or "00:00:00").strip()
    return f"{date} {time_}".strip()

ALLOW = ("Premier",)  # only Premier League – keeps Bolton/League One out

matches = []

# Upcoming
for e in eventsnext(MUFC_ID):
    if not any(k in (e.get("strLeague") or "") for k in ALLOW):
        continue
    matches.append({
        "date": tidy_date(e),
        "comp": e.get("strLeague"),
        "home": e.get("strHomeTeam"),
        "away": e.get("strAwayTeam"),
        "status": "SCHEDULED",
        "tv": None,
        "score": None
    })

# Recent
for e in eventslast(MUFC_ID):
    if not any(k in (e.get("strLeague") or "") for k in ALLOW):
        continue
    hs, as_ = e.get("intHomeScore"), e.get("intAwayScore")
    score = None
    try:
        if hs is not None and as_ is not None:
            score = {"home": int(hs), "away": int(as_)}
    except: pass
    outcome = None
    if score:
        if e.get("strHomeTeam") == "Manchester United":
            outcome = "W" if score["home"] > score["away"] else "D" if score["home"] == score["away"] else "L"
        elif e.get("strAwayTeam") == "Manchester United":
            outcome = "W" if score["away"] > score["home"] else "D" if score["away"] == score["home"] else "L"
    matches.append({
        "date": tidy_date(e),
        "comp": e.get("strLeague"),
        "home": e.get("strHomeTeam"),
        "away": e.get("strAwayTeam"),
        "status": "FINISHED" if score else "FINISHED",
        "tv": None,
        "score": score,
        "outcome": outcome
    })

matches.sort(key=lambda m: m["date"])
out = {"updated": int(time.time()*1000), "matches": matches}
with open("assets/fixtures.json","w",encoding="utf-8") as f:
    json.dump(out, f)
print(f"Wrote assets/fixtures.json ({len(matches)} matches)")
