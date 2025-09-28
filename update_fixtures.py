# scripts/update_fixtures.py
import json, time, urllib.request, os, sys
from datetime import datetime, timezone

UA = {"User-Agent":"KeelBot/1.0"}
API = "https://www.thesportsdb.com/api/v1/json/3"
MUFC_ID = "133612"   # Manchester United

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def to_iso(ts: str | None, date: str | None, time_s: str | None):
    # TSDB can give strTimestamp (UTC) or separate date/time
    if ts:
        try:
            # e.g. "2025-09-20 14:00:00"
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except: pass
    if date and time_s:
        try:
            dt = datetime.strptime(f"{date} {time_s}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except: pass
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except: pass
    return None

def outcome_for_mu(home, away, hs, as_):
    try:
        hs = int(hs) if hs is not None else None
        as_ = int(as_) if as_ is not None else None
    except:
        return None
    if hs is None or as_ is None:
        return None
    if home == "Manchester United":
        if hs > as_: return "W"
        if hs == as_: return "D"
        return "L"
    else:
        if as_ > hs: return "W"
        if as_ == hs: return "D"
        return "L"

def map_event(e):
    iso = to_iso(e.get("strTimestamp"), e.get("dateEventUTC") or e.get("dateEvent"), (e.get("strTimeUTC") or e.get("strTime")))
    hs, as_ = e.get("intHomeScore"), e.get("intAwayScore")
    status = "SCHEDULED" if (hs in (None,"") and as_ in (None,"")) else "FINISHED"
    oc = outcome_for_mu(e.get("strHomeTeam"), e.get("strAwayTeam"), hs, as_)
    return {
        "date": iso,
        "comp": e.get("strLeague") or "",
        "home": e.get("strHomeTeam") or "",
        "away": e.get("strAwayTeam") or "",
        "tv": (e.get("strTVStation") or "").strip(),
        "status": status,
        "score": None if status=="SCHEDULED" else {
            "home": int(hs), "away": int(as_), "outcome": oc
        }
    }

def main():
    os.makedirs("assets", exist_ok=True)

    # next & last
    upcoming = json.loads(get(f"{API}/eventsnext.php?id={MUFC_ID}").decode("utf-8")).get("events") or []
    recent   = json.loads(get(f"{API}/eventslast.php?id={MUFC_ID}").decode("utf-8")).get("results") or []

    items = [map_event(e) for e in (upcoming + recent)]
    # Filter out any strange null dates
    items = [m for m in items if m.get("date")]

    # sort by date ascending for whole list (UI splits/limits)
    items.sort(key=lambda m: m["date"])

    with open("assets/fixtures.json","w") as f:
        json.dump({"updated": int(time.time()*1000), "matches": items}, f)
    print("Wrote assets/fixtures.json with", len(items), "matches")

if __name__ == "__main__":
    main()
