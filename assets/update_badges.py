# scripts/update_badges.py
import os, sys, re
from fetch_helpers import http_get_json, read_json, write_json_atomic, qs

APIKEY = os.getenv("TSDB_KEY", "3")
SEASON = os.getenv("SEASON", "2025-2026")
LEAGUE_ID = os.getenv("TSDB_LEAGUE_ID", "4328")
OUT = "assets/badges.json"

def norm(s):
    return re.sub(r"[.\-’'&]", "", (s or "").lower()).replace("fc","").replace("  "," ").strip()

def fetch_team_badges():
    url = qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/lookuptable.php", l=LEAGUE_ID, s=SEASON)
    j = http_get_json(url)
    teams = j.get("table") or []
    badges = {}
    for t in teams:
        name = t.get("name") or t.get("team") or ""
        team_id = t.get("teamid") or t.get("team_id")
        # get team detail for badge url
        # try by id first
        badge_url = None
        if team_id:
            j2 = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/lookupteam.php", id=team_id))
            arr = j2.get("teams") or []
            if arr:
                badge_url = arr[0].get("strTeamBadge")
        # fallback: search by name
        if not badge_url and name:
            j3 = http_get_json(qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/searchteams.php", t=name))
            arr = j3.get("teams") or []
            if arr:
                badge_url = arr[0].get("strTeamBadge")
        if name:
            badges[name] = badge_url or None
    return badges

def main():
    prev = read_json(OUT) or {"badges": {}}
    prev_map = prev.get("badges") or {}
    fresh = fetch_team_badges()

    # merge: keep any non-null previous value; otherwise use fresh
    merged = {}
    keys = set(prev_map.keys()) | set(fresh.keys())
    for k in sorted(keys):
        v = prev_map.get(k)
        if v: merged[k] = v
        else: merged[k] = fresh.get(k)

    # ensure all 20 teams exist as keys
    if len(merged.keys()) < 20:
        print(f"[badges] WARNING: only {len(merged.keys())} keys; continuing.")

    out = {
        "season": SEASON,
        "updated": None,  # human ISO also fine if you prefer
        "badges": merged
    }
    write_json_atomic(OUT, out)
    print(f"[badges] Wrote {OUT} with {len(merged)} teams.")

if __name__ == "__main__":
    main()
