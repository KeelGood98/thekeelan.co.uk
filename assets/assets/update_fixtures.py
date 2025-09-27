import json, os, datetime, urllib.request

API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")  # add in repo secrets
TEAM_ID = 66  # Manchester United
BASE = "https://api.football-data.org/v4/teams/{}/matches?dateFrom={}&dateTo={}"

def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    today = datetime.date.today()
    date_from = (today - datetime.timedelta(days=30)).isoformat()
    date_to   = (today + datetime.timedelta(days=120)).isoformat()
    url = BASE.format(TEAM_ID, date_from, date_to)
    data = fetch(url, headers={"X-Auth-Token": API_KEY})

    fixtures = []
    for m in data.get("matches", []):
        utc = m["utcDate"][:10]  # YYYY-MM-DD
        comp = m["competition"]["name"]
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        venue = ""  # API doesn't give venue on team matches endpoint
        time_local = m["utcDate"][11:16]  # HH:MM (UTC—your frontend shows as provided)
        status_raw = m.get("status","")
        status = "upcoming"
        score = None
        if status_raw in ("FINISHED","AWARDED"):
            status = "FT"
            full = m.get("score",{}).get("fullTime",{})
            if full.get("home") is not None and full.get("away") is not None:
                score = f'{full["home"]}–{full["away"]}'
        elif status_raw in ("IN_PLAY","PAUSED"):
            status = "LIVE"

        fixtures.append({
            "date": utc, "time": time_local, "comp": comp,
            "home": home, "away": away, "status": status, "score": score,
            "venue": venue, "tv": []
        })

    # Merge TV overrides
    tv_path = "assets/tv_overrides.json"
    if os.path.exists(tv_path):
        with open(tv_path, "r", encoding="utf-8") as f:
            tv = json.load(f)
        for fx in fixtures:
            opponent = fx["away"] if fx["home"].lower().startswith("man") else fx["home"]
            key = f'{fx["date"]} {opponent}'
            if key in tv:
                fx["tv"] = tv[key]

    # Sort chronologically and write
    fixtures.sort(key=lambda x: (x["date"], x["time"]))
    os.makedirs("assets", exist_ok=True)
    with open("assets/fixtures.json", "w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
