#!/usr/bin/env python3
import json, time, urllib.request, datetime

TEAM_ID = "360"  # Manchester United
ESPN_SCHEDULE = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{TEAM_ID}/schedule"

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_event(ev):
    # date/time
    iso = ev.get("date")
    comp = (ev.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    details = {c.get("homeAway"): c for c in competitors}
    home = details.get("home", {}).get("team", {}).get("displayName", "")
    away = details.get("away", {}).get("team", {}).get("displayName", "")
    league = (ev.get("league") or {}).get("name") or (comp.get("league") or {}).get("name") or ""

    # score / outcome
    status = (ev.get("status") or {}).get("type") or {}
    state = (status.get("state") or "").upper()  # "pre", "post", etc.
    completed = state == "POST"

    sh = details.get("home", {}).get("score")
    sa = details.get("away", {}).get("score")
    try:
        sh_i = int(sh) if sh is not None else None
        sa_i = int(sa) if sa is not None else None
    except:
        sh_i = sa_i = None

    outcome = ""
    if completed and sh_i is not None and sa_i is not None:
        if home.lower() == "manchester united":
            if sh_i > sa_i: outcome = "W"
            elif sh_i == sa_i: outcome = "D"
            else: outcome = "L"
        elif away.lower() == "manchester united":
            if sa_i > sh_i: outcome = "W"
            elif sa_i == sh_i: outcome = "D"
            else: outcome = "L"

    # TV
    chans = []
    for b in comp.get("broadcasts") or []:
        name = (b.get("names") or [b.get("name")]) or []
        if isinstance(name, str): name = [name]
        for n in name:
            if n and n not in chans: chans.append(n)
    tv = ", ".join(chans) if chans else ""

    return {
        "date": iso,
        "comp": league,
        "home": home,
        "away": away,
        "tv": tv,
        "status": status.get("name") or "",
        "score": {
            "home": sh_i,
            "away": sa_i,
            "outcome": outcome
        }
    }

def main():
    data = fetch(ESPN_SCHEDULE)
    events = data.get("events") or []
    games = [parse_event(e) for e in events]

    # keep Premier League only for display sections
    pl = [g for g in games if "premier" in (g["comp"] or "").lower()]

    out = {
        "source": "ESPN",
        "team": "Manchester United",
        "updated": int(time.time() * 1000),
        "matches": pl
    }
    with open("assets/fixtures.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"Wrote assets/fixtures.json with {len(pl)} Premier League matches")

if __name__ == "__main__":
    main()
