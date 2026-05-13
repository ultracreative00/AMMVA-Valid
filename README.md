# AMMVA-Valid

A strict **AAMVA PDF417 barcode validator** that runs entirely on localhost.
Upload an image of any US/Canadian driver's license back, and the validator
decodes the PDF417 barcode then checks every field against the
**AAMVA DL/ID Card Design Standard versions 1–10 (2000–2025)**.

---

## Anti-Fake Detection Layers

| Layer | What it catches |
|---|---|
| AAMVA header signature | Missing `@\n\x1c\rANSI` compliance prefix |
| IIN registry check | IINs not in the official AAMVA jurisdiction table |
| IIN ↔ State cross-check | Mismatched issuer IIN vs. DAJ state field |
| Cross-date logic | Future issue dates, expiry ≤ issue date, DOB after issue |
| Field format validation | Eye color, height (nnnIN/nnnCM), sex code, truncation codes |
| Dual-engine agreement | pyzbar + zxing-cpp must decode identical data |

---

## Prerequisites (Windows 10)

### 1. System installs (in order)

| Tool | Notes |
|---|---|
| **Python 3.11 or 3.12** | python.org — check "Add to PATH" |
| **Visual C++ Redistributable 2015-2022 x64** | Required by OpenCV / pyzbar |
| **ZBar Windows installer** | sourceforge.net/projects/zbar — add `bin/` to system PATH |
| **Git** | git-scm.com |

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

> **ZBar DLL error on Windows?**  
> Download the ZBar `.exe` installer, run it, then add its `bin/` folder to your system `PATH` environment variable and restart your terminal.

---

## Usage

```bash
# Clone
git clone https://github.com/ultracreative00/AMMVA-Valid.git
cd AMMVA-Valid

# Install
pip install -r requirements.txt

# Run
python app.py

# Open browser
# http://127.0.0.1:5000
```

---

## Project Structure

```
AMMVA-Valid/
├── app.py               ← Flask server + dual-engine barcode decoder
├── aamva_parser.py      ← Full AAMVA spec engine (parser + validator)
├── requirements.txt
├── README.md
├── LICENSE              ← MIT
├── .gitignore
├── templates/
│   └── index.html       ← Drag-and-drop upload UI
├── static/
│   ├── css/style.css    ← Dark design system
│   └── js/main.js       ← Fetch API + result renderer
└── uploads/             ← Temp storage (auto-cleared, gitignored)
```

---

## Supported Jurisdictions

All 50 US states · DC · Puerto Rico · US Virgin Islands · Guam · American Samoa  
Ontario · Quebec · British Columbia · Alberta · Manitoba · Saskatchewan  
Nova Scotia · New Brunswick · Newfoundland · Prince Edward Island  
Northwest Territories · Yukon

---

## Legal Notice

This tool is for **authorized identity verification only**.  
Unauthorized scanning of another person's government-issued ID may violate  
state/provincial privacy laws and the REAL ID Act.  
Use responsibly and in compliance with your jurisdiction's regulations.

---

## License

MIT — see `LICENSE`
