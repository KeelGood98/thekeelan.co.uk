#!/usr/bin/env python3
import os, datetime
from fetch_helpers import http_get_json, save_json, now_iso

TSDB_LEAGUE_ID = "4328"  # English Premier League
OUT_PATH = os.path.join("assets", "table.json")

def season_candidates():
    today = datetime.date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return [f"{start}-{start+1}", f"{start-1}-{start}", "2024-2025"]

def fetch_table_tsdb(season, api_key):
    url = f"https://www.thesportsdb.com/api/v1/json/{api_key}/lookuptable.php?l={TSDB_LEAGUE_ID}&s={season}"
    data = http_get_json(url) or {}
    arr = data.get("table") or data.get("standings") or []
    out = []
    for i, r in enumerate(arr, 1):
        team = (r.get("name") or r.get("teamname") or r.get("team") or r.get("strTeam") or "").strip()
        if not team:
            continue
        played = int(r.get("played") or r.get("intPlayed") or 0)
        won    = int(r.get("win")    or r.get("intWin")    or 0)
        draw   = int(r.get("draw")   or r.get("intDraw")   or 0)
        lost   = int(r.get("loss")   or r.get("intLoss")   or 0)
        gf     = int(r.get("goalsfor")       or r.get("intGoalsFor")      or 0)
        ga     = int(r.get("goalsagainst")   or r.get("intGoalsAgainst")  or 0)
        gd     = int(r.get("goalsdifference")or r.get("intGoalDifference")or (gf - ga))
        pts    = int(r.get("total")  or r.get("intPoints") or 0)
        pos    = int(r.get("position") or i)
        out.append({
            "pos": pos, "team": team, "played": played, "won": won, "drawn": draw,
            "lost": lost, "gf": gf, "ga": ga, "gd": gd, "pts": pts
        })
    out.sort(key=lambda x: x["pos"])
    return out

def main():
    api_key = os.environ.get("TSDB_API_KEY") or "3"  # TSDB demo key if you haven't set a secret
    best, used = [], None
    for s in season_candidates():
        try:
            rows = fetch_table_tsdb(s, api_key)
        except Exception as e:
            print(f"[table] WARN: {s} fetch failed: {e}")
            continue
        if len(rows) > len(best):
            best, used = rows, s
        if len(rows) >= 20:
            break

    if not best:
        print("[table] ERROR: no rows from TSDB; writing empty list")
        save_json(OUT_PATH, {"updated": now_iso(), "standings": []})
        return 0

    if len(best) < 20:
        print(f"[table] WARN: only {len(best)} rows (season {used})")

    save_json(OUT_PATH, {"updated": now_iso(), "standings": best[:20]})
    print(f"[table] OK wrote {len(best[:20])} rows (season {used}) to {OUT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
