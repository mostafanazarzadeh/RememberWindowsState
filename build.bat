@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title RememberWindowsState Build Script

echo.
echo ================================================
echo   RememberWindowsState Build Script
echo ================================================
echo.

REM -- Clean previous build output
echo [0/4] Cleaning previous build output...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo Done.

REM -- 1. Install Python dependencies
echo.
echo [1/4] Installing Python dependencies...
python -m pip install -r requirements.txt -q
echo Done.

REM -- 2. Create icon.ico
echo.
echo [2/4] Creating icon.ico...
python create_icon.py
if errorlevel 1 (
    echo WARNING: icon conversion failed. Continuing anyway.
)

REM -- 3. Build executable with PyInstaller
echo.
echo [3/4] Building executable with PyInstaller...
python -m PyInstaller --clean --noconfirm RememberWindowsState.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See output above.
    exit /b 1
)

echo.
echo EXE ready: dist\RememberWindowsState.exe

REM -- 4. Build Windows installer with Inno Setup
echo.
echo [4/4] Building Windows installer...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined ISCC (
    "%ISCC%" installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed.
    ) else (
        echo.
        echo ================================================
        echo   Installer ready:
        echo   dist\installer\RememberWindowsState_Setup_1.3.0.exe
        echo ================================================
    )
) else (
    echo Inno Setup 6 not found - skipping installer.
    echo Download from: https://jrsoftware.org/isdl.php
)

echo.
