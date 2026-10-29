@echo off
REM Builds FormDataConverter.exe (single file, no console window)
REM Requires Python 3.9+ installed and on PATH.
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --windowed --name FormDataConverter formdata_gui.py
echo.
echo Done. Your exe is at dist\FormDataConverter.exe
pause
