#!/usr/bin/env python3
import os, sys, json, time, datetime, urllib.request

def http_get_json(url, timeout=30):
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if i == 2:
                raise
            time.sleep(1.5 * (i + 1))

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

def current_pl_seasons():
    # PL runs Aug–May. If month >= Jul use Y–Y+1, else Y-1–Y
    today = datetime.date.today()
    start_year = today.year if today.month >= 7 else today.year - 1
    this_season = f"{start_year}-{start_year+1}"
    prev_season = f"{start_year-1}-{start_year}"
    # include a stable fallback that we know was complete
    return [this_season, prev_season, "2024-2025"]

def fetch_tsdb_table(season, api_key):
    # PL league id on TSDB = 4328
    url = f"https://www.thesportsdb.com/api/v1/json/{api_key}/lookuptable.php?l=4328&s={season}"
    data = http_get_json(url) or {}
    arr = data.get("table") or data.get("standings") or []
    rows = []
    for i, r in enumerate(arr, 1):
        team = r.get("name") or r.get("teamname") or r.get("team") or r.get("strTeam") or ""
        if not team:
            continue
        rows.append({
            "position": int(r.get("position") or i),
            "team": team,
            "played": int(r.get("played") or r.get("intPlayed") or 0),
            "won": int(r.get("win") or r.get("intWin") or 0),
            "draw": int(r.get("draw") or r.get("intDraw") or 0),
            "lost": int(r.get("loss") or r.get("intLoss") or 0),
            "goalsFor": int(r.get("goalsfor") or r.get("intGoalsFor") or 0),
            "goalsAgainst": int(r.get("goalsagainst") or r.get("intGoalsAgainst") or 0),
            "goalDiff": int(r.get("goalsdifference") or r.get("intGoalDifference") or 0),
            "points": int(r.get("total") or r.get("intPoints") or 0),
        })
    rows.sort(key=lambda x: x["position"])
    return rows

def main():
    api_key = os.environ.get("TSDB_API_KEY") or os.environ.get("TSDB_API") or "3"  # '3' is TSDB's demo key
    out_path = os.path.join("assets", "table.json")

    best_rows = []
    used_season = None

    for season in current_pl_seasons():
        try:
            rows = fetch_tsdb_table(season, api_key)
        except Exception as e:
            print(f"[table] WARN: TSDB fetch failed for {season}: {e}", file=sys.stderr)
            continue

        if len(rows) > len(best_rows):
            best_rows = rows
            used_season = season
        if len(rows) >= 20:
            break

    if not best_rows:
        print("[table] ERROR: no data from TSDB (all seasons)", file=sys.stderr)
        # do not fail the job—write an empty array so the site shows "No data"
        save_json(out_path, [])
        return 0

    if len(best_rows) < 20:
        print(f"[table] WARN: only {len(best_rows)} rows from season {used_season}", file=sys.stderr)

    # Normalize and cap at 20
    normalized = []
    for r in best_rows[:20]:
        normalized.append({
            "position": r["position"],
            "team": r["team"],
            "played": r["played"],
            "won": r["won"],
            "draw": r["draw"],
            "lost": r["lost"],
            "goalsFor": r["goalsFor"],
            "goalsAgainst": r["goalsAgainst"],
            "goalDiff": r["goalDiff"],
            "points": r["points"],
        })

    save_json(out_path, normalized)
    print(f"[table] OK: wrote {len(normalized)} rows from {used_season} to {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
