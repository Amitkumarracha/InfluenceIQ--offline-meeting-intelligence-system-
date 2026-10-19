"""Explicit provisioning of pinned English/Hindi OCR data; never called during inference."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT

REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
BLOBS = {"eng": "bbef4675053b5b468cdb477053e28b1c698ba08e",
         "hin": "a8f0aaec09378115b12a2c6287c57695d082aea2"}
BASE = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{REVISION}/"


def provision(directory):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"repository": "https://github.com/tesseract-ocr/tessdata_fast",
                "revision": REVISION, "license": "Apache-2.0", "models": {}}
    for language, expected in BLOBS.items():
        target = directory / (language + ".traineddata")
        data = target.read_bytes() if target.is_file() else b""
        def blob(value):
            return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()
        if blob(data) != expected:
            with urllib.request.urlopen(BASE + target.name, timeout=60) as response:
                data = response.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024 or blob(data) != expected:
                raise RuntimeError("OCR model failed pinned content verification: " + language)
            temporary = target.with_suffix(".tmp")
            try:
                temporary.write_bytes(data)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        manifest["models"][language] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "git_blob": expected}
    if not (directory / "LICENSE").is_file():
        with urllib.request.urlopen(BASE + "LICENSE", timeout=30) as response:
            (directory / "LICENSE").write_bytes(response.read(100000))
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    provision(PROJECT_ROOT / "models/tesseract")
