"""
AAMVA PDF417 Barcode Validator - Flask localhost server
Run: python app.py
Visit: http://127.0.0.1:5000
"""
import os, uuid, re
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_OK = True
except ImportError:
    PYZBAR_OK = False

try:
    import zxingcpp
    ZXING_OK = True
except ImportError:
    ZXING_OK = False

from aamva_parser import validate_aamva_raw

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def preprocess_image(path: str):
    """
    Multi-pass preprocessing pipeline. Returns list of numpy arrays (grayscale).
    Tries progressively more aggressive corrections to handle bad photos.
    """
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Cannot read image file - ensure it is a valid image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    candidates = [gray]

    # 1. Upscale small images (barcodes need density to decode)
    h, w = gray.shape
    if max(h, w) < 1200:
        scale = 1200 / max(h, w)
        up = cv2.resize(gray, (int(w * scale), int(h * scale)),
                        interpolation=cv2.INTER_CUBIC)
        candidates.append(up)

    # 2. CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    candidates.append(clahe.apply(gray))

    # 3. Adaptive threshold (handles uneven lighting)
    candidates.append(cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2))

    # 4. Otsu threshold
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    candidates.append(otsu)

    # 5. Sharpen then threshold
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(gray, -1, kernel)
    candidates.append(sharp)

    # 6. Deskew attempt (barcodes photographed at an angle)
    coords = np.column_stack(np.where(gray < 128))
    if len(coords) > 100:
        try:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.5:  # only deskew if notably tilted
                M = cv2.getRotationMatrix2D(
                    (w // 2, h // 2), angle, 1.0)
                deskewed = cv2.warpAffine(
                    gray, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE)
                candidates.append(deskewed)
        except Exception:
            pass

    return candidates


def raw_bytes_to_str(data: bytes) -> str:
    """
    Convert raw barcode bytes to string without corrupting control characters.

    CRITICAL: AAMVA header contains bytes 0x40(@) 0x0A(LF) 0x1C(FS) 0x0D(CR)
    - UTF-8 with 'replace' turns 0x1C into the replacement char, breaking regex
    - latin-1 is a perfect 1:1 byte-to-char mapping with NO corruption
    - We NEVER strip() the result because the leading '@' IS the header start
    """
    return data.decode("latin-1")


def decode_barcode(path: str):
    """
    Try every engine + preprocessing combination.
    Returns (raw_string, engines_dict, consistent).

    KEY RULES:
    - Never call .strip() on decoded data - strips the AAMVA header prefix
    - Use latin-1 decoding, not utf-8
    - pyzbar: use .data (bytes) -> latin-1
    - zxingcpp: prefer .bytes if available, else .text (may be pre-decoded)
    """
    variants = preprocess_image(path)
    pil_orig = Image.open(path).convert("RGB")
    results = {}  # engine_name -> raw_string

    for i, variant in enumerate(variants):
        pil_variant = Image.fromarray(variant)

        # --- pyzbar ---
        if PYZBAR_OK and "pyzbar" not in results:
            try:
                decoded_list = pyzbar_decode(variant)
                for d in decoded_list:
                    if d.type == "PDF417" and d.data:
                        # Use raw bytes -> latin-1, NO strip()
                        results["pyzbar"] = raw_bytes_to_str(d.data)
                        break
            except Exception:
                pass

        # --- zxing-cpp ---
        if ZXING_OK and "zxingcpp" not in results:
            try:
                res = zxingcpp.read_barcode(pil_variant)
                if res and res.valid and "PDF417" in res.format.name.upper():
                    # Prefer .bytes (raw) over .text (may be processed)
                    if hasattr(res, "bytes") and res.bytes:
                        results["zxingcpp"] = raw_bytes_to_str(res.bytes)
                    elif res.text:
                        # .text is already a str but may still have the header intact
                        results["zxingcpp"] = res.text
            except Exception:
                pass

        if len(results) >= 2:
            break

    # Final fallback: try original PIL image directly
    if PYZBAR_OK and "pyzbar" not in results:
        try:
            decoded_list = pyzbar_decode(pil_orig)
            for d in decoded_list:
                if d.type == "PDF417" and d.data:
                    results["pyzbar_orig"] = raw_bytes_to_str(d.data)
                    break
        except Exception:
            pass

    if not results:
        raise ValueError(
            "No PDF417 barcode detected. "
            "Tips: photograph the BACK of the ID, ensure good lighting, "
            "hold the camera parallel to the card, and avoid glare."
        )

    # Pick best result (prefer pyzbar as it returns raw bytes faithfully)
    best_key = next(
        (k for k in ("pyzbar", "pyzbar_orig", "zxingcpp") if k in results),
        list(results.keys())[0]
    )
    raw = results[best_key]

    values = list(results.values())
    consistent = len(set(values)) == 1 if len(values) > 1 else True

    return raw, results, consistent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/validate", methods=["POST"])
def validate():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type. Upload PNG, JPG, BMP, or TIFF"}), 400

    filename = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(save_path)

    try:
        raw, engines, consistent = decode_barcode(save_path)
    except ValueError as e:
        return jsonify({"error": str(e), "stage": "decode"}), 422
    finally:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass

    result = validate_aamva_raw(raw)
    result["decode_engines"] = list(engines.keys())
    result["engine_agreement"] = consistent

    if not consistent:
        result["warnings"].insert(
            0,
            "CROSS-ENGINE DISAGREEMENT: The two decoders read different data. "
            "May indicate a damaged or tampered barcode."
        )

    return jsonify(result)


@app.route("/debug", methods=["POST"])
def debug():
    """
    Debug endpoint: returns the raw decoded bytes as a hex dump + repr.
    POST an image file to /debug to see exactly what the decoder reads.
    Use this to diagnose header detection issues.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    f = request.files["file"]
    filename = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(save_path)

    try:
        raw, engines, consistent = decode_barcode(save_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    finally:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass

    raw_bytes = raw.encode("latin-1")
    first_80  = raw_bytes[:80]

    hex_dump = " ".join(f"{b:02X}" for b in first_80)
    char_repr = "".join(
        chr(b) if 32 <= b < 127 else f"[{b:02X}]" for b in first_80
    )

    return jsonify({
        "engines":        list(engines.keys()),
        "total_length":   len(raw),
        "first_80_hex":   hex_dump,
        "first_80_chars": char_repr,
        "raw_repr":       repr(raw[:120]),
        "starts_with_at": raw.startswith("@"),
        "ansi_position":  raw.find("ANSI"),
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "pyzbar": PYZBAR_OK, "zxingcpp": ZXING_OK})


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    print("\n" + "=" * 55)
    print(" AAMVA PDF417 Barcode Validator")
    print(" http://127.0.0.1:5000")
    print(" Debug endpoint: POST image to /debug")
    print("=" * 55 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
