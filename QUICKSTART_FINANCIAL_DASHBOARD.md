# Quick Start - Financial Dashboard on GitHub Pages

## ✅ What's Been Completed

1. **Export Script Created** (`Finance/scripts/export_financial_dashboard.py`)
   - Pulls data from your FinancialDatabase.db
   - Generates beautiful HTML dashboard
   - Exports JSON data file
   - Ready to run weekly

2. **Automation Scripts Created**
   - PowerShell script: `publish-dashboard.ps1` (handles export + Git commit)
   - Batch file: `publish-dashboard.bat` (for Task Scheduler)

3. **First Dashboard Generated** ✓
   - **Location**: `D:\Vicinity Safety\Website\financial-reports\index.html`
   - **Data**: `D:\Vicinity Safety\Website\financial-reports\financial-data.json`

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Initialize Git (if not already done)
```powershell
cd "D:\Vicinity Safety\Website"
git init
git remote add origin https://github.com/YOUR_USERNAME/Website.git
git push -u origin main
```

### Step 2: Enable GitHub Pages
1. Go to your GitHub repo settings
2. **Settings** → **Pages**
3. Source: `main` → Save

✅ Your dashboard will be live at:
```
https://YOUR_USERNAME.github.io/Website/financial-reports/
```

### Step 3: Set Up Weekly Automation
Open **Windows Task Scheduler** (search "Task Scheduler"):

1. Right-click **Task Scheduler Library** → **Create Basic Task**
2. **Name**: `Weekly Financial Dashboard Export`
3. **Trigger**: Weekly (pick a day/time, e.g., Monday 2:00 AM)
4. **Action**: 
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: 
   ```
   /c "D:\Vicinity Safety\Website\Finance\scripts\publish-dashboard.bat"
   ```
5. Click OK

### Step 4: Test It
Run the export manually:
```powershell
cd "D:\Vicinity Safety\Website\Finance"
python scripts/export_financial_dashboard.py
```

---

## 📊 What Your Dashboard Shows

✓ Current cash balance  
✓ Sales (last 30 days)  
✓ Inventory value & products  
✓ Top-selling products  
✓ VAT summary  

---

## 📋 File Structure

```
Website/
├── financial-reports/          ← Your GitHub Pages content
│   ├── index.html             ← Live dashboard
│   └── financial-data.json    ← Raw data
│
├── Finance/
│   ├── app/
│   │   └── finance_ui.py      ← Your desktop app (unchanged)
│   ├── db/
│   │   └── FinancialDatabase.db ← Source data
│   └── scripts/
│       ├── export_financial_dashboard.py
│       ├── publish-dashboard.ps1
│       └── publish-dashboard.bat
│
└── GITHUB_PAGES_SETUP.md       ← Full setup guide
```

---

## 🔄 How It Works

**Automated Weekly Process:**

1. **Monday 2:00 AM** (your scheduled time)
2. Script runs: `export_financial_dashboard.py`
   - Reads current data from SQLite database
   - Generates fresh HTML dashboard
   - Exports JSON data
3. PowerShell script automatically:
   - `git add financial-reports/`
   - `git commit -m "Update financial dashboard - [timestamp]"`
   - `git push origin main`
4. **2 minutes later**: Dashboard is live on GitHub Pages
5. Your team can view it anytime at the URL above

---

## 💡 Manual Export (No GitHub)

To export without pushing to GitHub:
```powershell
cd "D:\Vicinity Safety\Website\Finance"
python scripts/export_financial_dashboard.py
```
Files appear in `financial-reports/` folder immediately.

---

## ✨ Next Steps (In Order)

- [ ] Test export script: `python scripts/export_financial_dashboard.py`
- [ ] Check `financial-reports/index.html` opens in browser
- [ ] Set up Git repository (if not done)
- [ ] Enable GitHub Pages in Settings
- [ ] Test commit script: `.\scripts\publish-dashboard.ps1`
- [ ] Check GitHub for new commit
- [ ] Verify dashboard is live on GitHub Pages URL
- [ ] Create Task Scheduler automation
- [ ] Wait for first scheduled run

---

## ❓ Questions?

**Q: Is my data secure?**  
A: Only summary data is exported (sales, inventory). No passwords, user details, or sensitive info. You control permissions via GitHub repo settings.

**Q: Can I export more frequently?**  
A: Yes! Change Task Scheduler from Weekly to Daily or Hourly.

**Q: Can I customize the dashboard?**  
A: Yes! Edit `export_financial_dashboard.py` - the HTML template is in the `generate_html_dashboard()` function.

**Q: What if export fails?**  
A: Check the logs in Task Scheduler history. Run manually to see error messages.

---

## 📞 Troubleshooting

If GitHub push fails:
```powershell
git config --global user.email "your-email@github.com"
git config --global user.name "Your Name"
git status  # Check what's happening
```

If Task Scheduler doesn't run:
1. Open Task Scheduler → History tab
2. Check if it's enabled (right-click → Enable)
3. Verify Python is in PATH: `python --version`

---

**Created**: March 26, 2026  
**Status**: ✅ Ready to deploy

See `GITHUB_PAGES_SETUP.md` for detailed instructions.
