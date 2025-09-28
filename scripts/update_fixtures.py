#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json for Manchester United using TheSportsDB.
- Keeps the league table untouched (this script only touches fixtures.json).
- Writes scores + W/D/L outcomes for past matches so the UI can colour rows.
- Includes upcoming fixtures.
- Merges optional TV overrides from assets/tv_overrides.json if present.

Works with the free v3 key ("3").

Output format:
{
  "updated": <epoch_ms>,
  "team": "Manchester United",
  "matches": [
     {
       "date": "2025-09-27T11:30:00Z",
       "comp": "English Premier League",
       "home": "Brentford",
       "away": "Manchester United",
       "status": "FINISHED" | "SCHEDULED",
       "tv": "Sky Sports",
       "score": {"home": 1, "away": 3, "outcome": "W"}  # outcome is from MU perspective
     },
     ...
  ]
}
"""

import json, sys, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TEAM_NAME = "Manchester United"   # change if you ever want another club

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FIXTURES_PATH = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_PATH = os.path.join(ASSETS_DIR, "tv_overrides.json")

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"keelan-fixtures/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def json_get(url):
    return json.loads(fetch(url).decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

def get_team_id(team_name: str) -> str:
    """Look up TheSportsDB id for the given team. Fallback to known id if needed."""
    try:
        data = json_get(TSDB_BASE + "searchteams.php?t=" + urllib.parse.quote(team_name))
        teams = (data or {}).get("teams") or []
        if teams:
            return teams[0].get("idTeam") or ""
    except Exception:
        pass
    # Known MUFC id (safety fallback)
    return "133612"

def to_iso_utc(ts: str, date_str: str, time_str: str) -> str:
    """
    Convert TheSportsDB timestamps to ISO 8601 UTC (Z).
    - Prefer strTimestamp (UTC with offset)
    - Else combine dateEvent + strTime (assume UTC if no tz info)
    """
    dt = None
    if ts:
        # e.g. "2025-09-27 11:30:00+00:00"
        try:
            ts_norm = ts.replace(" ", "T")
            dt = datetime.fromisoformat(ts_norm)
        except Exception:
            dt = None
    if dt is None and date_str:
        try:
            # strTime may be "15:00:00" or "15:00"
            t = (time_str or "00:00:00")
            if len(t) == 5: t += ":00"
            dt = datetime.fromisoformat(f"{date_str}T{t}")
        except Exception:
            dt = None
    if dt is None:
        # last resort: now
        dt = datetime.utcnow().replace(tzinfo=timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def build_match(ev: dict, mu_name: str, status_hint: str = "") -> dict:
    """Convert a TSDB event to our match dict."""
    date_iso = to_iso_utc(
        ev.get("strTimestamp") or "",
        ev.get("dateEvent") or "",
        ev.get("strTime") or ""
    )

    home = ev.get("strHomeTeam") or ""
    away = ev.get("strAwayTeam") or ""
    comp = ev.get("strLeague") or ""
    tv = ev.get("strTVStation") or ""  # often empty from TSDB
    ih = ev.get("intHomeScore")
    ia = ev.get("intAwayScore")

    # Coerce scores to ints if possible
    def to_int(x):
        try:
            return int(x)
        except Exception:
            return None

    hs = to_int(ih)
    as_ = to_int(ia)

    status = status_hint or ("FINISHED" if (hs is not None and as_ is not None) else "SCHEDULED")

    # Work out W/D/L from MU perspective
    outcome = None
    if status == "FINISHED" and hs is not None and as_ is not None:
        if home.lower() == mu_name.lower():
            if hs > as_: outcome = "W"
            elif hs == as_: outcome = "D"
            else: outcome = "L"
        elif away.lower() == mu_name.lower():
            if as_ > hs: outcome = "W"
            elif as_ == hs: outcome = "D"
            else: outcome = "L"

    match = {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "status": status,
        "tv": tv or "",
    }
    if hs is not None and as_ is not None:
        match["score"] = {"home": hs, "away": as_}
        if outcome:
            match["score"]["outcome"] = outcome
    return match

def apply_tv_overrides(matches):
    """Apply optional TV overrides by YYYY-MM-DD key or by exact date+opponent."""
    if not os.path.exists(TV_OVERRIDES_PATH):
        return
    try:
        with open(TV_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            ov = json.load(f) or {}
    except Exception:
        return

    # Supports:
    # 1) ov["by_date"]["2025-09-27"] = "Sky Sports"
    # 2) ov["by_exact"]["2025-09-27T11:30:00Z|Brentford v Manchester United"] = "TNT"
    by_date = (ov.get("by_date") or {})
    by_exact = (ov.get("by_exact") or {})

    for m in matches:
        try:
            d = m.get("date","")[:10]
            key_exact = f'{m.get("date","")}|{m.get("home","")} v {m.get("away","")}'
            if key_exact in by_exact:
                m["tv"] = by_exact[key_exact]
            elif d in by_date:
                m["tv"] = by_date[d]
        except Exception:
            pass

def main():
    ensure_assets()
    team_id = get_team_id(TEAM_NAME)

    last_url = TSDB_BASE + "eventslast.php?id=" + team_id   # past results
    next_url = TSDB_BASE + "eventsnext.php?id=" + team_id   # upcoming fixtures

    results = []
    upcoming = []

    # Load last results
    try:
        j = json_get(last_url)
        for ev in (j.get("results") or []):
            results.append(build_match(ev, TEAM_NAME, status_hint="FINISHED"))
    except Exception as e:
        print("WARNING: failed to fetch last results:", e, file=sys.stderr)

    # Load next fixtures
    try:
        j = json_get(next_url)
        for ev in (j.get("events") or []):
            upcoming.append(build_match(ev, TEAM_NAME, status_hint="SCHEDULED"))
    except Exception as e:
        print("WARNING: failed to fetch next events:", e, file=sys.stderr)

    # Combine & apply overrides
    matches = sorted(results + upcoming, key=lambda m: m["date"])
    apply_tv_overrides(matches)

    out = {
        "updated": int(time.time()*1000),
        "team": TEAM_NAME,
        "matches": matches
    }
    with open(FIXTURES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {FIXTURES_PATH} with {len(matches)} matches")

if __name__ == "__main__":
    main()
