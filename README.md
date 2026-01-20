# Daily Activity Tracker

A personal life tracking app built with Streamlit for monitoring daily habits, tasks, and goals.

## Features

- **Dynamic daily checklists** with customizable templates
- **Point-based tracking system** - track positive habits and negative ones
- **Automatic daily backups** with recovery and import/export
- **Date navigation** - view/edit any past date or plan ahead
- **Advanced analytics**:
  - Trends & insights with 7-day moving averages
  - Category balance across life areas (Spiritual, Social, Physical, Intellectual, Other)
  - Smart pattern detection (mood/energy correlations, upward/downward trends)
- **Streak tracking & habit formation**:
  - Current and longest streaks for each task
  - Positive day streak tracking
  - Consistency scores and habit strength indicators
  - Personalized habit insights
- **Goal setting & tracking**:
  - Weekly, monthly, and yearly goal management
  - Real-time progress tracking with visual progress bars
  - Goal completion indicators
- **Weekly review dashboard** - Structured reflection and planning
- **Task quick actions** - edit points, save to templates, copy from history
- **Mood & Energy tracking** - correlate with performance

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
