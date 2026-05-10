import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


DATA_DIR = Path("data")
WEATHER_FILE = DATA_DIR / "weather.json"

LOCATION_NAME = "Leeds"
LATITUDE = 53.8008
LONGITUDE = -1.5491

BASE_URL = "https://api.open-meteo.com/v1/forecast"


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


WEATHER_ICONS = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️",
    53: "🌦️",
    55: "🌧️",
    56: "🌧️",
    57: "🌧️",
    61: "🌦️",
    63: "🌧️",
    65: "🌧️",
    66: "🌧️",
    67: "🌧️",
    71: "🌨️",
    73: "🌨️",
    75: "❄️",
    77: "❄️",
    80: "🌦️",
    81: "🌧️",
    82: "⛈️",
    85: "🌨️",
    86: "❄️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️"
}


def fetch_json(url: str):
    request = Request(
        url,
        headers={
            "User-Agent": "thekeelan.co.uk GitHub Pages weather updater"
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


def weather_description(code) -> str:
    try:
        return WEATHER_CODES.get(int(code), "Unknown")
    except Exception:
        return "Unknown"


def weather_icon(code) -> str:
    try:
        return WEATHER_ICONS.get(int(code), "🌡️")
    except Exception:
        return "🌡️"


def round_number(value, digits=0):
    try:
        return round(float(value), digits)
    except Exception:
        return None


def build_weather_data() -> dict:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m"
        ]),
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "sunrise",
            "sunset"
        ]),
        "timezone": "Europe/London",
        "wind_speed_unit": "mph",
        "forecast_days": 3
    }

    url = f"{BASE_URL}?{urlencode(params)}"
    raw = fetch_json(url)

    current = raw.get("current", {})
    daily = raw.get("daily", {})

    current_code = current.get("weather_code")

    forecast = []

    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    rain_probs = daily.get("precipitation_probability_max", [])
    weather_codes = daily.get("weather_code", [])
    sunrises = daily.get("sunrise", [])
    sunsets = daily.get("sunset", [])

    for index, date_value in enumerate(dates):
        code = weather_codes[index] if index < len(weather_codes) else None

        forecast.append({
            "date": date_value,
            "description": weather_description(code),
            "icon": weather_icon(code),
            "maxTemp": round_number(max_temps[index], 0) if index < len(max_temps) else None,
            "minTemp": round_number(min_temps[index], 0) if index < len(min_temps) else None,
            "rainChance": round_number(rain_probs[index], 0) if index < len(rain_probs) else None,
            "sunrise": sunrises[index] if index < len(sunrises) else "",
            "sunset": sunsets[index] if index < len(sunsets) else ""
        })

    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "Open-Meteo",
        "location": LOCATION_NAME,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": {
            "time": current.get("time", ""),
            "temperature": round_number(current.get("temperature_2m"), 0),
            "feelsLike": round_number(current.get("apparent_temperature"), 0),
            "humidity": round_number(current.get("relative_humidity_2m"), 0),
            "precipitation": round_number(current.get("precipitation"), 1),
            "windSpeed": round_number(current.get("wind_speed_10m"), 0),
            "windGusts": round_number(current.get("wind_gusts_10m"), 0),
            "weatherCode": current_code,
            "description": weather_description(current_code),
            "icon": weather_icon(current_code)
        },
        "forecast": forecast
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    data = build_weather_data()

    if data["current"]["temperature"] is None:
        raise RuntimeError("Weather data missing current temperature; refusing to overwrite weather.json")

    write_json(WEATHER_FILE, data)
    print(f"Wrote {WEATHER_FILE}")


if __name__ == "__main__":
    main()
