@echo off
setlocal

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo TileCutter 启动失败，请确认 Python 与依赖已安装。
    pause
)

endlocal
