import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://www.cheapshark.com/api/1.0"
DATA_DIR = Path("data")
GAMING_FILE = DATA_DIR / "gaming.json"


STORE_NAMES = {
    "1": "Steam",
    "2": "GamersGate",
    "3": "Green Man Gaming",
    "4": "Amazon",
    "5": "GameStop",
    "6": "Direct2Drive",
    "7": "GOG",
    "8": "Origin",
    "9": "Get Games",
    "10": "Shiny Loot",
    "11": "Humble Store",
    "12": "Desura",
    "13": "Uplay",
    "14": "IndieGameStand",
    "15": "Fanatical",
    "16": "Gamesrocket",
    "17": "Games Republic",
    "18": "SilaGames",
    "19": "Playfield",
    "20": "ImperialGames",
    "21": "WinGameStore",
    "22": "FunStockDigital",
    "23": "GameBillet",
    "24": "Voidu",
    "25": "Epic Games Store",
    "26": "Razer Game Store",
    "27": "Gamesplanet",
    "28": "Gamesload",
    "29": "2Game",
    "30": "IndieGala",
    "31": "Blizzard Shop",
    "32": "AllYouPlay",
    "33": "DLGamer",
    "34": "Noctre",
    "35": "DreamGame"
}


WATCHLIST_TITLES = [
    "Euro Truck Simulator 2",
    "American Truck Simulator",
    "Rainbow Six Siege",
    "Grand Theft Auto V",
    "Red Dead Redemption 2",
    "Cyberpunk 2077",
    "Baldur's Gate 3",
    "Elden Ring",
    "Hogwarts Legacy",
    "Forza Horizon 5"
]


QUICK_LINKS = [
    {
        "label": "Steam",
        "url": "https://store.steampowered.com/"
    },
    {
        "label": "PC Game Pass",
        "url": "https://www.xbox.com/en-GB/xbox-game-pass/pc-game-pass"
    },
    {
        "label": "CheapShark",
        "url": "https://www.cheapshark.com/"
    },
    {
        "label": "CDKeys",
        "url": "https://www.cdkeys.com/"
    },
    {
        "label": "Humble Bundle",
        "url": "https://www.humblebundle.com/"
    },
    {
        "label": "Fanatical",
        "url": "https://www.fanatical.com/"
    }
]


GAMEPASS_PICKS = [
    {
        "title": "Forza Horizon 5",
        "genre": "Racing",
        "note": "Good controller game. Easy to jump in."
    },
    {
        "title": "Halo Infinite",
        "genre": "FPS",
        "note": "Quick multiplayer option if you fancy pain with plasma grenades."
    },
    {
        "title": "PowerWash Simulator",
        "genre": "Chill",
        "note": "Brain-off mode. Weirdly elite."
    }
]


def fetch_json(endpoint: str, params: dict | None = None):
    query = f"?{urlencode(params)}" if params else ""
    url = f"{BASE_URL}{endpoint}{query}"

    request = Request(
        url,
        headers={
            "User-Agent": "thekeelan.co.uk GitHub Pages gaming updater"
        }
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Network error from {url}: {error}") from error


def money(value: str | float | int) -> str:
    try:
        amount = float(value)
        return f"${amount:.2f}"
    except Exception:
        return "$0.00"


def percentage(value: str | float | int) -> str:
    try:
        amount = float(value)
        return f"{round(amount)}%"
    except Exception:
        return "0%"


def cheapshark_deal_url(deal_id: str) -> str:
    return f"https://www.cheapshark.com/redirect?dealID={deal_id}"


def normalise_deal(item: dict) -> dict:
    store_id = str(item.get("storeID", "")).strip()

    return {
        "title": item.get("title", "Unknown"),
        "store": STORE_NAMES.get(store_id, f"Store {store_id}" if store_id else "Unknown store"),
        "salePrice": money(item.get("salePrice", "0")),
        "normalPrice": money(item.get("normalPrice", "0")),
        "saving": percentage(item.get("savings", "0")),
        "dealRating": item.get("dealRating", ""),
        "steamRating": item.get("steamRatingText", ""),
        "steamRatingPercent": item.get("steamRatingPercent", ""),
        "thumb": item.get("thumb", ""),
        "url": cheapshark_deal_url(item.get("dealID", "")),
        "dealID": item.get("dealID", "")
    }


def get_best_deals() -> list[dict]:
    raw = fetch_json(
        "/deals",
        {
            "pageSize": 12,
            "sortBy": "Deal Rating",
            "desc": 1,
            "lowerPrice": 1,
            "upperPrice": 25,
            "steamRating": 70
        }
    )

    deals = [normalise_deal(item) for item in raw if item.get("dealID")]

    return deals[:12]


def get_watchlist_deals() -> list[dict]:
    watchlist = []

    for title in WATCHLIST_TITLES:
        raw = fetch_json(
            "/deals",
            {
                "title": title,
                "pageSize": 1,
                "sortBy": "Price",
                "desc": 0
            }
        )

        if raw:
            deal = normalise_deal(raw[0])
            deal["searchTitle"] = title
            watchlist.append(deal)
        else:
            watchlist.append({
                "title": title,
                "searchTitle": title,
                "store": "No deal found",
                "salePrice": "N/A",
                "normalPrice": "N/A",
                "saving": "0%",
                "dealRating": "",
                "steamRating": "",
                "steamRatingPercent": "",
                "thumb": "",
                "url": f"https://www.cheapshark.com/search?q={title.replace(' ', '+')}",
                "dealID": ""
            })

    return watchlist


def build_gaming_data() -> dict:
    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "CheapShark",
        "bestDeals": get_best_deals(),
        "watchlist": get_watchlist_deals(),
        "gamepass": GAMEPASS_PICKS,
        "links": QUICK_LINKS
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    data = build_gaming_data()

    if not data["bestDeals"]:
        raise RuntimeError("CheapShark returned no best deals; refusing to overwrite gaming.json")

    write_json(GAMING_FILE, data)
    print(f"Wrote {GAMING_FILE}")


if __name__ == "__main__":
    main()
