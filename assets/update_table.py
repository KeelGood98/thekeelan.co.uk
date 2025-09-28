# scripts/update_table.py
import os, sys
from fetch_helpers import http_get_json, read_json, write_json_atomic, now_ms, qs

# TheSportsDB constants
# EPL league id = 4328, season format '2025-2026'
LEAGUE_ID = os.getenv("TSDB_LEAGUE_ID", "4328")
SEASON    = os.getenv("SEASON", "2025-2026")
APIKEY    = os.getenv("TSDB_KEY", "3")  # '3' is TSDB's demo key; replace with your key if you have one

OUT = "assets/table.json"

def map_row(r):
    # Map TSDB table fields to our schema
    # TSDB fields: name, teamid, played, win, draw, loss, goalsfor, goalsagainst, total, goaldifference
    return {
        "pos":        int(r.get("rank") or r.get("position") or r.get("idx") or 0),
        "team":       r.get("name") or r.get("team") or "",
        "played":     int(r.get("played") or 0),
        "won":        int(r.get("win") or r.get("won") or 0),
        "drawn":      int(r.get("draw") or r.get("drawn") or 0),
        "lost":       int(r.get("loss") or r.get("lost") or 0),
        "gf":         int(r.get("goalsfor") or r.get("gf") or 0),
        "ga":         int(r.get("goalsagainst") or r.get("ga") or 0),
        "gd":         int(r.get("goaldifference") or r.get("gd") or (int(r.get("goalsfor") or 0) - int(r.get("goalsagainst") or 0))),
        "pts":        int(r.get("total") or r.get("points") or r.get("pts") or 0),
    }

def main():
    url = qs(f"https://www.thesportsdb.com/api/v1/json/{APIKEY}/lookuptable.php", l=LEAGUE_ID, s=SEASON)
    j = http_get_json(url)
    raw = j.get("table") or j.get("standings") or []
    rows = [map_row(r) for r in raw]
    # Sort by pos if present
    rows.sort(key=lambda x: (x["pos"] if x["pos"] else 999))

    # Guardrail: require 20 rows; otherwise keep last good file
    if len(rows) < 20:
        prev = read_json(OUT)
        if prev and isinstance(prev.get("standings"), list) and len(prev["standings"]) >= 20:
            print(f"[table] WARNING: fetched {len(rows)} rows; keeping previous file.")
            write_json_atomic(OUT, prev)  # keep
            sys.exit(0)
        else:
            # fail the job loudly
            raise SystemExit(f"[table] ERROR: fetched only {len(rows)} rows for EPL {SEASON}")

    out = {
        "season": SEASON,
        "source": "TheSportsDB",
        "updated": now_ms(),
        "standings": rows
    }
    write_json_atomic(OUT, out)
    print(f"[table] Wrote {OUT} with {len(rows)} rows.")

if __name__ == "__main__":
    main()
