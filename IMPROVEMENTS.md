# LifeTracker Improvements

## Latest Changes (v4.0 - Redesigned UI)

### User Experience Overhaul
- **Simplified task entry** - Collapsible "Add Tasks" section with template buttons and quick custom task form
- **Compact dashboard** - Key metrics displayed in a single row at top (Points, Completion %, Streak, Mood, Energy)
- **Cleaner date navigation** - Streamlined navigation with context-aware date display
- **Task list reorganization** - Category-based expandable sections replacing multi-column layout
- **Consolidated tabs** - Reduced from 5 tabs to 3 focused sections:
  - 📊 Analytics & Trends (combines Trends and Category Balance)
  - 🔥 Habits & Streaks (streak tracking and consistency)
  - 🎯 Goals (goal tracking, weekly review, and history)
- **Mobile-optimized** - Single-column layouts work better on all screen sizes
- **Simplified actions** - Removed complex popover menus, streamlined to essential delete button
- **Quick template loader** - One-click button to load all templates at once
- **Minimal design** - More white space, clearer visual hierarchy, less clutter

### Design Philosophy
- Focus on speed of daily logging
- Reduce clicks and cognitive load
- Better balance between logging and analytics
- Responsive design that works well on mobile and desktop

## Previous Updates (v3.0)

### Productivity & Habit Building Features
- **Removed notes field** - Cleaned up unused daily_metrics notes structure
- **Added Streaks & Habits tab** with:
  - Current and longest streak tracking for every task
  - Overall positive day streak counter
  - 30-day win rate percentage
  - Task-level consistency scores (completion percentage)
  - Habit strength indicators and insights
  - Smart recommendations for habit building
  - Automatic classification of habits (Established, Building, Needs Attention)
- **Added Goals & Review tab** with:
  - Weekly, monthly, and yearly goal setting
  - Point-based goal tracking with visual progress bars
  - Real-time progress calculation
  - Goal completion status indicators
  - Easy goal creation and deletion
  - Weekly review dashboard with:
    - Week summary statistics
    - Reflection prompts for continuous improvement
    - Guided questions for planning ahead

### Key Functions Added
- `get_task_streak()` - Calculate current and longest streaks for any task
- `get_positive_day_streak()` - Track consecutive positive net point days
- `get_task_consistency()` - Calculate completion percentage over time periods
- `get_all_unique_tasks()` - Get list of all tasks from recent history

## Previous Updates (v2.0)

### Simplification & Enhanced Analytics
- **Removed day types system** - No more complex point multipliers or negative tolerance calculations
- **Removed running tracker** - Simplified focus on daily habits and tasks
- **Added Trends & Insights tab** with:
  - 7-day moving average trend analysis
  - Weekly comparison metrics
  - Smart insights (mood/energy correlations, trend detection, best/worst days)
  - Positive day percentage tracking
- **Added Category Balance tab** with:
  - Total points breakdown by life area
  - Category trends over time
  - Balance insights and recommendations
  - Visual analytics with color-coded charts

## Recent Enhancements (v1.0)

### 1. Data Backup & Recovery
- **Automatic Daily Backups**: Creates a timestamped backup once per day automatically
- **Manual Backup**: Create backups on demand via the sidebar
- **Export Data**: Download a JSON backup file at any time
- **Import Data**: Restore from a backup file (creates automatic backup before importing)
- **Auto-Recovery**: If data file is corrupted, automatically attempts to restore from the most recent backup
- Backups are stored in `backups/` folder (keeps last 30 backups)

### 2. Error Handling
- Comprehensive error handling for all file operations
- Graceful handling of corrupted JSON files
- User-friendly error messages instead of crashes
- Automatic creation of missing data structures

### 3. Date Navigation
- Navigate to any past date using the date picker
- Quick navigation buttons:
  - **⏮️ -7 Days**: Jump back one week
  - **◀️ Previous**: Go to previous day
  - **▶️ Next**: Go to next day
  - **📍 Today**: Return to current day
- View and edit any historical day's checklist
- UI updates to show which date you're viewing

### 4. Task Quick Actions
- **Edit Points**: Modify task point values inline without deleting
- **Save to Template**: Save any task to a template for reuse
  - Add to existing template
  - Create new template on the fly
- **Copy Tasks**: Copy tasks from history to today
  - Copy individual tasks
  - Copy all tasks from a day
- **Delete**: Remove tasks from the current day

### 5. Other Improvements
- History now shows last 14 days (increased from 7)
- Better visual feedback when viewing past dates
- All data operations now have proper validation

## File Structure

```
LifeTracker/
├── dynamic_activity_logger_2026.py   # Main application
├── requirements.txt                   # Python dependencies
├── dynamic_activity_log_2026.json    # Your data (auto-created)
├── backups/                          # Automatic backups (auto-created)
│   ├── backup_20260119_120000.json
│   └── ...
└── .streamlit/
    └── secrets.toml                  # Password config
```

## Usage Tips

### Recovering from Data Loss
1. If your data file gets corrupted, the app will automatically try to restore from backups
2. You can manually import a backup via the sidebar: **Backup & Export** → Upload backup JSON
3. Regular exports are recommended for extra safety

### Working with Past Dates
1. Use the date picker to select any past date
2. You can add/edit/remove tasks for past dates
3. All changes are saved immediately
4. Use the "📍 Today" button to quickly return to current day

### Quick Task Management
1. **Edit** points by clicking the ✏️ Edit button under each category
2. **Save** frequently used tasks to templates for easy reuse
3. **Copy** yesterday's tasks to today using the History tab
4. **Delete** tasks you no longer need

## Running the App

```bash
streamlit run dynamic_activity_logger_2026.py
```

## Next Steps (Optional Improvements)

These weren't implemented but could be added later:
- Daily notes field (structure exists but no UI)
- Running tracker notes display
- Streak tracking
- Configuration file for timezone and defaults
- Keyboard shortcuts
- CSV export for analysis
