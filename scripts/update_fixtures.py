#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ASSETS_DIR = "assets"
TEAM_ID = "133612"  # Man United on TheSportsDB
TEAM_NAME = "Manchester United"

UTC = timezone.utc
UK_TZ = ZoneInfo("Europe/London")


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GHAction/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def safe_int(x, default=None):
    try:
        return int(x)
    except Exception:
        return default


def to_https(u: str | None) -> str | None:
    if not u:
        return u
    return u.replace("http://", "https://")


def comp_short(name: str) -> str:
    n = (name or "").lower()
    if "champions league" in n and "qualif" in n:
        return "UCLQ"
    if "champions league" in n:
        return "UCL"
    if "europa league" in n:
        return "UEL"
    if "premier league" in n:
        return "EPL"
    if "fa cup" in n:
        return "FAC"
    if "carabao" in n or "efl cup" in n or "league cup" in n:
        return "LC"
    if "community shield" in n:
        return "CS"
    if "friendly" in n:
        return "FR"
    parts = [p[:1].upper() for p in name.split() if p and p[0].isalpha()]
    return "".join(parts)[:4] or "UNK"


def to_uk_date_time(dt_utc: datetime):
    uk = dt_utc.astimezone(UK_TZ)
    return uk.strftime("%Y-%m-%d"), uk.strftime("%H:%M")


def read_tv_overrides(path="assets/tv_overrides.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("overrides") or []
    except FileNotFoundError:
        return []
    except Exception as e:
        print("WARN: tv_overrides.json parse error:", e)
        return []


def apply_override(match, overrides):
    for o in overrides:
        if (
            o.get("date_uk") == match["date_uk"]
            and o.get("time_uk") == match["time_uk"]
            and (o.get("home") or "").lower() == match["home"].lower()
            and (o.get("away") or "").lower() == match["away"].lower()
        ):
            if o.get("tv"):
                match["tv"] = o["tv"]
            hl = o.get("highlights")
            if isinstance(hl, dict):
                match["highlights"] = {
                    "sky": to_https(hl.get("sky")),
                    "yt": to_https(hl.get("yt")),
                }
            return


def build_match(e: dict) -> dict:
    stamp = e.get("strTimestamp")
    dt_utc = None
    if stamp:
        try:
            dt_utc = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(UTC)
        except Exception:
            dt_utc = None

    if dt_utc is None:
        d = e.get("dateEvent") or ""
        t = e.get("strTime") or "00:00:00"
        if len(t) == 5:
            t += ":00"
        try:
            dt_utc = datetime.fromisoformat(f"{d}T{t}").replace(tzinfo=UTC)
        except Exception:
            dt_utc = datetime.utcnow().replace(tzinfo=UTC)

    date_uk, time_uk = to_uk_date_time(dt_utc)
    comp_name = e.get("strLeague") or ""
    comp_code = comp_short(comp_name)
    home = e.get("strHomeTeam") or ""
    away = e.get("strAwayTeam") or ""
    hs = safe_int(e.get("intHomeScore"))
    as_ = safe_int(e.get("intAwayScore"))

    score_obj = None
    if hs is not None and as_ is not None:
        outcome = ""
        if home.lower() == TEAM_NAME.lower():
            outcome = "W" if hs > as_ else "D" if hs == as_ else "L"
        elif away.lower() == TEAM_NAME.lower():
            outcome = "W" if as_ > hs else "D" if hs == as_ else "L"
        score_obj = {"home": hs, "away": as_, "outcome": outcome}

    return {
        "date_uk": date_uk,
        "time_uk": time_uk,
        "comp": comp_name,
        "comp_code": comp_code,
        "home": home,
        "away": away,
        "score": score_obj,
        "tv": "TBD",
        "highlights": {"sky": None, "yt": None},
        "utc": dt_utc.isoformat(),
        "idEvent": e.get("idEvent"),
    }


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    overrides = read_tv_overrides()

    url_next = f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={TEAM_ID}"
    url_last = f"https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={TEAM_ID}"

    matches = []

    try:
        jn = json.loads(fetch(url_next).decode("utf-8"))
        for e in jn.get("events") or []:
            m = build_match(e)
            apply_override(m, overrides)
            matches.append(m)
    except Exception as exc:
        print("ERROR fetching next:", exc)

    try:
        jl = json.loads(fetch(url_last).decode("utf-8"))
        for e in jl.get("results") or []:
            m = build_match(e)
            apply_override(m, overrides)
            matches.append(m)
    except Exception as exc:
        print("ERROR fetching last:", exc)

    seen = set()
    deduped = []
    for m in matches:
        k = m.get("idEvent")
        if k and k in seen:
            continue
        if k:
            seen.add(k)
        deduped.append(m)

    def _iso(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.utcnow().replace(tzinfo=UTC)

    deduped.sort(key=lambda x: _iso(x.get("utc", "")))

    out = {
        "updated": int(time.time() * 1000),
        "team": TEAM_NAME,
        "matches": deduped,
        "source": "TheSportsDB",
    }

    with open(os.path.join(ASSETS_DIR, "fixtures.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"Wrote assets/fixtures.json with {len(deduped)} matches")


if __name__ == "__main__":
    main()
