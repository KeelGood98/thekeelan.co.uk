#!/usr/bin/env python3
"""
Build assets/table.json with the current Premier League table.

We fetch data from the Premier League public API instead of scraping
Wikipedia/Skysports (which change markup often).

Output schema (list of 20 dicts):
[
  {
    "pos": 1, "team": "Liverpool", "P": 6, "W": 5, "D": 0, "L": 1,
    "GF": 12, "GA": 7, "GD": 5, "Pts": 15
  },
  ...
]

This matches what index.html expects.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import requests


API = "https://footballapi.pulselive.com/football"
HEADERS = {
    # These headers are required by the PL API when called from non-browser envs
    "Origin": "https://www.premierleague.com",
    "Referer": "https://www.premierleague.com/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def get_current_comp_season_id() -> int:
    """
    Look up the current Premier League competition season id.
    Competition id for PL is 1.

    API: /competitions/{compId}/compseasons
    """
    url = f"{API}/competitions/1/compseasons"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    seasons = r.json()  # list of {id, label, year, current, ...}

    # Prefer the one flagged 'current', otherwise the latest by id
    current = [s for s in seasons if s.get("current")]
    if current:
        return int(current[0]["id"])

    seasons_sorted = sorted(seasons, key=lambda s: int(s["id"]), reverse=True)
    return int(seasons_sorted[0]["id"])


def fetch_table(comp_season_id: int) -> List[Dict[str, Any]]:
    """
    API: /standings?compSeasons={id}&altIds=true&detail=2
    """
    params = {
        "compSeasons": comp_season_id,
        "altIds": "true",
        "detail": "2",
        "page": 0,
        "pageSize": 50,
    }
    url = f"{API}/standings"
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # The table is usually in standings[0]['table']
    try:
        table = data["standings"][0]["table"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected standings JSON shape: {e}")

    rows = []
    for row in table:
        # overall record
        overall = row["overall"]
        team = row["team"]["name"]
        rows.append(
            {
                "pos": row["position"],
                "team": team,
                "P": overall["played"],
                "W": overall["won"],
                "D": overall["drawn"],
                "L": overall["lost"],
                "GF": overall["goalsFor"],
                "GA": overall["goalsAgainst"],
                "GD": overall["goalDifference"],
                "Pts": overall["points"],
            }
        )
    if len(rows) < 18:
        raise RuntimeError(f"Only {len(rows)} rows scraped")
    return rows


def write_json(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} ({len(rows)} teams)")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    out_path = repo / "assets" / "table.json"

    comp_season_id = get_current_comp_season_id()
    rows = fetch_table(comp_season_id)
    write_json(rows, out_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
