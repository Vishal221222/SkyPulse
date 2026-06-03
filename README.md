# SkyPulse Weather - Flask Weather App

A stunning Flask weather app with:

- Browser local weather using Geolocation
- City search with Open-Meteo Geocoding API
- Current temperature, feels-like temperature, humidity, rain, pressure and wind
- Next 12-hour forecast
- 7-day forecast
- Animated glassmorphism frontend
- No API key required

## Run locally

```bash
cd stunning_weather_app
python -m venv env
```

### Windows PowerShell

```bash
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### CMD

```bash
env\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
source env/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Notes

Local weather uses the browser's `navigator.geolocation` feature. The browser will ask for location permission.

This project uses Open-Meteo, so you do not need to create an API key.
