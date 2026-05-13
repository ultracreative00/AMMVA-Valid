"""
AAMVA PDF417 Barcode Validator — Flask localhost server
Run:   python app.py
Visit: http://127.0.0.1:5000
"""
import os
import uuid
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
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16 MB
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")

ALLOWED_EXT = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def preprocess_image(path: str):
    """
    Multi-pass image preprocessing to maximise PDF417 detection success.
    Returns a list of numpy uint8 arrays (grayscale variants).
    """
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Cannot read image file — unsupported format or corrupt data.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    candidates = [gray]

    # Upscale small images
    if max(h, w) < 1000:
        scale = 1000 / max(h, w)
        up = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        candidates.append(up)

    # Adaptive threshold (handles uneven lighting)
    th = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    candidates.append(th)

    # CLAHE histogram equalisation
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    candidates.append(clahe.apply(gray))

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    candidates.append(cv2.filter2D(gray, -1, kernel))

    return candidates


def decode_barcode(path: str):
    """
    Attempt PDF417 decoding with both pyzbar and zxing-cpp over multiple
    preprocessed image variants. Returns (raw_text, engines_dict, consistent).
    """
    variants = preprocess_image(path)
    pil_orig = Image.open(path)
    results  = {}   # engine_name -> decoded string

    for variant in variants:
        if PYZBAR_OK and "pyzbar" not in results:
            for d in pyzbar_decode(variant):
                if d.type == "PDF417":
                    txt = d.data.decode("utf-8", "replace").strip()
                    if txt:
                        results["pyzbar"] = txt

        if ZXING_OK and "zxingcpp" not in results:
            res = zxingcpp.read_barcode(Image.fromarray(variant))
            if res and res.valid and res.format.name == "PDF417":
                txt = res.text.strip()
                if txt:
                    results["zxingcpp"] = txt

        if len(results) >= 2:
            break

    # Final fallback on original PIL image
    if PYZBAR_OK and "pyzbar" not in results:
        for d in pyzbar_decode(pil_orig):
            if d.type == "PDF417":
                results["pyzbar"] = d.data.decode("utf-8", "replace").strip()

    if not results:
        raise ValueError(
            "No PDF417 barcode detected. "
            "Ensure the image is clear, well-lit, and shows the back of the ID card."
        )

    values     = list(results.values())
    consistent = len(set(values)) == 1 if len(values) > 1 else True
    return values[0], results, consistent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/validate", methods=["POST"])
def validate():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file type. Upload PNG, JPG, BMP, TIFF, or WebP"}), 400

    filename  = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(save_path)

    try:
        raw, engines, consistent = decode_barcode(save_path)
    except ValueError as e:
        return jsonify({"error": str(e), "stage": "decode"}), 422
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)   # never persist uploaded files

    result = validate_aamva_raw(raw)
    result["decode_engines"]   = list(engines.keys())
    result["engine_agreement"] = consistent

    if not consistent:
        result["warnings"].insert(
            0,
            "CROSS-ENGINE DISAGREEMENT: pyzbar and zxing-cpp read different data. "
            "This may indicate a damaged or manipulated barcode."
        )

    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({
        "status":   "ok",
        "pyzbar":   PYZBAR_OK,
        "zxingcpp": ZXING_OK,
    })


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    print("\n  AAMVA PDF417 Validator")
    print("  Running at http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
