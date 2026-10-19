"""Optional local Tesseract OCR for embedded slide images; no runtime downloads."""
from __future__ import annotations
from dataclasses import dataclass
import io
from pathlib import Path
import re
import shutil
import subprocess
from src.utils.config import PROJECT_ROOT, get


@dataclass
class OCRResult:
    source: str
    slide_id: str
    image_index: int
    text: str
    confidence: float | None


def _settings():
    languages = str(get("ppt.ocr_languages", "eng+hin"))
    if not re.fullmatch(r"[a-zA-Z0-9_]+(?:\+[a-zA-Z0-9_]+)*", languages):
        raise ValueError("Invalid OCR language names")
    directory = Path(get("ppt.ocr_model_dir", "models/tesseract"))
    return languages, directory if directory.is_absolute() else PROJECT_ROOT/directory


def _ocr_available() -> bool:
    languages, directory = _settings()
    return bool(get("ppt.ocr_enabled", False) and shutil.which("tesseract")
                and all((directory/(language+".traineddata")).is_file() for language in languages.split("+")))


def is_ocr_enabled() -> bool:
    return _ocr_available()


def _ocr_image_bytes(image_bytes: bytes) -> tuple[str, float | None]:
    from PIL import Image, ImageOps
    if len(image_bytes) > 20*1024*1024:
        raise ValueError("Slide image exceeds the OCR byte limit")
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.width*image.height > 16_000_000:
            raise ValueError("Slide image exceeds the OCR pixel limit")
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
    languages, directory = _settings()
    try:
        result = subprocess.run(["tesseract", "stdin", "stdout", "--tessdata-dir", str(directory),
            "-l", languages, "--oem", "1", "--psm", "11"], input=encoded.getvalue(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Offline slide OCR failed or timed out; native text and original slides are retained") from error
    return result.stdout.decode("utf-8").strip(), None


def extract_ocr_text(slide_id: str, image_bytes_list: list[bytes]) -> list[OCRResult]:
    if not get("ppt.ocr_enabled", False):
        return []
    if not _ocr_available():
        raise RuntimeError("Install Tesseract and run scripts/download_ocr_models.py before enabling slide OCR")
    results = []
    for index, image in enumerate(image_bytes_list):
        text, confidence = _ocr_image_bytes(image)
        if text:
            results.append(OCRResult("ocr", slide_id, index, text, confidence))
    return results
