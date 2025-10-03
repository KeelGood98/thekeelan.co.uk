#!/usr/bin/env python3
import json, sys, os, requests

OUT="assets/weather.json"
# Leeds approx
LAT, LON = 53.799, -1.549
URL=f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,wind_speed_10m&timezone=Europe%2FLondon"

def main():
    try:
        r=requests.get(URL,timeout=20)
        r.raise_for_status()
        j=r.json()
        cur=j.get("current_weather") or j.get("current") or j.get("current_units") or j.get("current")
        if "current_weather" in j:
            current={"temperature":j["current_weather"]["temperature"], "wind_mph": j["current_weather"]["windspeed"]*0.621371}
        elif j.get("current"):
            current={"temperature": j["current"]["temperature_2m"], "wind_mph": j["current"]["wind_speed_10m"]*0.621371}
        else:
            current={"temperature": 0, "wind_mph": 0}
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT,"w",encoding="utf-8") as f:
            json.dump({"current":current}, f, ensure_ascii=False, indent=2)
        print(f"wrote {OUT}")
    except Exception as e:
        print(f"[update_weather] Non-fatal: {e}")
        sys.exit(0)

if __name__=="__main__":
    main()
