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
}

function formatNumber(value, fallback = "--") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback;
  return Math.round(Number(value));
}

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(new Date(value));
}

function formatDay(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short",
    day: "numeric",
  }).format(new Date(value));
}

function setTheme(current) {
  document.body.classList.remove("day-theme", "rain-theme", "storm-theme");
  const condition = String(current.condition || "").toLowerCase();

  if (condition.includes("thunder") || condition.includes("storm")) {
    document.body.classList.add("storm-theme");
  } else if (condition.includes("rain") || condition.includes("drizzle") || condition.includes("showers")) {
    document.body.classList.add("rain-theme");
  } else if (Number(current.is_day) === 1) {
    document.body.classList.add("day-theme");
  }
}

async function fetchWeather({ latitude, longitude, name }) {
  showMessage("Fetching live weather data...");
  const params = new URLSearchParams({ lat: latitude, lon: longitude, name: name || "Your Current Location" });
  const response = await fetch(`/api/weather?${params.toString()}`);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Unable to fetch weather data.");
  }

  renderWeather(payload);
  hideMessage();
}

function renderWeather(data) {
  dashboard.classList.remove("hidden");
  setTheme(data.current);

  elements.placeName.textContent = data.place || "Selected Location";
  elements.updatedTime.textContent = `Updated ${formatTime(data.current.time)} • ${data.timezone || "local timezone"}`;
  elements.weatherIcon.textContent = data.current.icon || "🌡️";
  elements.temperature.textContent = formatNumber(data.current.temperature);
  elements.conditionText.textContent = data.current.condition || "Weather Update";
  elements.feelsLike.textContent = formatNumber(data.current.feels_like);
  elements.humidity.textContent = `${formatNumber(data.current.humidity)}%`;
  elements.wind.textContent = `${formatNumber(data.current.wind_speed)} km/h`;
  elements.rain.textContent = `${formatNumber(data.current.rain || data.current.precipitation)} mm`;
  elements.pressure.textContent = `${formatNumber(data.current.pressure)} hPa`;

  elements.hourlyForecast.innerHTML = data.hourly.map((item) => `
    <article class="hour-card">
      <p class="time">${formatTime(item.time)}</p>
      <div class="mini-icon">${item.icon}</div>
      <strong>${formatNumber(item.temperature)}°</strong>
      <small>Rain ${formatNumber(item.precipitation_probability)}%<br>Wind ${formatNumber(item.wind_speed)} km/h</small>
    </article>
  `).join("");

  elements.dailyForecast.innerHTML = data.daily.map((item) => `
    <article class="day-card">
      <p class="time">${formatDay(item.date)}</p>
      <div class="mini-icon">${item.icon}</div>
      <strong>${formatNumber(item.max)}° / ${formatNumber(item.min)}°</strong>
      <small>${item.condition}<br>Rain ${formatNumber(item.rain_chance)}%<br>Wind ${formatNumber(item.wind_max)} km/h</small>
    </article>
  `).join("");
}

async function searchLocations(query) {
  const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "No location found.");
  }
  return payload.locations || [];
}

function renderSuggestions(locations) {
  lastLocations = locations;

  if (!locations.length) {
    suggestions.style.display = "block";
    suggestions.innerHTML = `<div class="suggestion-item">No matching city found</div>`;
    return;
  }

  suggestions.style.display = "block";
  suggestions.innerHTML = locations.map((location, index) => `
    <div class="suggestion-item" data-index="${index}">
      <strong>${location.name}</strong><br>
      <small>${location.admin1 ? `${location.admin1}, ` : ""}${location.country}</small>
    </div>
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
    }
  }, 350);
});

suggestions.addEventListener("click", async (event) => {
  const item = event.target.closest(".suggestion-item");
  if (!item) return;

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

  if (query.length < 2) {
    showMessage("Please enter a city name.", "error");
    return;
  }

  try {
    const locations = await searchLocations(query);
    if (!locations.length) {
      showMessage("No city found. Try another spelling.", "error");
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
  }
});

localWeatherBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    showMessage("Geolocation is not supported by this browser.", "error");
    return;
  }

  showMessage("Allow location permission to show your local weather...");
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const { latitude, longitude } = position.coords;
      try {
        cityInput.value = "";
        suggestions.style.display = "none";
        await fetchWeather({ latitude, longitude, name: "Your Current Location" });
      } catch (error) {
        showMessage(error.message, "error");
      }
    },
    () => {
      showMessage("Location permission denied. Search your city manually.", "error");
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 600000,
    }
  );
});

window.addEventListener("click", (event) => {
  if (!event.target.closest(".search-box")) {
    suggestions.style.display = "none";
  }
});

// Default city shown on first load. Change this to your preferred location.
fetchWeather({ latitude: 28.6139, longitude: 77.2090, name: "New Delhi, India" }).catch((error) => {
  showMessage(error.message, "error");
});
