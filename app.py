from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

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


def weather_label(code: int | None) -> dict[str, str]:
    if code is None:
        return {"title": "Unknown", "icon": "🌡️"}
    return WEATHER_CODES.get(int(code), {"title": "Weather Update", "icon": "🌡️"})


def safe_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name}") from None


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Weather service unavailable: {exc}") from exc


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
        "count": 6,
        "language": "en",
        "format": "json",
    }

    try:
        payload = get_json(OPEN_METEO_GEOCODE_URL, params)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    locations = []
    for item in payload.get("results", []) or []:
        country = item.get("country") or ""
        admin1 = item.get("admin1") or ""
        name = item.get("name") or "Unknown place"
        label_parts = [name]
        if admin1 and admin1 != name:
            label_parts.append(admin1)
        if country:
            label_parts.append(country)

        locations.append(
            {
                "id": item.get("id"),
                "name": name,
                "admin1": admin1,
                "country": country,
                "label": ", ".join(label_parts),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "timezone": item.get("timezone"),
                "elevation": item.get("elevation"),
            }
        )

    return jsonify({"locations": locations})


@app.get("/api/weather")
def weather():
    try:
        latitude = safe_float(request.args.get("lat"), "latitude")
        longitude = safe_float(request.args.get("lon"), "longitude")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

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

    current_code = current.get("weather_code")
    current_label = weather_label(current_code)

    hourly_items = []
    hourly_times = hourly.get("time", []) or []
    now_hour = datetime.now().strftime("%Y-%m-%dT%H")
    start_index = 0
    for index, hour_value in enumerate(hourly_times):
        if str(hour_value).startswith(now_hour):
            start_index = index
            break

    for i in range(start_index, min(start_index + 12, len(hourly_times))):
        code = hourly.get("weather_code", [None] * len(hourly_times))[i]
        label = weather_label(code)
        hourly_items.append(
            {
                "time": hourly_times[i],
                "temperature": hourly.get("temperature_2m", [None] * len(hourly_times))[i],
                "humidity": hourly.get("relative_humidity_2m", [None] * len(hourly_times))[i],
                "precipitation_probability": hourly.get("precipitation_probability", [None] * len(hourly_times))[i],
                "wind_speed": hourly.get("wind_speed_10m", [None] * len(hourly_times))[i],
                "condition": label["title"],
                "icon": label["icon"],
            }
        )

    daily_items = []
    daily_times = daily.get("time", []) or []
    for i in range(len(daily_times)):
        code = daily.get("weather_code", [None] * len(daily_times))[i]
        label = weather_label(code)
        daily_items.append(
            {
                "date": daily_times[i],
                "max": daily.get("temperature_2m_max", [None] * len(daily_times))[i],
                "min": daily.get("temperature_2m_min", [None] * len(daily_times))[i],
                "sunrise": daily.get("sunrise", [None] * len(daily_times))[i],
                "sunset": daily.get("sunset", [None] * len(daily_times))[i],
                "rain_chance": daily.get("precipitation_probability_max", [None] * len(daily_times))[i],
                "wind_max": daily.get("wind_speed_10m_max", [None] * len(daily_times))[i],
                "condition": label["title"],
                "icon": label["icon"],
            }
        )

    response = {
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
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
