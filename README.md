# AAMVA PDF417 Barcode Validator

A strict localhost barcode validator for US and Canadian driver's licenses and ID cards, fully compliant with the **AAMVA DL/ID Card Design Standard versions 1–10**.

## Features

- ✅ Full AAMVA Annex D header parsing
- ✅ Complete IIN registry — all 50 US states, DC, territories, and Canadian provinces
- ✅ Anti-fake detection: IIN registry check, state/IIN cross-match, cross-date logic, field format validation
- ✅ Dual-engine decoding (pyzbar + zxing-cpp) with cross-engine agreement check
- ✅ Multi-pass OpenCV image preprocessing for degraded images
- ✅ Dark-mode web UI with drag-and-drop upload
- ✅ Authenticity score (0–100)
- ✅ All data processed locally — nothing leaves your machine

## Prerequisites (Windows 10)

### 1. System-level

| Tool | Notes |
|---|---|
| **Python 3.11 or 3.12** | [python.org](https://python.org) — check "Add to PATH" during install |
| **Visual C++ Redistributable 2015–2022 x64** | Required by OpenCV/pyzbar |
| **ZBar Windows installer** | From [sourceforge.net/projects/zbar](https://sourceforge.net/projects/zbar/) — add `bin/` to PATH |
| **Git** | [git-scm.com](https://git-scm.com) |

### 2. Python packages

```bash
pip install -r requirements.txt
```

## Running the Validator

```bash
# Clone the repo
git clone https://github.com/ultracreative00/AMMVA-Valid.git
cd AMMVA-Valid

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py

# Open in browser
# http://127.0.0.1:5000
```

## Anti-Fake Detection Layers

| Layer | What it catches |
|---|---|
| AAMVA header signature | Barcodes missing the exact `@\n\x1c\rANSI` prefix |
| IIN registry check | Any IIN not in the official AAMVA jurisdiction table |
| IIN ↔ State cross-check | IIN registered to one state but barcode claims another |
| Cross-date logic | Future issue dates, expiry before issue, DOB after issue |
| Field format validation | Eye color codes, height format, sex code, truncation flags |
| Dual-engine agreement | pyzbar and zxing-cpp must decode identical data |

## Project Structure

```
AAMMVA-Valid/
├── app.py              # Flask server
├── aamva_parser.py     # AAMVA spec engine + anti-fake logic
├── requirements.txt
├── .gitignore
├── templates/
│   └── index.html      # Web UI
└── uploads/            # Temp storage (auto-cleared per request)
```

## Legal Notice

This tool is for **authorized identity verification only**. Unauthorized scanning of another person's government-issued ID may violate state privacy laws and the REAL ID Act. Use responsibly and in compliance with your jurisdiction's regulations.

## Reference

- AAMVA DL/ID Card Design Standard, Annex D (2020/2025 editions)
- AAMVA Issuer Identification Number (IIN) Registry, Table D-1
