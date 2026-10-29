@echo off
setlocal
title Start 4C6 notebook

rem ======================================================================
rem  4C6 lab launcher
rem   1. downloads the lab notebook (and any helper .py) from GitHub
rem      into the folder 'lab_4C6' on the desktop (an existing notebook
rem      is only replaced if the student agrees; the helper always is)
rem   2. starts Jupyter Notebook in that folder
rem
rem  Optional: pass a folder as the first argument to use it instead of
rem  the default target (handy for testing), e.g.
rem      Start_4C6.bat "C:\temp\lab_test"
rem ======================================================================

rem ---- settings --------------------------------------------------------
set "REPO_URL=https://raw.githubusercontent.com/torebutlin/divc_labs/master/4C6"
rem The notebook holds the student's work, so an existing one is only
rem replaced if they agree. The helper .py isn't theirs to edit, so it is
rem always brought up to date (a copy that differed is kept as .old).
set "FILES=4C6_Notebook.ipynb"
rem 4C6 has no helper yet: list any here, separated by spaces.
set "HELPERS="
rem The desktop may be redirected (e.g. to OneDrive), so ask Windows where it is
set "DESKTOP_DIR="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')" 2^>nul`) do set "DESKTOP_DIR=%%D"
if not defined DESKTOP_DIR set "DESKTOP_DIR=%USERPROFILE%\Desktop"
if not exist "%DESKTOP_DIR%\" set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "TARGET_DIR=%DESKTOP_DIR%\lab_4C6"
set "CONDA_ROOT=C:\ProgramData\anaconda3"
set "CONDA_ENV=pydvma"

rem Jupyter normally keeps its runtime files (server info, kernel
rem connection files) in %APPDATA%\jupyter\runtime. Newer Python creates
rem that folder with permissions that only work while the user *owns*
rem the folder; once a roaming profile is synced back down, ownership
rem changes and the user is locked out, so Jupyter crashes on startup with
rem "PermissionError ... jupyter\runtime\jpserver-XXXX-open.html".
rem Keep the runtime folder in non-roaming local app data instead.
set "JUPYTER_RUNTIME_DIR=%LOCALAPPDATA%\jupyter-runtime"

rem Use only the packages installed in the environment. Anything a user has
rem pip-installed into their roaming profile (%APPDATA%\Python) follows them
rem to every PC and would otherwise take priority over the environment.
set "PYTHONNOUSERSITE=1"
rem ----------------------------------------------------------------------

if not "%~1"=="" set "TARGET_DIR=%~1"
rem A trailing backslash would escape the closing quote on the jupyter command line
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

rem ---- check Anaconda / environment ----
if not exist "%CONDA_ROOT%\Scripts\activate.bat" (
    echo ERROR: Anaconda not found at "%CONDA_ROOT%".
    goto :fail
)
if not exist "%CONDA_ROOT%\envs\%CONDA_ENV%\python.exe" (
    echo ERROR: Python environment "%CONDA_ENV%" not found in "%CONDA_ROOT%\envs".
    goto :fail
)

rem ---- make sure the runtime folder is usable ----
if not exist "%JUPYTER_RUNTIME_DIR%\" mkdir "%JUPYTER_RUNTIME_DIR%" 2>nul
call :can_write "%JUPYTER_RUNTIME_DIR%" || set "JUPYTER_RUNTIME_DIR=%TEMP%\jupyter-runtime-%RANDOM%%RANDOM%"

rem ---- target folder ----
if not exist "%TARGET_DIR%\" mkdir "%TARGET_DIR%" 2>nul
if not exist "%TARGET_DIR%\" (
    echo ERROR: could not create or access "%TARGET_DIR%".
    goto :fail
)

rem ---- download lab files ----
echo Fetching lab files into "%TARGET_DIR%" ...
for %%F in (%FILES%) do call :fetch "%%F"
if defined HELPERS for %%F in (%HELPERS%) do call :fetch "%%F" always

rem ---- start Jupyter ----
echo.
echo Starting Jupyter Notebook - a browser window will open shortly.
echo Keep this window open while you work; close it when you have finished.
echo.
call "%CONDA_ROOT%\Scripts\activate.bat" "%CONDA_ROOT%"
call conda activate %CONDA_ENV%
call jupyter notebook --notebook-dir="%TARGET_DIR%"
if errorlevel 1 (
    echo.
    echo Jupyter exited with an error - see the messages above.
    goto :fail
)
exit /b 0


rem ======================================================================
:fetch
rem Download one file to a temp copy, then decide whether to replace the
rem existing one, so a failed download never damages a student's file.
rem With "always" as a second argument, a file that differs is replaced
rem without asking, and the old one kept with .old added to its name.
set "NAME=%~1"
set "DEST=%TARGET_DIR%\%NAME%"
set "TMPFILE=%TEMP%\4C6_%RANDOM%_%NAME%"

"%SystemRoot%\System32\curl.exe" -fsSL --retry 2 --connect-timeout 15 -o "%TMPFILE%" "%REPO_URL%/%NAME%"
if errorlevel 1 goto :fetch_failed
if not exist "%DEST%" goto :fetch_install

fc /b "%TMPFILE%" "%DEST%" <nul >nul 2>&1
if not errorlevel 1 (
    echo   %NAME%: already up to date.
    del "%TMPFILE%"
    goto :eof
)
if /i "%~2"=="always" goto :fetch_replace
echo.
echo   %NAME% already exists in your folder and differs from the latest version.
set "ANSWER="
set /p "ANSWER=  Overwrite it with the latest version? Any changes you made will be lost. [y/N] "
if /i "%ANSWER%"=="y" goto :fetch_install
if /i "%ANSWER%"=="yes" goto :fetch_install
echo   Keeping your existing %NAME%.
del "%TMPFILE%"
goto :eof

:fetch_replace
copy /y "%DEST%" "%DEST%.old" >nul
move /y "%TMPFILE%" "%DEST%" >nul && echo   %NAME%: updated to the latest version - your old copy is now %NAME%.old.
goto :eof

:fetch_install
move /y "%TMPFILE%" "%DEST%" >nul && echo   %NAME%: downloaded.
goto :eof

:fetch_failed
if exist "%TMPFILE%" del "%TMPFILE%"
if exist "%DEST%" (
    echo   %NAME%: could not download the latest version - using your existing copy.
    goto :eof
)
echo   WARNING: could not download %NAME%.
goto :eof

:can_write
set "PROBE=%~1\write-test-%RANDOM%.tmp"
(type nul > "%PROBE%") 2>nul || exit /b 1
del "%PROBE%" 2>nul
exit /b 0

:fail
echo.
pause
exit /b 1
