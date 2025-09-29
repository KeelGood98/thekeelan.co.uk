#!/usr/bin/env python3
"""
Build assets/fixtures.json for Manchester United with correct UK times.

Order of sources (strongest to weakest):
  1) Team season       : /eventsseason.php?id=<teamId>&s=<season>
  2) League season     : /eventsseason.php?id=4328&s=<season> (Premier League) -> filter MUFC
  3) League rounds     : /eventsround.php?id=4328&s=<season>&r=1..40        -> filter MUFC
  4) Fallback (stitch) : /eventslast.php?id=<teamId> + /eventsnext.php?id=<teamId>

We output ISO timestamps in UTC (Z). If TSDB provides strTimestamp we use it.
Otherwise we interpret the provided kick-off as Europe/London and convert to UTC.
"""

import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+

ASSETS_DIR = "assets"
OUT_FILE = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_FILE = os.path.join(ASSETS_DIR, "tv_overrides.json")

TEAM_NAME = "Manchester United"
DEFAULT_TEAM_ID = "133612"        # MUFC on TheSportsDB
PL_LEAGUE_ID = "4328"             # English Premier League

BASE = "https://www.thesportsdb.com/api/v1/json/3"

def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"GitHubAction/1.0 (+thekeelan.co.uk)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def current_season_str(now_utc: datetime) -> str:
    start = now_utc.year if now_utc.month >= 7 else now_utc.year - 1
    return f"{start}-{start+1}"

def lookup_team_id(name: str) -> str:
    try:
        url = f"{BASE}/searchteams.php?t={urllib.parse.quote(name)}"
        data = fetch_json(url)
        teams = data.get("teams") or []
        for t in teams:
            if (t.get("strTeam") or "").strip().lower() == name.lower():
                return t.get("idTeam") or DEFAULT_TEAM_ID
    except Exception as e:
        print("[fixtures] team lookup failed:", e, file=sys.stderr)
    return DEFAULT_TEAM_ID

# ---- Time handling ----
UK_TZ = ZoneInfo("Europe/London")

def to_iso_utc_from_local(date_str, time_str):
    """Interpret given date & time as Europe/London, convert to UTC ISO with Z."""
    d = (date_str or "").strip()
    t = (time_str or "").strip()
    if not t or t.upper() in ("TBD", "00:00"):
        t = "15:00"  # safe default if missing
    try:
        naive = datetime.strptime(d + " " + t, "%Y-%m-%d %H:%M")
        local_dt = naive.replace(tzinfo=UK_TZ)
        utc_dt = local_dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:00Z")
    except Exception:
        # last-ditch: date only at 15:00 UK
        try:
            naive = datetime.strptime(d + " 15:00", "%Y-%m-%d %H:%M")
            local_dt = naive.replace(tzinfo=UK_TZ)
            utc_dt = local_dt.astimezone(timezone.utc)
            return utc_dt.strftime("%Y-%m-%dT%H:%M:00Z")
        except Exception:
            return None

def best_iso_utc(e):
    """
    Choose the best UTC timestamp:
      - strTimestamp (already UTC or has offset)
      - else interpret dateEvent + (strTimeLocal or strTime) as Europe/London -> convert to UTC
    """
    ts = (e.get("strTimestamp") or "").strip()
    if ts:
        try:
            # TSDB often like "2025-09-20 16:30:00+00:00" or ISO; normalise to UTC 'Z'
            ts_norm = ts.replace(" ", "T").replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_norm)  # aware
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass

    # Fallback: treat as UK local time
    date_str = e.get("dateEvent") or ""
    time_local = e.get("strTimeLocal") or e.get("strTime") or ""
    return to_iso_utc_from_local(date_str, time_local)

# -----------------------

def outcome_from_mufc_pov(home, away, hs, as_):
    try:
        hs = int(hs) if hs is not None else None
        as_ = int(as_) if as_ is not None else None
    except Exception:
        return None
    if hs is None or as_ is None:
        return None
    if home.lower() == "manchester united":
        return "W" if hs>as_ else "L" if hs<as_ else "D"
    if away.lower() == "manchester united":
        return "W" if as_>hs else "L" if as_<hs else "D"
    return None

def guess_uk_tv(date_iso, comp):
    if not comp or "premier" not in comp.lower():
        return ""
    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%dT%H:%M:00Z")
        hm = dt.strftime("%H:%M")
        wk = dt.strftime("%a")  # Mon..Sun (in UTC, but pattern is fine for heuristic)
        if wk == "Sat" and hm == "12:30": return "TNT Sports (est.)"
        if wk == "Sat" and hm in ("17:30","20:00"): return "Sky Sports (est.)"
        if wk == "Sun" and hm in ("14:00","16:30","19:00"): return "Sky Sports (est.)"
        if wk in ("Mon","Fri") and hm in ("19:45","20:00"): return "Sky Sports (est.)"
    except Exception:
        pass
    return "TBD"

def load_tv_overrides():
    try:
        with open(TV_OVERRIDES_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(d, dict):
                return d
    except FileNotFoundError:
        pass
    except Exception as e:
        print("[tv_overrides] warn:", e, file=sys.stderr)
    return {}

def get_team_season(team_id, season):
    url = f"{BASE}/eventsseason.php?id={team_id}&s={urllib.parse.quote(season)}"
    try:
        return (fetch_json(url).get("events") or [])
    except Exception as e:
        print("[fixtures] team season failed:", e, file=sys.stderr)
        return []

def get_league_season(league_id, season):
    url = f"{BASE}/eventsseason.php?id={league_id}&s={urllib.parse.quote(season)}"
    try:
        return (fetch_json(url).get("events") or [])
    except Exception as e:
        print("[fixtures] league season failed:", e, file=sys.stderr)
        return []

def get_league_rounds(league_id, season, max_rounds=40):
    all_events = []
    for r in range(1, max_rounds+1):
        url = f"{BASE}/eventsround.php?id={league_id}&s={urllib.parse.quote(season)}&r={r}"
        try:
            evs = (fetch_json(url).get("events") or [])
            if not evs and r > 38:
                break
            all_events.extend(evs)
        except Exception as e:
            print(f"[fixtures] round {r} failed:", e, file=sys.stderr)
            continue
    out, seen = [], set()
    for e in all_events:
        k = e.get("idEvent")
        if k and k not in seen:
            seen.add(k)
            out.append(e)
    return out

def get_last(team_id):
    url = f"{BASE}/eventslast.php?id={team_id}"
    try:
        return (fetch_json(url).get("results") or [])
    except Exception as e:
        print("[fixtures] last failed:", e, file=sys.stderr)
        return []

def get_next(team_id):
    url = f"{BASE}/eventsnext.php?id={team_id}"
    try:
        return (fetch_json(url).get("events") or [])
    except Exception as e:
        print("[fixtures] next failed:", e, file=sys.stderr)
        return []

def is_mufc(e):
    h = (e.get("strHomeTeam") or "").lower()
    a = (e.get("strAwayTeam") or "").lower()
    return ("manchester united" in h) or ("manchester united" in a)

def normalise(e, tv_overrides):
    home = (e.get("strHomeTeam") or "").strip()
    away = (e.get("strAwayTeam") or "").strip()
    comp = (e.get("strLeague") or e.get("strLeagueShort") or "").strip()
    date_iso = best_iso_utc(e)

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

    tv_raw = (e.get("strTVChannel") or "").strip()
    opponent = away if home.lower()=="manchester united" else home
    override_key = f"{(e.get('dateEvent') or '').strip()} {opponent}"
    tv = tv_overrides.get(override_key, tv_raw) or ""
    if not tv:
        tv = guess_uk_tv(date_iso or "", comp)

    return {
        "date": date_iso,
        "comp": comp,
        "home": home,
        "away": away,
        "tv": tv,
        "score": score,
        "status": status
    }

def build():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    season = current_season_str(now_utc)
    tv_overrides = load_tv_overrides()

    team_id = lookup_team_id(TEAM_NAME) or DEFAULT_TEAM_ID
    print(f"[fixtures] Using team id {team_id} for {TEAM_NAME}")
    print(f"[fixtures] Season {season}")

    # 1) Team season
    raw = get_team_season(team_id, season)

    # 2) League season (filter MUFC)
    if not raw:
        print("[fixtures] team season empty -> trying league season…")
        league_all = get_league_season(PL_LEAGUE_ID, season)
        raw = [e for e in league_all if is_mufc(e)]

    # 3) League rounds (filter MUFC)
    if not raw:
        print("[fixtures] league season empty -> trying league rounds…")
        rounds_all = get_league_rounds(PL_LEAGUE_ID, season, max_rounds=40)
        raw = [e for e in rounds_all if is_mufc(e)]

    # 4) Fallback: stitched last + next
    used_fallback_stitch = False
    if not raw:
        print("[fixtures] rounds empty -> using last+next fallback")
        used_fallback_stitch = True
        raw = (get_last(team_id) or []) + (get_next(team_id) or [])

    filtered = [e for e in (raw or []) if is_mufc(e)]
    matches = [normalise(e, tv_overrides) for e in filtered]

    def key_dt(m):
        try: return datetime.strptime(m.get("date") or "", "%Y-%m-%dT%H:%M:00Z")
        except: return datetime.max
    matches.sort(key=key_dt)

    out = {
        "team": TEAM_NAME,
        "season": season,
        "updated": int(time.time()*1000),
        "matches": matches
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"[fixtures] Wrote {OUT_FILE} with {len(matches)} matches"
          + (" (fallback: last+next)" if used_fallback_stitch else ""))

if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print("[fixtures] ERROR:", e, file=sys.stderr)
        sys.exit(1)
