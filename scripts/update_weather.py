#!/usr/bin/env python3
import json
from pathlib import Path
import requests

OUT = Path("assets/weather.json")

# Leeds coords
LAT, LON = 53.801277, -1.548567
API = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&windspeed_unit=mph"

def main():
    r = requests.get(API, timeout=30); r.raise_for_status()
    js = r.json()
    cur = js.get("current_weather", {})
    out = {
        "location": "Leeds",
        "temp_c": cur.get("temperature"),
        "wind_mph": cur.get("windspeed")
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__=="__main__":
    main()
