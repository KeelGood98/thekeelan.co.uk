# scripts/update_fixtures.py
import os, sys, datetime
from fetch_helpers import http_get_json, read_json, write_json_atomic, now_ms, qs

APIKEY = os.getenv("TSDB_KEY", "3")
SEASON = os.getenv("SEASON", "2025-2026")
TEAM_NAME = os.getenv("TEAM_NAME", "Manchester United")
OUT = "assets/fixtures.json"

def find_team_id(name):
    j = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/searchteams.php", t=name))
    arr = j.get("teams") or []
    for t in arr:
        if t.get("strTeam") == name:
            return t.get("idTeam")
    return arr[0].get("idTeam") if arr else None

def parse_outcome(h, a, home_is_mufc):
    try:
        h = int(h); a = int(a)
    except: return ""
    if h == a: return "d"
    win = (h > a and home_is_mufc) or (a > h and not home_is_mufc)
    return "w" if win else "l"

def season_fixtures(team_id):
    # Use season endpoint if available; if not, combine last+next
    events = []
    try:
        j = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/eventsseason.php", id=team_id, s=SEASON))
        events = j.get("events") or []
    except: pass
    if not events:
        last5 = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/eventslast.php", id=team_id)).get("results") or []
        next5 = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/eventsnext.php", id=team_id)).get("events") or []
        events = last5 + next5
    return events

def map_event(e):
    # TSDB fields: dateEvent, strTime, strTimestamp (UTC), strLeague, strHomeTeam, strAwayTeam, intHomeScore, intAwayScore, strStatus
    date_iso = e.get("strTimestamp") or (e.get("dateEvent") + "T" + (e.get("strTime") or "00:00:00Z"))
    home = e.get("strHomeTeam") or e.get("homeTeam") or ""
    away = e.get("strAwayTeam") or e.get("awayTeam") or ""
    comp = e.get("strLeague") or e.get("strTournament") or e.get("strCompetition") or ""
    hs = e.get("intHomeScore"); as_ = e.get("intAwayScore")
    status = (e.get("strStatus") or "").upper()
    finished = status in ("FINISHED","FT","MATCH FINISHED") or (hs not in (None,"") and as_ not in (None,""))
    home_is_mufc = (home == "Manchester United")
    outcome = parse_outcome(hs, as_, home_is_mufc) if finished else ""
    return {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "status": "FINISHED" if finished else "SCHEDULED",
        "score": { "home": (int(hs) if hs not in (None,"") else ""), "away": (int(as_) if as_ not in (None,"") else ""), "outcome": outcome },
        "tv": "",               # leave blank; page will fill via tv_overrides.json
        "highlights": {}        # optional manual links
    }

def main():
    team_id = find_team_id(TEAM_NAME)
    if not team_id:
        raise SystemExit(f"[fixtures] Could not resolve team id for {TEAM_NAME}")
    ev = season_fixtures(team_id)
    mapped = [map_event(e) for e in ev]
    out = {
        "team": TEAM_NAME,
        "season": SEASON,
        "source": "TheSportsDB",
        "updated": now_ms(),
        "matches": mapped
    }
    write_json_atomic(OUT, out)
    print(f"[fixtures] Wrote {OUT} with {len(mapped)} matches.")

if __name__ == "__main__":
    main()
