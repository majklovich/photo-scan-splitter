#!/bin/sh
set -eu

python3 -m PyInstaller --noconfirm --clean --windowed --name PhotoScanSplitter app.py

echo "Built dist/PhotoScanSplitter.app"
