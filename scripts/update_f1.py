#!/usr/bin/env python3
import json, sys, os, requests
from datetime import datetime

OUT="assets/f1.json"
YEAR = datetime.utcnow().year  # current season

def main():
    try:
        # OpenF1 races list
        races = requests.get(f"https://api.openf1.org/v1/races?year={YEAR}", timeout=25).json()
        # Only completed races (have session key)
        races = [r for r in races if r.get("circuit_short_name")]

        results = []
        for r in races:
            # top 3 finishers for that race
            session_key = r.get("session_key")
            if not session_key:
                continue
            res = requests.get(f"https://api.openf1.org/v1/results?session_key={session_key}&position<=3", timeout=25).json()
            top3=[]
            for row in sorted(res, key=lambda x:int(x.get("position", 999))):
                top3.append({
                    "pos": int(row["position"]),
                    "name": row.get("driver_name",""),
                    "team": row.get("team_name","")
                })
            results.append({
                "round": r.get("round"),
                "race": r.get("country_name") or r.get("circuit_short_name",""),
                "country": r.get("country_name",""),
                "date_uk": (r.get("date_start_utc") or "")[:10],
                "top3": top3
            })

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT,"w",encoding="utf-8") as f:
            json.dump({"season":YEAR,"races":results}, f, ensure_ascii=False, indent=2)
        print(f"wrote {OUT}: {len(results)} races")
    except Exception as e:
        print(f"[update_f1] Non-fatal: {e}")
        sys.exit(0)

if __name__=="__main__":
    main()
