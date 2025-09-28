#!/usr/bin/env python3
import json, time, urllib.request

TEAM_ID = "360"  # Manchester United
ESPN_SCHEDULE = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{TEAM_ID}/schedule"

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_event(ev):
    comp = (ev.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    by_side = {c.get("homeAway"): c for c in competitors}

    home = by_side.get("home", {}).get("team", {}).get("displayName", "")
    away = by_side.get("away", {}).get("team", {}).get("displayName", "")
    league = (ev.get("league") or {}).get("name") or (comp.get("league") or {}).get("name") or ""
    date_iso = ev.get("date") or ""

    # Status / state: "pre", "post", etc.
    stype = (ev.get("status") or {}).get("type") or {}
    state = (stype.get("state") or "").lower()

    # Scores (if available)
    sh = by_side.get("home", {}).get("score")
    sa = by_side.get("away", {}).get("score")
    try:
        sh_i = int(sh) if sh is not None else None
        sa_i = int(sa) if sa is not None else None
    except:
        sh_i = sa_i = None

    # Outcome from MUFC perspective (if complete)
    outcome = ""
    if state == "post" and sh_i is not None and sa_i is not None:
        if home.lower() == "manchester united":
            outcome = "W" if sh_i > sa_i else ("D" if sh_i == sa_i else "L")
        elif away.lower() == "manchester united":
            outcome = "W" if sa_i > sh_i else ("D" if sa_i == sh_i else "L")

    # TV channels (if listed)
    chans = []
    for b in comp.get("broadcasts") or []:
        names = b.get("names") or [b.get("name")]
        if isinstance(names, str): names = [names]
        for n in names:
            if n and n not in chans:
                chans.append(n)
    tv = ", ".join(chans)

    return {
        "date": date_iso,
        "comp": league,
        "home": home,
        "away": away,
        "tv": tv,
        "status": stype.get("name") or "",
        "state": state,  # keep for sorting/upcoming logic
        "score": {"home": sh_i, "away": sa_i, "outcome": outcome}
    }

def main():
    data = fetch(ESPN_SCHEDULE)
    events = data.get("events") or []
    games = [parse_event(e) for e in events]

    # Keep ONLY Premier League matches
    pl = [g for g in games if "premier" in (g["comp"] or "").lower()]

    # Sort by date (string ISO sorts fine here)
    pl.sort(key=lambda g: g["date"])

    # Save
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
