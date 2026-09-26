# Split a Scanned Page into Photos

A small Python desktop application that splits a scanned A4 page with four photos into four separate PNG files.

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

1. Choose **Choose Scan...** and open the scanned page.
2. Move the vertical and horizontal cuts into the gaps between the photos.
3. Choose **Split and Save 4 Photos...** and select the destination folder.

The output files will be `photo_1.png` through `photo_4.png`, ordered from left to right and top to bottom. Supported input formats are JPG, PNG, TIFF, BMP, and WebP. The original scan is not changed.