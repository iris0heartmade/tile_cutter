@echo off
setlocal

cd /d "%~dp0"
python -u main.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo TileCutter failed to start. Check the error message above.
) else (
    echo.
    echo TileCutter has exited.
)

echo Exit code: %EXIT_CODE%
pause
endlocal
