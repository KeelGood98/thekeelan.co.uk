#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch current-season F1 race results via Ergast, write assets/f1.json
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

ASSETS = "assets"
API = "https://ergast.com/api/f1/current/results.json?limit=1000"


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GHAction/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    os.makedirs(ASSETS, exist_ok=True)
    data = json.loads(fetch(API).decode("utf-8"))
    races = (
        data.get("MRData", {})
        .get("RaceTable", {})
        .get("Races", [])
    )

    out = []
    for r in races:
        race_name = r.get("raceName")
        country = r.get("Circuit", {}).get("Location", {}).get("country")
        date = r.get("date")
        time = (r.get("time") or "00:00:00Z").replace("Z", "+00:00")
        iso_utc = f"{date}T{time}"
        results = r.get("Results", [])

        top3 = []
        for res in results[:3]:
            driver = res.get("Driver", {})
            name = f"{driver.get('givenName','')} {driver.get('familyName','')}".strip()
            team = res.get("Constructor", {}).get("name")
            pos = res.get("position")
            pts = res.get("points")
            top3.append({"pos": pos, "name": name, "team": team, "pts": pts})

        out.append(
            {
                "round": r.get("round"),
                "race": race_name,
                "country": country,
                "date_utc": iso_utc,
                "top3": top3,
            }
        )

    with open(os.path.join(ASSETS, "f1.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"updated": datetime.now(timezone.utc).isoformat(), "races": out},
            f,
            ensure_ascii=False,
        )
    print(f"Wrote assets/f1.json with {len(out)} races")


if __name__ == "__main__":
    main()
