import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://api.football-data.org/v4"
TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()

DATA_DIR = Path("data")
PL_TABLE_FILE = DATA_DIR / "pl_table.json"
MUFC_FIXTURES_FILE = DATA_DIR / "mufc_fixtures.json"

MUFC_NAMES = {
    "Manchester United FC",
    "Manchester United",
    "Man United",
    "Man Utd"
}


def fetch_json(endpoint: str) -> dict:
    if not TOKEN:
        raise RuntimeError("Missing FOOTBALL_DATA_TOKEN environment variable")

    request = Request(
        f"{BASE_URL}{endpoint}",
        headers={
            "X-Auth-Token": TOKEN,
            "User-Agent": "thekeelan.co.uk GitHub Pages updater"
        }
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {endpoint}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Network error from {endpoint}: {error}") from error


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def format_date(utc_date: str) -> str:
    if not utc_date:
        return "TBC"

    try:
        dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        return dt.strftime("%a %d %b, %H:%M")
    except Exception:
        return utc_date


def short_team_name(name: str) -> str:
    replacements = {
        " FC": "",
        "AFC": "",
        "Manchester United": "Manchester United",
        "Manchester City": "Manchester City",
        "Tottenham Hotspur": "Tottenham",
        "Brighton & Hove Albion": "Brighton",
        "Wolverhampton Wanderers": "Wolves",
        "Nottingham Forest": "Nott'm Forest",
        "Newcastle United": "Newcastle",
        "West Ham United": "West Ham"
    }

    clean = name or "Unknown"

    for old, new in replacements.items():
        clean = clean.replace(old, new)

    return clean.strip()


def build_pl_table():
    raw = fetch_json("/competitions/PL/standings")
    table = raw["standings"][0]["table"]

    teams = []

    for row in table:
        team = row.get("team", {})

        teams.append({
            "position": safe_int(row.get("position")),
            "name": short_team_name(team.get("name", "")),
            "badge": team.get("crest", ""),
            "played": safe_int(row.get("playedGames")),
            "won": safe_int(row.get("won")),
            "drawn": safe_int(row.get("draw")),
            "lost": safe_int(row.get("lost")),
            "goalDifference": safe_int(row.get("goalDifference")),
            "points": safe_int(row.get("points"))
        })

    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "teams": teams
    }


def match_involves_mufc(match: dict) -> bool:
    home = match.get("homeTeam", {}).get("name", "")
    away = match.get("awayTeam", {}).get("name", "")

    return home in MUFC_NAMES or away in MUFC_NAMES


def get_result_for_mufc(match: dict) -> str:
    score = match.get("score", {}).get("fullTime", {})
    home_goals = score.get("home")
    away_goals = score.get("away")

    if home_goals is None or away_goals is None:
        return ""

    home = match.get("homeTeam", {}).get("name", "")
    away = match.get("awayTeam", {}).get("name", "")

    if home_goals == away_goals:
        return "D"

    mufc_home = home in MUFC_NAMES
    mufc_won = (mufc_home and home_goals > away_goals) or ((not mufc_home) and away_goals > home_goals)

    return "W" if mufc_won else "L"


def get_score(match: dict) -> str:
    score = match.get("score", {}).get("fullTime", {})
    home_goals = score.get("home")
    away_goals = score.get("away")

    if home_goals is None or away_goals is None:
        return ""

    return f"{home_goals}-{away_goals}"


def build_mufc_fixtures():
    raw = fetch_json("/competitions/PL/matches")
    matches = [m for m in raw.get("matches", []) if match_involves_mufc(m)]

    # Keep recent completed games and upcoming games.
    priority_statuses = {"FINISHED", "TIMED", "SCHEDULED", "IN_PLAY", "PAUSED"}
    matches = [m for m in matches if m.get("status") in priority_statuses]

    finished = [m for m in matches if m.get("status") == "FINISHED"][-5:]
    upcoming = [m for m in matches if m.get("status") != "FINISHED"][:8]

    chosen = finished + upcoming

    fixtures = []

    for match in chosen:
        home = short_team_name(match.get("homeTeam", {}).get("name", ""))
        away = short_team_name(match.get("awayTeam", {}).get("name", ""))
        status = match.get("status", "")

        fixtures.append({
            "date": format_date(match.get("utcDate", "")),
            "competition": match.get("competition", {}).get("name", "Premier League"),
            "home": home,
            "away": away,
            "score": get_score(match),
            "result": get_result_for_mufc(match) if status == "FINISHED" else "",
            "venue": "TBC",
            "channel": "TBC" if status != "FINISHED" else "",
            "status": status
        })

    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "fixtures": fixtures
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    table = build_pl_table()
    fixtures = build_mufc_fixtures()

    write_json(PL_TABLE_FILE, table)
    write_json(MUFC_FIXTURES_FILE, fixtures)

    print(f"Wrote {PL_TABLE_FILE}")
    print(f"Wrote {MUFC_FIXTURES_FILE}")


if __name__ == "__main__":
    main()
