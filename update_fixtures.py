#!/usr/bin/env python3
import os, datetime
from fetch_helpers import http_get_json, save_json, now_iso

TEAM_NAME = "Manchester United"
OUT_PATH = os.path.join("assets", "fixtures.json")
TV_OVERRIDES_PATH = os.path.join("assets", "tv_overrides.json")

def to_iso(date_str, time_str, ts):
    # Prefer TSDB strTimestamp if present; else combine date + time in Europe/London as ISO-like (no tz)
    if ts:
        # ts example: "2025-09-20T15:00:00+00:00"
        return ts
    if not date_str:
        return ""
    t = time_str or "15:00"  # default
    return f"{date_str}T{t}:00"

def outcome_for_united(home, away, hs, as_):
    if hs is None or as_ is None:
        return ""
    if home == TEAM_NAME:
        if hs > as_: return "W"
        if hs == as_: return "D"
        return "L"
    else:
        if as_ > hs: return "W"
        if as_ == hs: return "D"
        return "L"

def load_tv_overrides():
    try:
        ov = http_get_json("file:" + os.path.abspath(TV_OVERRIDES_PATH))
        if isinstance(ov, dict):
            return ov
    except Exception:
        pass
    return {}

def apply_tv_overrides(matches, overrides):
    # You can store overrides either as:
    # {"2025-10-04": "TNT Sports"}  or by opponent-day: {"2025-10-04 Sunderland": "TNT Sports"}
    if not overrides: return matches
    out = []
    for m in matches:
        day = (m["date"] or "")[:10]
        key1 = day
        key2 = f"{day} {m['home'] if m['home']!=TEAM_NAME else m['away']}"
        tv = overrides.get(key2) or overrides.get(key1)
        if tv:
            m = dict(m); m["tv"] = tv
        out.append(m)
    return out

def unified(events):
    res = []
    for e in events or []:
        comp = e.get("strLeague") or e.get("strLeagueShort") or ""
        home = e.get("strHomeTeam") or ""
        away = e.get("strAwayTeam") or ""
        hs   = e.get("intHomeScore"); hs = int(hs) if hs not in (None, "", "null") else None
        as_  = e.get("intAwayScore"); as_ = int(as_) if as_ not in (None, "", "null") else None
        status = "SCHEDULED"
        if hs is not None or as_ is not None:
            status = "FINISHED"
        res.append({
            "date": to_iso(e.get("dateEventLocal") or e.get("dateEvent"), e.get("strTimeLocal") or e.get("strTime"), e.get("strTimestamp")),
            "comp": comp,
            "home": home,
            "away": away,
            "score": {
                "home": hs if hs is not None else "",
                "away": as_ if as_ is not None else "",
                "outcome": outcome_for_united(home, away, hs, as_)
            },
            "status": status
        })
    return res

def main():
    api_key = os.environ.get("TSDB_API_KEY") or "3"
    # 1) resolve MUFC id once
    q = http_get_json(f"https://www.thesportsdb.com/api/v1/json/{api_key}/searchteams.php?t=Manchester%20United") or {}
    teams = q.get("teams") or []
    if not teams:
        save_json(OUT_PATH, {"updated": now_iso(), "team": TEAM_NAME, "matches": []})
        print("[fixtures] WARN: no team found")
        return 0
    team_id = teams[0].get("idTeam") or ""
    # 2) last + next
    last  = http_get_json(f"https://www.thesportsdb.com/api/v1/json/{api_key}/eventslast.php?id={team_id}") or {}
    next_ = http_get_json(f"https://www.thesportsdb.com/api/v1/json/{api_key}/eventsnext.php?id={team_id}") or {}
    last_e  = last.get("results") or last.get("events") or []
    next_e  = next_.get("events")  or []
    matches = unified(last_e) + unified(next_e)

    # merge simple TV overrides
    overrides = {}
    try:
        with open(TV_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            import json
            overrides = json.load(f)
    except Exception:
        overrides = {}

    matches = apply_tv_overrides(matches, overrides)

    save_json(OUT_PATH, {"updated": now_iso(), "team": TEAM_NAME, "matches": matches})
    print(f"[fixtures] OK wrote {len(matches)} matches to {OUT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
