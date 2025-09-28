# update_fixtures.py
import json, time, urllib.request, ssl, os, datetime

ssl._create_default_https_context = ssl._create_unverified_context

TEAM_ID = "360"  # ESPN team id for Manchester United
URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{TEAM_ID}/schedule"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse():
    raw = json.loads(fetch(URL).decode("utf-8"))
    team_name = (raw.get("team") or {}).get("displayName","Manchester United")

    events = raw.get("events") or []
    matches = []

    def outcome_for_united(home_score, away_score, home_is_united):
        if home_score is None or away_score is None:
            return None
        diff = (home_score - away_score) if home_is_united else (away_score - home_score)
        if diff > 0: return "W"
        if diff == 0: return "D"
        return "L"

    for ev in events:
        try:
            comp = (ev.get("competitions") or [])[0]
        except Exception:
            continue

        date_iso = ev.get("date")
        comp_name = (comp.get("competitors") or [{}])[0].get("type","")  # ignored
        competition = (comp.get("venue") or {}).get("fullName","")      # ignored
        # ESPN puts competition name elsewhere:
        comp_name = (ev.get("competitions") or [{}])[0].get("details", "") or (ev.get("name") or ev.get("shortName") or "")
        if not comp_name:
            comp_name = (ev.get("leagues") or [{}])[0].get("name","")

        competitors = comp.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway")=="home"), None)
        away = next((c for c in competitors if c.get("homeAway")=="away"), None)
        if not home or not away: 
            continue

        home_name = (home.get("team") or {}).get("displayName")
        away_name = (away.get("team") or {}).get("displayName")

        # Filter strictly to games involving Manchester United (safety valve)
        if "manchester united" not in (home_name or "").lower() and "manchester united" not in (away_name or "").lower():
            continue

        def parse_score(node):
            try:
                return int((node.get("score") or {}).get("value"))
            except: 
                try: return int(node.get("score"))
                except: return None

        home_score = parse_score(home)
        away_score = parse_score(away)

        status_type = (((ev.get("status") or {}).get("type")) or {}).get("name","")
        finished = status_type.lower() in {"status_final","final","post","fulltime","status_postponed"} or (
            home_score is not None and away_score is not None
        )

        home_is_united = "manchester united" in (home_name or "").lower()
        oc = outcome_for_united(home_score, away_score, home_is_united) if finished else None

        matches.append({
            "date": date_iso,        # full ISO; we’ll format on the page
            "comp": comp_name or "",
            "home": home_name or "",
            "away": away_name or "",
            "status": "FINISHED" if finished else "SCHEDULED",
            "score": None if not finished else {
                "home": home_score,
                "away": away_score,
                "outcome": oc
            }
        })

    matches.sort(key=lambda m: m["date"] or "")
    return {
        "updated": int(time.time()*1000),
        "team": team_name,
        "matches": matches
    }

def main():
    os.makedirs("assets", exist_ok=True)
    out = parse()
    with open("assets/fixtures.json","w") as f:
        json.dump(out, f)
    print("wrote assets/fixtures.json with", len(out["matches"]), "matches")

if __name__ == "__main__":
    main()
