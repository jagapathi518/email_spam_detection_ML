# Alternative Hosting Platforms

## Why Render?

SpamGuard AI uses **Render** as its hosting platform because:
1. It supports Docker-based deployment, which gives us full control over the runtime
2. It provides a free tier suitable for this project's requirements
3. It supports persistent web services (always-on, not serverless)
4. It provides health check monitoring
5. It supports Blueprint (Infrastructure as Code) for reproducible deployments

## Why NOT Vercel?

**Vercel** is optimized for frontend and serverless applications:
- **Serverless functions only:** Vercel runs backend code as serverless functions with a maximum execution time of 10 seconds (free tier). Our ML model loading takes longer than this.
- **No persistent process:** We need the model to stay loaded in memory between requests. Serverless functions cold-start on every invocation.
- **No Docker support on free tier:** Vercel's free tier does not support custom Docker runtimes.
- **Designed for Next.js/frontend:** While it can run Python, it's not optimized for Flask + gunicorn backends.

**Verified:** Vercel serverless function timeout is 10s on Hobby plan (source: vercel.com/docs/functions/runtimes, accessed October 2024).

## Why NOT Netlify?

**Netlify** has similar limitations to Vercel for this use case:
- **Serverless functions:** Netlify Functions have a 10-second timeout on the free tier.
- **No persistent backend:** Like Vercel, it's designed for static sites with API functions, not persistent Flask services.
- **No Docker support:** Netlify does not support custom Docker containers.
- **Cold starts for each function call:** The model would need to be loaded on every single request.

**Verified:** Netlify Functions timeout is 10s on free tier (source: docs.netlify.com/functions/overview, accessed October 2024).

## Summary

| Feature | Render (Free) | Vercel (Hobby) | Netlify (Free) |
|---------|--------------|----------------|----------------|
| Persistent process | ✅ Yes (spins down after 15 min idle) | ❌ No (serverless) | ❌ No (serverless) |
| Docker support | ✅ Yes | ❌ No (free) | ❌ No |
| Function timeout | N/A (persistent) | 10s | 10s |
| ML model in memory | ✅ Yes | ❌ Too slow to cold-start | ❌ Too slow to cold-start |
| RAM | 512 MB | 1024 MB (but per-function) | 1024 MB (but per-function) |
| Monthly hours | 750h | Unlimited | Unlimited |
| Custom domain | ✅ Free | ✅ Free | ✅ Free |
