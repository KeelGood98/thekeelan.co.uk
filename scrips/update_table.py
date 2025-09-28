# scripts/update_table.py
import json, time, urllib.request, urllib.parse, os, sys
from datetime import datetime

UA = {"User-Agent": "KeelBot/1.0"}
API = "https://www.thesportsdb.com/api/v1/json/3"

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def now_season():
    now = datetime.utcnow()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{start}-{start+1}"

def main():
    os.makedirs("assets", exist_ok=True)
    season = now_season()

    # 1) Premier League table (league id 4328)
    url = f"{API}/lookuptable.php?l=4328&s={urllib.parse.quote(season)}"
    data = json.loads(get(url).decode("utf-8"))
    table = data.get("table") or []
    rows = []
    for t in table:
        rows.append({
            "pos": int(t.get("intRank") or 0),
            "team": t.get("strTeam") or "",
            "played": int(t.get("intPlayed") or 0),
            "won": int(t.get("intWin") or 0),
            "drawn": int(t.get("intDraw") or 0),
            "lost": int(t.get("intLoss") or 0),
            "gf": int(t.get("intGoalsFor") or 0),
            "ga": int(t.get("intGoalsAgainst") or 0),
            "gd": int(t.get("intGoalDifference") or 0),
            "pts": int(t.get("intPoints") or 0)
        })
    rows.sort(key=lambda r: r["pos"] or 999)

    if len(rows) < 20:
        print(f"[table] WARNING: only {len(rows)} rows for {season}.", file=sys.stderr)

    with open("assets/table.json", "w") as f:
        json.dump({
            "season": season,
            "source": "TheSportsDB",
            "updated": int(time.time()*1000),
            "standings": rows
        }, f)
    print("Wrote assets/table.json with", len(rows), "rows")

    # 2) League teams -> badges map
    try:
        teams = json.loads(get(f"{API}/search_all_teams.php?l=English%20Premier%20League").decode("utf-8")).get("teams") or []
        badges = { (t.get("strTeam") or "").strip(): (t.get("strTeamBadge") or "") for t in teams if t.get("strTeam") }
        # normalize a few names we know can vary
        fix = {
            "Brighton & Hove Albion": "Brighton and Hove Albion"
        }
        normalized = {}
        for k,v in badges.items():
            normalized[ fix.get(k,k) ] = v
        with open("assets/badges.json","w") as f:
            json.dump({"badges": normalized, "updated": int(time.time()*1000)}, f)
        print("Wrote assets/badges.json with", len(normalized), "entries")
    except Exception as e:
        print("badges build error:", e, file=sys.stderr)

if __name__ == "__main__":
    main()
