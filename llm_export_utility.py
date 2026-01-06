import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

def export_for_llm_analysis(data, output_path="llm_analysis_export.json"):
    """
    Export enriched JSON specifically optimized for LLM qualitative analysis.
    Adds context, summaries, patterns, and metadata to make analysis easier.
    """
    
    today = datetime.now().date()
    
    # Calculate enriched data
    enriched = {
        "metadata": {
            "export_date": today.strftime("%Y-%m-%d"),
            "export_timestamp": datetime.now().isoformat(),
            "total_days_logged": len(data["daily_logs"]),
            "date_range": {
                "start": min(data["daily_logs"].keys()) if data["daily_logs"] else None,
                "end": max(data["daily_logs"].keys()) if data["daily_logs"] else None
            },
            "current_level": data.get("level", 1),
            "total_points": data.get("total_points", 0),
            "version": "2.0_enhanced"
        },
        
        # Activity definitions with full context
        "activity_definitions": {},
        
        # Daily entries with enriched context
        "daily_entries": [],
        
        # Weekly summaries
        "weekly_summaries": [],
        
        # Monthly summaries
        "monthly_summaries": [],
        
        # All notes in chronological order
        "chronological_notes": [],
        
        # Streak information
        "streaks": {},
        
        # Goal tracking history
        "goals": data.get("goals", {}),
        
        # Pattern insights (pre-calculated for LLM)
        "calculated_patterns": {}
    }
    
    # 1. Enrich activity definitions
    for activity_name, activity_info in data.get("activities", {}).items():
        enriched["activity_definitions"][activity_name] = {
            **activity_info,
            "total_completions": sum(
                logs.get(activity_name, 0) 
                for logs in data["daily_logs"].values()
            ),
            "total_minutes": sum(
                data["time_logs"].get(date, {}).get(activity_name, 0)
                for date in data.get("time_logs", {}).keys()
            ) if activity_info.get("time_based") else None,
            "is_positive": activity_info.get("points", 0) > 0,
            "is_negative": activity_info.get("points", 0) < 0
        }
    
    # 2. Create enriched daily entries
    for date_str in sorted(data["daily_logs"].keys()):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Calculate daily totals by category
        category_points = {"Spiritual": 0, "Social": 0, "Physical": 0, "Intellectual": 0}
        for activity, count in data["daily_logs"][date_str].items():
            if activity in data["activities"]:
                category = data["activities"][activity]["category"]
                points = data["activities"][activity]["points"] * count
                category_points[category] += points
        
        daily_entry = {
            "date": date_str,
            "day_of_week": date_obj.strftime("%A"),
            "week_number": date_obj.isocalendar()[1],
            "month": date_obj.strftime("%B"),
            "activities_completed": data["daily_logs"][date_str],
            "time_spent": data.get("time_logs", {}).get(date_str, {}),
            "metrics": data.get("daily_metrics", {}).get(date_str, {}),
            "category_points": category_points,
            "total_points": sum(category_points.values()),
            "activities_count": len(data["daily_logs"][date_str]),
            "balanced_day": all(v > 0 for v in category_points.values()),  # All 4 categories positive
        }
        
        enriched["daily_entries"].append(daily_entry)
    
    # 3. Calculate weekly summaries
    weeks = {}
    for entry in enriched["daily_entries"]:
        week_key = f"{entry['date'][:4]}-W{entry['week_number']:02d}"
        if week_key not in weeks:
            weeks[week_key] = {
                "week": week_key,
                "year": entry["date"][:4],
                "week_number": entry["week_number"],
                "days": [],
                "total_points": 0,
                "category_points": {"Spiritual": 0, "Social": 0, "Physical": 0, "Intellectual": 0},
                "avg_mood": [],
                "avg_energy": [],
                "notes": []
            }
        
        weeks[week_key]["days"].append(entry["date"])
        weeks[week_key]["total_points"] += entry["total_points"]
        for cat, pts in entry["category_points"].items():
            weeks[week_key]["category_points"][cat] += pts
        
        if entry["metrics"].get("mood"):
            weeks[week_key]["avg_mood"].append(entry["metrics"]["mood"])
        if entry["metrics"].get("energy"):
            weeks[week_key]["avg_energy"].append(entry["metrics"]["energy"])
        if entry["metrics"].get("notes"):
            weeks[week_key]["notes"].append(entry["metrics"]["notes"])
    
    for week_key, week_data in weeks.items():
        week_data["avg_mood"] = sum(week_data["avg_mood"]) / len(week_data["avg_mood"]) if week_data["avg_mood"] else None
        week_data["avg_energy"] = sum(week_data["avg_energy"]) / len(week_data["avg_energy"]) if week_data["avg_energy"] else None
        week_data["days_logged"] = len(week_data["days"])
        enriched["weekly_summaries"].append(week_data)
    
    # 4. Calculate monthly summaries
    months = {}
    for entry in enriched["daily_entries"]:
        month_key = entry["date"][:7]  # YYYY-MM
        if month_key not in months:
            months[month_key] = {
                "month": month_key,
                "year": entry["date"][:4],
                "month_name": entry["month"],
                "days": [],
                "total_points": 0,
                "category_points": {"Spiritual": 0, "Social": 0, "Physical": 0, "Intellectual": 0},
                "avg_mood": [],
                "avg_energy": [],
                "balanced_days": 0,
                "notes": []
            }
        
        months[month_key]["days"].append(entry["date"])
        months[month_key]["total_points"] += entry["total_points"]
        for cat, pts in entry["category_points"].items():
            months[month_key]["category_points"][cat] += pts
        
        if entry["balanced_day"]:
            months[month_key]["balanced_days"] += 1
        
        if entry["metrics"].get("mood"):
            months[month_key]["avg_mood"].append(entry["metrics"]["mood"])
        if entry["metrics"].get("energy"):
            months[month_key]["avg_energy"].append(entry["metrics"]["energy"])
        if entry["metrics"].get("notes"):
            months[month_key]["notes"].append(entry["metrics"]["notes"])
    
    for month_key, month_data in months.items():
        month_data["avg_mood"] = sum(month_data["avg_mood"]) / len(month_data["avg_mood"]) if month_data["avg_mood"] else None
        month_data["avg_energy"] = sum(month_data["avg_energy"]) / len(month_data["avg_energy"]) if month_data["avg_energy"] else None
        month_data["days_logged"] = len(month_data["days"])
        enriched["monthly_summaries"].append(month_data)
    
    # 5. Extract all notes chronologically
    for entry in enriched["daily_entries"]:
        if entry["metrics"].get("notes"):
            enriched["chronological_notes"].append({
                "date": entry["date"],
                "day_of_week": entry["day_of_week"],
                "note": entry["metrics"]["notes"],
                "mood": entry["metrics"].get("mood"),
                "energy": entry["metrics"].get("energy"),
                "total_points": entry["total_points"]
            })
    
    # 6. Calculate streaks for each activity
    for activity_name in data["activities"].keys():
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        last_date = None
        
        for date_str in sorted(data["daily_logs"].keys()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if activity_name in data["daily_logs"][date_str]:
                if last_date and (date_obj - last_date).days == 1:
                    temp_streak += 1
                else:
                    temp_streak = 1
                
                longest_streak = max(longest_streak, temp_streak)
                last_date = date_obj
            else:
                temp_streak = 0
        
        # Current streak
        check_date = today
        while True:
            date_str = check_date.strftime("%Y-%m-%d")
            if date_str in data["daily_logs"] and activity_name in data["daily_logs"][date_str]:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        enriched["streaks"][activity_name] = {
            "current_streak": current_streak,
            "longest_streak": longest_streak
        }
    
    # 7. Calculate patterns for LLM analysis
    if enriched["daily_entries"]:
        # Best/worst days
        best_day = max(enriched["daily_entries"], key=lambda x: x["total_points"])
        worst_day = min(enriched["daily_entries"], key=lambda x: x["total_points"])
        
        # Day of week patterns
        dow_points = {}
        dow_counts = {}
        for entry in enriched["daily_entries"]:
            dow = entry["day_of_week"]
            if dow not in dow_points:
                dow_points[dow] = 0
                dow_counts[dow] = 0
            dow_points[dow] += entry["total_points"]
            dow_counts[dow] += 1
        
        dow_averages = {dow: dow_points[dow] / dow_counts[dow] for dow in dow_points}
        
        # Mood/energy patterns
        high_mood_days = [e for e in enriched["daily_entries"] if e["metrics"].get("mood", 0) >= 8]
        low_mood_days = [e for e in enriched["daily_entries"] if e["metrics"].get("mood", 0) <= 4]
        
        enriched["calculated_patterns"] = {
            "best_day": {
                "date": best_day["date"],
                "points": best_day["total_points"],
                "activities": list(best_day["activities_completed"].keys())
            },
            "worst_day": {
                "date": worst_day["date"],
                "points": worst_day["total_points"],
                "activities": list(worst_day["activities_completed"].keys())
            },
            "best_day_of_week": max(dow_averages.items(), key=lambda x: x[1])[0],
            "worst_day_of_week": min(dow_averages.items(), key=lambda x: x[1])[0],
            "day_of_week_averages": dow_averages,
            "high_mood_days_count": len(high_mood_days),
            "low_mood_days_count": len(low_mood_days),
            "overall_avg_mood": sum(e["metrics"].get("mood", 0) for e in enriched["daily_entries"]) / len([e for e in enriched["daily_entries"] if e["metrics"].get("mood")]) if any(e["metrics"].get("mood") for e in enriched["daily_entries"]) else None,
            "overall_avg_energy": sum(e["metrics"].get("energy", 0) for e in enriched["daily_entries"]) / len([e for e in enriched["daily_entries"] if e["metrics"].get("energy")]) if any(e["metrics"].get("energy") for e in enriched["daily_entries"]) else None,
        }
    
    # 8. Add a human-readable summary for LLM
    enriched["summary_for_llm"] = {
        "description": "This is activity tracking data for an LDS individual following the youth framework of Spiritual, Social, Physical, and Intellectual development.",
        "data_explanation": {
            "daily_entries": "Each day's activities, time spent, mood/energy ratings, and points by category",
            "weekly_summaries": "Aggregated weekly data with averages and totals",
            "monthly_summaries": "Aggregated monthly data with averages and totals",
            "chronological_notes": "All daily reflection notes in chronological order for qualitative analysis",
            "streaks": "Current and longest streaks for each activity",
            "calculated_patterns": "Pre-calculated patterns to help identify trends"
        },
        "analysis_suggestions": [
            "Look for correlations between spiritual activities and mood/energy",
            "Identify patterns in notes during high vs low mood days",
            "Analyze which activities appear together on best days",
            "Look for weekly or monthly trends in category balance",
            "Examine the relationship between screen time (negative activities) and wellbeing",
            "Identify obstacles mentioned in notes during low-performing weeks",
            "Look for spiritual growth patterns in chronological notes"
        ]
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    
    return enriched

# Example usage function
def generate_llm_prompt(json_path="llm_analysis_export.json"):
    """Generate a sample prompt for LLM analysis"""
    
    prompt = f"""I'm sharing my personal activity tracking data from 2026. This data tracks my activities across four categories: Spiritual, Social, Physical, and Intellectual, following the LDS youth development framework.

Please analyze the attached JSON file ({json_path}) and provide insights on:

1. **Spiritual Growth Patterns**: 
   - What trends do you see in my scripture study and prayer habits?
   - How do spiritual activities correlate with my mood and energy?
   - What do my notes reveal about my spiritual journey?

2. **Areas of Strength**:
   - Which categories am I most consistent in?
   - What activities do I excel at?
   - What patterns appear on my best days?

3. **Areas for Improvement**:
   - Where am I struggling?
   - What negative patterns do you notice?
   - How is screen time affecting my overall wellbeing?

4. **Personalized Recommendations**:
   - Based on my unique patterns, what specific actions would help most?
   - What goals should I prioritize?
   - How can I better balance all four categories?

5. **Qualitative Insights**:
   - What themes emerge from my daily notes?
   - Are there emotional patterns tied to specific activities or days?
   - What life events or challenges appear in the data?

Please be specific, referencing actual dates, activities, and metrics from my data. I want actionable insights grounded in my real patterns.
"""
    
    return prompt


if __name__ == "__main__":
    # This would be called from within the Streamlit app
    # For now, just show the structure
    print("LLM Export Utility Ready")
    print("\nTo use in your Streamlit app, add:")
    print("1. Import button to export enriched JSON")
    print("2. Call export_for_llm_analysis(data)")
    print("3. Provide the sample prompt to users")
