#!/usr/bin/env python3
"""
Build assets/fixtures.json for Manchester United.

- Primary source: TheSportsDB season endpoint.
- Robust fallbacks: eventslast + eventsnext if season returns nothing.
- Keeps your JSON shape so the frontend continues to colour W/D/L and show TV/links.
"""

import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

ASSETS_DIR = "assets"
OUT_FILE = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_FILE = os.path.join(ASSETS_DIR, "tv_overrides.json")

TEAM_NAME = "Manchester United"   # we’ll look up the id by name
DEFAULT_TEAM_ID = "133612"        # safety net

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

def to_iso(date_str, time_str):
    d = (date_str or "").strip()
    t = (time_str or "15:00").strip()
    try:
        dt = datetime.strptime(d + " " + t, "%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:00Z")
    except Exception:
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
        wk = dt.strftime("%a")  # Mon..Sun
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

def get_events_season(team_id, season):
    url = f"{BASE}/eventsseason.php?id={team_id}&s={urllib.parse.quote(season)}"
    try:
        return (fetch_json(url).get("events") or [])
    except Exception as e:
        print("[fixtures] season fetch failed:", e, file=sys.stderr)
        return []

def get_events_last(team_id):
    url = f"{BASE}/eventslast.php?id={team_id}"
    try:
        return (fetch_json(url).get("results") or [])
    except Exception as e:
        print("[fixtures] last fetch failed:", e, file=sys.stderr)
        return []

def get_events_next(team_id):
    url = f"{BASE}/eventsnext.php?id={team_id}"
    try:
        return (fetch_json(url).get("events") or [])
    except Exception as e:
        print("[fixtures] next fetch failed:", e, file=sys.stderr)
        return []

def normalise(e, tv_overrides):
    home = (e.get("strHomeTeam") or "").strip()
    away = (e.get("strAwayTeam") or "").strip()
    comp = (e.get("strLeague") or e.get("strLeagueShort") or "").strip()
    date_iso = to_iso(e.get("dateEvent"), e.get("strTimeLocal") or e.get("strTime"))

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

    raw = get_events_season(team_id, season)

    # Fallback if season feed empty: stitch last + next
    if not raw:
        last_e = get_events_last(team_id)
        next_e = get_events_next(team_id)
        raw = (last_e or []) + (next_e or [])
        print(f"[fixtures] season empty; using last+next fallback: {len(raw)} events")

    # Only keep games where MUFC is actually one of the teams
    filtered = []
    for e in (raw or []):
        h = (e.get("strHomeTeam") or "").lower()
        a = (e.get("strAwayTeam") or "").lower()
        if "manchester united" in h or "manchester united" in a:
            filtered.append(e)

    matches = [normalise(e, tv_overrides) for e in filtered]
    # sort by date
    def t(m):
        try: return datetime.strptime(m.get("date") or "", "%Y-%m-%dT%H:%M:00Z")
        except: return datetime.max
    matches.sort(key=t)

    out = {
        "team": TEAM_NAME,
        "season": season,
        "updated": int(time.time()*1000),
        "matches": matches
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"[fixtures] Wrote {OUT_FILE} with {len(matches)} matches")

if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print("[fixtures] ERROR:", e, file=sys.stderr)
        sys.exit(1)
