from __future__ import annotations

from typing import Any

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
IP_LOCATION_URL = "https://ipapi.co/json/"

REQUEST_HEADERS = {
    "User-Agent": "SkyPulseWeatherApp/1.1 (Flask Student Project)",
    "Accept": "application/json",
}

WEATHER_CODES = {
    0: {"title": "Clear Sky", "icon": "☀️"},
    1: {"title": "Mainly Clear", "icon": "🌤️"},
    2: {"title": "Partly Cloudy", "icon": "⛅"},
    3: {"title": "Overcast", "icon": "☁️"},
    45: {"title": "Fog", "icon": "🌫️"},
    48: {"title": "Rime Fog", "icon": "🌫️"},
    51: {"title": "Light Drizzle", "icon": "🌦️"},
    53: {"title": "Moderate Drizzle", "icon": "🌦️"},
    55: {"title": "Dense Drizzle", "icon": "🌧️"},
    56: {"title": "Freezing Drizzle", "icon": "🌧️"},
    57: {"title": "Freezing Drizzle", "icon": "🌧️"},
    61: {"title": "Slight Rain", "icon": "🌧️"},
    63: {"title": "Moderate Rain", "icon": "🌧️"},
    65: {"title": "Heavy Rain", "icon": "⛈️"},
    66: {"title": "Freezing Rain", "icon": "🌧️"},
    67: {"title": "Freezing Rain", "icon": "🌧️"},
    71: {"title": "Slight Snow", "icon": "🌨️"},
    73: {"title": "Moderate Snow", "icon": "🌨️"},
    75: {"title": "Heavy Snow", "icon": "❄️"},
    77: {"title": "Snow Grains", "icon": "❄️"},
    80: {"title": "Rain Showers", "icon": "🌦️"},
    81: {"title": "Rain Showers", "icon": "🌧️"},
    82: {"title": "Violent Rain Showers", "icon": "⛈️"},
    85: {"title": "Snow Showers", "icon": "🌨️"},
    86: {"title": "Heavy Snow Showers", "icon": "❄️"},
    95: {"title": "Thunderstorm", "icon": "⛈️"},
    96: {"title": "Thunderstorm with Hail", "icon": "⛈️"},
    99: {"title": "Severe Thunderstorm", "icon": "🌩️"},
}


def weather_label(code: Any) -> dict[str, str]:
    try:
        return WEATHER_CODES.get(int(code), {"title": "Weather Update", "icon": "🌡️"})
    except (TypeError, ValueError):
        return {"title": "Unknown", "icon": "🌡️"}


def safe_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name}. Please provide a valid coordinate.") from None


def get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params or {}, headers=REQUEST_HEADERS, timeout=15)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = response.json()
        else:
            payload = {}

        if response.status_code >= 400:
            reason = payload.get("reason") or payload.get("error") or response.text[:180]
            raise RuntimeError(f"API error {response.status_code}: {reason}")

        if not isinstance(payload, dict):
            raise RuntimeError("Weather service returned an unexpected response.")
        return payload
    except requests.exceptions.SSLError as exc:
        raise RuntimeError("SSL certificate problem. Try upgrading certifi: pip install --upgrade certifi") from exc
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError("Internet/DNS connection failed. Check Wi-Fi, mobile hotspot, VPN, or firewall.") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Weather service timed out. Try again in a few seconds.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Weather service unavailable: {exc}") from exc


def list_get(values: Any, index: int, default: Any = None) -> Any:
    if isinstance(values, list) and 0 <= index < len(values):
        return values[index]
    return default


def make_place_label(name: str, admin1: str | None, country: str | None) -> str:
    parts = [name]
    if admin1 and admin1 != name:
        parts.append(admin1)
    if country:
        parts.append(country)
    return ", ".join(parts)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/geocode")
def geocode():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"error": "Enter at least 2 characters for city search."}), 400

    params = {
        "name": query,
        "count": 10,
        "language": "en",
        "format": "json",
    }

    try:
        payload = get_json(OPEN_METEO_GEOCODE_URL, params)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    locations: list[dict[str, Any]] = []
    for item in payload.get("results", []) or []:
        name = item.get("name") or "Unknown place"
        admin1 = item.get("admin1") or ""
        country = item.get("country") or ""
        latitude = item.get("latitude")
        longitude = item.get("longitude")

        if latitude is None or longitude is None:
            continue

        locations.append(
            {
                "id": item.get("id"),
                "name": name,
                "admin1": admin1,
                "country": country,
                "label": make_place_label(name, admin1, country),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": item.get("timezone"),
                "elevation": item.get("elevation"),
            }
        )

    return jsonify({"locations": locations})


@app.get("/api/ip-location")
def ip_location():
    try:
        payload = get_json(IP_LOCATION_URL)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    city = payload.get("city") or "Approximate location"
    region = payload.get("region") or ""
    country = payload.get("country_name") or payload.get("country") or ""

    if latitude is None or longitude is None:
        return jsonify({"error": "Approximate IP location was not available."}), 503

    return jsonify(
        {
            "latitude": latitude,
            "longitude": longitude,
            "label": make_place_label(city, region, country),
            "source": "ip",
            "note": "Approximate IP-based location, not precise GPS location.",
        }
    )


@app.get("/api/weather")
def weather():
    try:
        latitude = safe_float(request.args.get("lat"), "latitude")
        longitude = safe_float(request.args.get("lon"), "longitude")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return jsonify({"error": "Latitude or longitude is outside the valid range."}), 400

    place_name = (request.args.get("name") or "Your Current Location").strip()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]
        ),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "weather_code",
                "precipitation_probability",
                "wind_speed_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ]
        ),
        "timezone": "auto",
        "forecast_days": 7,
    }

    try:
        payload = get_json(OPEN_METEO_FORECAST_URL, params)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    current = payload.get("current", {}) or {}
    hourly = payload.get("hourly", {}) or {}
    daily = payload.get("daily", {}) or {}

    current_label = weather_label(current.get("weather_code"))

    hourly_items: list[dict[str, Any]] = []
    hourly_times = hourly.get("time", []) or []
    current_time = str(current.get("time") or "")[:13]
    start_index = 0
    for index, hour_value in enumerate(hourly_times):
        if str(hour_value).startswith(current_time):
            start_index = index
            break

    for i in range(start_index, min(start_index + 12, len(hourly_times))):
        label = weather_label(list_get(hourly.get("weather_code"), i))
        hourly_items.append(
            {
                "time": list_get(hourly_times, i),
                "temperature": list_get(hourly.get("temperature_2m"), i),
                "humidity": list_get(hourly.get("relative_humidity_2m"), i),
                "precipitation_probability": list_get(hourly.get("precipitation_probability"), i),
                "wind_speed": list_get(hourly.get("wind_speed_10m"), i),
                "condition": label["title"],
                "icon": label["icon"],
            }
        )

    daily_items: list[dict[str, Any]] = []
    daily_times = daily.get("time", []) or []
    for i in range(len(daily_times)):
        label = weather_label(list_get(daily.get("weather_code"), i))
        daily_items.append(
            {
                "date": list_get(daily_times, i),
                "max": list_get(daily.get("temperature_2m_max"), i),
                "min": list_get(daily.get("temperature_2m_min"), i),
                "sunrise": list_get(daily.get("sunrise"), i),
                "sunset": list_get(daily.get("sunset"), i),
                "rain_chance": list_get(daily.get("precipitation_probability_max"), i),
                "wind_max": list_get(daily.get("wind_speed_10m_max"), i),
                "condition": label["title"],
                "icon": label["icon"],
            }
        )

    return jsonify(
        {
            "place": place_name,
            "latitude": payload.get("latitude", latitude),
            "longitude": payload.get("longitude", longitude),
            "timezone": payload.get("timezone"),
            "current": {
                "time": current.get("time"),
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "precipitation": current.get("precipitation"),
                "rain": current.get("rain"),
                "cloud_cover": current.get("cloud_cover"),
                "pressure": current.get("pressure_msl"),
                "wind_speed": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
                "wind_gusts": current.get("wind_gusts_10m"),
                "is_day": current.get("is_day"),
                "condition": current_label["title"],
                "icon": current_label["icon"],
            },
            "hourly": hourly_items,
            "daily": daily_items,
            "units": payload.get("current_units", {}),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
