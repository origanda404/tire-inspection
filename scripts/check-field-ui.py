"""Read-only runtime preflight; does not start the camera or modify the model."""
import importlib
import json
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
report = {"python": sys.version, "platform": platform.platform(), "packages": {},
          "free_mb": shutil.disk_usage(ROOT).free // (1024 * 1024)}
for name in ["numpy", "PIL", "onnxruntime", "fastapi", "uvicorn", "multipart", "picamera2", "libcamera"]:
    try:
        module = importlib.import_module(name)
        report["packages"][name] = {"ok": True, "version": str(getattr(module, "__version__", "system"))}
    except Exception as exc:
        report["packages"][name] = {"ok": False, "error": str(exc)}
try:
    from inference.onnx_engine import OnnxEngine
    OnnxEngine()
    report["model_load"] = "passed (hash/class/input checks); no image inference in this check"
except Exception as exc:
    report["model_load"] = str(exc)
print(json.dumps(report, indent=2, ensure_ascii=False))
