# Financial Dashboard - GitHub Pages Setup Guide

## Overview

Your financial data is automatically exported to a beautiful HTML dashboard and committed to GitHub weekly. This dashboard is then hosted on GitHub Pages (free, no server needed).

**Result**: Your website will have a live financial dashboard at `https://your-username.github.io/Website/financial-reports/`

---

## Step 1: Initialize Git Repository

First, make sure your website folder is a Git repository:

```powershell
cd "D:\Vicinity Safety\Website"
git init
```

If not already done, add your GitHub remote:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/Website.git
git branch -M main
git push -u origin main
```

---

## Step 2: Test the Export Script

Before automating, test it manually:

```powershell
cd "D:\Vicinity Safety\Website\Finance"
.\.venv\Scripts\Activate.ps1

# Test the export
python scripts/export_financial_dashboard.py
```

✓ Check that `D:\Vicinity Safety\Website\financial-reports\index.html` was created.

---

## Step 3: Test the GitHub Commit Script

Run the full publish script (includes Git operations):

```powershell
cd "D:\Vicinity Safety\Website\Finance"
.\scripts\publish-dashboard.ps1 -CommitMessage "Initial financial dashboard"
```

**What it does:**
1. Runs the Python export script
2. Stages the files: `git add financial-reports/`
3. Creates commit: `git commit -m "Update financial dashboard - [timestamp]"`
4. Pushes to GitHub: `git push origin main`

---

## Step 4: Enable GitHub Pages

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/Website`
2. Click **Settings** → **Pages**
3. Under "Build and deployment":
   - Source: Select **Deploy from a branch**
   - Branch: `main` / `(root)`
4. Click **Save**

✓ GitHub Pages is now enabled. Your dashboard will be at:
```
https://YOUR_USERNAME.github.io/Website/financial-reports/
```

---

## Step 5: Automate Weekly Updates (Windows Task Scheduler)

Create a scheduled task to run the export every week:

### Option A: Using Task Scheduler GUI

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Right-click **Task Scheduler Library** → **Create Basic Task**
3. Fill in:
   - **Name**: `Weekly Financial Dashboard Export`
   - **Description**: `Auto-export finance data and commit to GitHub`
4. **Trigger** tab: Choose `Weekly` → Pick a day/time (e.g., Monday 2:00 AM)
5. **Action** tab: 
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: `/c "D:\Vicinity Safety\Website\Finance\scripts\publish-dashboard.bat"`
   - Start in: `D:\Vicinity Safety\Website`
6. Click **OK**

### Option B: Using PowerShell (Automated)

Run this PowerShell script as **Administrator**:

```powershell
# Create weekly task
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File 'D:\Vicinity Safety\Website\Finance\scripts\publish-dashboard.ps1'"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 2am

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType ServiceAccount

Register-ScheduledTask -Action $action -Trigger $trigger `
  -Principal $principal -TaskName "Weekly Financial Dashboard Export" `
  -Description "Auto-export finance data and commit to GitHub"
```

---

## Step 6: Test the Scheduled Task

1. Open **Task Scheduler**
2. Find **Weekly Financial Dashboard Export**
3. Right-click → **Run**
4. Check GitHub - you should see a new commit in 1-2 minutes
5. Visit your live dashboard: `https://YOUR_USERNAME.github.io/Website/financial-reports/`

---

## What Gets Exported

Every week, the script exports:

### **1. HTML Dashboard** (`financial-reports/index.html`)
- Current cash balance
- Sales for last 30 days
- Inventory value
- Top-selling products
- Current inventory levels
- VAT summary

### **2. JSON Data** (`financial-reports/financial-data.json`)
```json
{
  "export_date": "2026-03-26T10:30:00",
  "balance": 45234.50,
  "sales_30d": {
    "total_orders": 12,
    "total_units": 45,
    "total_sales": 8950.00
  },
  "inventory": [...],
  "top_products": [...]
}
```

---

## Manual Export (No GitHub Commit)

To export without committing to GitHub:

```powershell
cd "D:\Vicinity Safety\Website\Finance"
python scripts/export_financial_dashboard.py
```

Files are saved to: `D:\Vicinity Safety\Website\financial-reports\`

---

## Troubleshooting

### GitHub Push Fails
```powershell
# Check your Git credentials
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"

# If using HTTPS, update your credentials:
# Windows Credential Manager → Windows Credentials → GitHub
```

### Task Scheduler Doesn't Run
1. Ensure Python is in your PATH: `python --version`
2. Check Task Scheduler history (right-click task → View history)
3. Run manually: `powershell -File "D:\Vicinity Safety\Website\Finance\scripts\publish-dashboard.ps1"`

### Files Not Appearing on GitHub Pages
1. Check if commits are reaching GitHub: `git log --oneline`
2. Wait 1-2 minutes for GitHub Pages to rebuild
3. Verify Pages is enabled in Settings → Pages
4. Check the URL is correct

---

## Accessing Your Dashboard

- **Local**: `D:\Vicinity Safety\Website\financial-reports\index.html`
- **GitHub Pages**: `https://YOUR_USERNAME.github.io/Website/financial-reports/`
- **JSON Data**: `https://YOUR_USERNAME.github.io/Website/financial-reports/financial-data.json`

---

## Optional: Link from Your Website

Add a link to your existing website HTML:

```html
<a href="/financial-reports/" target="_blank" class="btn btn-primary">
  Financial Dashboard
</a>
```

or

```html
<iframe src="/financial-reports/" width="100%" height="800"></iframe>
```

---

## FAQ

**Q: Is the data secure?**  
A: Only summary/aggregate data is exported. Sensitive info (passwords, user details) is NOT exported. You control the visibility via GitHub repository privacy settings.

**Q: How often does it update?**  
A: By default, weekly (you can change the schedule). Every update creates a new commit with a timestamp.

**Q: Can I customize the dashboard?**  
A: Yes! Edit `scripts/export_financial_dashboard.py` and modify the HTML template in the `generate_html_dashboard()` function.

**Q: What if I need real-time updates?**  
A: Change the schedule to daily or hourly. Update line ` -DaysOfWeek Monday ` to run multiple times per week.

**Q: Does GitHub Pages work with private repositories?**  
A: Yes, but only if you have GitHub Pro (free for public repos). For private repos, consider enabling it only if you have the upgrade.

---

## Next Steps

1. ✅ Test export: `python scripts/export_financial_dashboard.py`
2. ✅ Test commit: `.\scripts\publish-dashboard.ps1`
3. ✅ Enable GitHub Pages in Settings
4. ✅ Create scheduled task in Task Scheduler
5. ✅ Wait for Monday 2 AM (or your scheduled time)
6. ✅ Check `https://YOUR_USERNAME.github.io/Website/financial-reports/`

---

## Support

For issues:
1. Check the troubleshooting section above
2. Review Python errors: `python scripts/export_financial_dashboard.py`
3. Check Git logs: `git log --oneline` and `git status`
4. View Task Scheduler history for automation issues

