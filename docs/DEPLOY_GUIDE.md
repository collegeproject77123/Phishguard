# PhishGuard Deployment Guide for Fly.io (Complete Walkthrough)

This guide walks you through deploying your PhishGuard ML backend to Fly.io **step by step**. Follow each section carefully.

---

## Prerequisites
- You have a Fly.io account and logged into the web UI
- You created an empty GitHub repo and connected it to Fly
- You have Git installed on your computer
- You're in the project folder (`E:\(Group 11A) phish-guard\phish-guard`)

---

## Step 1: Push Your Code to GitHub

### 1.1 Open PowerShell

Press `Win + X` and select **Windows PowerShell** (or open Terminal in VS Code).

### 1.2 Navigate to your project folder

```powershell
cd "E:\(Group 11A) phish-guard\phish-guard"
```

Verify you're in the right place by checking if you see the `ml-backend` folder:

```powershell
ls ml-backend
```

You should see: `app.py`, `requirements.txt`, `Dockerfile`, etc.

### 1.3 Configure Git (first time only)

If you haven't used Git before, run:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 1.4 Initialize Git repo (if not already done)

```powershell
git init
```

### 1.5 Add all files to Git

```powershell
git add .
```

### 1.6 Create initial commit

```powershell
git commit -m "Initial commit: PhishGuard Chrome extension + ML backend"
```

Expected output: should show files being committed (something like "create mode 100644 manifest.json", etc.)

### 1.7 Add GitHub repo as remote

Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual GitHub username and repo name:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
```

Example:
```powershell
git remote add origin https://github.com/G-man312/phishguard.git
```

### 1.8 Push to GitHub

```powershell
git branch -M main
git push -u origin main
```

**What to expect:**
- PowerShell may prompt you to login to GitHub (a browser window will open)
- You'll see `Enumerating objects...`, `Compressing objects...`, then `done.`
- After ~30 seconds, you should see confirmation

**Verify it worked:**
- Go to your GitHub repo URL (e.g., `https://github.com/G-man312/phishguard`) in your browser
- You should see all your files (manifest.json, ml-backend folder, etc.)

---

## Step 2: Configure Fly.io to Deploy from GitHub

### 2.1 Go to Fly.io Dashboard

1. Open https://fly.io in your browser
2. Log in if needed
3. Click the "+" icon or "Create App" button (top left area)

### 2.2 Connect GitHub Repo

1. A dialog appears: **"Choose a repository"**
2. On the **left side**, you'll see your GitHub account listed with your repos
3. **Find and click on your repo** (e.g., `G-man312/phishguard`)
   - You may see a "Refresh cache" button; click it if your repo doesn't appear

### 2.3 Configure Deployment Settings

After clicking your repo, a form appears with these fields:

| Field | Value |
|-------|-------|
| **App name** | `phishguard` (or any unique name) |
| **Organization** | `Personal` |
| **Branch to deploy** | `main` |
| **Current Working Directory** | `ml-backend` (IMPORTANT!) |
| **Config path** | Leave empty |

**The most important setting:** Set "Current Working Directory" to `ml-backend` because that's where your `Dockerfile` is.

### 2.4 Click "Deploy"

1. Fly will start building your Docker image (this takes 1-3 minutes)
2. You'll see a log output with lines like:
   ```
   Building docker image...
   Installing Python dependencies...
   Successfully deployed
   ```

### 2.5 Wait for Deployment to Complete

- You'll see a green checkmark or "Success" message
- Fly will assign your app a URL like: `https://phishguard.fly.dev`
- **Copy and save this URL** — you'll need it later!

---

## Step 3: Verify the Backend is Running

### 3.1 Test the `/health` endpoint

1. Open your browser
2. Go to: `https://<YOUR_FLY_APP>.fly.dev/health`
   - Replace `<YOUR_FLY_APP>` with your actual app name (e.g., `phishguard`)
   - Full example: `https://phishguard.fly.dev/health`

3. You should see JSON output like:
   ```json
   {
     "status": "healthy",
     "model_loaded": true
   }
   ```

If you see this ✅ **Great! Your backend is deployed and working.**

If you see an error ❌ Go to **Troubleshooting** section at the end.

---

## Step 4: Update the Extension to Use Your Deployed Backend

Now you need to tell the Chrome extension to use your new Fly.io URL instead of `localhost:5000`.

### 4.1 Open background.js in VS Code

1. In VS Code, open the file: `background.js`
2. Find the line that says:
   ```javascript
   const ML_API_URL = 'http://localhost:5000/predict';
   ```
   (Should be around line 4)

3. Replace `http://localhost:5000` with your Fly.io URL:
   ```javascript
   const ML_API_URL = 'https://phishguard.fly.dev/predict';
   ```
   (Replace `phishguard` with your actual Fly app name)

4. Save the file (Ctrl + S)

### 4.2 Open popup.js in VS Code

1. Open the file: `popup.js`
2. Find the lines that say:
   ```javascript
   const ML_API_URL = 'http://localhost:5000/predict';
   const REPORT_API_URL = 'http://localhost:5000/report';
   ```
   (Should be around lines 2-3)

3. Replace both lines:
   ```javascript
   const ML_API_URL = 'https://phishguard.fly.dev/predict';
   const REPORT_API_URL = 'https://phishguard.fly.dev/report';
   ```

4. Save the file (Ctrl + S)

**That's it!** Your extension will now talk to your deployed backend on Fly.io.

---

## Step 5: Test the Extension Locally (Before Publishing)

### 5.1 Load the Extension in Chrome

1. Open Chrome browser
2. Go to: `chrome://extensions/`
3. Toggle **"Developer mode"** (top right corner)
4. Click **"Load unpacked"** (top left)
5. Select your project folder: `E:\(Group 11A) phish-guard\phish-guard`
6. Click **"Select Folder"**

You should see the PhishGuard extension appear in the list with a colorful icon.

### 5.2 Test It

1. Click the PhishGuard icon in your Chrome toolbar (top right)
2. The popup should load and show "Checking..." briefly
3. Visit a website (e.g., `https://google.com`)
4. Click the PhishGuard icon again — you should see the classification (e.g., "Safe Site")

**If this works** ✅ Your extension is now using the Fly.io backend!

**If it fails** ❌ Check that your URL in `background.js` and `popup.js` matches your Fly.io app name exactly.

---

## Step 6: Prepare for Chrome Web Store Publishing (Optional)

Once you're happy with testing, you can publish to the Chrome Web Store so anyone can install it with one click.

(I can provide detailed instructions for this if you need them.)

---

## Troubleshooting

### My `/health` endpoint returns an error

**Cause:** The Flask app is running, but the ML model file wasn't included in the Docker build.

**Fix:**
1. Make sure `phishguard_model.pkl` exists in `ml-backend` folder (check locally first)
2. Push it to GitHub: 
   ```powershell
   git add ml-backend/phishguard_model.pkl
   git commit -m "Add ML model file"
   git push origin main
   ```
3. Redeploy from Fly.io UI (find the "Redeploy" button)

---

### The extension can't connect to my Fly.io URL

**Cause:** The URL is slightly different, or there's a typo.

**Fix:**
1. Go to your Fly.io dashboard: https://fly.io/dashboard
2. Find your app name in the list
3. Click on it and look for the URL (usually shown as `phishguard.fly.dev`)
4. Copy the exact URL
5. Update `background.js` and `popup.js` with the correct URL

---

### I see "Mixed Content" error in Chrome DevTools

**Cause:** The extension is loaded over HTTPS but trying to reach HTTP.

**Fix:** Always use `https://` for your Fly.io URL (it should already be HTTPS by default).

---

### The extension loads but `/predict` endpoint fails

**Cause:** The model file is missing on Fly.

**Fix:** Same as "health endpoint" troubleshooting above.

---

## Summary of What You Did

✅ Pushed your code to GitHub  
✅ Connected GitHub to Fly.io  
✅ Deployed the ML backend to Fly.io (HTTPS endpoint)  
✅ Updated extension to use Fly.io backend  
✅ Tested the extension locally in Chrome  

**You're now ready to:**
- Publish the extension to Chrome Web Store (optional), OR
- Keep using it locally with the Fly.io backend

---

## Next Steps

Once you've verified everything works:

1. **Chrome Web Store Publishing** — I can help you prepare the package, privacy policy, and screenshots
2. **More Testing** — Visit various websites and test classification accuracy
3. **Gather Feedback** — See if the extension catches real phishing attempts

Let me know which step you want to do next!
