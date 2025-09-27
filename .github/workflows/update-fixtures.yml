# assets/update_fixtures.py
# Build assets/fixtures.json for thekeelan.co.uk
# Source: TheSportsDB (free, no API key)

import json
import os
import urllib.request
import urllib.parse
import datetime

TEAM_ID = "133612"                  # Manchester United (TheSportsDB)
TEAM_NAME = "Manchester United"

def fetch(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def current_season() -> str:
    today = datetime.date.today()
    if today.month >= 8:
        return f"{today.year}-{today.year+1}"
    return f"{today.year-1}-{today.year}"

def map_event(e: dict) -> dict:
    date = (e.get("dateEvent") or e.get("dateEventLocal") or "")[:10]
    time = (e.get("strTime") or e.get("strTimeLocal") or "00:00")[:5]
    comp = e.get("strLeague") or ""
    home = e.get("strHomeTeam") or ""
    away = e.get("strAwayTeam") or ""
    venue = e.get("strVenue") or ""

    status = "upcoming"
    score = None
    if e.get("intHomeScore") is not None and e.get("intAwayScore") is not None:
        status = "FT"
        score = f'{e["intHomeScore"]}–{e["intAwayScore"]}'

    return {
        "date": date,
        "time": time,
        "comp": comp,
        "home": home,
        "away": away,
        "status": status,
        "score": score,
        "venue": venue,
        "tv": [],
        "homeBadge": None,
        "awayBadge": None,
    }

def build_badge_map() -> dict:
    """Return { teamNameLower: badgeUrl } for Premier League clubs."""
    league = "English Premier League"
    url = "https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=" + urllib.parse.quote(league)
    try:
        data = fetch(url)
        teams = data.get("teams") or []
        return { (t.get("strTeam") or "").lower(): t.get("strTeamBadge") for t in teams if t.get("strTeam") }
    except Exception as ex:
        print("Badge map fetch failed:", ex)
        return {}

def main():
    season = current_season()
    print("Season:", season)

    # Endpoints
    url_season = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={TEAM_ID}&s={season}"
    url_next   = f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={TEAM_ID}"
    url_last   = f"https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={TEAM_ID}"

    all_events = []
    for name, url in [("season", url_season), ("next", url_next), ("last", url_last)]:
        try:
            data = fetch(url)
            key = "events" if name != "last" else "results"
            events = data.get(key) or []
            print(f"Fetched {name}: {len(events)}")
            all_events.extend(events)
        except Exception as ex:
            print(f"Fetch {name} failed:", ex)

    # Keep only actual Manchester United matches (home or away)
    filtered = [
        e for e in all_events
        if (e.get("strHomeTeam") == TEAM_NAME or e.get("strAwayTeam") == TEAM_NAME)
    ]

    # Map into our simplified structure
    fixtures = [map_event(e) for e in filtered]

    # Attach badges (Premier League clubs guaranteed; others best-effort None)
    badge_map = build_badge_map()
    for fx in fixtures:
        fx["homeBadge"] = badge_map.get((fx["home"] or "").lower())
        fx["awayBadge"] = badge_map.get((fx["away"] or "").lower())

    # Merge manual UK TV overrides if present
    tv_overrides = {}
    try:
        with open("assets/tv_overrides.json", "r", encoding="utf-8") as f:
            tv_overrides = json.load(f)
    except FileNotFoundError:
        pass

    for fx in fixtures:
        opponent = fx["away"] if (fx["home"] or "").lower().startswith("man") else fx["home"]
        key = f'{fx["date"]} {opponent}'
        if key in tv_overrides:
            fx["tv"] = tv_overrides[key]

    # Sort & de-duplicate
    fixtures.sort(key=lambda x: (x["date"], x["time"]))
    seen = set()
    dedup = []
    for f in fixtures:
        k = (f["date"], f["home"], f["away"])
        if k not in seen:
            seen.add(k); dedup.append(f)

    os.makedirs("assets", exist_ok=True)
    with open("assets/fixtures.json", "w", encoding="utf-8") as out:
        json.dump(dedup, out, ensure_ascii=False, indent=2)

    print("Wrote assets/fixtures.json with", len(dedup), "entries")

if __name__ == "__main__":
    main()
