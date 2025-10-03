#!/usr/bin/env python3
import json
from pathlib import Path
import requests

OUT = Path("assets/f1.json")
ERGAST = "https://ergast.com/api/f1/current/results.json"

def main():
    try:
        r = requests.get(ERGAST, timeout=30); r.raise_for_status()
        js = r.json()
    except Exception:
        # write minimal file so UI doesn't explode
        OUT.write_text(json.dumps({"season":"","rounds":[]}, indent=2), encoding="utf-8")
        print("Ergast unavailable; wrote empty f1.json")
        return

    mrdata = js.get("MRData", {})
    races = (mrdata.get("RaceTable") or {}).get("Races") or []
    rounds=[]
    for race in races:
        results = race.get("Results") or []
        rounds.append({
            "race": f"{race.get('raceName','')} ({(race.get('Circuit') or {}).get('Location',{}).get('country','')})",
            "date": race.get("date",""),
            "results": [{
                "pos": r.get("position"),
                "driver": f"{(r.get('Driver') or {}).get('givenName','')} {(r.get('Driver') or {}).get('familyName','')}".strip(),
                "team": (r.get('Constructor') or {}).get('name',''),
                "pts": r.get("points")
            } for r in results[:10]]
        })
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"season":mrdata.get("RaceTable",{}).get("season",""),"rounds":rounds}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(rounds)} rounds)")

if __name__=="__main__":
    main()
