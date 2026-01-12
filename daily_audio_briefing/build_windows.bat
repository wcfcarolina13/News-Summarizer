@echo off
REM Daily Audio Briefing - Windows Build Script
REM
REM Prerequisites:
REM   1. Python 3.10+ with pip
REM   2. NSIS 3.x installed and in PATH (https://nsis.sourceforge.io/)
REM   3. Run: pip install -r requirements-desktop.txt
REM
REM This script will:
REM   1. Build the app with PyInstaller
REM   2. Create the installer with NSIS
REM

echo ==============================================
echo   Daily Audio Briefing - Windows Build
echo ==============================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check for NSIS
makensis /VERSION >nul 2>&1
if errorlevel 1 (
    echo WARNING: NSIS not found. Installer will not be created.
    echo Download NSIS from: https://nsis.sourceforge.io/
    set SKIP_NSIS=1
) else (
    set SKIP_NSIS=0
)

echo.
echo Step 1: Installing dependencies...
echo.
pip install -r requirements-desktop.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 2: Building application with PyInstaller...
echo.
python -m PyInstaller DailyAudioBriefing.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo Application built successfully!
echo Output: dist\DailyAudioBriefing\DailyAudioBriefing.exe
echo.

if "%SKIP_NSIS%"=="1" (
    echo Skipping installer creation (NSIS not found)
    echo To create installer, install NSIS and run: makensis installer.nsi
) else (
    echo Step 3: Creating installer with NSIS...
    echo.
    makensis installer.nsi
    if errorlevel 1 (
        echo ERROR: NSIS installer creation failed
        pause
        exit /b 1
    )
    echo.
    echo ==============================================
    echo   BUILD COMPLETE!
    echo ==============================================
    echo.
    echo Installer: dist\DailyAudioBriefing-1.0.0-Windows-Setup.exe
)

echo.
pause
