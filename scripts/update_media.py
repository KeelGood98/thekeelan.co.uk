import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

DATA_DIR = Path("data")
MEDIA_FILE = DATA_DIR / "media.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "").strip()


MEDIA_LINKS = [
    {
        "label": "Netflix",
        "url": "https://www.netflix.com/gb/",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=netflix.com"
    },
    {
        "label": "Prime Video",
        "url": "https://www.primevideo.com/",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=primevideo.com"
    },
    {
        "label": "Disney+",
        "url": "https://www.disneyplus.com/en-gb",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=disneyplus.com"
    },
    {
        "label": "NOW",
        "url": "https://www.nowtv.com/",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=nowtv.com"
    },
    {
        "label": "Apple TV+",
        "url": "https://tv.apple.com/gb",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=tv.apple.com"
    },
    {
        "label": "TMDB",
        "url": "https://www.themoviedb.org/",
        "logo": "https://www.google.com/s2/favicons?sz=64&domain=themoviedb.org"
    }
]


def fetch_json(endpoint: str, params: dict | None = None) -> dict:
    if not TMDB_API_KEY:
        raise RuntimeError("Missing TMDB_API_KEY environment variable")

    query_params = {
        "api_key": TMDB_API_KEY,
        "language": "en-GB"
    }

    if params:
        query_params.update(params)

    url = f"{BASE_URL}{endpoint}?{urlencode(query_params)}"

    request = Request(
        url,
        headers={
            "User-Agent": "thekeelan.co.uk GitHub Pages media updater"
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


def poster_url(path: str | None) -> str:
    if not path:
        return ""

    return f"{IMAGE_BASE_URL}{path}"


def tmdb_url(media_type: str, item_id) -> str:
    if not item_id:
        return "https://www.themoviedb.org/"

    if media_type == "tv":
        return f"https://www.themoviedb.org/tv/{item_id}"

    return f"https://www.themoviedb.org/movie/{item_id}"


def clean_date(value: str | None) -> str:
    if not value:
        return "TBC"

    return value


def rating(value) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def normalise_item(item: dict, media_type: str) -> dict:
    title = item.get("title") or item.get("name") or "Untitled"
    release_date = item.get("release_date") or item.get("first_air_date") or ""

    return {
        "id": item.get("id"),
        "mediaType": media_type,
        "title": title,
        "overview": item.get("overview", ""),
        "poster": poster_url(item.get("poster_path")),
        "backdrop": poster_url(item.get("backdrop_path")),
        "releaseDate": clean_date(release_date),
        "rating": rating(item.get("vote_average")),
        "votes": item.get("vote_count", 0),
        "url": tmdb_url(media_type, item.get("id"))
    }


def get_trending_movies() -> list[dict]:
    raw = fetch_json("/trending/movie/week")
    results = raw.get("results", [])
    return [normalise_item(item, "movie") for item in results[:10]]


def get_trending_tv() -> list[dict]:
    raw = fetch_json("/trending/tv/week")
    results = raw.get("results", [])
    return [normalise_item(item, "tv") for item in results[:10]]


def get_upcoming_movies() -> list[dict]:
    raw = fetch_json(
        "/movie/upcoming",
        {
            "region": "GB",
            "page": 1
        }
    )

    results = raw.get("results", [])
    return [normalise_item(item, "movie") for item in results[:10]]


def get_now_playing_movies() -> list[dict]:
    raw = fetch_json(
        "/movie/now_playing",
        {
            "region": "GB",
            "page": 1
        }
    )

    results = raw.get("results", [])
    return [normalise_item(item, "movie") for item in results[:10]]


def build_media_data() -> dict:
    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "TMDB",
        "region": "GB",
        "trendingMovies": get_trending_movies(),
        "trendingTv": get_trending_tv(),
        "upcomingMovies": get_upcoming_movies(),
        "nowPlayingMovies": get_now_playing_movies(),
        "links": MEDIA_LINKS,
        "attribution": "This product uses the TMDB API but is not endorsed or certified by TMDB."
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    data = build_media_data()

    if not data["trendingMovies"] and not data["trendingTv"]:
        raise RuntimeError("TMDB returned no media data; refusing to overwrite media.json")

    write_json(MEDIA_FILE, data)
    print(f"Wrote {MEDIA_FILE}")


if __name__ == "__main__":
    main()
