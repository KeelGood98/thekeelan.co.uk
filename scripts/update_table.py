#!/usr/bin/env python3
import json, sys, os, time
import pandas as pd
import requests

URL = "https://www.bbc.co.uk/sport/football/premier-league/table"
OUT = "assets/table.json"

def main():
    try:
        html = requests.get(URL, timeout=20)
        html.raise_for_status()
        # BBC has multiple tables; pick the first with "Pos" and "Team"
        tables = pd.read_html(html.text)
        table = None
        for t in tables:
            cols = [c.lower() for c in t.columns.astype(str)]
            if any("pos" in c for c in cols) and any("team" in c for c in cols):
                table = t
                break
        if table is None:
            raise RuntimeError("No suitable table found")

        # Normalise column names
        colmap = {}
        for c in table.columns:
            lc = str(c).lower()
            if "pos" in lc: colmap[c] = "pos"
            elif "team" in lc: colmap[c] = "team"
            elif lc in ("pld","p","played"): colmap[c] = "p"
            elif lc in ("w","won"): colmap[c] = "w"
            elif lc in ("d","drawn","draws"): colmap[c] = "d"
            elif lc in ("l","lost"): colmap[c] = "l"
            elif lc in ("f","gf","for"): colmap[c] = "gf"
            elif lc in ("a","ga","against"): colmap[c] = "ga"
            elif lc in ("gd","goal difference","goal diff"): colmap[c] = "gd"
            elif lc in ("pts","points"): colmap[c] = "pts"
        table = table.rename(columns=colmap)

        required = ["pos","team","p","w","d","l","gf","ga","gd","pts"]
        for r in required:
            if r not in table.columns:
                table[r] = ""

        rows = []
        for _, r in table.iterrows():
            rows.append({
                "pos": int(r["pos"]) if str(r["pos"]).isdigit() else r["pos"],
                "team": str(r["team"]),
                "p": int(r["p"]) if str(r["p"]).isdigit() else r["p"],
                "w": int(r["w"]) if str(r["w"]).isdigit() else r["w"],
                "d": int(r["d"]) if str(r["d"]).isdigit() else r["d"],
                "l": int(r["l"]) if str(r["l"]).isdigit() else r["l"],
                "gf": int(r["gf"]) if str(r["gf"]).isdigit() else r["gf"],
                "ga": int(r["ga"]) if str(r["ga"]).isdigit() else r["ga"],
                "gd": int(r["gd"]) if str(r["gd"]).replace("-","").isdigit() else r["gd"],
                "pts": int(r["pts"]) if str(r["pts"]).isdigit() else r["pts"],
            })

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"wrote {OUT} ({len(rows)} rows)")
    except Exception as e:
        print(f"[update_table] Non-fatal: {e}")
        # do NOT overwrite existing file on failure
        sys.exit(0)

if __name__ == "__main__":
    main()
