# Deployment Guide — SpamGuard AI

## Prerequisites

- A GitHub account (free)
- A Render account (free — no credit card required for the free tier)
- The SpamGuard AI repository with trained model artifacts in `models/v1/`

## Step-by-Step Deployment

### 1. Create a GitHub Repository

1. Go to https://github.com and sign in (or create a free account)
2. Click the **"+"** button → **"New repository"**
3. Name it `spamguard-ai` (or any name you prefer)
4. Set it to **Public** (required for Render free tier)
5. **Do not** initialize with README (we already have one)
6. Click **"Create repository"**

### 2. Push Your Code to GitHub

Open PowerShell in your project directory and run:

```powershell
git init
git add .
git commit -m "Initial commit: SpamGuard AI"
git branch -M main
git remote add origin https://github.com/jagapathi518/email_spam_detection_ML.git
git push -u origin main
```

### 3. Create a Render Account

1. Go to https://render.com and click **"Get Started for Free"**
2. Sign up with your GitHub account (recommended for easy repo access)
3. No credit card is required for the free tier

### 4. Deploy via Blueprint

1. In Render, go to **Dashboard** → **Blueprints**
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repository
4. Render will detect the `render.yaml` file and configure the service automatically
5. Click **"Apply"**

**Alternative: Manual Docker Service**
1. In Render, go to **Dashboard** → **New** → **Web Service**
2. Connect your GitHub repo
3. Set **Environment** to **Docker**
4. Set **Plan** to **Free**
5. Add environment variables:
   - `FLASK_ENV` = `production`
   - `PORT` = `10000`
   - `MODEL_VERSION` = `v1`
6. Set **Health Check Path** to `/api/health`
7. Click **"Create Web Service"**

### 5. Verify Deployment

1. Wait for the build to complete (may take 5–10 minutes)
2. Click the service URL (e.g., `https://spamguard-ai.onrender.com`)
3. Run the smoke test:
```powershell
python scripts/smoke_test.py https://spamguard-ai.onrender.com
```

### 6. Reading Logs

In Render Dashboard → your service → **Logs** tab:
- Look for `Model loaded and warmed up successfully` at startup
- Application logs show: timestamp, route, status code, latency, request ID
- **No email content should appear in logs** (verified by tests)

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Build fails | Missing dependencies | Check `requirements.txt` is complete |
| Health check fails | Port mismatch | Ensure `PORT` env var matches Render config (default: 10000) |
| Out-of-memory kill | Model too large | Check Docker memory usage, reduce model size |
| Build timeout | Large Docker image | Optimize Dockerfile layers, use `.dockerignore` |
| Cold start takes > 2 min | Normal for free tier | Inform users via UI; consider keep-alive pinger |
| 503 errors | Model not loaded | Check logs for model loading errors |

## Free-Tier Notes

- **Spin-down:** After 15 minutes of no traffic, the service sleeps. First request after sleep takes ~1 minute.
- **Monthly hours:** 750 instance-hours per workspace per month. One always-running service uses ~720 hours/month, leaving little margin.
- **Ephemeral disk:** All local files are lost on restart/sleep. Model must be baked into the Docker image.
- **No persistent storage:** No database or file storage included.

## Optional: Keep-Alive Pinger

An external uptime monitoring service (e.g., UptimeRobot) can ping your service every 14 minutes to prevent spin-down. **Trade-offs:**
- ✅ Eliminates cold starts for users
- ⚠️ Uses more of your 750 monthly hours (a constantly-awake service uses ~720h/month)
- ⚠️ Render's terms discourage using pingers specifically to avoid spin-down on the free tier

**This is left as your choice, not enabled by default.**

## Custom Domain (Free Tier)

Render's free tier supports custom domains with automatic HTTPS (Let's Encrypt):
1. Go to your service → **Settings** → **Custom Domains**
2. Add your domain
3. Update your DNS with the provided CNAME record
4. HTTPS is provisioned automatically
