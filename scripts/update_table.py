#!/usr/bin/env python3
"""
Builds assets/table.json from ESPN's public standings API (Premier League).

No HTML scraping; stable JSON.
"""

import json
import pathlib
import sys
import time
import urllib.request

OUT = pathlib.Path("assets/table.json")
ESPN_STANDINGS = (
    "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings"
    "?region=gb&lang=en&sort=rank:asc"
)

# Map ESPN stat abbreviations to our keys
STAT_MAP = {
    "GP": "P",   # games played
    "W":  "W",
    "D":  "D",
    "L":  "L",
    "GF": "GF",
    "GA": "GA",
    "GD": "GD",
    "P":  "Pts",
}

def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

def entries_to_rows(entries):
    rows = []
    for e in entries:
        team = e["team"]["displayName"]
        rank = int(e["stats"][0]["value"]) if e["stats"] and e["stats"][0]["name"].lower() == "rank" else None

        # Build dict of stats by abbreviation
        stats_by_abbr = {}
        for s in e.get("stats", []):
            abbr = s.get("abbreviation")
            if abbr: stats_by_abbr[abbr] = s.get("value")

        row = {
            "#": rank,
            "Team": team,
            "P":  stats_by_abbr.get("GP", 0),
            "W":  stats_by_abbr.get("W", 0),
            "D":  stats_by_abbr.get("D", 0),
            "L":  stats_by_abbr.get("L", 0),
            "GF": stats_by_abbr.get("GF", 0),
            "GA": stats_by_abbr.get("GA", 0),
            "GD": stats_by_abbr.get("GD", 0),
            "Pts": stats_by_abbr.get("P", 0),
        }
        rows.append(row)

    # sanity
    rows = [r for r in rows if r["#"] is not None]
    rows.sort(key=lambda r: r["#"])
    if len(rows) < 18:
        raise RuntimeError(f"Only {len(rows)} rows scraped")
    return rows

def main():
    data = fetch_json(ESPN_STANDINGS)
    # children[0] → the league (there is usually one child)
    entries = (
        data.get("children", [{}])[0]
        .get("standings", {})
        .get("entries", [])
    )
    rows = entries_to_rows(entries)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    # touch a simple update stamp used in your header
    pathlib.Path("assets/update_stamp.txt").write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")
    print(f"wrote {OUT} with {len(rows)} rows")

if __name__ == "__main__":
    sys.exit(main())
