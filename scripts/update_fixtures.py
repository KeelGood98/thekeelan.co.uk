#!/usr/bin/env python3
"""
Build assets/fixtures.json for Manchester United (all comps, whole season).

- Source: TheSportsDB season endpoint (free, no key required).
- Team ID (MUFC): 133612  (do NOT change unless you want another club)
- Does not modify the league table pipeline.
- Optional TV overrides: assets/tv_overrides.json
  Example:
  {
    "2025-09-20 Chelsea": "Sky Sports",
    "2025-10-25 Brighton": "TNT Sports"
  }
"""

import json, os, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ASSETS_DIR = "assets"
OUT_FILE    = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_FILE = os.path.join(ASSETS_DIR, "tv_overrides.json")

TEAM_ID_MUFC = "133612"  # Manchester United on TheSportsDB

def fetch(url, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GitHubAction/1.0 (+thekeelan.co.uk)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def current_season_str(now_utc: datetime) -> str:
    # PL season runs Jul/ Aug -> next year
    start = now_utc.year if now_utc.month >= 7 else now_utc.year - 1
    return f"{start}-{start+1}"

def load_tv_overrides():
    try:
        with open(TV_OVERRIDES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except Exception as e:
        print("[tv_overrides] warning:", e, file=sys.stderr)
    return {}

def to_iso(date_str, time_str):
    """
    Convert date + time (both strings) to ISO8601 (UTC) for our JSON.
    If time is missing, assume 15:00.
    """
    d = (date_str or "").strip()
    t = (time_str or "15:00").strip()
    # TheSportsDB times can be local or UTC; we just keep a consistent string.
    try:
        dt = datetime.strptime(d + " " + t, "%Y-%m-%d %H:%M")
        # keep naive but mark as 'Z' so client treats it consistently
        return dt.strftime("%Y-%m-%dT%H:%M:00Z")
    except Exception:
        # Fallback to date only
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT15:00:00Z")
        except Exception:
            return None

def outcome_from_mufc_pov(home, away, hs, as_):
    try:
        hs = int(hs) if hs is not None else None
        as_ = int(as_) if as_ is not None else None
    except Exception:
        return None
    if hs is None or as_ is None:
        return None
    if home.lower() == "manchester united":
        if   hs > as_: return "W"
        elif hs < as_: return "L"
        else:          return "D"
    elif away.lower() == "manchester united":
        if   as_ > hs: return "W"
        elif as_ < hs: return "L"
        else:          return "D"
    return None

def guess_uk_tv(date_iso, comp):
    # simple heuristic – your front-end also guesses; this is a light helper
    if not comp or "premier" not in comp.lower():
        return ""
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%dT%H:%M:00Z")
        # treat this as UK local time block guess
        hm = dt.strftime("%H:%M")
        wk = dt.strftime("%a")  # Mon/Tue/...
        if wk == "Sat" and hm == "12:30": return "TNT Sports (est.)"
        if wk == "Sat" and hm in ("17:30","20:00"): return "Sky Sports (est.)"
        if wk == "Sun" and hm in ("14:00","16:30","19:00"): return "Sky Sports (est.)"
        if wk in ("Mon","Fri") and hm in ("19:45","20:00"): return "Sky Sports (est.)"
    except Exception:
        pass
    return "TBD"

def season_events(team_id, season_str):
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={team_id}&s={season_str}"
    raw = fetch(url).decode("utf-8")
    data = json.loads(raw)
    return data.get("events") or []

def build():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    season  = current_season_str(now_utc)

    tv_overrides = load_tv_overrides()

    events = season_events(TEAM_ID_MUFC, season)

    matches = []
    for e in events:
        home = (e.get("strHomeTeam") or "").strip()
        away = (e.get("strAwayTeam") or "").strip()

        # Safety guard: only keep matches where MUFC is involved
        if "manchester united" not in (home.lower() + " " + away.lower()):
            continue

        comp = (e.get("strLeague") or e.get("strLeagueShort") or "").strip()

        # Time: prefer local if provided, else strTime, else noon
        date_iso = to_iso(e.get("dateEvent"), e.get("strTimeLocal") or e.get("strTime"))

        # Score / status
        hs = e.get("intHomeScore")
        as_ = e.get("intAwayScore")
        finished = (hs is not None and as_ is not None)
        status = "FINISHED" if finished else "SCHEDULED"

        score = None
        if finished:
            score = {
                "home": int(hs),
                "away": int(as_),
                "outcome": outcome_from_mufc_pov(home, away, hs, as_)
            }

        # TV channel: TheSportsDB sometimes has strTVChannel; allow override; else guess
        tv_raw = (e.get("strTVChannel") or "").strip()
        # Override key: "YYYY-MM-DD Opponent" (opponent from MUFC pov)
        opp = away if home.lower() == "manchester united" else home
        override_key = f"{(e.get('dateEvent') or '').strip()} {opp}"
        tv = tv_overrides.get(override_key, tv_raw) or ""
        if not tv:
            tv = guess_uk_tv(date_iso or "", comp)

        matches.append({
            "date": date_iso,        # ISO string "YYYY-MM-DDTHH:MM:00Z"
            "comp": comp,
            "home": home,
            "away": away,
            "tv": tv,
            "score": score,
            "status": status
        })

    # Sort chronologically
    def t(m): 
        try:   return datetime.strptime(m.get("date") or "", "%Y-%m-%dT%H:%M:00Z")
        except: return datetime.max
    matches.sort(key=t)

    out = {
        "team": "Manchester United",
        "season": season,
        "updated": int(time.time()*1000),
        "matches": matches
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"Wrote {OUT_FILE} with {len(matches)} matches for season {season}")

if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print("[fixtures] ERROR:", e, file=sys.stderr)
        sys.exit(1)
