/**
 * WeatherGPT - Main Application Controller
 */

window.currentCity = "Indore";
window.currentLanguage = "hinglish";
window.currentPersona = "general";

// Dynamic API Base URL for local & cloud deployment
function getBackendBase() {
  if (window.BACKEND_API_URL) return window.BACKEND_API_URL.replace(/\/$/, '');
  const saved = localStorage.getItem('WEATHERGPT_BACKEND_URL');
  if (saved) return saved.replace(/\/$/, '');
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
    return 'http://localhost:8000';
  }
  // When hosted on any cloud domain (Render, Railway, custom domain), use origin
  if (window.location.protocol.startsWith('http')) {
    return window.location.origin;
  }
  return 'https://weathergpt-sih-2026-1.onrender.com';
}

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  setupEventListeners();
  window.chatController.init(updateWeatherDashboard);

  // Initialize Atmospheric Particle Engine
  if (window.weatherVisualizer) {
    window.weatherVisualizer.init();
  }

  // Initialize Doppler Radar & Pan-India Map
  window.radarViewer.init(22.7196, 75.8577);

  // Initial Weather Load for default city (Indore)
  await loadCityWeather(window.currentCity);

  // Load All-India Live Weather News Ticker
  initAllIndiaTicker();

  // Check Backend Health
  checkBackendHealth();
}

function setupEventListeners() {
  // City Selector Dropdown
  const citySelect = document.getElementById('citySelector');
  if (citySelect) {
    citySelect.addEventListener('change', (e) => {
      window.currentCity = e.target.value;
      loadCityWeather(window.currentCity);
    });
  }

  // Pan-India Map Quick Trigger Button
  const panIndiaBtn = document.getElementById('panIndiaMapToggleBtn');
  if (panIndiaBtn) {
    panIndiaBtn.addEventListener('click', () => {
      const radarTab = document.querySelector('.dash-tab[data-tab="radar-view"]');
      if (radarTab) radarTab.click();
      window.radarViewer.setPanIndiaView();
    });
  }

  // Radar Pan-India View Button
  const radarPanIndiaBtn = document.getElementById('radarPanIndiaBtn');
  if (radarPanIndiaBtn) {
    radarPanIndiaBtn.addEventListener('click', () => {
      document.querySelectorAll('.radar-action-chip').forEach(c => c.classList.remove('active'));
      radarPanIndiaBtn.classList.add('active');
      window.radarViewer.setPanIndiaView();
    });
  }

  // Radar Focus City View Button
  const radarCityFocusBtn = document.getElementById('radarCityFocusBtn');
  if (radarCityFocusBtn) {
    radarCityFocusBtn.addEventListener('click', () => {
      document.querySelectorAll('.radar-action-chip').forEach(c => c.classList.remove('active'));
      radarCityFocusBtn.classList.add('active');
      window.radarViewer.setCityFocusView();
    });
  }

  // Suggestion Chips Click
  const sugBtns = document.querySelectorAll('.sug-chip');
  sugBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.query;
      if (q) window.chatController.sendMessage(q);
    });
  });

  // Voice Mic Button
  const micBtn = document.getElementById('voiceMicBtn');
  if (micBtn) {
    micBtn.addEventListener('click', () => {
      window.voiceEngine.toggleRecording(micBtn, (transcript) => {
        const inputField = document.getElementById('chatInput');
        if (inputField) {
          inputField.value = transcript;
          window.chatController.sendMessage(transcript);
          inputField.value = '';
        }
      });
    });
  }

  // Dashboard Tabs Switcher
  const dashTabs = document.querySelectorAll('.dash-tab');
  const dashPanes = document.querySelectorAll('.dash-content-pane');
  dashTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      dashTabs.forEach(t => t.classList.remove('active'));
      dashPanes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.dataset.tab;
      
      if (targetId === 'weather-view') {
        document.getElementById('weatherView').classList.add('active');
      } else if (targetId === 'radar-view') {
        document.getElementById('radarView').classList.add('active');
        window.radarViewer.resize();
      } else if (targetId === 'nwp-view') {
        document.getElementById('nwpView').classList.add('active');
        loadNWPComparison(window.currentCity);
      } else if (targetId === 'climate-view') {
        document.getElementById('climateView').classList.add('active');
        loadClimateTrends(window.currentCity);
      }
    });
  });
}

// Global helper to switch city from anywhere (ticker, map marker, suggestions)
window.selectCityByName = function(cityName) {
  window.currentCity = cityName;
  const citySelect = document.getElementById('citySelector');
  if (citySelect) {
    let found = false;
    for (let opt of citySelect.options) {
      if (opt.value.toLowerCase() === cityName.toLowerCase()) {
        citySelect.value = opt.value;
        found = true;
        break;
      }
    }
    if (!found) {
      const newOpt = document.createElement('option');
      newOpt.value = cityName;
      newOpt.textContent = cityName;
      newOpt.selected = true;
      citySelect.appendChild(newOpt);
    }
  }
  loadCityWeather(cityName);
};

// All-India Live Weather News Ticker
async function initAllIndiaTicker() {
  const tickerTrack = document.getElementById('tickerTrack');
  if (!tickerTrack) return;

  const defaultCities = [
    { name: "New Delhi", temp: 32, cond: "☀️ Sunny", alert: null },
    { name: "Mumbai", temp: 29, cond: "🌧️ Coastal Showers", alert: "High Tide" },
    { name: "Bengaluru", temp: 24, cond: "⛅ Pleasant", alert: null },
    { name: "Kolkata", temp: 30, cond: "🌦️ Passing Rain", alert: null },
    { name: "Chennai", temp: 31, cond: "🌊 Sea Breeze", alert: null },
    { name: "Indore", temp: 28, cond: "⚡ Convective Clouds", alert: "Yellow Watch" },
    { name: "Bhopal", temp: 29, cond: "⛅ Partly Cloudy", alert: null },
    { name: "Jaipur", temp: 34, cond: "☀️ Dry Heat", alert: null },
    { name: "Hyderabad", temp: 30, cond: "⛅ Clear", alert: null },
    { name: "Ahmedabad", temp: 33, cond: "☀️ Clear Sky", alert: null },
    { name: "Shimla", temp: 17, cond: "🌤️ Mountain Cool", alert: null },
    { name: "Srinagar", temp: 16, cond: "⛅ Mild", alert: null },
    { name: "Guwahati", temp: 27, cond: "🌧️ Thunderstorms", alert: "Rain Warning" },
    { name: "Kochi", temp: 28, cond: "🌧️ Monsoon Rain", alert: null },
    { name: "Patna", temp: 31, cond: "⛅ Humid", alert: null },
    { name: "Lucknow", temp: 32, cond: "☀️ Sunny", alert: null }
  ];

  try {
    const resp = await fetch(`${getBackendBase()}/api/weather/all-india`);
    if (resp.ok) {
      const data = await resp.json();
      if (data.cities && data.cities.length > 0) {
        renderTickerItems(data.cities);
        return;
      }
    }
  } catch (e) {
    console.warn("Using baseline All-India ticker data:", e);
  }

  renderTickerItems(defaultCities);

  // Auto-refresh All-India ticker every 5 minutes
  setInterval(async () => {
    try {
      const resp = await fetch(`${getBackendBase()}/api/weather/all-india`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.cities && data.cities.length > 0) renderTickerItems(data.cities);
      }
    } catch (_) {}
  }, 300000);
}

function renderTickerItems(cities) {
  const tickerTrack = document.getElementById('tickerTrack');
  if (!tickerTrack) return;

  // Duplicate for seamless infinite marquee scroll
  const duplicated = [...cities, ...cities];
  tickerTrack.innerHTML = '';

  duplicated.forEach(c => {
    const chip = document.createElement('span');
    chip.className = 'ticker-city-chip';
    chip.title = `Click to view ${c.name} forecast`;
    const alertHTML = c.alert ? `<span class="city-alert">${c.alert}</span>` : '';
    const condText = c.condition ? c.condition : (c.cond || '⛅ Partly Cloudy');
    chip.innerHTML = `
      <b class="city-name">📍 ${c.name}</b>: 
      <span class="city-temp">${c.temperature || c.temp}°C</span> 
      <span class="city-cond">${condText}</span>
      ${alertHTML}
    `;
    chip.addEventListener('click', () => {
      window.selectCityByName(c.name);
    });
    tickerTrack.appendChild(chip);
  });
}

async function loadCityWeather(city) {
  try {
    const resp = await fetch(`${getBackendBase()}/api/weather/forecast?location=${encodeURIComponent(city)}`);
    if (resp.ok) {
      const weather = await resp.json();
      updateWeatherDashboard(weather);
      window.radarViewer.updateLocation(weather.latitude, weather.longitude, weather.location);
      return;
    }
  } catch (e) {
    console.warn("Backend unreachable, falling back to direct Open-Meteo:", e);
  }

  // Client-Side Direct Fallback
  try {
    const coords = {
      indore: { lat: 22.7196, lon: 75.8577, name: "Indore" },
      bhopal: { lat: 23.2599, lon: 77.4126, name: "Bhopal" },
      delhi: { lat: 28.6139, lon: 77.2090, name: "Delhi" },
      mumbai: { lat: 19.0760, lon: 72.8777, name: "Mumbai" },
      jaipur: { lat: 26.9124, lon: 75.7873, name: "Jaipur" },
      bengaluru: { lat: 12.9716, lon: 77.5946, name: "Bengaluru" },
      kolkata: { lat: 22.5726, lon: 88.3639, name: "Kolkata" },
      chennai: { lat: 13.0827, lon: 80.2707, name: "Chennai" }
    };
    const c = coords[city.toLowerCase()] || coords.indore;
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${c.lat}&longitude=${c.lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&hourly=temperature_2m,precipitation_probability&timezone=auto`;
    const r = await fetch(url);
    const d = await r.json();
    const weather = {
      location: c.name,
      latitude: c.lat,
      longitude: c.lon,
      temperature: Math.round(d.current.temperature_2m),
      apparent_temperature: Math.round(d.current.apparent_temperature),
      condition: d.current.precipitation > 0 ? "Rain Showers" : "Partly Cloudy",
      precipitation_probability: d.hourly?.precipitation_probability?.[12] || 15,
      humidity: d.current.relative_humidity_2m,
      wind_speed: Math.round(d.current.wind_speed_10m),
      uv_index: 6.2,
      air_quality_index: 45,
      hourly: []
    };
    updateWeatherDashboard(weather);
    window.radarViewer.updateLocation(weather.latitude, weather.longitude, weather.location);
  } catch (err) {
    console.error("Direct fetch failed:", err);
  }
}

function updateWeatherDashboard(weather) {
  if (!weather) return;

  // City & condition
  document.getElementById('cardLocation').textContent = weather.location;
  document.getElementById('cardCondition').textContent = weather.condition;
  document.getElementById('cardTemp').textContent = Math.round(weather.temperature) + '°';
  document.getElementById('cardApparent').textContent = Math.round(weather.apparent_temperature) + '°C';
  document.getElementById('cardPrecipChance').textContent = weather.precipitation_probability + '%';

  // Metrics
  document.getElementById('metricWind').textContent = `${weather.wind_speed} km/h`;
  document.getElementById('metricHumidity').textContent = `${weather.humidity}%`;
  document.getElementById('metricUV').textContent = `${weather.uv_index}`;
  document.getElementById('metricAQI').textContent = `${weather.air_quality_index || 45} (Good)`;

  // Alert Intelligence in hero card
  const alertBox = document.getElementById('cardAlertBox');
  if (weather.severe_warning && weather.severe_warning.severity !== 'normal') {
    alertBox.style.display = 'block';
    document.getElementById('cardAlertTitle').textContent = weather.severe_warning.headline;
    document.getElementById('cardAlertDesc').textContent = weather.severe_warning.description;

    const kisanAct = document.getElementById('kisanAlertAction');
    const yatriAct = document.getElementById('yatriAlertAction');
    const nagrikAct = document.getElementById('nagrikAlertAction');

    if (weather.precipitation_probability > 40) {
      if (kisanAct) kisanAct.textContent = "Foliar spray aur sinchai agale 24 ghante ke liye taal dein taaki chemical wash-off na ho.";
      if (yatriAct) yatriAct.textContent = "Bypass highways par visibility kam rahegi; sham ke samay slow drive karein.";
      if (nagrikAct) nagrikAct.textContent = "Low-lying underpass me waterlogging ho sakti hai; umbrella sath rakhein.";
    } else {
      if (kisanAct) kisanAct.textContent = "Mausam saaf hai; nindai-gudai aur keetnashak spray subah ke samay kar sakte hain.";
      if (yatriAct) yatriAct.textContent = "Highway corridor conditions clear aur safe hain; travel schedule on time rahega.";
      if (nagrikAct) nagrikAct.textContent = "Dopahar me direct dhoop se bachein aur hydration banaye rakhein.";
    }
  } else {
    alertBox.style.display = 'none';
  }

  // 24-Hour Risk Timeline Ribbon
  const riskBar = document.getElementById('riskTimelineBar');
  if (riskBar && weather.hourly && weather.hourly.length > 0) {
    riskBar.innerHTML = '';
    const hours = weather.hourly.slice(0, 16);
    hours.forEach(h => {
      const isRain = h.precipitation_probability > 35;
      const isHighRain = h.precipitation_probability > 60;
      const riskClass = isHighRain ? 'risk-high' : (isRain ? 'risk-mod' : 'risk-low');
      const segment = document.createElement('div');
      segment.className = `risk-seg ${riskClass}`;
      segment.innerHTML = `
        <span class="seg-time">${h.time}</span>
        <span class="seg-icon">${h.condition.split(' ')[0] || '🌤️'}</span>
        <span class="seg-temp">${Math.round(h.temperature)}°</span>
        <div class="seg-bar-fill" style="height:${Math.max(15, h.precipitation_probability)}%"></div>
        <span class="seg-rain">${h.precipitation_probability}%</span>
      `;
      riskBar.appendChild(segment);
    });
  }

  // Dynamic Unified Multi-Domain Intelligence Cards
  updateUnifiedAdvisories(weather);

  // Hourly Strip
  const hourlyContainer = document.getElementById('hourlyStrip');
  if (hourlyContainer && weather.hourly) {
    hourlyContainer.innerHTML = '';
    weather.hourly.slice(0, 12).forEach(item => {
      const el = document.createElement('div');
      el.className = 'hourly-item';
      el.innerHTML = `
        <span class="hourly-time">${item.time}</span>
        <span class="hourly-icon">${item.condition.split(' ')[0] || '🌤️'}</span>
        <span class="hourly-temp">${Math.round(item.temperature)}°C</span>
        <span class="hourly-rain">${item.precipitation_probability}% 💧</span>
      `;
      hourlyContainer.appendChild(el);
    });
  }

  // 7-Day Outlook & Visual Sliders
  const dailyContainer = document.getElementById('dailyList');
  if (window.weatherVisualizer && weather.daily) {
    window.weatherVisualizer.renderDailySliders(weather.daily);
  } else if (dailyContainer && weather.daily) {
    dailyContainer.innerHTML = '';
    weather.daily.forEach(d => {
      const row = document.createElement('div');
      row.className = 'daily-row';
      row.innerHTML = `
        <span class="daily-day">${d.date}</span>
        <span class="daily-cond">${d.condition}</span>
        <span class="daily-temps">${Math.round(d.max_temp)}°<span class="temp-min">${Math.round(d.min_temp)}°</span></span>
      `;
      dailyContainer.appendChild(row);
    });
  }

  // Atmospheric Particle Canvas, SVG Wave & Mini-Gauges
  if (window.weatherVisualizer) {
    window.weatherVisualizer.setWeatherState(weather.condition, weather.precipitation_probability);
    if (weather.hourly) window.weatherVisualizer.renderHourlySpline(weather.hourly);
    window.weatherVisualizer.updateGauges(weather);
  }
}

// Updates all 4 domains simultaneously in the single unified advisory format
function updateUnifiedAdvisories(weather) {
  const isRain = weather.precipitation_probability > 40;
  const isWindy = weather.wind_speed > 20;

  // 1. Kisan
  const soil = document.getElementById('kisanSoilMoisture');
  const spray = document.getElementById('kisanSprayWindow');
  const irrig = document.getElementById('kisanIrrigation');
  const pest = document.getElementById('kisanPestRisk');

  if (soil) soil.textContent = `${Math.min(95, Math.max(35, weather.humidity + 5))}% (${isRain ? 'Adequate' : 'Optimal'})`;
  if (spray) {
    spray.textContent = (isWindy || isRain) ? "Unfavorable (Wind/Rain Drift risk)" : "Favorable Morning Window (7-10 AM)";
  }
  if (irrig) {
    irrig.textContent = isRain ? "Postpone Irrigation (Rain Expected)" : "Safe for regular light irrigation";
  }
  if (pest) {
    pest.textContent = weather.humidity > 65 ? "Fungal Blight Risk: Moderate (High Humidity)" : "Pest Risk: Low";
  }

  // 2. Yatri
  const safety = document.getElementById('yatriSafetyScore');
  const vis = document.getElementById('yatriVisibility');
  const crosswind = document.getElementById('yatriCrosswind');
  const flood = document.getElementById('yatriFloodRisk');

  if (safety) safety.textContent = isRain ? "6.9 / 10 (Wet Roads Caution)" : "9.0 / 10 (Optimal Transit)";
  if (vis) vis.textContent = isRain ? "Visibility: 3 - 5 km (Showers)" : "Visibility: > 8 km (Clear View)";
  if (crosswind) crosswind.textContent = `Crosswind: ${weather.wind_speed} km/h (${isWindy ? 'Caution on elevated bridges' : 'Gentle'})`;
  if (flood) flood.textContent = isRain ? "Underpass: Watch for brief waterlogging" : "Underpass Waterlogging: Low Risk";

  // 3. Nagrik
  const comfort = document.getElementById('generalComfort');
  const goOut = document.getElementById('generalGoOut');
  const risk = document.getElementById('generalRisk');

  if (comfort) comfort.textContent = `${Math.round(weather.temperature)}°C • ${weather.humidity}% Humidity`;
  if (goOut) goOut.textContent = isRain ? "Umbrella / Raincoat recommended for commute" : "Outdoor weather pleasant & clear";
  if (risk) {
    risk.textContent = weather.severe_warning && weather.severe_warning.severity !== 'normal'
      ? `Active Watch: ${weather.severe_warning.headline}`
      : "IMD Watch Level: Normal / Green Zone";
  }

  // 4. Disaster Readiness
  const dLevel = document.getElementById('disasterLevel');
  const dPop = document.getElementById('disasterPop');
  const dChannels = document.getElementById('disasterChannels');
  const dShelters = document.getElementById('disasterShelters');

  if (dLevel) dLevel.textContent = weather.severe_warning ? weather.severe_warning.headline : "Level-1 (Normal Green)";
  if (dPop) dPop.textContent = isRain ? "Catchment monitoring active in low-lying sectors" : "No vulnerable settlements at risk";
  if (dChannels) dChannels.textContent = "NDMA CAP Gateway Stream Active";
  if (dShelters) dShelters.textContent = "SDRF Regional Response: Routine Logged";
}

async function loadNWPComparison(city) {
  try {
    const resp = await fetch(`${getBackendBase()}/api/weather/models?location=${encodeURIComponent(city)}`);
    if (resp.ok) {
      const data = await resp.json();
      document.getElementById('nwpConsensusText').textContent = data.consensus_summary;
    }
  } catch (e) {
    console.warn("NWP fetch error:", e);
  }
}

async function loadClimateTrends(city) {
  try {
    const resp = await fetch(`${getBackendBase()}/api/climate/history?location=${encodeURIComponent(city)}`);
    if (resp.ok) {
      const data = await resp.json();
      const barsContainer = document.getElementById('climateBars');
      barsContainer.innerHTML = '';

      const maxRain = Math.max(...data.annual_rainfall_mm, 1200);

      data.historical_years.forEach((yr, idx) => {
        const val = data.annual_rainfall_mm[idx];
        const pct = Math.round((val / maxRain) * 100);
        const col = document.createElement('div');
        col.className = 'climate-bar-col';
        col.innerHTML = `
          <span class="climate-bar-val">${val}mm</span>
          <div class="climate-bar-fill" style="height:${pct}%"></div>
          <span class="climate-bar-year">${yr}</span>
        `;
        barsContainer.appendChild(col);
      });

      document.getElementById('climateAnalysisText').textContent = data.summary_analysis;
    }
  } catch (e) {
    console.warn("Climate history error:", e);
  }
}

async function checkBackendHealth() {
  const statusEl = document.getElementById('apiStatus');
  try {
    const resp = await fetch(`${getBackendBase()}/health`);
    if (resp.ok) {
      statusEl.classList.add('online');
      statusEl.querySelector('.status-label').textContent = 'Online';
    } else {
      throw new Error();
    }
  } catch (e) {
    if (statusEl) {
      statusEl.classList.remove('online');
      statusEl.querySelector('.status-dot').style.background = '#f59e0b';
      statusEl.querySelector('.status-label').textContent = 'Connecting...';
    }
  }
}
