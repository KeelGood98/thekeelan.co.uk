#!/usr/bin/env python3
import json, os, time, urllib.request
from datetime import datetime, timezone

OUT = "assets"
os.makedirs(OUT, exist_ok=True)

TEAM_NAME = "Manchester United"
PREF_LEAGUE = "English Premier League"
FALLBACK_ID = "133612"  # MU first team on TheSportsDB

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"keelan-actions/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def to_iso(ts, d, t):
    # normalise to ISO UTC
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace(" ", "T")).replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except: pass
    if d and t:
        try:
            dt = datetime.fromisoformat(f"{d}T{t}:00").replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except: pass
    if d:
        try:
            dt = datetime.fromisoformat(f"{d}T00:00:00").replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except: pass
    return None

def outcome_for_mu(sh, sa, home_is_mu):
    if sh is None or sa is None: return None
    if sh == sa: return "D"
    mu = sh if home_is_mu else sa
    opp = sa if home_is_mu else sh
    return "W" if mu > opp else "L"

def norm(s): return (s or "").strip().lower()

# ---- Resolve MU id safely
tid = None
try:
    data = json.loads(fetch("https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=Manchester%20United").decode("utf-8"))
    cands = [t for t in (data.get("teams") or []) if norm(t.get("strTeam")) == norm(TEAM_NAME)]
    # prefer Premier League entry if multiple (e.g. U21/U23 etc.)
    cands.sort(key=lambda t: 0 if PREF_LEAGUE.lower() in norm(t.get("strLeague")) else 1)
    if cands:
        tid = cands[0].get("idTeam")
except Exception as e:
    print("[fixtures] warn: lookup error:", e)

if not tid:
    print("[fixtures] using fallback id", FALLBACK_ID)
    tid = FALLBACK_ID

def load_events(kind):
    url = f"https://www.thesportsdb.com/api/v1/json/3/events{kind}.php?id={tid}"
    try:
        j = json.loads(fetch(url).decode("utf-8"))
        return (j.get("results") or j.get("events") or [])
    except Exception as e:
        print(f"[fixtures] warn {kind}:", e)
        return []

next_events = load_events("next")
last_events = load_events("last")

raw = []
# past
for e in last_events:
    home, away = e.get("strHomeTeam") or "", e.get("strAwayTeam") or ""
    sh = None if (e.get("intHomeScore") in (None,"","null")) else int(e.get("intHomeScore"))
    sa = None if (e.get("intAwayScore") in (None,"","null")) else int(e.get("intAwayScore"))
    raw.append({
        "status": "FINISHED",
        "date": to_iso(e.get("strTimestamp"), e.get("dateEvent"), e.get("strTime")),
        "comp": e.get("strLeague") or "",
        "home": home,
        "away": away,
        "score": {"home": sh, "away": sa, "outcome": outcome_for_mu(sh, sa, norm(home)==norm(TEAM_NAME))},
        "tv": (e.get("strTVStation") or "").strip() or None
    })
# upcoming
for e in next_events:
    home, away = e.get("strHomeTeam") or "", e.get("strAwayTeam") or ""
    raw.append({
        "status": "SCHEDULED",
        "date": to_iso(e.get("strTimestamp"), e.get("dateEvent"), e.get("strTime")),
        "comp": e.get("strLeague") or "",
        "home": home,
        "away": away,
        "score": None,
        "tv": (e.get("strTVStation") or "").strip() or None
    })

# ---- HARD FILTER: keep only MU matches
mu = norm(TEAM_NAME)
matches = [m for m in raw if norm(m["home"]) == mu or norm(m["away"]) == mu]

# sanity: if API returned the wrong team (e.g., Bolton), abort the run
if not matches or len(matches) < len(raw) * 0.3:
    raise SystemExit("[fixtures] sanity check failed: fetched data doesn’t look like MU. Not writing fixtures.json.")

# order ascending by date
matches.sort(key=lambda m: m["date"] or "")

with open(os.path.join(OUT, "fixtures.json"), "w", encoding="utf-8") as f:
    json.dump({"updated": int(time.time()*1000), "team": TEAM_NAME, "matches": matches}, f)
print(f"Wrote fixtures.json with {len(matches)} MU matches.")
