#!/bin/sh
set -eu

python3 -m PyInstaller --noconfirm --clean --windowed --name PhotoScanSplitter app.py

rm -rf build dist/PhotoScanSplitter PhotoScanSplitter.spec

echo "Built dist/PhotoScanSplitter.app"
