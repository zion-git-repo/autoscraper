# Deployment Guide for HotDoc Scraper

## ⚠️ Important Note
This app uses **Selenium with Chrome**, which is **NOT supported on most free hosting platforms**.

## Recommended Free Options

### Option 1: Render (Partially Supported)
**Status:** May work but Chrome/Selenium support is limited on free tier

**Steps:**
1. Create a GitHub repository and push your code
2. Sign up at [render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Render will detect the `render.yaml` configuration automatically
6. Click "Create Web Service"

**Limitations:**
- App sleeps after 15 minutes of inactivity
- Takes ~30 seconds to wake up
- Chrome may not work reliably (free tier limitations)

---

### Option 2: Railway (Better Selenium Support)
**Status:** Best free option for Selenium apps
**Free Tier:** $5 credit/month (~500 hours)

**Steps:**
```bash
# 1. Create a GitHub repo and push code
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main

# 2. Deploy to Railway
# Go to https://railway.app
# Sign up with GitHub
# Click "New Project" → "Deploy from GitHub repo"
# Select your repository
# Railway auto-detects and deploys
```

**Add buildpack for Chrome:**
In Railway dashboard:
- Go to Settings → "Add Buildpack"
- Add: `https://github.com/heroku/heroku-buildpack-google-chrome`

---

### Option 3: Run Locally (Recommended for Development)
**Status:** Best option if you have a spare computer/server

```bash
# Install dependencies
pip install -r requirements-deploy.txt

# Run the app
python app.py
```

Keep your computer running and use a service like **ngrok** for public access:
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5005
```

---

### Option 4: PythonAnywhere (No Selenium Support)
**Status:** ❌ Does NOT support Selenium
PythonAnywhere blocks Selenium on free tier - **not recommended** for this project.

---

## Files Needed for Deployment

- `requirements-deploy.txt` - Minimal dependencies (✅ created)
- `render.yaml` - Render configuration (✅ created)
- `scraper_config.py` - Chrome configuration for cloud (✅ created)
- `.gitignore` - Exclude unnecessary files (✅ created)

---

## Alternative: Remove Selenium (Use requests only)

If you want better free hosting support, consider modifying the scraper to use only `requests` + `BeautifulSoup` without Selenium. This will:
- ✅ Work on ALL free hosting platforms
- ✅ Be faster and use less resources
- ❌ May not work with JavaScript-heavy pages

---

## Recommended Approach

**For Free Hosting:**
1. Try **Railway** first (best Selenium support)
2. If Railway credits run out, try **Render**

**For Reliable Long-term:**
1. Use **ngrok** with local machine ($0)
2. Or upgrade to paid hosting ($5-10/month):
   - Render Paid Plan
   - DigitalOcean App Platform
   - Heroku (no free tier anymore)

---

## Testing Deployment

After deploying, test by:
1. Open the deployed URL
2. Try scraping 1-2 clinics (use range 1-2)
3. Check if Chrome initializes correctly in logs
4. If Chrome fails, Selenium is not supported on that platform
