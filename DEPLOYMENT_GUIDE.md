# 🚀 Streamlit Cloud Deployment Guide

## 📋 Prerequisites

1. GitHub account (free)
2. Streamlit Cloud account (free) - sign up at https://share.streamlit.io

---

## 📁 Step 1: Prepare Your Files

Your repository should have this structure:

```
daily-activity-tracker/
├── .gitignore                          ✅ Excludes data files
├── README.md                           ✅ Documentation
├── requirements.txt                    ✅ Python dependencies
├── dynamic_activity_logger_2026.py     ✅ Main app
├── .streamlit/
│   ├── config.toml                     ✅ App configuration
│   └── secrets.toml.example            ✅ Example secrets file
```

**Important:** The actual `secrets.toml` is NOT committed (it's in `.gitignore`)

---

## 🔐 Step 2: Create Private GitHub Repository

### Option A: Using GitHub Desktop (Easiest)

1. Download GitHub Desktop: https://desktop.github.com
2. Open GitHub Desktop
3. File → New Repository
   - Name: `daily-activity-tracker`
   - Local Path: Choose where you saved the files
   - ☑️ **Initialize this repository with a README** (uncheck - we have one)
   - ☑️ **Make this a private repository**
4. Click "Create Repository"
5. Click "Publish repository"
   - ☑️ **Keep this code private**
6. Done!

### Option B: Using Command Line

```bash
# Navigate to your project folder
cd /path/to/your/deployment/folder

# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Daily Activity Tracker"

# Create repository on GitHub.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/daily-activity-tracker.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## ☁️ Step 3: Deploy to Streamlit Cloud

### 3.1: Sign Up / Sign In

1. Go to https://share.streamlit.io
2. Click "Sign up" or "Sign in with GitHub"
3. Authorize Streamlit to access your GitHub

### 3.2: Create New App

1. Click "New app" button
2. Fill in the form:
   - **Repository:** `your-username/daily-activity-tracker`
   - **Branch:** `main`
   - **Main file path:** `dynamic_activity_logger_2026.py`
   - **App URL:** Choose something like `daily-tracker-yourname`

3. Click "Advanced settings" (optional but recommended)
   - **Python version:** 3.11
   
4. Click "Deploy!"

### 3.3: Wait for Deployment

- First deployment takes 2-5 minutes
- You'll see logs showing installation progress
- When complete, you'll get a URL like:
  ```
  https://daily-tracker-yourname.streamlit.app
  ```

---

## 🔒 Step 4: Add Password Protection (Optional)

### 4.1: In Streamlit Cloud Dashboard

1. Go to your app's page
2. Click "⚙️ Settings" (top right)
3. Click "Secrets" in the left menu
4. Add this content:

```toml
[passwords]
app_password = "YourSecurePassword123!"
```

5. Click "Save"
6. Your app will restart automatically

### 4.2: Share the Password

- Only people with the password can access your app
- Change the password anytime in the Secrets panel
- You can also remove password protection by deleting the secrets

---

## 📱 Step 5: Add to iPhone Home Screen

### On iPhone:

1. Open Safari (must use Safari, not Chrome)
2. Go to your app URL: `https://your-app.streamlit.app`
3. Tap the **Share** button (box with arrow)
4. Scroll down and tap **"Add to Home Screen"**
5. Edit name if you want (e.g., "Daily Tracker")
6. Tap **"Add"**

### Result:

- Icon appears on home screen
- Tap it to open like a native app
- Runs in full-screen mode
- No browser chrome visible

---

## 🔄 Step 6: Updating Your App

Whenever you make changes:

### Using GitHub Desktop:

1. Make changes to files locally
2. Open GitHub Desktop
3. It will show your changes
4. Write commit message (e.g., "Added new template")
5. Click "Commit to main"
6. Click "Push origin"
7. Streamlit Cloud auto-deploys in ~30 seconds

### Using Command Line:

```bash
git add .
git commit -m "Your change description"
git push
```

---

## 💾 Data Persistence

### How Data is Stored:

- Your `dynamic_activity_log_2026.json` file is stored on Streamlit's servers
- It persists between app restarts
- **Important:** Streamlit Cloud can reset file storage occasionally

### Backup Strategy:

Add this to your sidebar to download backups:

```python
with st.sidebar:
    st.divider()
    st.subheader("💾 Backup")
    
    if st.button("Download Data"):
        with open(DATA_FILE, 'r') as f:
            st.download_button(
                label="📥 Download JSON",
                data=f.read(),
                file_name=f"backup_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
```

**Best practice:** Download backup weekly or monthly

---

## 🐛 Troubleshooting

### App Won't Deploy

**Error:** `ModuleNotFoundError: No module named 'X'`
- **Fix:** Add missing module to `requirements.txt`

**Error:** `FileNotFoundError: [Errno 2] No such file or directory`
- **Fix:** App can't find data file on first run - this is normal, it will create it

### App is Slow

- Streamlit Cloud "sleeps" after 7 days of inactivity
- First load after sleep takes ~30 seconds
- Subsequent loads are instant
- **Solution:** Use it regularly, or upgrade to paid tier ($20/month for instant wake)

### Data Got Reset

- File storage can occasionally reset on Streamlit Cloud
- **Solution:** Keep regular backups (download JSON weekly)

### Can't Access from iPhone

- Make sure you're using the full URL with `https://`
- Try clearing Safari cache
- Make sure password is correct (if enabled)

---

## 🔐 Privacy & Security

### What Streamlit Can See:

- Your app code (public if repo is public)
- Your data file (stored on their AWS servers)
- Usage logs (when you access the app)

### What They Can't See:

- If you add password, they can't see it (it's encrypted)
- If you encrypt your JSON data (advanced), they can't read it

### Best Practices:

1. ✅ Use private GitHub repository
2. ✅ Add password protection
3. ✅ Don't include super sensitive info in plain text
4. ✅ Keep regular backups
5. ⚠️ Consider this is a cloud service - they technically have access

### Maximum Privacy Option:

If you need maximum privacy, use **self-hosted** instead:
- Run on your Mac 24/7
- Use Tailscale VPN to access from iPhone
- 100% your infrastructure
- (Let me know if you want this setup instead)

---

## 📊 Usage Limits (Free Tier)

- ✅ Unlimited apps
- ✅ Unlimited users (for you and anyone with password)
- ✅ 1 GB storage
- ✅ 1 GB RAM per app
- ⚠️ Apps "sleep" after inactivity (30 sec wake time)
- ⚠️ Community support only

**This is more than enough for personal use!**

---

## 🎯 Quick Reference

### Your URLs:
- **App:** https://YOUR-APP-NAME.streamlit.app
- **GitHub Repo:** https://github.com/YOUR-USERNAME/daily-activity-tracker
- **Streamlit Dashboard:** https://share.streamlit.io

### Common Commands:

```bash
# Update app
git add .
git commit -m "Update"
git push

# View deployment logs
# Go to Streamlit Cloud dashboard → Your App → Manage → Logs

# Restart app
# Streamlit Cloud dashboard → Your App → Reboot
```

---

## ✅ Post-Deployment Checklist

- [ ] App is accessible at URL
- [ ] Can log in (if password enabled)
- [ ] Can add tasks and check them off
- [ ] Can see analytics
- [ ] Added to iPhone home screen
- [ ] Tested on both Mac and iPhone
- [ ] Downloaded initial backup
- [ ] Bookmarked the URL

---

## 🆘 Need Help?

**Streamlit Community Forum:** https://discuss.streamlit.io
**Streamlit Docs:** https://docs.streamlit.io

**Common issues already solved in this setup:**
✅ Mobile-responsive design
✅ Data persistence
✅ Password protection
✅ Clean UI (no Streamlit branding)
✅ Fast loading
✅ Works offline after first load (PWA features)

---

## 🚀 You're Ready!

Follow the steps above and you'll have your app running in ~15 minutes!

**Need the self-hosted Tailscale option instead?** Let me know and I'll provide that guide.
