#!/usr/bin/env python3
import json, sys, time, urllib.request

ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings?region=gb"

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def stat_map(stats):
    m = {}
    for s in stats or []:
        name = s.get("name")
        val = s.get("value")
        if val is None:
            dv = s.get("displayValue")
            try:
                val = int(str(dv).replace("–","-"))
            except Exception:
                val = dv
        m[name] = val
    return m

def main():
    data = fetch(ESPN_STANDINGS)

    # ESPN nests things; entries live under children[0].standings.entries in practice
    children = data.get("children") or []
    if not children:
        print("ERROR: ESPN payload unexpected (no children)", file=sys.stderr)
        sys.exit(1)

    node = children[0]
    standings = node.get("standings", {})
    entries = standings.get("entries") or []

    rows = []
    for e in entries:
        team = e.get("team", {})
        name = team.get("displayName") or team.get("name") or ""
        logos = team.get("logos") or []
        logo = (logos[0].get("href") if logos else None) or ""

        sm = stat_map(e.get("stats"))
        # common keys in ESPN soccer standings
        pos = sm.get("rank") or e.get("rank") or None
        played = sm.get("gamesPlayed") or sm.get("GP")
        won = sm.get("wins") or sm.get("W")
        drawn = sm.get("ties") or sm.get("draws") or sm.get("D")
        lost = sm.get("losses") or sm.get("L")
        gf = sm.get("pointsFor") or sm.get("goalsFor")
        ga = sm.get("pointsAgainst") or sm.get("goalsAgainst")
        gd = sm.get("pointDifferential") or sm.get("goalDifferential") or sm.get("GD")
        pts = sm.get("points") or sm.get("P")

        row = {
            "pos": int(pos) if pos not in (None, "") else None,
            "team": name,
            "played": int(played or 0),
            "won": int(won or 0),
            "drawn": int(drawn or 0),
            "lost": int(lost or 0),
            "gf": int(gf or 0),
            "ga": int(ga or 0),
            "gd": int(gd or 0),
            "pts": int(pts or 0),
            "logo": logo,
        }
        rows.append(row)

    rows = [r for r in rows if r["team"]]
    rows.sort(key=lambda r: r["pos"] or 999)

    out = {
        "source": "ESPN",
        "updated": int(time.time() * 1000),
        "standings": rows,
    }
    with open("assets/table.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"Wrote assets/table.json with {len(rows)} rows")

if __name__ == "__main__":
    main()
