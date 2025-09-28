#!/usr/bin/env python3
import json, time, urllib.request, urllib.parse, os

API  = "https://www.thesportsdb.com/api/v1/json/3"
TEAM = "Manchester United"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"thekeelan-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def ts(e):
    if e.get("strTimestamp"): return e["strTimestamp"]
    d = e.get("dateEvent") or e.get("dateEventLocal") or ""
    t = e.get("strTime") or "00:00:00"
    if len(t)==5: t += ":00"
    return f"{d}T{t}Z"

def main():
    os.makedirs("assets", exist_ok=True)

    # Resolve MUFC id
    tid = ""
    for t in (get(f"{API}/searchteams.php?t={urllib.parse.quote(TEAM)}").get("teams") or []):
        if (t.get("strTeam") or "").strip().lower() == TEAM.lower():
            tid = t.get("idTeam"); break

    nexts = get(f"{API}/eventsnext.php?id={tid}").get("events") or []
    lasts = get(f"{API}/eventslast.php?id={tid}").get("results") or []

    def map_up(e):
        return {"date":ts(e),"comp":e.get("strLeague") or "",
                "home":e.get("strHomeTeam"),"away":e.get("strAwayTeam"),
                "status":"SCHEDULED","tv":""}

    def map_res(e):
        hs=int(e.get("intHomeScore") or 0); as_=int(e.get("intAwayScore") or 0)
        if (e.get("strHomeTeam") or "").lower()==TEAM.lower():
            oc = "W" if hs>as_ else ("L" if hs<as_ else "D")
        else:
            oc = "W" if as_>hs else ("L" if as_<hs else "D")
        return {"date":ts(e),"comp":e.get("strLeague") or "",
                "home":e.get("strHomeTeam"),"away":e.get("strAwayTeam"),
                "status":"FINISHED","score":{"home":hs,"away":as_,"outcome":oc}}

    data={"updated":int(time.time()*1000),
          "matches":[*map(map_up,nexts), *map(map_res,lasts)]}

    with open("assets/fixtures.json","w") as f: json.dump(data, f)

if __name__=="__main__":
    main()
