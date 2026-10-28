@echo off
setlocal
title 4C6 lab PC setup

rem ======================================================================
rem  One-off setup for a 4C6 lab PC.  Right-click > Run as administrator.
rem   1. creates the "pydvma" conda environment if it isn't there yet
rem   2. installs / updates pydvma, Jupyter Notebook, ipywidgets and ipympl in it
rem   3. checks it all imports
rem   4. copies Start_4C6.bat (from this folder) to the all-users desktop
rem  Safe to re-run: existing environments are just brought up to date.
rem ======================================================================

set "CONDA_ROOT=C:\ProgramData\anaconda3"
set "ENV_DIR=%CONDA_ROOT%\envs\pydvma"
set "PYTHON_VERSION=3.14"
rem ipympl makes the notebook plots interactive: without it they are static
set "PACKAGES=pydvma[full] notebook ipywidgets ipympl"
set "LAUNCHER=%~dp0Start_4C6.bat"
set "DESKTOP=%PUBLIC%\Desktop"

rem ---- preflight ----
fltmc >nul 2>&1
if errorlevel 1 (
    echo This script needs administrator rights:
    echo right-click it and choose "Run as administrator".
    goto :fail
)
if not exist "%CONDA_ROOT%\Scripts\activate.bat" (
    echo ERROR: Anaconda not found at "%CONDA_ROOT%".
    goto :fail
)
if not exist "%LAUNCHER%" (
    echo ERROR: Start_4C6.bat needs to be in the same folder as this script.
    goto :fail
)

echo.
echo [1/4] pydvma environment
if exist "%ENV_DIR%\python.exe" (
    echo   Already exists - will update it.
    goto :install
)
call "%CONDA_ROOT%\Scripts\activate.bat" "%CONDA_ROOT%"
call conda create -p "%ENV_DIR%" python=%PYTHON_VERSION% pip
if not exist "%ENV_DIR%\python.exe" (
    echo ERROR: creating the environment failed - see messages above.
    goto :fail
)

:install
echo.
echo [2/4] Installing / updating %PACKAGES%
rem -s: ignore the per-user site-packages of whoever is running this, otherwise
rem pip "upgrades" by uninstalling packages from that user's roaming profile
"%ENV_DIR%\python.exe" -s -m pip install --upgrade --disable-pip-version-check %PACKAGES%
if errorlevel 1 (
    echo ERROR: pip install failed - see messages above.
    goto :fail
)

echo.
echo [3/4] Checking the environment
"%ENV_DIR%\python.exe" -s -c "import importlib.metadata as m, pydvma, ipywidgets, ipympl, notebook; print('  OK: python', __import__('sys').version.split()[0], '/ pydvma', m.version('pydvma'), '/ notebook', m.version('notebook'), '/ ipywidgets', m.version('ipywidgets'), '/ ipympl', m.version('ipympl'))"
if errorlevel 1 (
    echo ERROR: the environment doesn't import cleanly - see messages above.
    goto :fail
)

echo.
echo [4/4] Copying Start_4C6.bat to the all-users desktop
copy /y "%LAUNCHER%" "%DESKTOP%\Start_4C6.bat" >nul
if errorlevel 1 (
    echo ERROR: could not copy to "%DESKTOP%".
    goto :fail
)
echo   %DESKTOP%\Start_4C6.bat

echo.
echo Setup complete.
pause
exit /b 0

:fail
echo.
echo Setup FAILED.
pause
exit /b 1
