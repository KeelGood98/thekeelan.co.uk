# scripts/update_table.py
import json, time, urllib.request, urllib.parse, os, sys
from datetime import datetime

ASSETS_DIR = "assets"
LEAGUE_ID = "4328"  # TheSportsDB: English Premier League

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"GHAction/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def norm(s: str) -> str:
    return (s or "").lower().replace("&","and").replace("’","'") \
            .replace("–","-").replace("—","-") \
            .encode("ascii","ignore").decode() \
            .replace(" ", "").replace("-", "").replace(".", "")

def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # --- season string like 2025-2026
    now = datetime.utcnow()
    start = now.year if now.month >= 7 else now.year - 1
    season = f"{start}-{start+1}"

    # --- TABLE
    table_url = f"https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l={LEAGUE_ID}&s={urllib.parse.quote(season)}"
    try:
        data = json.loads(fetch(table_url).decode("utf-8"))
    except Exception as e:
        print("ERROR fetching table:", e, file=sys.stderr)
        data = {}

    rows = []
    for t in (data.get("table") or []):
        # intRank may be string -> cast safely
        def _int(k): 
            try: return int(t.get(k) or 0)
            except: return 0
        rows.append({
            "pos": _int("intRank"),
            "team": t.get("strTeam") or "",
            "played": _int("intPlayed"),
            "won": _int("intWin"),
            "drawn": _int("intDraw"),
            "lost": _int("intLoss"),
            "gf": _int("intGoalsFor"),
            "ga": _int("intGoalsAgainst"),
            "gd": _int("intGoalDifference"),
            "pts": _int("intPoints"),
        })
    rows.sort(key=lambda r: r["pos"] or 999)

    table_out = {
        "season": season,
        "source": "TheSportsDB",
        "updated": int(time.time() * 1000),
        "standings": rows
    }
    with open(os.path.join(ASSETS_DIR, "table.json"), "w", encoding="utf-8") as f:
        json.dump(table_out, f)
    print("Wrote assets/table.json with", len(rows), "rows for", season)

    # --- BADGES (league teams → badge urls)
    badge_map = {}
    try:
        teams_url = f"https://www.thesportsdb.com/api/v1/json/3/lookup_all_teams.php?id={LEAGUE_ID}"
        teams = json.loads(fetch(teams_url).decode("utf-8")).get("teams") or []
        for tm in teams:
            name = tm.get("strTeam") or ""
            badge = tm.get("strTeamBadge") or ""
            # normalize to your JS keying (lowercase + strip non-alnum + &→and)
            badge_map[norm(name)] = (badge or "").replace("http://","https://")
    except Exception as e:
        print("ERROR building badges:", e, file=sys.stderr)

    with open(os.path.join(ASSETS_DIR, "badges.json"), "w", encoding="utf-8") as f:
        json.dump({"badges": badge_map, "updated": int(time.time()*1000)}, f)
    print("Wrote assets/badges.json with", len(badge_map), "entries")

if __name__ == "__main__":
    main()
