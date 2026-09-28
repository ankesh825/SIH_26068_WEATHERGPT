/**
 * WeatherGPT - Interactive Doppler Radar & Pan-India Climate Map Module
 * (Leaflet + RainViewer Real-time Radar API)
 */

const PAN_INDIA_CITIES = [
  { name: "New Delhi", lat: 28.6139, lon: 77.2090, state: "Delhi" },
  { name: "Mumbai", lat: 19.0760, lon: 72.8777, state: "Maharashtra" },
  { name: "Bengaluru", lat: 12.9716, lon: 77.5946, state: "Karnataka" },
  { name: "Kolkata", lat: 22.5726, lon: 88.3639, state: "West Bengal" },
  { name: "Chennai", lat: 13.0827, lon: 80.2707, state: "Tamil Nadu" },
  { name: "Indore", lat: 22.7196, lon: 75.8577, state: "Madhya Pradesh" },
  { name: "Bhopal", lat: 23.2599, lon: 77.4126, state: "Madhya Pradesh" },
  { name: "Jaipur", lat: 26.9124, lon: 75.7873, state: "Rajasthan" },
  { name: "Hyderabad", lat: 17.3850, lon: 78.4867, state: "Telangana" },
  { name: "Ahmedabad", lat: 23.0225, lon: 72.5714, state: "Gujarat" },
  { name: "Shimla", lat: 31.1048, lon: 77.1734, state: "Himachal Pradesh" },
  { name: "Srinagar", lat: 34.0837, lon: 74.7973, state: "Jammu & Kashmir" },
  { name: "Guwahati", lat: 26.1445, lon: 91.7362, state: "Assam" },
  { name: "Kochi", lat: 9.9312, lon: 76.2673, state: "Kerala" },
  { name: "Patna", lat: 25.5941, lon: 85.1376, state: "Bihar" },
  { name: "Lucknow", lat: 26.8467, lon: 80.9462, state: "Uttar Pradesh" }
];

class RadarViewer {
  constructor(containerId) {
    this.containerId = containerId;
    this.map = null;
    this.radarLayer = null;
    this.currentLat = 22.7196; // Indore default
    this.currentLon = 75.8577;
    this.currentCityName = "Indore";
    this.activeCityMarker = null;
    this.indiaMarkers = [];
    this.isPanIndiaMode = true;
  }

  init(lat, lon) {
    if (this.map) return;

    this.currentLat = lat || this.currentLat;
    this.currentLon = lon || this.currentLon;

    const el = document.getElementById(this.containerId);
    if (!el) return;

    // Create Leaflet Map centered on India
    this.map = L.map(this.containerId, {
      center: [22.8, 79.5],
      zoom: 5,
      zoomControl: true
    });

    // Dark Basemap tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB & OpenStreetMap &bull; IMD/MoES Doppler Stream',
      maxZoom: 18
    }).addTo(this.map);

    // Add Pan-India regional city markers
    this.plotPanIndiaMarkers();

    // Active city marker
    this.activeCityMarker = L.marker([this.currentLat, this.currentLon]).addTo(this.map);
    this.activeCityMarker.bindPopup(`<b>${this.currentCityName}</b> (Active Location)`).openPopup();

    // Fetch live RainViewer radar timestamps
    this.loadRainViewerTiles();
  }

  plotPanIndiaMarkers() {
    PAN_INDIA_CITIES.forEach(city => {
      const circle = L.circleMarker([city.lat, city.lon], {
        radius: 6,
        fillColor: '#38bdf8',
        color: '#ffffff',
        weight: 1.5,
        opacity: 0.9,
        fillOpacity: 0.8
      }).addTo(this.map);

      circle.bindTooltip(`<b>${city.name}</b> (${city.state})`, { direction: 'top', offset: [0, -5] });
      circle.on('click', () => {
        if (window.selectCityByName) {
          window.selectCityByName(city.name);
        }
      });
      this.indiaMarkers.push(circle);
    });
  }

  setPanIndiaView() {
    this.isPanIndiaMode = true;
    if (this.map) {
      this.map.setView([22.8, 79.5], 5);
      this.map.invalidateSize();
    }
  }

  setCityFocusView(lat, lon, cityName) {
    this.isPanIndiaMode = false;
    this.currentLat = lat || this.currentLat;
    this.currentLon = lon || this.currentLon;
    this.currentCityName = cityName || this.currentCityName;

    if (this.map) {
      this.map.setView([this.currentLat, this.currentLon], 7);
      if (this.activeCityMarker) {
        this.activeCityMarker.setLatLng([this.currentLat, this.currentLon]);
        this.activeCityMarker.bindPopup(`<b>${this.currentCityName}</b>`).openPopup();
      }
      this.map.invalidateSize();
    }
  }

  updateLocation(lat, lon, cityName) {
    this.currentLat = lat;
    this.currentLon = lon;
    this.currentCityName = cityName;
    if (this.map) {
      if (this.activeCityMarker) {
        this.activeCityMarker.setLatLng([lat, lon]);
        this.activeCityMarker.bindPopup(`<b>${cityName}</b>`).openPopup();
      }
      if (!this.isPanIndiaMode) {
        this.map.setView([lat, lon], 7);
      }
      this.map.invalidateSize();
    }
  }

  async loadRainViewerTiles() {
    try {
      const resp = await fetch('https://api.rainviewer.com/public/weather-maps.json');
      if (resp.ok) {
        const data = await resp.json();
        const radarFrames = data.radar?.past;
        if (radarFrames && radarFrames.length > 0) {
          const latest = radarFrames[radarFrames.length - 1];
          const tilePath = latest.path;

          if (this.radarLayer) {
            this.map.removeLayer(this.radarLayer);
          }

          // Add live radar overlay
          this.radarLayer = L.tileLayer(`https://tilecache.rainviewer.com${tilePath}/256/{z}/{x}/{y}/2/1_1.png`, {
            opacity: 0.65,
            zIndex: 100
          }).addTo(this.map);

          const timeEl = document.getElementById('radarTimestamp');
          if (timeEl) {
            const dt = new Date(latest.time * 1000);
            timeEl.textContent = `Live Pan-India Radar Scan: ${dt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
          }
        }
      }
    } catch (e) {
      console.warn("RainViewer radar live tile fetch note:", e);
    }
  }

  resize() {
    if (this.map) {
      setTimeout(() => {
        this.map.invalidateSize();
      }, 100);
    }
  }
}

window.radarViewer = new RadarViewer('radarMap');
