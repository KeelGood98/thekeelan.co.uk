# update_fixtures.py
import json, time, urllib.request, ssl, os

ssl._create_default_https_context = ssl._create_unverified_context
TEAM_ID = "360"  # Manchester United
URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{TEAM_ID}/schedule"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse_tv(comp):
    # ESPN geoBroadcasts -> take TV names (if any)
    gbs = comp.get("geoBroadcasts") or []
    names=[]
    for gb in gbs:
        typ = (gb.get("type") or {}).get("shortName","").lower()
        name = (gb.get("media") or {}).get("shortName") or gb.get("market") or gb.get("region")
        if typ in {"tv","web"} and name:
            names.append(str(name))
    # de-dupe, keep order
    seen=set(); out=[]
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return ", ".join(out) if out else None

def outcome_for_united(home_score, away_score, home_is_united):
    if home_score is None or away_score is None:
        return None
    diff = (home_score - away_score) if home_is_united else (away_score - home_score)
    if diff > 0: return "W"
    if diff == 0: return "D"
    return "L"

def main():
    raw = json.loads(fetch(URL).decode("utf-8"))
    events = raw.get("events") or []
    matches=[]
    for ev in events:
        comps = ev.get("competitions") or []
        if not comps: 
            continue
        comp = comps[0]
        competitors = comp.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway")=="home"), None)
        away = next((c for c in competitors if c.get("homeAway")=="away"), None)
        if not home or not away:
            continue
        home_name = (home.get("team") or {}).get("displayName","")
        away_name = (away.get("team") or {}).get("displayName","")
        if "manchester united" not in home_name.lower() and "manchester united" not in away_name.lower():
            continue

        def score_of(c):
            sc = c.get("score")
            if isinstance(sc, dict) and "value" in sc:
                try: return int(sc["value"])
                except: return None
            try: return int(sc)
            except: return None

        hs = score_of(home)
        as_ = score_of(away)
        status_type = (((ev.get("status") or {}).get("type")) or {}).get("name","")
        finished = (status_type or "").lower() in {"status_final","final","post","fulltime"} or (hs is not None and as_ is not None)

        oc = outcome_for_united(hs, as_, "manchester united" in home_name.lower()) if finished else None
        tv = parse_tv(comp)

        # competition name
        comp_name = (ev.get("leagues") or [{}])[0].get("name") or ev.get("name") or ev.get("shortName") or ""

        matches.append({
            "date": ev.get("date"),
            "comp": comp_name,
            "home": home_name,
            "away": away_name,
            "status": "FINISHED" if finished else "SCHEDULED",
            "tv": tv,
            "score": None if not finished else {"home": hs, "away": as_, "outcome": oc}
        })

    matches.sort(key=lambda m: m["date"] or "")
    os.makedirs("assets", exist_ok=True)
    with open("assets/fixtures.json","w") as f:
        json.dump({"updated": int(time.time()*1000), "team":"Manchester United", "matches": matches}, f)
    print("wrote assets/fixtures.json", len(matches))

if __name__ == "__main__":
    main()
