# SkyPulse Weather App

A polished Flask weather app with city search, browser GPS location, approximate IP fallback, current weather, 12-hour forecast and 7-day forecast.

## Run

```bash
python -m venv env
```

Windows:

```bash
env\Scripts\activate
```

macOS/Linux:

```bash
source env/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Flask:

```bash
python app.py
```

Open exactly one of these URLs:

```text
http://localhost:5000
http://127.0.0.1:5000
```

## Important for location

Browser GPS location works only on secure contexts. For local development, `localhost` and `127.0.0.1` are allowed. Do not open the HTML file directly and do not use `http://0.0.0.0:5000` in the browser.

If precise browser location is denied or unavailable, the app automatically tries approximate IP-based location.
