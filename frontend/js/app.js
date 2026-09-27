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
  return 'https://weathergpt-sih-2026-1.onrender.com';
}

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  setupEventListeners();
  window.chatController.init(updateWeatherDashboard);

  // Initialize Radar Map
  window.radarViewer.init(22.7196, 75.8577);

  // Initial Weather Load for default city (Indore)
  await loadCityWeather(window.currentCity);

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

  // Persona Chips
  const personaChips = document.querySelectorAll('.persona-chip');
  personaChips.forEach(chip => {
    chip.addEventListener('click', () => {
      personaChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      window.currentPersona = chip.dataset.persona;
      switchPersonaDashboard(window.currentPersona);
      updateContextualSuggestions(window.currentPersona);
    });
  });

  // Language Buttons
  const langBtns = document.querySelectorAll('.lang-btn');
  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      langBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      window.currentLanguage = btn.dataset.lang;
      window.voiceEngine.setLanguage(window.currentLanguage);
    });
  });

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
    console.warn("Backend starting or unreachable, falling back to direct Open-Meteo:", e);
  }

  // Client-Side Direct Fallback
  try {
    const coords = {
      indore: { lat: 22.7196, lon: 75.8577, name: "Indore" },
      bhopal: { lat: 23.2599, lon: 77.4126, name: "Bhopal" },
      delhi: { lat: 28.6139, lon: 77.2090, name: "Delhi" },
      mumbai: { lat: 19.0760, lon: 72.8777, name: "Mumbai" },
      jaipur: { lat: 26.9124, lon: 75.7873, name: "Jaipur" }
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
      if (yatriAct) yatriAct.textContent = "Bypass highways par visibility kam rahegi; sham 4 baje se 8 baje ke beech driving se bachein.";
      if (nagrikAct) nagrikAct.textContent = "Low-lying underpass me paani bhar sakta hai; umbrella aur power bank ready rakhein.";
    } else {
      if (kisanAct) kisanAct.textContent = "Mausam saaf hai; nindai-gudai aur keetnashak spray subah ke samay kar sakte hain.";
      if (yatriAct) yatriAct.textContent = "Highway corridor conditions clear aur safe hain; travel schedule on time rahega.";
      if (nagrikAct) nagrikAct.textContent = "Dopahar me direct dhoop se bachein aur hydration banaye rakhein.";
    }

    const tickerText = document.getElementById('tickerText');
    if (tickerText) {
      tickerText.textContent = `${weather.location}: ${weather.severe_warning.headline} - ${weather.severe_warning.description}`;
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

  // Dynamic Persona Metrics
  updatePersonaMetrics(weather);
  switchPersonaDashboard(window.currentPersona || 'citizen');

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

  // 7-Day Outlook
  const dailyContainer = document.getElementById('dailyList');
  if (dailyContainer && weather.daily) {
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
}

function switchPersonaDashboard(persona) {
  const generalDash = document.getElementById('generalDashboard');
  const kisanDash = document.getElementById('kisanDashboard');
  const yatriDash = document.getElementById('yatriDashboard');
  const disasterDash = document.getElementById('disasterDashboard');

  if (generalDash) generalDash.style.display = 'none';
  if (kisanDash) kisanDash.style.display = 'none';
  if (yatriDash) yatriDash.style.display = 'none';
  if (disasterDash) disasterDash.style.display = 'none';

  if (persona === 'farmer' && kisanDash) {
    kisanDash.style.display = 'block';
  } else if (persona === 'traveler' && yatriDash) {
    yatriDash.style.display = 'block';
  } else if (persona === 'disaster_officer' && disasterDash) {
    disasterDash.style.display = 'block';
  } else if (generalDash) {
    generalDash.style.display = 'block';
  }
}

function updatePersonaMetrics(weather) {
  const isRain = weather.precipitation_probability > 40;
  const isWindy = weather.wind_speed > 20;

  // Kisan
  const soil = document.getElementById('kisanSoilMoisture');
  const spray = document.getElementById('kisanSprayWindow');
  const irrig = document.getElementById('kisanIrrigation');
  const pest = document.getElementById('kisanPestRisk');

  if (soil) soil.textContent = `${Math.min(95, Math.max(35, weather.humidity + 5))}% (${isRain ? 'Adequate' : 'Dry'})`;
  if (spray) {
    if (isWindy || isRain) {
      spray.textContent = "Unfavorable (Wind/Rain Drift)";
      spray.className = "k-val warn";
    } else {
      spray.textContent = "Favorable (Morning 7-10 AM)";
      spray.className = "k-val safe";
    }
  }
  if (irrig) {
    irrig.textContent = isRain ? "Postpone Irrigation (Rain Expected)" : "Normal Irrigation Needed";
    irrig.className = isRain ? "k-val info" : "k-val safe";
  }
  if (pest) {
    pest.textContent = weather.humidity > 65 ? "High (Fungal Blight Watch)" : "Low";
    pest.className = weather.humidity > 65 ? "k-val warn" : "k-val safe";
  }

  // Yatri
  const safety = document.getElementById('yatriSafetyScore');
  const vis = document.getElementById('yatriVisibility');
  const crosswind = document.getElementById('yatriCrosswind');
  if (safety) safety.textContent = isRain ? "6.8 / 10 (Wet Roads)" : "8.9 / 10 (Optimal)";
  if (vis) vis.textContent = isRain ? "3 - 5 km (Scattered Rain)" : "> 8 km (Clear)";
  if (crosswind) crosswind.textContent = `${weather.wind_speed} km/h (${isWindy ? 'Caution on flyovers' : 'Gentle'})`;

  // Disaster Officer
  const dLevel = document.getElementById('disasterLevel');
  if (dLevel) dLevel.textContent = weather.severe_warning ? weather.severe_warning.headline : "Level-1 (Green / Normal)";

  const goOut = document.getElementById('generalGoOut');
  const comfort = document.getElementById('generalComfort');
  const risk = document.getElementById('generalRisk');
  if (goOut) {
    goOut.textContent = isRain ? "Umbrella le ke niklo" : "Outdoor OK";
    goOut.className = isRain ? "k-val warn" : "k-val safe";
  }
  if (comfort) {
    comfort.textContent = `${Math.round(weather.temperature)}°C • ${weather.humidity}% humid`;
  }
  if (risk) {
    risk.textContent = weather.severe_warning && weather.severe_warning.severity !== 'normal'
      ? weather.severe_warning.headline
      : "Normal / Green";
    risk.className = weather.severe_warning && weather.severe_warning.severity !== 'normal' ? "k-val warn" : "k-val safe";
  }
}

function updateContextualSuggestions(persona) {
  const container = document.getElementById('suggestionChips');
  if (!container) return;

  const city = window.currentCity || 'Indore';
  let prompts = [];

  if (persona === 'farmer') {
    prompts = [
      `🌾 ${city} me aaj keetnashak spray safe hai?`,
      `💧 Sinchai kab tak postpone karni chahiye?`,
      `🌱 Kharif fasal ke liye 7-din barish forecast`,
      `🐛 Nami se fungal disease risk kya hai?`
    ];
  } else if (persona === 'traveler') {
    prompts = [
      `🚗 ${city} se highway travel safe hai?`,
      `🌫️ Bypass corridor par fog aur visibility?`,
      `💨 Two-wheeler ke liye crosswind hazard?`,
      `🛣️ Underpass waterlogging alert check karo`
    ];
  } else if (persona === 'disaster_officer') {
    prompts = [
      `🚨 Active districts aur alert severity check karo`,
      `👥 Catchment area population at risk report`,
      `📢 2G SMS aur IVR broadcast status trigger`,
      `🏢 SDRF shelter readiness report`
    ];
  } else {
    prompts = [
      `Hi WeatherGPT, aaj ${city} ka mausam batao`,
      `🌧️ Kal ${city} mein baarish hogi kya?`,
      `☀️ Dopahar me UV Index aur heatwave alert?`,
      `📅 ${city} 7-Day weather forecast`
    ];
  }

  container.innerHTML = '';
  prompts.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'sug-chip';
    btn.textContent = p;
    btn.addEventListener('click', () => {
      window.chatController.sendMessage(p);
    });
    container.appendChild(btn);
  });
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
