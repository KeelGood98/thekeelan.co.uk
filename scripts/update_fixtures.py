#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json for Manchester United.

Primary source: ESPN public schedule JSON
  https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/360/schedule
Fallback (only if ESPN fails): TheSportsDB team "next/last" feeds for MUFC

Output format matches your front-end:
{
  "updated": <ms>,
  "team": "Manchester United",
  "matches": [
    {
      "date": "2025-09-20T17:30:00Z",
      "comp": "English Premier League",
      "home": "Manchester United",
      "away": "Chelsea",
      "status": "FINISHED" | "SCHEDULED",
      "tv": "TBD" | "Sky Sports" | ...,
      "score": { "home": 2, "away": 1, "outcome": "W" }  # only for finished
    },
    ...
  ]
}
"""

import json, os, sys, time, urllib.request
from datetime import datetime, timezone

# ---- Paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(ROOT, "assets")
FIXTURES_PATH = os.path.join(ASSETS_DIR, "fixtures.json")
TV_OVERRIDES_PATH = os.path.join(ASSETS_DIR, "tv_overrides.json")

TEAM_NAME = "Manchester United"

# ---- ESPN config
ESPN_SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/360/schedule"
)

# ---- TSDB fallback (MUFC only, no season scrape)
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TSDB_TEAM_ID = "133612"  # MUFC

# ---------- helpers

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "keelan-fixtures/1.4"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def jget(url):
    return json.loads(fetch(url).decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

def to_iso_z(dt_str: str) -> str:
    """Normalize ESPN/TSDB date strings to ISO-8601 Z."""
    if not dt_str:
        return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z","+00:00"))
    except Exception:
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00","Z")

def to_int(x):
    try:
        return int(x)
    except Exception:
        return None

def outcome_for_mu(home, away, hs, as_):
    if hs is None or as_ is None: return None
    mu = TEAM_NAME.lower()
    if (home or "").lower() == mu:
        return "W" if hs > as_ else ("D" if hs == as_ else "L")
    if (away or "").lower() == mu:
        return "W" if as_ > hs else ("D" if as_ == hs else "L")
    return None

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

# ---------- ESPN primary

def build_from_espn() -> list:
    data = jget(ESPN_SCHEDULE_URL)
    events = (data or {}).get("events") or []
    out = []
    for ev in events:
        comp = ""
        try:
            comp = ev["competitions"][0]["name"]
        except Exception:
            pass

        date_iso = to_iso_z(ev.get("date"))
        comps = ev.get("competitions") or []
        if not comps:
            continue
        c0 = comps[0]

        # Competitors: home/away
        home = away = ""
        hs = as_ = None
        for comptr in c0.get("competitors", []):
            nm = comptr.get("team", {}).get("displayName") or ""
            side = comptr.get("homeAway")
            sc = comptr.get("score")
            sc_i = to_int(sc) if sc is not None else None
            if side == "home":
                home = nm; hs = sc_i
            elif side == "away":
                away = nm; as_ = sc_i

        # ESPN gives state: "pre", "in", "post"
        state = (c0.get("status") or {}).get("type", {}).get("state", "").lower()
        status = "SCHEDULED" if state in ("pre", "in") else "FINISHED"

        # TV: ESPN JSON often empty/US-centric — default to TBD
        tv = "TBD"

        m = {
            "date": date_iso,
            "comp": comp or (ev.get("shortName") or ""),
            "home": home,
            "away": away,
            "status": status,
            "tv": tv
        }
        if status == "FINISHED" and hs is not None and as_ is not None:
            oc = outcome_for_mu(home, away, hs, as_)
            sc = {"home": hs, "away": as_}
            if oc: sc["outcome"] = oc
            m["score"] = sc

        # Keep only fixtures that actually involve MUFC
        if TEAM_NAME.lower() not in (home.lower(), away.lower()):
            continue

        out.append(m)

    # Deduplicate on (date, home, away), then sort
    seen = set(); dedup = []
    for m in out:
        key = (m["date"], m["home"], m["away"])
        if key in seen: continue
        seen.add(key); dedup.append(m)
    dedup.sort(key=lambda x: x["date"])
    return dedup

# ---------- TSDB fallback (MU-only next/last)

def build_from_tsdb() -> list:
    def tsdb(url):
        try:
            return jget(url)
        except Exception:
            return {}

    def normalize(ev):
        date_iso = to_iso_z(
            (ev.get("strTimestamp") or "")
            or (ev.get("dateEvent") or "") + "T" + (ev.get("strTime") or "00:00:00")
        )
        home = ev.get("strHomeTeam") or ""
        away = ev.get("strAwayTeam") or ""
        comp = ev.get("strLeague") or ""
        tv   = ev.get("strTVStation") or "TBD"
        hs = to_int(ev.get("intHomeScore"))
        as_ = to_int(ev.get("intAwayScore"))
        status = "FINISHED" if (hs is not None and as_ is not None) else "SCHEDULED"
        m = {"date": date_iso, "comp": comp, "home": home, "away": away, "status": status, "tv": tv}
        if status == "FINISHED":
            oc = outcome_for_mu(home, away, hs, as_)
            sc = {"home": hs, "away": as_}
            if oc: sc["outcome"] = oc
            m["score"] = sc
        return m

    next_url = TSDB_BASE + f"eventsnext.php?id={TSDB_TEAM_ID}"
    last_url = TSDB_BASE + f"eventslast.php?id={TSDB_TEAM_ID}"
    out = []
    for key, url in (("events", next_url), ("results", last_url)):
        arr = (tsdb(url) or {}).get(key) or []
        for ev in arr:
            # keep MUFC only
            if TEAM_NAME.lower() not in (
                (ev.get("strHomeTeam") or "").lower(),
                (ev.get("strAwayTeam") or "").lower()
            ):
                continue
            out.append(normalize(ev))

    # de-dupe + sort
    seen = set(); dedup = []
    for m in out:
        key = (m["date"], m["home"], m["away"])
        if key in seen: continue
        seen.add(key); dedup.append(m)
    dedup.sort(key=lambda x: x["date"])
    return dedup

# ---------- main

def main():
    ensure_assets()

    matches = []
    try:
        matches = build_from_espn()
        if not matches:
            raise RuntimeError("ESPN returned no MUFC matches")
        source = "ESPN"
    except Exception as e:
        print("[fixtures] ESPN failed, falling back to TSDB:", e, file=sys.stderr)
        try:
            matches = build_from_tsdb()
            source = "TSDB"
        except Exception as e2:
            print("[fixtures] TSDB fallback failed:", e2, file=sys.stderr)
            matches = []
            source = "none"

    apply_tv_overrides(matches)

    out = {
        "updated": int(time.time() * 1000),
        "team": TEAM_NAME,
        "source": source,
        "matches": matches
    }
    with open(FIXTURES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {FIXTURES_PATH} with {len(matches)} matches (source: {source})")

if __name__ == "__main__":
    main()
