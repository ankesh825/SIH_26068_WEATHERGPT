/**
 * WeatherGPT - Visualizer Engine & Atmospheric Canvas
 * High-performance, GPU-accelerated atmospheric particles, dynamic SVG spline curves & visual gauges
 */

class WeatherVisualizer {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.animId = null;
    this.particles = [];
    this.weatherType = 'clear'; // 'clear', 'rain', 'cloud', 'storm', 'snow'
    this.isNight = false;
  }

  init() {
    this.canvas = document.getElementById('atmosphereCanvas');
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());
      this.initParticles();
      this.startAnimation();
    }
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const parent = this.canvas.parentElement;
    if (parent) {
      this.canvas.width = parent.clientWidth;
      this.canvas.height = parent.clientHeight;
    }
  }

  setWeatherState(conditionText, rainProb, isDayTime = true) {
    this.isNight = !isDayTime;
    const lower = (conditionText || '').toLowerCase();

    if (lower.includes('thunder') || lower.includes('storm') || lower.includes('toofan')) {
      this.weatherType = 'storm';
    } else if (rainProb > 40 || lower.includes('rain') || lower.includes('drizzle') || lower.includes('shower') || lower.includes('baarish')) {
      this.weatherType = 'rain';
    } else if (lower.includes('snow') || lower.includes('barf')) {
      this.weatherType = 'snow';
    } else if (lower.includes('cloud') || lower.includes('overcast') || lower.includes('fog') || lower.includes('mist') || lower.includes('kohra')) {
      this.weatherType = 'cloud';
    } else {
      this.weatherType = 'clear';
    }

    this.initParticles();
  }

  initParticles() {
    this.particles = [];
    if (!this.canvas) return;
    const w = this.canvas.width || 400;
    const h = this.canvas.height || 220;

    const count = this.weatherType === 'rain' ? 80 : (this.weatherType === 'cloud' ? 25 : 35);

    for (let i = 0; i < count; i++) {
      if (this.weatherType === 'rain' || this.weatherType === 'storm') {
        this.particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          length: 12 + Math.random() * 14,
          speed: 6 + Math.random() * 8,
          opacity: 0.3 + Math.random() * 0.5,
          angle: 0.15 // slight slant
        });
      } else if (this.weatherType === 'cloud') {
        this.particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          radius: 35 + Math.random() * 45,
          speedX: 0.15 + Math.random() * 0.25,
          opacity: 0.08 + Math.random() * 0.12
        });
      } else if (this.weatherType === 'snow') {
        this.particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          radius: 1.5 + Math.random() * 2.5,
          speedY: 0.8 + Math.random() * 1.5,
          swing: Math.random() * Math.PI,
          opacity: 0.4 + Math.random() * 0.4
        });
      } else {
        // Clear / Sun Dust / Night Stars
        this.particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          radius: 1 + Math.random() * 2.5,
          speedY: -0.15 - Math.random() * 0.3,
          speedX: (Math.random() - 0.5) * 0.2,
          pulse: Math.random() * Math.PI,
          opacity: 0.2 + Math.random() * 0.5
        });
      }
    }
  }

  startAnimation() {
    if (this.animId) cancelAnimationFrame(this.animId);

    let flashTimer = 0;

    const loop = () => {
      if (!this.ctx || !this.canvas) return;
      const w = this.canvas.width;
      const h = this.canvas.height;
      this.ctx.clearRect(0, 0, w, h);

      // Thunderstorm random flash effect
      if (this.weatherType === 'storm') {
        flashTimer++;
        if (flashTimer > 180 && Math.random() < 0.03) {
          this.ctx.fillStyle = 'rgba(255, 255, 255, 0.18)';
          this.ctx.fillRect(0, 0, w, h);
          flashTimer = 0;
        }
      }

      // Draw Particles based on active weather type
      if (this.weatherType === 'rain' || this.weatherType === 'storm') {
        this.ctx.lineWidth = 1.2;
        this.particles.forEach(p => {
          this.ctx.strokeStyle = `rgba(56, 189, 248, ${p.opacity})`;
          this.ctx.beginPath();
          this.ctx.moveTo(p.x, p.y);
          this.ctx.lineTo(p.x + p.length * p.angle, p.y + p.length);
          this.ctx.stroke();

          p.y += p.speed;
          p.x += p.speed * p.angle;

          if (p.y > h) {
            p.y = -p.length;
            p.x = Math.random() * w;
          }
        });
      } else if (this.weatherType === 'cloud') {
        this.particles.forEach(p => {
          const grad = this.ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius);
          grad.addColorStop(0, `rgba(203, 213, 225, ${p.opacity})`);
          grad.addColorStop(1, 'rgba(203, 213, 225, 0)');
          this.ctx.fillStyle = grad;
          this.ctx.beginPath();
          this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          this.ctx.fill();

          p.x += p.speedX;
          if (p.x - p.radius > w) p.x = -p.radius;
        });
      } else {
        // Clear Day (Warm Sunlight Particles) or Night (Twinkling Stars)
        this.particles.forEach(p => {
          p.pulse += 0.03;
          const currentOpacity = p.opacity * (0.6 + 0.4 * Math.sin(p.pulse));
          this.ctx.fillStyle = this.isNight
            ? `rgba(186, 230, 253, ${currentOpacity})`
            : `rgba(251, 191, 36, ${currentOpacity})`;

          this.ctx.beginPath();
          this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          this.ctx.fill();

          p.y += p.speedY;
          p.x += p.speedX;

          if (p.y < 0) {
            p.y = h;
            p.x = Math.random() * w;
          }
        });
      }

      this.animId = requestAnimationFrame(loop);
    };

    loop();
  }

  // ===========================================================================
  // High-Resolution Smooth SVG Weather Spline Curve & Rain Columns
  // ===========================================================================
  renderHourlySpline(hourly) {
    const svg = document.getElementById('hourlySplineSvg');
    if (!svg || !hourly || hourly.length === 0) return;

    const data = hourly.slice(0, 10); // next 10 hours
    const width = 600;
    const height = 130;
    const paddingX = 35;
    const paddingY = 25;
    const chartW = width - paddingX * 2;
    const chartH = height - paddingY * 2;

    const temps = data.map(d => d.temperature);
    const minTemp = Math.min(...temps) - 1;
    const maxTemp = Math.max(...temps) + 1;
    const tempRange = maxTemp - minTemp || 1;

    // Calculate (x, y) coordinates for spline
    const points = data.map((d, i) => {
      const x = paddingX + (i / (data.length - 1)) * chartW;
      const y = paddingY + chartH - ((d.temperature - minTemp) / tempRange) * chartH;
      return { x, y, temp: Math.round(d.temperature), rain: d.precipitation_probability, time: d.time };
    });

    // Build smooth cubic Bezier path
    let pathD = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cpX = (p0.x + p1.x) / 2;
      pathD += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
    }

    // Build gradient area fill path
    const areaD = `${pathD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;

    // Rain probability bars
    let rainBarsSVG = '';
    points.forEach(p => {
      const barH = (p.rain / 100) * 36;
      const barY = height - barH;
      const barColor = p.rain > 50 ? '#38bdf8' : (p.rain > 20 ? 'rgba(56, 189, 248, 0.45)' : 'rgba(148, 163, 184, 0.15)');
      rainBarsSVG += `
        <rect x="${p.x - 7}" y="${barY}" width="14" height="${barH}" rx="3" fill="${barColor}" />
        <text x="${p.x}" y="${height - 2}" text-anchor="middle" font-size="8.5" fill="#94a3b8" font-weight="600">${p.rain > 15 ? p.rain + '%' : ''}</text>
      `;
    });

    // Temperature labels & glowing circles
    let nodesSVG = '';
    points.forEach(p => {
      nodesSVG += `
        <circle cx="${p.x}" cy="${p.y}" r="4" fill="#fbbf24" stroke="#0f172a" stroke-width="2" filter="drop-shadow(0 0 6px rgba(251, 191, 36, 0.8))" />
        <text x="${p.x}" y="${p.y - 8}" text-anchor="middle" font-size="10.5" fill="#f8fafc" font-weight="700">${p.temp}°</text>
        <text x="${p.x}" y="${p.y + 14}" text-anchor="middle" font-size="8" fill="#94a3b8">${p.time}</text>
      `;
    });

    svg.innerHTML = `
      <defs>
        <linearGradient id="splineAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.28" />
          <stop offset="60%" stop-color="#f59e0b" stop-opacity="0.08" />
          <stop offset="100%" stop-color="#0f172a" stop-opacity="0" />
        </linearGradient>
        <linearGradient id="splineStrokeGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#fbbf24" />
          <stop offset="50%" stop-color="#38bdf8" />
          <stop offset="100%" stop-color="#818cf8" />
        </linearGradient>
      </defs>
      <!-- Rain Bars in background -->
      ${rainBarsSVG}
      <!-- Gradient Fill Area -->
      <path d="${areaD}" fill="url(#splineAreaGrad)" />
      <!-- Glowing Curve Line -->
      <path d="${pathD}" fill="none" stroke="url(#splineStrokeGrad)" stroke-width="2.5" stroke-linecap="round" />
      <!-- Data Nodes & Values -->
      ${nodesSVG}
    `;
  }

  // ===========================================================================
  // Circular Gauges for Quick Metrics (Wind, Humidity, UV, AQI)
  // ===========================================================================
  updateGauges(weather) {
    // 1. Humidity (0 to 100%)
    const humEl = document.getElementById('gaugeHumidityCircle');
    if (humEl) {
      const humVal = Math.min(100, Math.max(0, weather.humidity));
      humEl.setAttribute('stroke-dasharray', `${humVal}, 100`);
    }

    // 2. Wind (0 to 60 km/h scale)
    const windEl = document.getElementById('gaugeWindCircle');
    if (windEl) {
      const windVal = Math.min(100, Math.round((weather.wind_speed / 50) * 100));
      windEl.setAttribute('stroke-dasharray', `${windVal}, 100`);
    }

    // 3. UV Index (0 to 12 scale)
    const uvEl = document.getElementById('gaugeUVCircle');
    if (uvEl) {
      const uvVal = Math.min(100, Math.round((weather.uv_index / 11) * 100));
      uvEl.setAttribute('stroke-dasharray', `${uvVal}, 100`);
    }

    // 4. AQI (0 to 200 scale)
    const aqiEl = document.getElementById('gaugeAQICircle');
    if (aqiEl) {
      const aqi = weather.air_quality_index || 45;
      const aqiVal = Math.min(100, Math.round((aqi / 180) * 100));
      aqiEl.setAttribute('stroke-dasharray', `${aqiVal}, 100`);
    }
  }

  // ===========================================================================
  // 7-Day Visual Temperature Gradient Sliders
  // ===========================================================================
  renderDailySliders(daily) {
    const container = document.getElementById('dailyList');
    if (!container || !daily || daily.length === 0) return;

    const allMin = Math.min(...daily.map(d => d.min_temp));
    const allMax = Math.max(...daily.map(d => d.max_temp));
    const overallRange = allMax - allMin || 1;

    container.innerHTML = '';
    daily.forEach((d, idx) => {
      const minLeft = ((d.min_temp - allMin) / overallRange) * 100;
      const barWidth = Math.max(12, ((d.max_temp - d.min_temp) / overallRange) * 100);

      const row = document.createElement('div');
      row.className = 'daily-row-visual';
      row.innerHTML = `
        <span class="daily-day-label">${idx === 0 ? 'Today' : d.date}</span>
        <span class="daily-cond-icon" title="${d.condition}">${d.condition.split(' ')[0] || '🌤️'}</span>
        <span class="daily-temp-low">${Math.round(d.min_temp)}°</span>
        <div class="daily-slider-track">
          <div class="daily-slider-fill" style="left: ${minLeft}%; width: ${barWidth}%;"></div>
        </div>
        <span class="daily-temp-high">${Math.round(d.max_temp)}°</span>
        <span class="daily-rain-pill ${d.precipitation_probability > 30 ? 'has-rain' : ''}">${d.precipitation_probability}% 💧</span>
      `;
      container.appendChild(row);
    });
  }
}

window.weatherVisualizer = new WeatherVisualizer();
