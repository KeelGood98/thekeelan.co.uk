from datetime import datetime
from fetch_helpers import safe_fetch, write_json, now_iso

TEAM_ID = 133612  # Manchester United

def normalise(ev):
    # TSDB keys
    date = ev.get("dateEvent") or ev.get("strTimestamp") or ""
    time_s = ev.get("strTime")
    if date and time_s and "T" not in date:
        date = f"{date}T{time_s}:00Z"

    hs = ev.get("intHomeScore")
    as_ = ev.get("intAwayScore")
    finished = (hs is not None and as_ is not None)

    # Outcome W/D/L from Manchester United POV if needed
    outcome = ""
    try:
        if finished:
            hs_i, as_i = int(hs), int(as_)
            if ev.get("strHomeTeam") == "Manchester United":
                outcome = "w" if hs_i>as_i else "l" if hs_i<as_i else "d"
            elif ev.get("strAwayTeam") == "Manchester United":
                outcome = "w" if as_i>hs_i else "l" if as_i<hs_i else "d"
    except Exception:
        pass

    hl = {}
    if ev.get("strVideo"):
        # TSDB often has direct YT link
        url = ev["strVideo"]
        if "youtu" in url:
            hl["yt"] = url
        else:
            hl["sky"] = url

    return {
        "id": ev.get("idEvent"),
        "date": date,
        "comp": ev.get("strLeague"),
        "home": ev.get("strHomeTeam"),
        "away": ev.get("strAwayTeam"),
        "tv": None,
        "score": {
            "home": hs,
            "away": as_,
            "outcome": outcome
        },
        "status": "FINISHED" if finished else "SCHEDULED",
        "highlights": hl
    }

def fetch_all():
    # season events (just in case you want the whole season)
    today = datetime.utcnow()
    y = today.year if today.month>=7 else today.year - 1
    season = f"{y}-{y+1}"
    season_url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={TEAM_ID}&s={season}"
    season_data = safe_fetch(season_url, default={}) or {}
    season_events = season_data.get("events") or []

    next_data = safe_fetch(f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={TEAM_ID}", default={}) or {}
    last_data = safe_fetch(f"https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={TEAM_ID}", default={}) or {}
    next_events = next_data.get("events") or []
    last_events = last_data.get("results") or []

    # merge & dedupe by idEvent
    seen, out = set(), []
    for block in (season_events, next_events, last_events):
        for ev in block:
            i = ev.get("idEvent")
            if i and i not in seen:
                seen.add(i)
                out.append(ev)
    return out

def main():
    raw = fetch_all()
    norm = [normalise(e) for e in raw]
    out = {
        "updated": now_iso(),
        "matches": norm
    }
    write_json("assets/fixtures.json", out)
    print(f"Wrote assets/fixtures.json with {len(norm)} matches")

if __name__ == "__main__":
    main()
