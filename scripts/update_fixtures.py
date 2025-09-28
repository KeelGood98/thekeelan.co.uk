#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json for Manchester United using TheSportsDB.
- Does NOT touch the league table or extras.
- Uses a locked team id (MUFC) to avoid any search ambiguity.
- Fetches the *entire season* schedule, then derives:
  • Upcoming (no score yet)
  • Recent Results (with score + W/D/L outcome from MU perspective)

Also merges optional TV overrides from assets/tv_overrides.json.

Output:
{
  "updated": 1695920000000,
  "team": "Manchester United",
  "matches": [
    {
      "date": "2025-09-27T11:30:00Z",
      "comp": "English Premier League",
      "home": "Brentford",
      "away": "Manchester United",
      "status": "FINISHED" | "SCHEDULED",
      "tv": "Sky Sports",
      "score": {"home": 1, "away": 3, "outcome": "W"}   # present only for finished games
    }
  ]
}
"""

import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

# ---------- CONFIG ----------
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TEAM_NAME = "Manchester United"
TEAM_ID   = "133612"  # hard-coded MUFC id on TheSportsDB (prevents any “Bolton” drift)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FIXTURES_PATH = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_PATH = os.path.join(ASSETS_DIR, "tv_overrides.json")
# ---------------------------

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"keelan-mufc/1.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def json_get(url):
    return json.loads(fetch(url).decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

def current_pl_season():
    """
    Return current season string like '2025-2026' with July rollover.
    """
    now = datetime.utcnow()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{start}-{start+1}"

def to_iso_utc(ts: str, date_str: str, time_str: str) -> str:
    """
    Convert TheSportsDB timestamps to ISO 8601 UTC (Z).
    Prefer strTimestamp (already has offset). Else combine dateEvent + strTime.
    """
    dt = None
    if ts:
        try:
            # e.g. "2025-09-27 11:30:00+00:00"
            ts_norm = ts.replace(" ", "T")
            dt = datetime.fromisoformat(ts_norm)
        except Exception:
            dt = None
    if dt is None and date_str:
        try:
            t = (time_str or "00:00:00")
            if len(t) == 5: t += ":00"
            dt = datetime.fromisoformat(f"{date_str}T{t}")
        except Exception:
            dt = None
    if dt is None:
        dt = datetime.utcnow().replace(tzinfo=timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def to_int(x):
    try:
        return int(x)
    except Exception:
        return None

def build_match(ev: dict) -> dict:
    """
    Convert a TSDB season event to our match dict.
    """
    date_iso = to_iso_utc(
        ev.get("strTimestamp") or "",
        ev.get("dateEvent") or "",
        ev.get("strTime") or ""
    )
    comp = ev.get("strLeague") or ""
    home = ev.get("strHomeTeam") or ""
    away = ev.get("strAwayTeam") or ""
    tv   = ev.get("strTVStation") or ""  # often empty on TSDB free tier

    hs = to_int(ev.get("intHomeScore"))
    as_ = to_int(ev.get("intAwayScore"))

    # decide finished based on whether scores exist OR kickoff already passed
    now_ms = time.time() * 1000
    try:
        dt_ms = datetime.fromisoformat(date_iso.replace("Z","+00:00")).timestamp() * 1000
    except Exception:
        dt_ms = now_ms

    is_finished = (hs is not None and as_ is not None) or (dt_ms < now_ms - 2*60*60*1000)  # 2h grace
    status = "FINISHED" if is_finished and (hs is not None and as_ is not None) else ("SCHEDULED" if dt_ms >= now_ms else "SCHEDULED")

    match = {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "status": status,
        "tv": tv
    }

    # add score + outcome if we have a result
    if hs is not None and as_ is not None:
        outcome = None
        if home.lower() == TEAM_NAME.lower():
            if hs > as_: outcome = "W"
            elif hs == as_: outcome = "D"
            else: outcome = "L"
        elif away.lower() == TEAM_NAME.lower():
            if as_ > hs: outcome = "W"
            elif as_ == hs: outcome = "D"
            else: outcome = "L"

        match["score"] = {"home": hs, "away": as_}
        if outcome:
            match["score"]["outcome"] = outcome

    return match

def apply_tv_overrides(matches):
    """
    Optionally set/override TV channel.
    Supports:
      - by_date:  {"2025-09-27": "Sky Sports"}
      - by_exact: {"2025-09-27T11:30:00Z|Brentford v Manchester United": "TNT Sports"}
    """
    if not os.path.exists(TV_OVERRIDES_PATH):
        return
    try:
        with open(TV_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            ov = json.load(f) or {}
    except Exception:
        return

    by_date  = ov.get("by_date") or {}
    by_exact = ov.get("by_exact") or {}

    for m in matches:
        d = m.get("date","")[:10]
        k = f'{m.get("date","")}|{m.get("home","")} v {m.get("away","")}'
        if k in by_exact:
            m["tv"] = by_exact[k]
        elif d in by_date:
            m["tv"] = by_date[d]

def main():
    ensure_assets()

    season = current_pl_season()
    # Season schedule for MUFC
    url = TSDB_BASE + f"eventsseason.php?id={TEAM_ID}&s={urllib.parse.quote(season)}"

    try:
        data = json_get(url)
        events = (data or {}).get("events") or []
    except Exception as e:
        print("ERROR: failed to fetch season events:", e, file=sys.stderr)
        events = []

    matches = [build_match(ev) for ev in events if (ev.get("strHomeTeam") or ev.get("strAwayTeam"))]

    # sort chronologically
    matches.sort(key=lambda m: m["date"])

    # TV overrides if you maintain them
    apply_tv_overrides(matches)

    out = {
        "updated": int(time.time()*1000),
        "team": TEAM_NAME,
        "matches": matches
    }
    with open(FIXTURES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {FIXTURES_PATH} with {len(matches)} matches for season {season}")

if __name__ == "__main__":
    main()
