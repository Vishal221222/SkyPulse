const searchForm = document.getElementById("searchForm");
const cityInput = document.getElementById("cityInput");
const suggestions = document.getElementById("suggestions");
const localWeatherBtn = document.getElementById("localWeatherBtn");
const messageBox = document.getElementById("messageBox");
const dashboard = document.getElementById("weatherDashboard");

const elements = {
  placeName: document.getElementById("placeName"),
  updatedTime: document.getElementById("updatedTime"),
  weatherIcon: document.getElementById("weatherIcon"),
  temperature: document.getElementById("temperature"),
  conditionText: document.getElementById("conditionText"),
  feelsLike: document.getElementById("feelsLike"),
  humidity: document.getElementById("humidity"),
  wind: document.getElementById("wind"),
  rain: document.getElementById("rain"),
  pressure: document.getElementById("pressure"),
  hourlyForecast: document.getElementById("hourlyForecast"),
  dailyForecast: document.getElementById("dailyForecast"),
};

let debounceTimer = null;
let lastLocations = [];

function showMessage(text, type = "info") {
  messageBox.textContent = text;
  messageBox.className = `message ${type}`;
}

function hideMessage() {
  messageBox.className = "message hidden";
  messageBox.textContent = "";
}

function setButtonLoading(button, isLoading, textWhenLoading = "Loading...") {
  if (!button) return;
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = textWhenLoading;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function formatNumber(value, fallback = "--") {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return fallback;
  return Math.round(Number(value));
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

function formatDay(value) {
  if (!value) return "--";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short",
    day: "numeric",
  }).format(date);
}

function setTheme(current) {
  document.body.classList.remove("day-theme", "rain-theme", "storm-theme");
  const condition = String(current?.condition || "").toLowerCase();

  if (condition.includes("thunder") || condition.includes("storm")) {
    document.body.classList.add("storm-theme");
  } else if (condition.includes("rain") || condition.includes("drizzle") || condition.includes("shower")) {
    document.body.classList.add("rain-theme");
  } else if (Number(current?.is_day) === 1) {
    document.body.classList.add("day-theme");
  }
}

async function readJsonResponse(response, fallbackMessage) {
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(payload.error || fallbackMessage);
  }
  return payload;
}

async function fetchWeather({ latitude, longitude, name }) {
  if (latitude === undefined || longitude === undefined) {
    throw new Error("Missing location coordinates.");
  }

  showMessage("Getting weather details...");
  const params = new URLSearchParams({
    lat: latitude,
    lon: longitude,
    name: name || "Your Current Location",
  });

  const response = await fetch(`/api/weather?${params.toString()}`);
  const payload = await readJsonResponse(response, "Unable to fetch weather data.");

  renderWeather(payload);
  hideMessage();
}

function renderWeather(data) {
  dashboard.classList.remove("hidden");
  setTheme(data.current);

  elements.placeName.textContent = data.place || "Selected Location";
  elements.updatedTime.textContent = `Updated ${formatTime(data.current?.time)} • ${data.timezone || "local timezone"}`;
  elements.weatherIcon.textContent = data.current?.icon || "🌡️";
  elements.temperature.textContent = formatNumber(data.current?.temperature);
  elements.conditionText.textContent = data.current?.condition || "Weather update";
  elements.feelsLike.textContent = formatNumber(data.current?.feels_like);
  elements.humidity.textContent = `${formatNumber(data.current?.humidity)}%`;
  elements.wind.textContent = `${formatNumber(data.current?.wind_speed)} km/h`;
  elements.rain.textContent = `${formatNumber(data.current?.rain ?? data.current?.precipitation)} mm`;
  elements.pressure.textContent = `${formatNumber(data.current?.pressure)} hPa`;

  elements.hourlyForecast.innerHTML = (data.hourly || []).map((item) => `
    <article class="hour-card">
      <p class="time">${formatTime(item.time)}</p>
      <div class="mini-icon">${item.icon || "🌡️"}</div>
      <strong>${formatNumber(item.temperature)}°</strong>
      <small>Rain ${formatNumber(item.precipitation_probability)}%<br>Wind ${formatNumber(item.wind_speed)} km/h</small>
    </article>
  `).join("");

  elements.dailyForecast.innerHTML = (data.daily || []).map((item) => `
    <article class="day-card">
      <p class="time">${formatDay(item.date)}</p>
      <div class="mini-icon">${item.icon || "🌡️"}</div>
      <strong>${formatNumber(item.max)}° / ${formatNumber(item.min)}°</strong>
      <small>${item.condition || "Weather"}<br>Rain ${formatNumber(item.rain_chance)}%<br>Wind ${formatNumber(item.wind_max)} km/h</small>
    </article>
  `).join("");
}

async function searchLocations(query) {
  const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
  const payload = await readJsonResponse(response, "Unable to search locations.");
  return payload.locations || [];
}

function renderSuggestions(locations) {
  lastLocations = locations;

  if (!locations.length) {
    suggestions.style.display = "block";
    suggestions.innerHTML = `<div class="suggestion-item empty">No matching city found</div>`;
    return;
  }

  suggestions.style.display = "block";
  suggestions.innerHTML = locations.map((location, index) => `
    <button class="suggestion-item" type="button" data-index="${index}">
      <strong>${location.name}</strong>
      <small>${location.admin1 ? `${location.admin1}, ` : ""}${location.country || ""}</small>
    </button>
  `).join("");
}

cityInput.addEventListener("input", () => {
  const query = cityInput.value.trim();
  clearTimeout(debounceTimer);

  if (query.length < 2) {
    suggestions.style.display = "none";
    return;
  }

  debounceTimer = setTimeout(async () => {
    try {
      const locations = await searchLocations(query);
      renderSuggestions(locations);
    } catch (error) {
      suggestions.style.display = "none";
      showMessage(error.message, "error");
    }
  }, 350);
});

suggestions.addEventListener("click", async (event) => {
  const item = event.target.closest(".suggestion-item");
  if (!item || item.classList.contains("empty")) return;

  const location = lastLocations[Number(item.dataset.index)];
  if (!location) return;

  cityInput.value = location.label;
  suggestions.style.display = "none";

  try {
    await fetchWeather({
      latitude: location.latitude,
      longitude: location.longitude,
      name: location.label,
    });
  } catch (error) {
    showMessage(error.message, "error");
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = cityInput.value.trim();
  const submitButton = searchForm.querySelector("button[type='submit']");

  if (query.length < 2) {
    showMessage("Please type a city name first.", "error");
    return;
  }

  try {
    setButtonLoading(submitButton, true, "Searching...");
    const locations = await searchLocations(query);
    if (!locations.length) {
      showMessage("City not found. Try a clear name like 'Delhi India' or 'Mumbai'.", "error");
      return;
    }

    const location = locations[0];
    cityInput.value = location.label;
    suggestions.style.display = "none";
    await fetchWeather({
      latitude: location.latitude,
      longitude: location.longitude,
      name: location.label,
    });
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    setButtonLoading(submitButton, false);
  }
});

function getLocationErrorMessage(error) {
  if (!error) return "Unable to fetch your current location.";

  if (error.code === 1) {
    return "Location permission is blocked. Allow location access from browser site settings, or search your city manually.";
  }
  if (error.code === 2) {
    return "Your device location is unavailable. Turn on Windows Location / mobile GPS, then try again.";
  }
  if (error.code === 3) {
    return "Location request timed out. Trying approximate IP location instead...";
  }
  return error.message || "Unable to fetch your current location.";
}

async function fetchApproximateIpLocation() {
  showMessage("Trying approximate location from your internet connection...");
  const response = await fetch("/api/ip-location");
  const payload = await readJsonResponse(response, "Approximate location is not available right now.");
  await fetchWeather({
    latitude: payload.latitude,
    longitude: payload.longitude,
    name: `${payload.label} (approx.)`,
  });
}

localWeatherBtn.addEventListener("click", () => {
  if (!window.isSecureContext) {
    showMessage("Open the app with http://localhost:5000 or http://127.0.0.1:5000. Browser GPS is blocked on insecure/non-local URLs.", "error");
    fetchApproximateIpLocation().catch((error) => showMessage(error.message, "error"));
    return;
  }

  if (!navigator.geolocation) {
    showMessage("Geolocation is not supported by this browser. Trying approximate IP location...", "error");
    fetchApproximateIpLocation().catch((error) => showMessage(error.message, "error"));
    return;
  }

  setButtonLoading(localWeatherBtn, true, "Locating...");
  showMessage("Please allow location permission in your browser.");

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      try {
        cityInput.value = "";
        suggestions.style.display = "none";
        await fetchWeather({
          latitude,
          longitude,
          name: `Your Current Location ±${formatNumber(accuracy)}m`,
        });
      } catch (error) {
        showMessage(error.message, "error");
      } finally {
        setButtonLoading(localWeatherBtn, false);
      }
    },
    async (error) => {
      try {
        showMessage(getLocationErrorMessage(error), "error");
        await fetchApproximateIpLocation();
      } catch (fallbackError) {
        showMessage(`${getLocationErrorMessage(error)} ${fallbackError.message}`, "error");
      } finally {
        setButtonLoading(localWeatherBtn, false);
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 300000,
    }
  );
});

window.addEventListener("click", (event) => {
  if (!event.target.closest(".search-box")) {
    suggestions.style.display = "none";
  }
});

fetchWeather({ latitude: 28.6139, longitude: 77.2090, name: "New Delhi, India" }).catch((error) => {
  showMessage(error.message, "error");
});
