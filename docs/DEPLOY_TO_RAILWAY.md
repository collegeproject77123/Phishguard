# Deploy PhishGuard ML Backend to Railway (Step-by-Step)

Railway is **free** ($5/month credit), **easy**, and **fast** to deploy. Follow these steps.

---

## Step 1: Go to Railway.app

1. Open https://railway.app in your browser
2. Click **"Start a New Project"** (or "Create")
3. You'll see options. Click **"Deploy from GitHub repo"**

---

## Step 2: Connect Your GitHub Account

1. Click **"GitHub"** (sign in if needed)
2. GitHub will ask permission - click **"Authorize railway-app"**
3. You'll be redirected back to Railway

---

## Step 3: Select Your Repository

1. You should see a list of your GitHub repos
2. **Find and click** `G-man312/Phishguard-` (the one we just pushed)
3. Click **"Deploy now"**

---

## Step 4: Configure the Deployment

Railway will show you a deploy form. You need to:

### 4.1 Set the Service Name (optional but helpful)
- Change from default to: `phishguard-ml`
- This helps you identify the service later

### 4.2 Set the Root Directory
- Click **"Root Directory"** dropdown
- Change to: `ml-backend`
- **(This is important!)** This tells Railway where the Dockerfile is

### 4.3 Click "Deploy"
- Railway will start building (takes 1-3 minutes)
- You'll see a log showing the build progress

---

## Step 5: Wait for Deployment

You'll see:
```
Building...
Running Dockerfile...
Installing dependencies...
✓ Deployment complete
```

Once done, Railway shows your app's details on the right side panel.

---

## Step 6: Get Your Deployment URL

In the **right panel**, look for:
- **"Domains"** section
- You should see a URL like: `https://phishguard-ml-production-xxxx.railway.app`

**Copy and save this URL!** (You'll use it in 5 minutes)

---

## Step 7: Test the Backend

1. Open your browser
2. Go to: `https://YOUR_RAILWAY_URL/health`
   - Replace `YOUR_RAILWAY_URL` with your actual URL from Step 6
   - Example: `https://phishguard-ml-production-xxxx.railway.app/health`

3. You should see JSON:
   ```json
   {
     "status": "healthy",
     "model_loaded": true
   }
   ```

**If you see this ✅** → Your backend is live and working!

**If you see an error ❌** → Check the Railway logs for errors

---

## Troubleshooting

### I don't see a URL in Railway
- Click on your deployment/service name in the left sidebar
- Look for "Domains" section on the right panel
- It might take 2-3 minutes to generate

### `/health` returns an error
- Check Railway logs (there's a "Logs" tab)
- Look for the error message
- Most common: Model file missing (but it should be there since we pushed it to GitHub)

### Build failed
- Check the build logs in Railway
- Make sure `ml-backend/Dockerfile` exists and is correct
- Redeploy by clicking the "Redeploy" button

---

## Next Steps

Once you see the "healthy" response ✅:

1. **Copy your Railway URL**
2. Go back to VS Code
3. I'll update `background.js` and `popup.js` to use this URL
4. Test the extension in Chrome
5. Ready to publish!

---

## Notes

- **You're on the free tier** ($5/month credit)
- No credit card charged (you won't exceed $5 with light testing)
- Your app will always be running (no cold starts like Render)
- HTTPS is automatic (Railway handles it)

