#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json strictly from Manchester United team feeds
to avoid any stray 'Bolton' fixtures.

Data sources (free tier, reliable):
  - https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id=<TEAM_ID>
  - https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id=<TEAM_ID>
"""

import json, os, sys, time, urllib.request
from datetime import datetime, timezone

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TEAM_NAME = "Manchester United"
TEAM_ID   = "133612"  # MUFC team id (locks us to the right club)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(ROOT, "assets")
FIXTURES_PATH = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_PATH = os.path.join(ASSETS_DIR, "tv_overrides.json")

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "keelan-mufc/1.3"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def jget(url):
    return json.loads(fetch(url).decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

def to_iso_utc(ts: str, date_str: str, time_str: str) -> str:
    """Return ISO8601 Z. Prefer strTimestamp if present; else date+time."""
    dt = None
    if ts:
        try: dt = datetime.fromisoformat(ts.replace(" ", "T"))
        except Exception: dt = None
    if dt is None and date_str:
        t = (time_str or "00:00:00")
        if len(t) == 5: t += ":00"
        try: dt = datetime.fromisoformat(f"{date_str}T{t}")
        except Exception: dt = None
    if dt is None:
        dt = datetime.utcnow().replace(tzinfo=timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")

def to_int(x):
    try: return int(x)
    except Exception: return None

def outcome_for_mu(home, away, hs, as_):
    if hs is None or as_ is None: return None
    mu = TEAM_NAME.lower()
    if (home or "").lower() == mu:
        if hs > as_: return "W"
        if hs == as_: return "D"
        return "L"
    if (away or "").lower() == mu:
        if as_ > hs: return "W"
        if as_ == hs: return "D"
        return "L"
    return None

def build_match(ev: dict) -> dict:
    date_iso = to_iso_utc(
        ev.get("strTimestamp") or "",
        ev.get("dateEvent") or "",
        ev.get("strTime") or ""
    )
    home = ev.get("strHomeTeam") or ""
    away = ev.get("strAwayTeam") or ""
    comp = ev.get("strLeague") or ""
    tv   = ev.get("strTVStation") or ""

    hs = to_int(ev.get("intHomeScore"))
    as_ = to_int(ev.get("intAwayScore"))

    status = "FINISHED" if (hs is not None and as_ is not None) else "SCHEDULED"
    m = {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "status": status,
        "tv": tv
    }
    if hs is not None and as_ is not None:
        o = outcome_for_mu(home, away, hs, as_)
        s = {"home": hs, "away": as_}
        if o: s["outcome"] = o
        m["score"] = s
    return m

def only_manchester_united(ev: dict) -> bool:
    """Hard guard: keep only MUFC rows."""
    mu = TEAM_NAME.lower()
    return ((ev.get("strHomeTeam") or "").lower() == mu or
            (ev.get("strAwayTeam") or "").lower() == mu)

def apply_tv_overrides(matches):
    if not os.path.exists(TV_OVERRIDES_PATH): return
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

def fetch_team_feed(kind: str) -> list:
    """
    kind: 'next' or 'last'
    """
    key = "events" if kind == "next" else "results"
    url = TSDB_BASE + (f"eventsnext.php?id={TEAM_ID}" if kind == "next"
                       else f"eventslast.php?id={TEAM_ID}")
    try:
        j = jget(url)
        raw = (j or {}).get(key) or []
        # Defensive: keep only MUFC rows
        raw = [ev for ev in raw if only_manchester_united(ev)]
        return [build_match(ev) for ev in raw]
    except Exception as e:
        print(f"[fixtures] fetch {kind} error:", e, file=sys.stderr)
        return []

def main():
    ensure_assets()

    upcoming = fetch_team_feed("next")
    recent   = fetch_team_feed("last")

    matches = upcoming + recent

    # Dedupe (date+home+away) then sort chronologically
    seen = set()
    deduped = []
    for m in matches:
        key = (m["date"], m["home"], m["away"])
        if key in seen: continue
        seen.add(key)
        deduped.append(m)

    deduped.sort(key=lambda m: m["date"])

    apply_tv_overrides(deduped)

    out = {
        "updated": int(time.time()*1000),
        "team": TEAM_NAME,
        "matches": deduped
    }
    with open(FIXTURES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {FIXTURES_PATH} with {len(deduped)} matches")

if __name__ == "__main__":
    main()
