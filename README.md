# Split a Scanned Page into Photos

A small Python desktop application that splits scanned pages into a configurable grid of separate image files.

## Requirements

- Python 3.9 or newer
- Tkinter (usually included with Python)

## Installation and launch

Run these commands in a terminal from this folder:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

## Usage

1. Choose **Add Scans...** and select one or more scanned pages.
2. Select a thumbnail in the gallery and choose **Open Selected**, or double-click a thumbnail.
3. Set the number of columns × rows in the controls at the bottom left of the editor. The default is `2 × 2`.
4. Drag the red vertical and horizontal cut lines into position. The cursor changes near a line to show that it can be moved.
5. Choose **Save** to save PNG files as `IMG_1.png`, `IMG_2.png`, and so on in the same folder as the scan. Numbering continues after the highest existing `IMG_N` file.
6. Choose **Save As...** to select a folder, a custom filename prefix, and either PNG or JPG format. The grid cells receive consecutive numbers after the chosen prefix.
7. Choose **Back to Gallery** to return to the thumbnails and open the next scan.

The output files are ordered from left to right and top to bottom. Supported input formats are JPG, PNG, TIFF, BMP, and WebP. The original scan is not changed.

## Build a macOS app

To create an application that can be opened from Finder without Terminal:

```bash
python3 -m pip install pyinstaller
chmod +x build_mac_app.sh
./build_mac_app.sh
```

The finished application will be at `dist/PhotoScanSplitter.app`. Double-click it in Finder, or drag it to the Applications folder. The build must be created on macOS; build it again after changing the source code.