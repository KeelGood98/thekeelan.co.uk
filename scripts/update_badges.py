#!/usr/bin/env python3
import os
from fetch_helpers import http_get_json, save_json, now_iso

OUT_PATH = os.path.join("assets", "badges.json")

def norm(s): 
    return (s or "").strip()

def main():
    api_key = os.environ.get("TSDB_API_KEY") or "3"
    # two endpoints to be robust
    urls = [
        f"https://www.thesportsdb.com/api/v1/json/{api_key}/search_all_teams.php?l=English%20Premier%20League",
        f"https://www.thesportsdb.com/api/v1/json/{api_key}/lookup_all_teams.php?id=4328",
    ]
    badges = {}
    for u in urls:
        try:
            data = http_get_json(u) or {}
            for t in (data.get("teams") or []):
                name = norm(t.get("strTeam"))
                crest = norm(t.get("strTeamBadge") or t.get("strTeamLogo") or "")
                if name and crest and name not in badges:
                    badges[name] = crest.replace("http://", "https://")
        except Exception as e:
            print("[badges] WARN", e)
            continue

    save_json(OUT_PATH, {"updated": now_iso(), "badges": badges})
    print(f"[badges] OK wrote {len(badges)} crests to {OUT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
