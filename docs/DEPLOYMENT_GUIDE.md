# WeatherGPT (SIH26068) Deployment Guide

This guide provides step-by-step instructions and all required configuration settings to deploy **WeatherGPT** on cloud platforms.

---

## 📋 Required Files & Names

The following files are already configured and ready in your project repository:

| File Name | Location | Purpose |
| :--- | :--- | :--- |
| `Dockerfile` | Project Root | Production container packaging both backend & frontend |
| `render.yaml` | Project Root | 1-Click Infrastructure Blueprint for Render.com |
| `Procfile` | Project Root | Start command definition for Railway & Heroku |
| `docker-compose.yml` | Project Root | Single-command local / server container orchestration |
| `backend/requirements.txt` | `backend/` | List of Python dependencies (FastAPI, Uvicorn, Pydantic, HTTPX, Google GenAI) |
| `.gitignore` | Project Root | Prevents `.env`, `.venv`, and temporary files from being leaked to Git |

---

## ⚙️ Important Environment Variables (Env Vars)

When deploying to any cloud provider, configure these Environment Variables:

| Variable Name | Required? | Recommended Value | Description |
| :--- | :---: | :--- | :--- |
| `PORT` | Auto | `8000` (Render/Railway sets this automatically) | Internal web server port |
| `HOST` | Yes | `0.0.0.0` | Bind address for accepting cloud incoming traffic |
| `ALLOWED_ORIGINS` | Yes | `*` | CORS origins allowed to call the API |
| `DEBUG` | No | `False` | Production debug mode toggle |
| `GEMINI_API_KEY` | Optional | `AIzaSy...` (from Google AI Studio) | If omitted, built-in dynamic NLU engine runs |
| `GEMINI_MODEL` | No | `gemini-1.5-flash` | Gemini model identifier |
| `CACHE_TTL_SECONDS` | No | `900` | Meteorological caching TTL (15 minutes) |

---

## 🚀 Deployment Methods

### Method 1: Render.com (Recommended Free Cloud Hosting)

Render provides free hosting for web services and connects directly to GitHub.

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "WeatherGPT production ready"
   git remote add origin https://github.com/YOUR_USERNAME/weathergpt.git
   git branch -M main
   git push -u origin main
   ```

2. **Login to Render**:
   - Go to [render.com](https://render.com) and sign in with GitHub.
   - Click **New +** -> **Web Service**.
   - Connect your `weathergpt` repository.

3. **Fill Configuration**:
   - **Name**: `weathergpt-ai` (or your choice)
   - **Language / Runtime**: `Python 3`
   - **Region**: `Singapore` (Fastest for India)
   - **Branch**: `main`
   - **Build Command**:
     ```bash
     pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: `Free`

4. **Add Environment Variables**:
   Under the **Environment Variables** section, add:
   - `ALLOWED_ORIGINS` = `*`
   - `GEMINI_API_KEY` = `your_gemini_api_key_here` (Optional)

5. Click **Create Web Service**.
   - Render will build and deploy your app.
   - Once completed, you will receive a public URL: `https://weathergpt-ai.onrender.com`.
   - Visiting this URL will directly open the WeatherGPT interface with live APIs!

---

### Method 2: Railway.app (Zero-Config 1-Click)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically detect the `Procfile` or `Dockerfile`.
5. Under **Variables**, add:
   - `ALLOWED_ORIGINS` = `*`
   - `GEMINI_API_KEY` = (Optional)
6. Under **Settings**, click **Generate Domain**.
7. Your app is live!

---

### Method 3: Docker / Self-Hosted VPS / AWS EC2

If you have a Linux server or Docker installed:

1. **Run with Docker Compose**:
   ```bash
   docker compose up -d --build
   ```
2. **Access locally or on public IP**:
   - Open `http://your-server-ip:8000`
   - API Docs at `http://your-server-ip:8000/docs`

---

### Method 4: Split Hosting (Backend on Render + Frontend on Vercel)

If you prefer hosting the frontend on Vercel and backend on Render:

1. Deploy the backend on Render as a Web Service.
2. Note your backend URL, for example: `https://weathergpt-api.onrender.com`.
3. In `frontend/js/app.js` and `frontend/js/chat.js`:
   Set `window.BACKEND_API_URL = "https://weathergpt-api.onrender.com";`
4. Deploy the `frontend/` folder to Vercel or Netlify via GitHub or the Vercel CLI (`vercel --prod`).
