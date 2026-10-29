#!/usr/bin/env bash
# Builds a single-file executable for the OS you run this on.
set -e
python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller --onefile --windowed --name FormDataConverter formdata_gui.py
echo "Done. Output is in ./dist/"
