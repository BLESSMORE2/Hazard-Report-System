# Deploy HIRS (Hazard Report) online

Your app can be deployed to free-tier hosts in a few minutes. Push the project to **GitHub** first, then connect the repo to one of the options below.

---

## Option 1: Render (recommended, free tier)

1. Go to [render.com](https://render.com) and sign up (GitHub login).
2. **New** → **Web Service**.
3. Connect your GitHub repo (the one containing this project).
4. Use these settings:
   - **Name:** `hirs-hazard-report` (or any name)
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn dash_app:server --bind 0.0.0.0:$PORT`
   - **Instance type:** Free
5. Click **Create Web Service**. Render will build and deploy. When it’s done, you’ll get a URL like `https://hirs-hazard-report.onrender.com`.

**Or use the config file:** If your repo has `render.yaml` in the root, choose **Blueprint** when creating a new service and point it at the repo; Render will use the settings from `render.yaml`.

---

## Option 2: Railway

1. Go to [railway.app](https://railway.app) and sign up (GitHub).
2. **New Project** → **Deploy from GitHub repo** → select your repo.
3. Railway will detect Python. If it doesn’t:
   - **Settings** → set **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn dash_app:server --bind 0.0.0.0:$PORT`
4. Under **Settings** → **Networking** → **Generate Domain** to get a public URL.

---

## Option 3: Heroku

1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and run `heroku login`.
2. In your project folder:
   ```bash
   heroku create your-app-name
   git push heroku main
   ```
3. The `Procfile` in the repo tells Heroku to run:  
   `gunicorn dash_app:server --bind 0.0.0.0:$PORT`  
   Your app will be at `https://your-app-name.herokuapp.com`.

*(Heroku’s free tier was discontinued; a paid plan is required.)*

---

## Before you deploy

1. **Git:** Put the project under Git and push to GitHub (or GitLab):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
2. **Secrets:** The app currently has no API keys or DB. If you add them later, set them as **environment variables** in the host’s dashboard (e.g. Render → Service → Environment), not in code.
3. **Python:** The services use the Python version from their environment (e.g. 3.12). Your `requirements.txt` is used to install dependencies.

---

## After deployment

- The first request on Render’s free tier can be slow (cold start); later requests are faster.
- Login/logout and data are in-memory; restarting the service clears them. For persistent data you’d add a database later.
- To update the live app: push changes to your GitHub branch; Render/Railway will redeploy automatically if auto-deploy is on.
