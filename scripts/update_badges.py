import os
from fetch_helpers import http_get_json, write_json_atomic, qs

APIKEY = os.getenv("TSDB_KEY", "3")
SEASON = os.getenv("SEASON", "2025-2026")
LEAGUE_ID = os.getenv("TSDB_LEAGUE_ID", "4328")
OUT = "assets/badges.json"

def fetch_team_badges():
    url = qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/lookuptable.php", l=LEAGUE_ID, s=SEASON)
    j = http_get_json(url)
    teams = j.get("table") or []
    badges = {}
    for t in teams:
        name = t.get("name") or t.get("team") or ""
        tid  = t.get("teamid") or t.get("team_id")
        badge = None
        if tid:
            d = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/lookupteam.php", id=tid))
            arr = d.get("teams") or []
            if arr: badge = arr[0].get("strTeamBadge")
        if not badge and name:
            d = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/searchteams.php", t=name))
            arr = d.get("teams") or []
            if arr: badge = arr[0].get("strTeamBadge")
        badges[name] = badge or None
    return badges

def main():
    badges = fetch_team_badges()
    out = { "season": SEASON, "updated": None, "badges": badges }
    write_json_atomic(OUT, out)
    print(f"[badges] Wrote {OUT} with {len(badges)} teams.")

if __name__ == "__main__":
    main()
