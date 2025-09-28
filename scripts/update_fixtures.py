#!/usr/bin/env python3
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone

OUT_DIR = "assets"
os.makedirs(OUT_DIR, exist_ok=True)

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "keelan-actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def to_iso(ts, d, t):
    # TheSportsDB gives either strTimestamp (UTC) or date+time (local-ish).
    if ts:
        try:
            # already UTC like "2025-09-20 16:30:00"
            dt = datetime.fromisoformat(ts.replace(" ", "T")).replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except Exception:
            pass
    if d and t:
        try:
            dt = datetime.fromisoformat(f"{d}T{t}:00").replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except Exception:
            pass
    if d:
        try:
            dt = datetime.fromisoformat(f"{d}T00:00:00").replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except Exception:
            pass
    return None

def outcome_for_mu(score_home, score_away, home_is_mu):
    if score_home is None or score_away is None:
        return None
    if score_home == score_away:
        return "D"
    mu = score_home if home_is_mu else score_away
    opp = score_away if home_is_mu else score_home
    return "W" if mu > opp else "L"

TEAM_NAME = "Manchester United"

# 1) look up MU team id
tid = None
try:
    j = json.loads(fetch("https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=Manchester%20United").decode("utf-8"))
    for t in (j.get("teams") or []):
        if (t.get("strTeam") or "").strip().lower() == TEAM_NAME.lower():
            tid = t.get("idTeam")
            break
except Exception as e:
    raise SystemExit(f"[fixtures] lookup error: {e}")

if not tid:
    raise SystemExit("[fixtures] could not resolve Manchester United idTeam")

def load_events(kind):
    url = f"https://www.thesportsdb.com/api/v1/json/3/events{kind}.php?id={tid}"
    try:
        j = json.loads(fetch(url).decode("utf-8"))
        # API returns {"results":[...]} for last, {"events":[...]} for next
        return (j.get("results") or j.get("events") or [])
    except Exception as e:
        print(f"[fixtures] warn {kind}:", e)
        return []

next_events = load_events("next")
last_events = load_events("last")

matches = []

# past results
for e in last_events:
    home = e.get("strHomeTeam") or ""
    away = e.get("strAwayTeam") or ""
    ts = to_iso(e.get("strTimestamp"), e.get("dateEvent"), e.get("strTime"))
    sh = None if (e.get("intHomeScore") in (None, "", "null")) else int(e.get("intHomeScore"))
    sa = None if (e.get("intAwayScore") in (None, "", "null")) else int(e.get("intAwayScore"))
    out = outcome_for_mu(sh, sa, home.lower()==TEAM_NAME.lower())
    matches.append({
        "status": "FINISHED",
        "date": ts,
        "comp": e.get("strLeague") or "",
        "home": home,
        "away": away,
        "score": {"home": sh, "away": sa, "outcome": out},
        "tv": (e.get("strTVStation") or "").strip() or None
    })

# upcoming fixtures
for e in next_events:
    home = e.get("strHomeTeam") or ""
    away = e.get("strAwayTeam") or ""
    ts = to_iso(e.get("strTimestamp"), e.get("dateEvent"), e.get("strTime"))
    matches.append({
        "status": "SCHEDULED",
        "date": ts,
        "comp": e.get("strLeague") or "",
        "home": home,
        "away": away,
        "score": None,
        "tv": (e.get("strTVStation") or "").strip() or None
    })

# filter safeguard: only games where MU is home or away
matches = [m for m in matches if (m["home"].lower()==TEAM_NAME.lower() or m["away"].lower()==TEAM_NAME.lower())]

# order by date ascending
def ts_key(m):
    try:
        return m["date"] or ""
    except:
        return ""
matches.sort(key=ts_key)

with open(os.path.join(OUT_DIR, "fixtures.json"), "w", encoding="utf-8") as f:
    json.dump({"updated": int(time.time()*1000), "team": TEAM_NAME, "matches": matches}, f)

print(f"Wrote fixtures.json with {len(matches)} matches for {TEAM_NAME}")
