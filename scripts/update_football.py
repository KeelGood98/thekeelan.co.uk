import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo


BASE_URL = "https://api.football-data.org/v4"
TOKEN = (
    os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    or os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
)

DATA_DIR = Path("data")
PL_TABLE_FILE = DATA_DIR / "pl_table.json"
MUFC_FIXTURES_FILE = DATA_DIR / "mufc_fixtures.json"
PL_STATS_FILE = DATA_DIR / "pl_stats.json"

UK_TZ = ZoneInfo("Europe/London")

MUFC_NAMES = {
    "Manchester United FC",
    "Manchester United",
    "Man United",
    "Man Utd"
}


def fetch_json(endpoint: str) -> dict:
    if not TOKEN:
        raise RuntimeError("Missing FOOTBALL_DATA_TOKEN or FOOTBALL_DATA_API_KEY environment variable")

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
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


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


def format_date(utc_date: str) -> str:
    if not utc_date:
        return "TBC"

    try:
        dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        uk_dt = dt.astimezone(UK_TZ)
        return uk_dt.strftime("%a %d %b, %H:%M")
    except Exception:
        return utc_date


def iso_to_uk_sort_value(utc_date: str) -> str:
    if not utc_date:
        return ""

    try:
        dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        return dt.astimezone(UK_TZ).isoformat()
    except Exception:
        return utc_date


def build_pl_table():
    raw = fetch_json("/competitions/PL/standings")
    table = raw["standings"][0]["table"]

    teams = []

    for row in table:
        team = row.get("team", {})

        teams.append({
            "position": safe_int(row.get("position")),
            "name": short_team_name(team.get("name", "")),
            "fullName": team.get("name", ""),
            "badge": team.get("crest", ""),
            "played": safe_int(row.get("playedGames")),
            "won": safe_int(row.get("won")),
            "drawn": safe_int(row.get("draw")),
            "lost": safe_int(row.get("lost")),
            "goalsFor": safe_int(row.get("goalsFor")),
            "goalsAgainst": safe_int(row.get("goalsAgainst")),
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


def score_text(score_part: dict) -> str:
    home_goals = score_part.get("home")
    away_goals = score_part.get("away")

    if home_goals is None or away_goals is None:
        return ""

    return f"{home_goals}-{away_goals}"


def get_full_time_score(match: dict) -> str:
    return score_text(match.get("score", {}).get("fullTime", {}))


def get_half_time_score(match: dict) -> str:
    return score_text(match.get("score", {}).get("halfTime", {}))


def get_winner(match: dict) -> str:
    winner = match.get("score", {}).get("winner")

    if winner == "HOME_TEAM":
        return short_team_name(match.get("homeTeam", {}).get("name", ""))

    if winner == "AWAY_TEAM":
        return short_team_name(match.get("awayTeam", {}).get("name", ""))

    if winner == "DRAW":
        return "Draw"

    return ""


def normalise_match(match: dict) -> dict:
    home = short_team_name(match.get("homeTeam", {}).get("name", ""))
    away = short_team_name(match.get("awayTeam", {}).get("name", ""))
    status = match.get("status", "")

    return {
        "id": match.get("id"),
        "date": format_date(match.get("utcDate", "")),
        "sortDate": iso_to_uk_sort_value(match.get("utcDate", "")),
        "competition": match.get("competition", {}).get("name", "Premier League"),
        "matchday": match.get("matchday"),
        "home": home,
        "away": away,
        "score": get_full_time_score(match),
        "halfTimeScore": get_half_time_score(match),
        "winner": get_winner(match),
        "result": get_result_for_mufc(match) if status == "FINISHED" else "",
        "venue": "TBC",
        "channel": "TBC" if status != "FINISHED" else "",
        "status": status
    }


def build_mufc_fixtures():
    raw = fetch_json("/competitions/PL/matches")
    matches = [m for m in raw.get("matches", []) if match_involves_mufc(m)]

    allowed_statuses = {"FINISHED", "TIMED", "SCHEDULED", "IN_PLAY", "PAUSED", "POSTPONED"}
    matches = [m for m in matches if m.get("status") in allowed_statuses]

    finished = [m for m in matches if m.get("status") == "FINISHED"][-6:]
    upcoming = [m for m in matches if m.get("status") != "FINISHED"][:8]

    recent_results = [normalise_match(match) for match in finished]
    upcoming_fixtures = [normalise_match(match) for match in upcoming]
    all_selected = recent_results + upcoming_fixtures

    next_match = upcoming_fixtures[0] if upcoming_fixtures else None

    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "team": "Manchester United",
        "nextMatch": next_match,
        "recentResults": recent_results,
        "upcomingFixtures": upcoming_fixtures,
        "fixtures": all_selected
    }


def normalise_scorer(item: dict) -> dict:
    player = item.get("player", {})
    team = item.get("team", {})

    return {
        "name": player.get("name", "Unknown"),
        "firstName": player.get("firstName", ""),
        "lastName": player.get("lastName", ""),
        "nationality": player.get("nationality", ""),
        "team": short_team_name(team.get("name", "")),
        "teamBadge": team.get("crest", ""),
        "goals": safe_int(item.get("goals")),
        "assists": safe_int(item.get("assists")),
        "penalties": safe_int(item.get("penalties"))
    }


def build_pl_stats(table_data: dict):
    scorers_raw = fetch_json("/competitions/PL/scorers")
    scorers = [normalise_scorer(item) for item in scorers_raw.get("scorers", [])[:10]]

    teams = table_data.get("teams", [])

    best_attacks = sorted(
        teams,
        key=lambda team: safe_int(team.get("goalsFor")),
        reverse=True
    )[:5]

    best_defences = sorted(
        teams,
        key=lambda team: safe_int(team.get("goalsAgainst"))
    )[:5]

    goal_difference_leaders = sorted(
        teams,
        key=lambda team: safe_int(team.get("goalDifference")),
        reverse=True
    )[:5]

    man_united = next(
        (
            team for team in teams
            if team.get("fullName") in MUFC_NAMES or team.get("name") in MUFC_NAMES
        ),
        None
    )

    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "competition": "Premier League",
        "topScorers": scorers,
        "bestAttacks": [
            {
                "name": team.get("name"),
                "badge": team.get("badge", ""),
                "goalsFor": team.get("goalsFor", 0),
                "played": team.get("played", 0)
            }
            for team in best_attacks
        ],
        "bestDefences": [
            {
                "name": team.get("name"),
                "badge": team.get("badge", ""),
                "goalsAgainst": team.get("goalsAgainst", 0),
                "played": team.get("played", 0)
            }
            for team in best_defences
        ],
        "goalDifferenceLeaders": [
            {
                "name": team.get("name"),
                "badge": team.get("badge", ""),
                "goalDifference": team.get("goalDifference", 0),
                "played": team.get("played", 0)
            }
            for team in goal_difference_leaders
        ],
        "manUnitedSummary": man_united
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    table = build_pl_table()
    fixtures = build_mufc_fixtures()
    stats = build_pl_stats(table)

    write_json(PL_TABLE_FILE, table)
    write_json(MUFC_FIXTURES_FILE, fixtures)
    write_json(PL_STATS_FILE, stats)

    print(f"Wrote {PL_TABLE_FILE}")
    print(f"Wrote {MUFC_FIXTURES_FILE}")
    print(f"Wrote {PL_STATS_FILE}")


if __name__ == "__main__":
    main()
