# Image Labeller

A colorful, keyboard-friendly Tkinter app for locally labeling images across nested folders. Labels come from a simple text file, and every choice is written to a CSV with one row per image.

## Features
- Recursively load images from a chosen folder (supports PNG/JPG/JPEG/BMP/GIF/TIFF/WEBP).
- Read labels from a text file (one label per line) and render them as vivid buttons.
- Write/refresh a CSV log with `timestamp,image_path,label` ensuring one entry per image.
- Previous/Next navigation plus arrow-key support.
- Live counters for each label and total progress.

## Quick Start
1) Install dependencies (Tk comes with most Python builds):
   ```bash
   python3 -m pip install -r requirements.txt
   ```
2) Prepare a labels file, e.g. `input_labels.txt`:
   ```text
   Yes
   No
   Maybe
   ```
3) Run the app:
   ```bash
   python3 app.py
   ```
4) In the UI:
   - Choose your images folder (subfolders are included).
   - Choose the labels text file.
   - (Optional) Set a CSV output path; defaults to `labels.csv` in the images folder.
   - Click **Load project** to start labeling.

## Usage Notes
- Each label click updates the CSV immediately and advances to the next image.
- Changing a label rewrites that image’s single CSV row and adjusts counters.
- Use **Previous** / **Next** buttons or ← / → keys to navigate.
- Progress and per-label counts update live in the sidebar.

## Troubleshooting
- If images do not render, ensure Pillow is installed and the files are one of the supported formats.
- If Tkinter is missing on your OS, install the Python Tk packages from your platform’s package manager (varies by OS).
