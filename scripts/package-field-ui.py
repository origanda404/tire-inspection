"""Build an explicit allowlist bundle: no runtime data, history or environment."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
paths = ["requirements-ui.txt", "requirements-pi.txt", "docs/FIELD_UI_RUNBOOK.md",
         "scripts/check-field-ui.py", "scripts/diagnose-camera.py", "docs/FIXES_2026-11-14.md", "inference/onnx_engine.py", "models/release.json",
         "models/production_yolo11n_cls.onnx", "ui/index.html", "ui/app.css", "ui/app.js",
         "field_app/__init__.py", "field_app/server.py", "field_app/camera.py"]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", default="outputs/field-ui-pi-2026-11-14.zip")
args = parser.parse_args()
destination = ROOT / args.output
destination.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    hashes = {}
    for relative in paths:
        source = ROOT / relative
        hashes[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
        archive.write(source, relative)
    archive.writestr("bundle-manifest.json", json.dumps(hashes, indent=2))
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
print(destination)
print("SHA256", hashlib.sha256(destination.read_bytes()).hexdigest())
