#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparse
import pytz

OUT = Path("assets/fixtures.json")
BBC_TEAM_URL = "https://www.bbc.co.uk/sport/football/teams/manchester-united/scores-fixtures"
TZ_UK = pytz.timezone("Europe/London")

COMP_MAP = {
    "Premier League":"EPL","English Premier League":"EPL","UEFA Champions League":"UCL",
    "FA Cup":"FAC","EFL Cup":"EFL","Carabao Cup":"EFL","Community Shield":"CS",
    "Friendly":"CF","Club Friendlies":"CF"
}
def comp_tag(name:str)->str:
    for k,v in COMP_MAP.items():
        if k.lower() in name.lower(): return v
    return "".join(p[0] for p in name.split()[:3]).upper()

def fetch():
    r=requests.get(BBC_TEAM_URL,timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    cards=soup.select("[data-event-id]")
    up,res=[],[]
    now=datetime.now(tz=TZ_UK)

    for card in cards:
        ko=card.get("data-kickoff")
        ko_dt=None
        if ko:
            try:
                ko_dt=dtparse.parse(ko)
                ko_dt=ko_dt.replace(tzinfo=timezone.utc).astimezone(TZ_UK) if ko_dt.tzinfo is None else ko_dt.astimezone(TZ_UK)
            except: pass

        teams=card.select(".sp-c-fixture__team-name,.qa-full-team-name")
        if len(teams)>=2:
            home=teams[0].get_text(strip=True); away=teams[1].get_text(strip=True)
        else:
            names=[t.get_text(strip=True) for t in card.select("[class*='team-name']")]
            home=names[0] if names else "TBC"; away=names[1] if len(names)>1 else "TBC"

        comp_el = card.select_one(".sp-c-fixture__competition, .sp-c-fixture__block, .gel-minion")
        comp_name = comp_el.get_text(strip=True) if comp_el else "Premier League"
        comp = comp_tag(comp_name)

        # score
        nums = [n.get_text(strip=True) for n in card.select(".sp-c-fixture__number")]
        score = f"{nums[0]}–{nums[1]}" if len(nums)>=2 and nums[0].isdigit() and nums[1].isdigit() else ""

        item = {
            "date": ko_dt.isoformat() if ko_dt else "",
            "time_uk": ko_dt.strftime("%H:%M") if ko_dt else "",
            "comp": comp, "comp_full": comp_name,
            "home": home, "away": away, "tv":"TBD"
        }

        if ko_dt and ko_dt>now:
            up.append(item)
        else:
            res.append({**item, "score": score or "—", "result": ""})

    up.sort(key=lambda x:x["date"]); res.sort(key=lambda x:x["date"], reverse=True)
    return {"team":"Manchester United","upcoming":up[:12],"results":res[:20]}

def main():
    data=fetch(); OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"Wrote {OUT}: {len(data['upcoming'])} upcoming, {len(data['results'])} results")

if __name__=="__main__": main()
