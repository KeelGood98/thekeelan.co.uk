#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build assets/fixtures.json for Manchester United by merging:
- ESPN team schedule (reliable upcoming)
- TheSportsDB team feeds (reliable finished scores)

Keeps your existing output schema used by index.html.
"""

import json, os, sys, time, urllib.request, urllib.error, re
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
OUT_PATH = os.path.join(ASSETS, "fixtures.json")
TV_OVERRIDES = os.path.join(ASSETS, "tv_overrides.json")

TEAM = "Manchester United"

# ESPN (Premier League team id for MUFC)
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/360/schedule"

# TheSportsDB (MUFC)
TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3/"
TSDB_TEAM_ID = "133612"  # MUFC
TSDB_NEXT = TSDB_BASE + f"eventsnext.php?id={TSDB_TEAM_ID}"
TSDB_LAST = TSDB_BASE + f"eventslast.php?id={TSDB_TEAM_ID}"

UA = {"User-Agent": "keelan/fixtures-merge 1.1"}

def fetch_json(url, timeout=35):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def ensure_assets():
    os.makedirs(ASSETS, exist_ok=True)

def iso_utc(s):
    if not s:
        return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        # Fallback patterns
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                dt = datetime.strptime(s[:len(fmt)], fmt).replace(tzinfo=timezone.utc)
                break
            except Exception:
                dt = None
        if dt is None:
            dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00","Z")

_slug_re = re.compile(r"[^a-z0-9]+", re.I)
def slug(x):
    return _slug_re.sub("", (x or "").lower())

def key_from(home, away, date_iso):
    # Robust merge key (names can vary slightly across sources)
    return f"{date_iso[:10]}|{slug(home)}|{slug(away)}"

def to_int(x):
    try:
        return int(x)
    except Exception:
        return None

def outcome_for_mu(home, away, hs, as_):
    if hs is None or as_ is None: return None
    mu = TEAM.lower()
    if (home or "").lower() == mu:
        return "W" if hs > as_ else ("D" if hs == as_ else "L")
    if (away or "").lower() == mu:
        return "W" if as_ > hs else ("D" if as_ == hs else "L")
    return None

def apply_tv_overrides(matches):
    if not os.path.exists(TV_OVERRIDES): return
    try:
        with open(TV_OVERRIDES, "r", encoding="utf-8") as f:
            ov = json.load(f) or {}
    except Exception:
        return
    by_date = ov.get("by_date") or {}
    by_exact = ov.get("by_exact") or {}
    for m in matches:
        d = m["date"][:10]
        k = f'{m["date"]}|{m["home"]} v {m["away"]}'
        if k in by_exact:
            m["tv"] = by_exact[k]
        elif d in by_date:
            m["tv"] = by_date[d]

# -------- ESPN (primary for upcoming, secondary for structure)
def from_espn():
    data = fetch_json(ESPN_URL)
    events = (data or {}).get("events") or []
    out = []
    for ev in events:
        comps = ev.get("competitions") or []
        if not comps: continue
        c0 = comps[0]

        # Competitors
        home = away = ""
        hs = as_ = None
        for comptr in c0.get("competitors", []):
            nm = comptr.get("team", {}).get("displayName") or ""
            side = comptr.get("homeAway")
            sc = comptr.get("score")
            sc_i = to_int(sc) if sc is not None else None
            if side == "home":
                home, hs = nm, sc_i
            elif side == "away":
                away, as_ = nm, sc_i

        # Only keep MUFC fixtures
        if TEAM.lower() not in (home.lower(), away.lower()):
            continue

        comp_name = ""
        try:
            comp_name = c0.get("name") or ev.get("name") or ev.get("shortName") or ""
        except Exception:
            comp_name = ev.get("name") or ""

        state = (c0.get("status") or {}).get("type", {}).get("state", "").lower()
        completed = (c0.get("status") or {}).get("type", {}).get("completed", False)
        status = "FINISHED" if (completed or state == "post") else "SCHEDULED"

        date_iso = iso_utc(ev.get("date"))
        tv = "TBD"  # ESPN often US-centric – we override if you provide TV overrides

        item = {
            "date": date_iso,
            "comp": comp_name or "English Premier League",
            "home": home,
            "away": away,
            "status": status,
            "tv": tv
        }
        if status == "FINISHED" and hs is not None and as_ is not None:
            sc = {"home": hs, "away": as_}
            oc = outcome_for_mu(home, away, hs, as_)
            if oc: sc["outcome"] = oc
            item["score"] = sc

        out.append(item)

    # Sort chronologically
    out.sort(key=lambda m: m["date"])
    return out

# -------- TSDB (reliable scores for recent results; fallback for upcoming if ESPN empty)
def from_tsdb():
    out = []
    def norm(ev):
        # Compose timestamp
        ts = ev.get("strTimestamp")
        if not ts:
            ts = (ev.get("dateEvent") or "") + "T" + (ev.get("strTime") or "00:00:00Z")
        date_iso = iso_utc(ts)
        home = ev.get("strHomeTeam") or ""
        away = ev.get("strAwayTeam") or ""
        if TEAM.lower() not in (home.lower(), away.lower()):
            return None
        comp = ev.get("strLeague") or ""
        tv = ev.get("strTVStation") or "TBD"
        hs = to_int(ev.get("intHomeScore"))
        as_ = to_int(ev.get("intAwayScore"))
        status = "FINISHED" if (hs is not None and as_ is not None) else "SCHEDULED"
        it = {"date": date_iso, "comp": comp, "home": home, "away": away, "status": status, "tv": tv}
        if status == "FINISHED":
            sc = {"home": hs, "away": as_}
            oc = outcome_for_mu(home, away, hs, as_)
            if oc: sc["outcome"] = oc
            it["score"] = sc
        return it

    for url, arr_key in ((TSDB_NEXT, "events"), (TSDB_LAST, "results")):
        try:
            js = fetch_json(url)
            for ev in (js or {}).get(arr_key) or []:
                it = norm(ev)
                if it: out.append(it)
        except Exception as e:
            print("[fixtures] TSDB fetch error:", e, file=sys.stderr)
            continue

    # De-dupe + sort
    seen = set(); dedup = []
    for m in out:
        k = key_from(m["home"], m["away"], m["date"])
        if k in seen: continue
        seen.add(k); dedup.append(m)
    dedup.sort(key=lambda m: m["date"])
    return dedup

# -------- merge logic
def merge_espn_tsdb():
    espn = []
    try:
        espn = from_espn()
    except Exception as e:
        print("[fixtures] ESPN error:", e, file=sys.stderr)

    tsdb = []
    try:
        tsdb = from_tsdb()
    except Exception as e:
        print("[fixtures] TSDB error:", e, file=sys.stderr)

    # Index ESPN by key (structure + upcoming)
    by_key = {}
    for m in espn:
        by_key[key_from(m["home"], m["away"], m["date"])] = m

    # For finished matches, prefer TSDB for scores/outcomes if ESPN lacked them
    for m in tsdb:
        k = key_from(m["home"], m["away"], m["date"])
        if k not in by_key:
            by_key[k] = m
        else:
            base = by_key[k]
            # If TSDB has score/outcome and base doesn't, fill it
            if m.get("status") == "FINISHED":
                if not base.get("score") and m.get("score"):
                    base["score"] = m["score"]
                # prefer a clearer competition name if ESPN blank
                if not base.get("comp"): base["comp"] = m.get("comp") or base.get("comp")

    merged = list(by_key.values())
    merged.sort(key=lambda m: m["date"])

    # Apply TV overrides at the end
    apply_tv_overrides(merged)
    return merged

def main():
    ensure_assets()
    matches = merge_espn_tsdb()

    out = {
        "updated": int(time.time() * 1000),
        "team": TEAM,
        "source": "ESPN+TSDB",
        "matches": matches
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {OUT_PATH} with {len(matches)} matches (merged ESPN+TSDB)")

if __name__ == "__main__":
    main()
