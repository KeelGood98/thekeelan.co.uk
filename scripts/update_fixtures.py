#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json for Manchester United without breaking anything else.

Strategy (robust on free tier):
  1) Pull next 5 and last 5 directly from MUFC team endpoints:
       - eventsnext.php?id=<TEAM_ID>
       - eventslast.php?id=<TEAM_ID>
     These work well and stay on the correct team when you use the team id.
  2) (Optional) Try to top up upcoming by reading the Premier League season feed
     (league id 4328). If it fails/empty on your tier, we simply skip it.
  3) Merge optional TV overrides from assets/tv_overrides.json.

Output (unchanged shape):
{
  "updated": 1695920000000,
  "team": "Manchester United",
  "matches": [
    {
      "date": "2025-09-27T11:30:00Z",
      "comp": "English Premier League",
      "home": "Brentford",
      "away": "Manchester United",
      "status": "SCHEDULED" | "FINISHED",
      "tv": "Sky Sports",
      "score": {"home": 1, "away": 3, "outcome": "W"}  # only for finished
    }
  ]
}
"""

import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

# ---------- CONFIG ----------
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TEAM_NAME = "Manchester United"
TEAM_ID   = "133612"  # MUFC (locks the team, prevents "Bolton" drift)
PL_LEAGUE_ID = "4328"  # Premier League (used only to *optionally* top up upcoming)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FIXTURES_PATH = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_PATH = os.path.join(ASSETS_DIR, "tv_overrides.json")
# ---------------------------

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "keelan-mufc/1.2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def json_get(url):
    return json.loads(fetch(url).decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

def to_iso_utc(ts: str, date_str: str, time_str: str) -> str:
    """
    Convert TSDB timestamps to ISO8601 UTC (Z). Prefer strTimestamp if present.
    """
    dt = None
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace(" ", "T"))
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

def outcome_for_mu(home, away, hs, as_):
    if hs is None or as_ is None:
        return None
    hn = (home or "").lower()
    an = (away or "").lower()
    mu = TEAM_NAME.lower()
    if hn == mu:
        if hs > as_: return "W"
        if hs == as_: return "D"
        return "L"
    if an == mu:
        if as_ > hs: return "W"
        if as_ == hs: return "D"
        return "L"
    return None

def build_match_from_event(ev: dict) -> dict:
    date_iso = to_iso_utc(
        ev.get("strTimestamp") or "",
        ev.get("dateEvent") or "",
        ev.get("strTime") or ""
    )
    comp = ev.get("strLeague") or ""
    home = ev.get("strHomeTeam") or ""
    away = ev.get("strAwayTeam") or ""
    tv   = ev.get("strTVStation") or ""

    hs = to_int(ev.get("intHomeScore"))
    as_ = to_int(ev.get("intAwayScore"))

    now_ms = time.time() * 1000.0
    try:
        dt_ms = datetime.fromisoformat(date_iso.replace("Z", "+00:00")).timestamp() * 1000.0
    except Exception:
        dt_ms = now_ms

    is_finished = (hs is not None and as_ is not None) or (dt_ms < now_ms - 2*60*60*1000)
    status = "FINISHED" if (hs is not None and as_ is not None) else "SCHEDULED"

    match = {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "status": status,
        "tv": tv
    }
    if hs is not None and as_ is not None:
        outc = outcome_for_mu(home, away, hs, as_)
        s = {"home": hs, "away": as_}
        if outc:
            s["outcome"] = outc
        match["score"] = s
    return match

def current_pl_season():
    now = datetime.utcnow()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{start}-{start+1}"

def apply_tv_overrides(matches):
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

def fetch_team_next_last():
    """Always available on free tier; returns 0..5 next and 0..5 last."""
    out = []
    # Next 5
    try:
        jn = json_get(TSDB_BASE + f"eventsnext.php?id={TEAM_ID}")
        for ev in (jn or {}).get("events") or []:
            out.append(build_match_from_event(ev))
    except Exception as e:
        print("[fixtures] next error:", e, file=sys.stderr)
    # Last 5
    try:
        jl = json_get(TSDB_BASE + f"eventslast.php?id={TEAM_ID}")
        for ev in (jl or {}).get("results") or []:
            out.append(build_match_from_event(ev))
    except Exception as e:
        print("[fixtures] last error:", e, file=sys.stderr)
    return out

def top_up_upcoming_with_league(matches):
    """
    Optional: try to add more upcoming PL fixtures from the season feed.
    If the endpoint is restricted/empty on your tier, we silently skip.
    """
    try:
        season = current_pl_season()
        j = json_get(TSDB_BASE + f"eventsseason.php?id={PL_LEAGUE_ID}&s={urllib.parse.quote(season)}")
        evs = (j or {}).get("events") or []
    except Exception as e:
        print("[fixtures] season top-up skipped:", e, file=sys.stderr)
        return

    # Build a set of already-seen date+home+away to avoid dupes
    seen = set((m["date"], m["home"], m["away"]) for m in matches)
    now_ms = time.time()*1000.0

    for ev in evs:
        if not ev: continue
        home = (ev.get("strHomeTeam") or "").lower()
        away = (ev.get("strAwayTeam") or "").lower()
        mu = TEAM_NAME.lower()
        if home != mu and away != mu:
            continue  # only MUFC games
        m = build_match_from_event(ev)
        # only future events and not already present
        try:
            dt_ms = datetime.fromisoformat(m["date"].replace("Z","+00:00")).timestamp()*1000.0
        except Exception:
            dt_ms = now_ms
        if dt_ms >= now_ms - 5*60*1000:
            key = (m["date"], m["home"], m["away"])
            if key not in seen:
                matches.append(m)
                seen.add(key)

def main():
    ensure_assets()

    matches = fetch_team_next_last()  # always returns something when available
    # Optional PL top-up (safe no-op if not available)
    top_up_upcoming_with_league(matches)

    # Sort chronologically
    matches.sort(key=lambda m: m["date"])

    # Apply local TV overrides if you keep them
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
