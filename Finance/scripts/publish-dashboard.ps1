# PowerShell script to export financial data and commit to GitHub
# Run this weekly to keep your GitHub Pages updated

param(
    [string]$CommitMessage = $null,
    [switch]$SkipGit = $false
)

# Get the base directory
$scriptDir = Split-Path -Parent $PSScriptRoot
$baseDir = Split-Path -Parent $scriptDir

# Run the Python export script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Financial Dashboard Export & GitHub Commit" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment if it exists
$venvPath = Join-Path $baseDir ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating Python virtual environment..." -ForegroundColor Yellow
    & $venvPath
} else {
    Write-Host "Warning: .venv not found, using system Python" -ForegroundColor Yellow
}

# Run export script
Write-Host "Running financial export..." -ForegroundColor Yellow
$exportScript = Join-Path $scriptDir "export_financial_dashboard.py"
python $exportScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error running export script!" -ForegroundColor Red
    exit 1
}

# Handle Git commit
if (-not $SkipGit) {
    Write-Host ""
    Write-Host "Preparing GitHub commit..." -ForegroundColor Yellow
    
    $reportsDir = Join-Path (Split-Path -Parent $baseDir) "financial-reports"
    
    if (-not (Test-Path $reportsDir)) {
        Write-Host "Error: Reports directory not found at $reportsDir" -ForegroundColor Red
        exit 1
    }
    
    # Set default commit message
    if ([string]::IsNullOrEmpty($CommitMessage)) {
        $date = Get-Date -Format "yyyy-MM-dd HH:mm"
        $CommitMessage = "Update financial dashboard - $date"
    }
    
    # Navigate to website root
    $websiteRoot = Split-Path -Parent $baseDir
    Push-Location $websiteRoot
    
    # Check if it's a git repository
    if (-not (Test-Path ".git")) {
        Write-Host "Error: Not a Git repository. Run 'git init' first in $websiteRoot" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    # Git operations
    Write-Host "Adding files to Git..." -ForegroundColor Yellow
    git add financial-reports/
    
    Write-Host "Committing changes..." -ForegroundColor Yellow
    git commit -m "$CommitMessage"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Committed successfully" -ForegroundColor Green
        
        Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
        git push origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Pushed to GitHub successfully!" -ForegroundColor Green
        } else {
            Write-Host "⚠ Push failed - check your network/credentials" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠ No changes to commit (reports already up to date)" -ForegroundColor Yellow
    }
    
    Pop-Location
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "Export Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. View your dashboard at: financial-reports/index.html" -ForegroundColor White
Write-Host "2. Enable GitHub Pages in your repo settings (Settings → Pages → Source: main)" -ForegroundColor White
Write-Host "3. Schedule this script to run weekly (see README)" -ForegroundColor White
