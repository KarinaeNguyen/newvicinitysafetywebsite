from __future__ import annotations
from pathlib import Path

from PIL import Image, UnidentifiedImageError
import io

def load_image_safely(path: str | Path) -> Image.Image:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {path}")
    data = path.read_bytes()
    if len(data) == 0:
        raise ValueError(f"Image file is empty (0 bytes): {path}")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # force decode now
        # Check format
        if img.format not in ("PNG", "JPEG", "JPG"):
            raise ValueError(f"File is not a PNG or JPEG image: {path} (detected format: {img.format})")
        return img
    except UnidentifiedImageError as e:
        head = data[:32]
        raise ValueError(
            f"Pillow cannot decode image {path}.\nFirst 32 bytes: {head!r}\n"
            f"Common causes: downloaded HTML error page, PDF, or corrupt file."
        ) from e

def convert_to_clean_png(src: str | Path, dst: str | Path) -> Path:
    src, dst = Path(src), Path(dst)
    img = load_image_safely(src)

    # Normalize mode for PNG output
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG", optimize=True)
    return dst

# --- Use this in your pipeline ---
SRC = Path("export/vicinity_safety_logo.png")
CLEAN = Path("export/vicinity_safety_logo.clean.png")

try:
    img = load_image_safely(SRC)
except Exception as diag:
    print("Image load failed:", diag)
    # Optional: if it's some other known format, try conversion anyway:
    # CLEAN = convert_to_clean_png(SRC, CLEAN)
    raise
else:
    # If you need a guaranteed-good file for ReportLab/ImageReader:
    convert_to_clean_png(SRC, CLEAN)
    print("OK. Clean PNG at:", CLEAN)
