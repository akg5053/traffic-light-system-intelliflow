@echo off
echo ========================================
echo IntelliFlow - Push Everything to Git
echo ========================================
echo.
echo This will:
echo   1. Replace .gitignore with minimal version (includes everything)
echo   2. Initialize Git (if not already)
echo   3. Add all files
echo   4. Prepare for commit
echo.
echo Repository size: ~2.5 GB
echo Estimated push time: 15-30 minutes
echo.
pause

echo.
echo Step 1: Backing up current .gitignore...
if exist .gitignore (
    copy .gitignore .gitignore.backup
    echo Backup created: .gitignore.backup
) else (
    echo No existing .gitignore found.
)

echo.
echo Step 2: Using minimal .gitignore (includes everything)...
copy .gitignore.include-all .gitignore
echo .gitignore updated!

echo.
echo Step 3: Checking Git status...
git status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Git not initialized. Initializing...
    git init
    echo Git initialized!
) else (
    echo Git already initialized.
)

echo.
echo Step 4: Adding all files to Git...
echo This may take a few minutes (2.5 GB to stage)...
git add .

echo.
echo Step 5: Checking what will be committed...
git status --short | find /c /v "" > temp_count.txt
set /p file_count=<temp_count.txt
del temp_count.txt
echo.
echo Files staged: %file_count%

echo.
echo ========================================
echo Ready to commit!
echo ========================================
echo.
echo Next steps:
echo   1. Review: git status
echo   2. Commit: git commit -m "Complete IntelliFlow project"
echo   3. Create repository on GitHub/GitLab/Bitbucket
echo   4. Push: git remote add origin ^<your-repo-url^>
echo         git push -u origin main
echo.
echo IMPORTANT:
echo   - First push will take 15-30 minutes
echo   - Use GitLab for best results (unlimited free storage)
echo   - Use stable internet connection
echo.
echo Press any key to exit...
pause >nul

