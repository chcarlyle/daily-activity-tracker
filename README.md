# Daily Activity Tracker

A personal life tracking app built with Streamlit for monitoring daily habits, tasks, and goals.

## Features

- Dynamic daily checklists with customizable templates
- Point-based tracking system with day-type modifiers
- Automatic daily backups with recovery
- Date navigation to view/edit historical data
- Running tracker
- Habit analytics and visualization

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run dynamic_activity_logger_2026.py
```

### Deployment on Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from your GitHub repository
4. In the Streamlit Cloud dashboard, add your secrets:
   - Go to App Settings → Secrets
   - Add the following:
   ```toml
   [passwords]
   app_password = "your_password_here"
   ```

## File Structure

- `dynamic_activity_logger_2026.py` - Main application
- `requirements.txt` - Python dependencies
- `IMPROVEMENTS.md` - Recent improvements documentation
- `.streamlit/secrets.toml` - Local secrets (NOT committed to git)

## Configuration

The app uses timezone `America/New_York` by default. To change this, edit the timezone references in the main Python file.

## Data Storage

- Data is stored in `dynamic_activity_log_2026.json` (auto-created, not committed to git)
- Automatic daily backups saved to `backups/` folder
- Export/import functionality available in the sidebar

## Privacy Note

This is a personal tracking app. The `.gitignore` file is configured to prevent your personal data and secrets from being committed to the repository.
