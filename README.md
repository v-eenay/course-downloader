# Course Downloader

A local desktop application for downloading course materials from **Coursera** and **Udemy**.  
Built by **Binay Koirala** — [koiralavinay@gmail.com](mailto:koiralavinay@gmail.com)

---

## Download (No Python Required)

> **Just want to use it?** Download the ready-to-run Windows executable — no installation, no Python needed.

**[⬇ Download latest release](https://github.com/v-eenay/course-downloader/releases/latest)**

1. Click the link above and download `CourseDownloader-vX.X.X-windows.exe`
2. Double-click to run
3. Log in to Coursera or Udemy in your browser first, paste the course URL, and click **Download**

---

## Features

- **Coursera** — full support: videos, subtitles, lecture notes, assignments, and supplementary materials
- **Udemy** — full support: videos, subtitles (all languages), articles, PDFs, code files, and attachments
- Specialization/multi-course downloads with nested folder structure
- Video quality selection: 720p, 1080p, 1440p, 2160p, or best available
- Automatic browser cookie authentication — no credentials stored
- Resume interrupted downloads (already-downloaded files are skipped)
- Clean per-lecture folder layout numbered for easy navigation

## Providers

### Coursera
Accepts course URLs, course slugs, specialization URLs, and professional certificate URLs.

### Udemy
Paste a full Udemy course URL (`https://www.udemy.com/course/example/`).  
You must be enrolled in the course and logged in to Udemy in your chosen browser.

Per lecture, the downloader saves:
- `NNN. Lecture Title.mp4` — video
- `NNN. Lecture Title.en-US.vtt` — subtitle per language (all available)
- `NNN. Lecture Title.html` — article / reading material
- `NNN. Lecture Title - attachment.pdf` — supplementary files (PDFs, ZIPs, code, etc.)
- `NNN. Lecture Title - link.url` — external links as Windows shortcuts

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`
- A supported browser (Edge, Chrome, Firefox, Brave, Opera, Vivaldi, Zen) with an active logged-in session

## Installation (from source)

```bash
pip install -r requirements.txt
```

## Usage

### GUI

```bash
python maingui.py
```

1. Select provider (Coursera / Udemy)
2. Select the browser you are logged in with
3. Paste the course URL
4. Choose a destination folder
5. Click **Download**

### CLI

```bash
cd downloader_core
python coursera_dl.py --provider coursera <course-slug> --path /output
python coursera_dl.py --provider udemy https://www.udemy.com/course/example/ --cauth-auto chrome --path /output
```

## Project Structure

```
maingui.py              GUI entry point
desktop_shell.py        App bootstrap
app_metadata.py         Version info
settings_store.py       Persistent settings

downloader_core/        Backend
  coursera_dl.py        Main CLI entry
  providers/            Provider abstraction layer
    coursera_provider.py
    udemy_provider.py
    udemy_api.py
    udemy_auth.py
    udemy_mapper.py

terminal_shell/         GUI components
  dashboard.py          Main window
  bridge.py             Download thread coordinator
  paint.py              Stylesheet
  copydeck.py           UI text
```

## Author

**Binay Koirala**  
[koiralavinay@gmail.com](mailto:koiralavinay@gmail.com)

