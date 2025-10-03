#!/usr/bin/env python3
import json, sys, os, re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TEAM = "Manchester United"
BASE = "https://www.bbc.co.uk/sport/football/teams/manchester-united/scores-fixtures"
OUT = "assets/fixtures.json"

# months to try for a typical season (Aug–May)
MONTHS = ["08","09","10","11","12","01","02","03","04","05"]

def year_span():
    today = datetime.utcnow()
    y = today.year
    # season crosses new year: Aug->Dec (year-0), Jan->May (year+1)
    return [(y if m in ["08","09","10","11","12"] else y+1, m) for m in MONTHS]

def fetch_month(y, m):
    url = f"{BASE}/{y}-{m}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def parse_month(html):
    soup = BeautifulSoup(html, "lxml")
    blocks = soup.select("[data-event-id]")  # each fixture block
    matches = []
    for b in blocks:
        try:
            # date at section heading up the tree
            date_header = b.find_previous("h3")
            date_txt = date_header.get_text(strip=True) if date_header else ""
            # teams
            home = b.select_one(".sp-c-fixture__team--home .sp-c-fixture__team-name-trunc").get_text(strip=True)
            away = b.select_one(".sp-c-fixture__team--away .sp-c-fixture__team-name-trunc").get_text(strip=True)
            comp = b.select_one(".sp-c-fixture__competition").get_text(strip=True) if b.select_one(".sp-c-fixture__competition") else "English Premier League"
            time_el = b.select_one(".sp-c-fixture__number--time, .sp-c-fixture__status .qa-status-description")
            time_txt = time_el.get_text(strip=True) if time_el else "TBD"

            # score if finished
            h_sc = b.select_one(".sp-c-fixture__number--home")
            a_sc = b.select_one(".sp-c-fixture__number--away")
            score = None
            if h_sc and a_sc:
                hs = h_sc.get_text(strip=True)
                as_ = a_sc.get_text(strip=True)
                if hs.isdigit() and as_.isdigit():
                    hs, as_ = int(hs), int(as_)
                    outcome = "W" if ((TEAM.lower() == home.lower() and hs>as_) or (TEAM.lower()==away.lower() and as_>hs)) else ("L" if ((TEAM.lower()==home.lower() and hs<as_) or (TEAM.lower()==away.lower() and as_<hs)) else "D")
                    score = {"home":hs,"away":as_,"outcome":outcome}

            matches.append({
                "date_uk": date_txt,
                "time_uk": time_txt if ":" in time_txt else "15:00" if time_txt.lower()=="tbd" else time_txt,
                "comp": comp,
                "comp_code": "".join(w[0] for w in comp.split() if w)[:3].upper(),
                "home": home,
                "away": away,
                "tv": "TBD",
                "highlights": {},
                "score": score
            })
        except Exception:
            continue
    return matches

def main():
    all_matches = []
    try:
        for y, m in year_span():
            try:
                html = fetch_month(y, m)
                all_matches.extend(parse_month(html))
            except Exception:
                continue

        # filter keep only fixtures that involve Manchester United
        mu = [m for m in all_matches if TEAM.lower() in (m["home"].lower()+" "+m["away"].lower())]

        upcoming = [m for m in mu if not m["score"]]
        results  = [m for m in mu if m["score"]]

        payload = {"upcoming": upcoming, "results": results}
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"wrote {OUT}: {len(upcoming)} upcoming, {len(results)} results")
    except Exception as e:
        print(f"[update_fixtures] Non-fatal: {e}")
        sys.exit(0)

if __name__ == "__main__":
    main()
