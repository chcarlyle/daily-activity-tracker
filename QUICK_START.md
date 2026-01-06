# 📱 Quick Deploy Checklist

## ✅ Pre-Deployment

- [ ] All files in folder (see below)
- [ ] GitHub account created
- [ ] Streamlit Cloud account created (share.streamlit.io)

## 📁 File Structure to Push

```
YOUR-FOLDER/
├── .gitignore                          ← Prevents committing data files
├── README.md                           ← Project description
├── requirements.txt                    ← Python packages needed
├── dynamic_activity_logger_2026.py     ← Your app!
├── .streamlit/
│   ├── config.toml                     ← App settings
│   └── secrets.toml.example            ← Example password file
├── DEPLOYMENT_GUIDE.md                 ← Full instructions
└── setup.sh                            ← Optional: automated setup

⚠️  DO NOT COMMIT:
    - .streamlit/secrets.toml (real passwords)
    - *.json (your activity data)
    - __pycache__/
```

## 🚀 Three-Step Deploy

### Step 1: Push to GitHub (Private Repo)

**Option A - GitHub Desktop (Easiest):**
1. Download GitHub Desktop
2. File → New Repository
3. Add files
4. ☑️ Make private
5. Publish

**Option B - Command Line:**
```bash
git init
git add .
git commit -m "Initial commit"
# Create repo on GitHub.com first, then:
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

**Option C - Use setup.sh script:**
```bash
chmod +x setup.sh
./setup.sh
```

### Step 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Main file: `dynamic_activity_logger_2026.py`
6. Click "Deploy"
7. Wait 2-3 minutes ☕

### Step 3: Add Password (Optional)

1. In Streamlit dashboard → Your App
2. Settings → Secrets
3. Add:
```toml
[passwords]
app_password = "YourSecurePassword"
```
4. Save
5. Share password with yourself only!

## 📱 Add to iPhone

1. Open Safari (not Chrome!)
2. Go to your app URL
3. Tap Share → "Add to Home Screen"
4. Done! 🎉

## 🔄 Update App Later

```bash
# Make changes to files
git add .
git commit -m "Updated templates"
git push

# App auto-updates in ~30 seconds!
```

## ⚠️ Important Notes

- ✅ Works with **private** GitHub repos
- ✅ Your data syncs across devices automatically
- ✅ Free tier is perfect for personal use
- ⚠️ Download backup weekly (in case of data reset)
- ⚠️ App "sleeps" after 7 days inactivity (30s wake time)

## 🎯 Your URLs

After deployment you'll have:

**App URL:** `https://your-app-name.streamlit.app`
**GitHub:** `https://github.com/username/repo-name`

Bookmark both!

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't push to GitHub | Make sure repo is created on GitHub.com first |
| App won't deploy | Check requirements.txt has all packages |
| Data disappeared | Download backup from app, report to Streamlit |
| Can't add to iPhone | Must use Safari browser |
| Slow loading | First load after sleep takes 30 sec (normal) |

## ✨ You're Done!

Total time: ~15 minutes

Once deployed:
- ✅ Access from Mac
- ✅ Access from iPhone  
- ✅ Data syncs automatically
- ✅ Works like a native app on iPhone
- ✅ Update by pushing to GitHub

See `DEPLOYMENT_GUIDE.md` for detailed instructions!
