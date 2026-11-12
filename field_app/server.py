"""Single-process, loopback-only field-trial server."""
import csv
import hashlib
import io
import json
import os
import shutil
import sqlite3
import threading
import tempfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
from PIL import Image

from field_app.camera import PiCamera

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE = 20 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


class NewSession(BaseModel):
    tire_id: str = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=100)
    source: Literal["camera", "upload"] = "camera"


class Review(BaseModel):
    inspector_label: Literal["", "Normal", "Warning", "Abnormal"] = ""
    inspector: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=4000)


class Store:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "sessions.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        # Interrupted analysis has no complete report and must be explicitly retried.
        for item in self.all():
            if item["status"] == "analyzing":
                item.update(status="error", error="โปรแกรมหยุดระหว่างวิเคราะห์ กรุณาวิเคราะห์ใหม่", report=None)
                self.put(item)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=15)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def put(self, item):
        item["updated_at"] = now()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?)",
                       (item["id"], json.dumps(item, ensure_ascii=False)))

    def get(self, sid):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM sessions WHERE id=?", (sid,)).fetchone()
        if not row:
            raise HTTPException(404, "ไม่พบรอบตรวจ")
        return json.loads(row[0])

    def all(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM sessions")]


def create_app(data_dir=None, engine_factory=None, camera=None):
    store = Store(data_dir or os.environ.get("TIRE_DATA_DIR", ROOT / "data/field-runtime"))
    lock = threading.RLock()
    camera = camera or PiCamera()
    pool = ThreadPoolExecutor(max_workers=1)
    engine = None
    engine_error = ""
    busy = False
    release = json.loads((ROOT / "models/release.json").read_text(encoding="utf-8"))

    def load_engine():
        nonlocal engine, engine_error
        if engine is None:
            try:
                if engine_factory is None:
                    from inference.onnx_engine import OnnxEngine
                    engine = OnnxEngine()
                else:
                    engine = engine_factory()
                engine_error = ""
            except Exception as exc:
                engine_error = str(exc)
                raise
        return engine

    @asynccontextmanager
    async def lifespan(app):
        yield
        pool.shutdown(wait=True)
        camera.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store = store

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # Browser-origin and DNS-rebinding guard. No LAN service in this release.
        if request.url.hostname not in {"localhost", "127.0.0.1", "testserver"}:
            return JSONResponse({"detail": "Local access only"}, status_code=403)
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("x-tire-client") != "field-ui":
                return JSONResponse({"detail": "Missing application header"}, status_code=403)
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin request refused"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(OSError)
    async def storage_failure(request, exc):
        return JSONResponse({"detail": "อ่าน/เขียนไฟล์ไม่สำเร็จ ตรวจพื้นที่และสิทธิ์: " + str(exc)}, status_code=503)

    @app.exception_handler(sqlite3.Error)
    async def db_failure(request, exc):
        return JSONResponse({"detail": "บันทึกฐานข้อมูลไม่สำเร็จ กรุณาลองใหม่"}, status_code=503)

    def editable(sid):
        item = store.get(sid)
        if item["status"] in {"analyzing", "final"}:
            raise HTTPException(409, "รอบนี้กำลังวิเคราะห์หรือยืนยันแล้ว ไม่สามารถแก้ไขได้")
        return item

    def validate_image(data):
        if not data or len(data) > MAX_IMAGE:
            raise HTTPException(413, "ภาพต้องมีข้อมูลและขนาดไม่เกิน 20 MB")
        try:
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in {"JPEG", "PNG"} or im.width * im.height > 25_000_000:
                    raise ValueError("รองรับ JPEG/PNG ไม่เกิน 25 ล้านพิกเซล")
                extension = ".jpg" if im.format == "JPEG" else ".png"
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                im.load()
        except Exception as exc:
            raise HTTPException(422, "ภาพอ่านไม่ได้: " + str(exc)) from exc
        return extension

    def add_image(item, data, name, metadata=None):
        extension = validate_image(data)
        if len(item["images"]) >= 100:
            raise HTTPException(409, "ถึงขีดจำกัดรุ่นทดลอง 100 ภาพต่อรอบ (ไม่ใช่เกณฑ์ครบวง)")
        if shutil.disk_usage(store.root).free < len(data) + 100 * 1024 * 1024:
            raise HTTPException(507, "พื้นที่ไม่พอ เก็บข้อมูลเดิมไว้แล้ว กรุณาสำรองข้อมูล")
        vid = uuid.uuid4().hex
        relative = f"{item['id']}/{vid}{extension}"
        target = store.root / relative
        target.parent.mkdir(exist_ok=True)
        temp = target.with_suffix(".tmp")
        with temp.open("wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temp.replace(target)
        item["images"].append(dict(id=vid, path=relative, name=name[:200], captured_at=now(),
                                   sha256=hashlib.sha256(data).hexdigest(), camera_metadata=metadata))
        item.update(status="draft", report=None, error="", completed=0)
        store.put(item)
        return item

    @app.get("/api/health")
    def health():
        return {"model_loaded": engine is not None, "model_error": engine_error,
                "camera_open": camera.device is not None, "busy": busy,
                "free_mb": shutil.disk_usage(store.root).free // (1024 * 1024),
                "model_version": release["version"]}

    @app.post("/api/model/load")
    def model_load():
        with lock:
            try:
                load_engine()
            except Exception as exc:
                raise HTTPException(503, "โหลดโมเดลไม่ได้: " + str(exc)) from exc
        return health()

    @app.post("/api/camera/start")
    def camera_start():
        try:
            camera.start()
        except Exception as exc:
            raise HTTPException(503, "เปิดกล้องไม่ได้: " + str(exc)) from exc
        return health()

    @app.get("/api/camera/preview")
    def preview():
        try:
            data, _ = camera.jpeg()
            return Response(data, media_type="image/jpeg")
        except Exception as exc:
            raise HTTPException(503, "อ่านภาพกล้องไม่ได้: " + str(exc)) from exc

    @app.get("/api/sessions")
    def sessions():
        with lock:
            return [{k: v for k, v in s.items() if k not in {"images", "report"}}
                    for s in sorted(store.all(), key=lambda s: s["updated_at"], reverse=True)]

    @app.post("/api/sessions")
    def new(body: NewSession):
        if not body.tire_id.strip() or not body.operator.strip():
            raise HTTPException(422, "กรอกรหัสยางและผู้บันทึก")
        with lock:
            item = dict(id=uuid.uuid4().hex, tire_id=body.tire_id.strip(), operator=body.operator.strip(),
                        source=body.source, created_at=now(), status="draft", images=[], report=None,
                        completed=0, error="", coverage_status="unverified", review=Review().model_dump(),
                        model_version=release["version"], model_sha256=release["sha256"]["production_yolo11n_cls.onnx"],
                        decision_policy=release["decision_policy"])
            store.put(item)
            return item

    @app.get("/api/sessions/{sid}")
    def get_session(sid: str):
        with lock:
            return store.get(sid)

    @app.post("/api/sessions/{sid}/images")
    def upload(sid: str, file: UploadFile):
        with lock:
            item = editable(sid)
            if item["source"] != "upload":
                raise HTTPException(409, "นำเข้าภาพได้เฉพาะรอบทดสอบไฟล์")
            return add_image(item, file.file.read(MAX_IMAGE + 1), file.filename or "image")

    @app.post("/api/sessions/{sid}/capture")
    def capture(sid: str):
        with lock:
            item = editable(sid)
            if item["source"] != "camera":
                raise HTTPException(409, "รอบนี้ใช้ภาพนำเข้า")
            try:
                data, metadata = camera.jpeg()
            except Exception as exc:
                raise HTTPException(503, "ถ่ายภาพไม่สำเร็จ: " + str(exc)) from exc
            return add_image(item, data, "Camera " + now(), metadata)

    @app.get("/api/sessions/{sid}/images/{vid}")
    def image(sid: str, vid: str):
        item = store.get(sid)
        view = next((v for v in item["images"] if v["id"] == vid), None)
        if view is None:
            raise HTTPException(404, "ไม่พบภาพ")
        path = store.root / view["path"]
        if not path.is_file():
            raise HTTPException(404, "ไฟล์ภาพหาย")
        return FileResponse(path)

    def analyze_job(sid):
        nonlocal busy
        try:
            from inference.onnx_engine import aggregate_whole_tire
            with lock:
                runner = load_engine()
            item = store.get(sid)
            results = []
            for view in item["images"]:
                path = store.root / view["path"]
                if hashlib.sha256(path.read_bytes()).hexdigest() != view["sha256"]:
                    raise ValueError("ภาพเปลี่ยนจากต้นฉบับที่เก็บไว้")
                result = runner.inspect(path)
                result.update(image=view["path"], view_id=view["id"])
                results.append(result)
                with lock:
                    current = store.get(sid)
                    current["completed"] = len(results)
                    store.put(current)
            report = aggregate_whole_tire(results)
            report["coverage_note"] = "ผลรวมจากภาพที่ส่งตรวจ ไม่ยืนยันตัวตนยางหรือความครบวง"
            report["timing_scope"] = "Image decode + preprocessing + inference; excludes model load, camera and UI"
            with lock:
                current = store.get(sid)
                current.update(status="review", report=report, error="")
                store.put(current)
        except Exception as exc:
            with lock:
                current = store.get(sid)
                current.update(status="error", report=None, error=str(exc))
                store.put(current)
        finally:
            with lock:
                busy = False

    @app.post("/api/sessions/{sid}/analyze")
    def analyze(sid: str):
        nonlocal busy
        with lock:
            item = editable(sid)
            if busy:
                raise HTTPException(409, "กำลังวิเคราะห์รอบอื่น กรุณารอ")
            if not item["images"]:
                raise HTTPException(422, "ยังไม่มีภาพสำหรับวิเคราะห์")
            if item["model_sha256"] != release["sha256"]["production_yolo11n_cls.onnx"]:
                raise HTTPException(409, "รุ่นโมเดลต่างจากตอนสร้างรอบ กรุณาสร้างรอบใหม่")
            item.update(status="analyzing", report=None, completed=0, error="")
            store.put(item)
            busy = True
            pool.submit(analyze_job, sid)
            return item

    @app.put("/api/sessions/{sid}/review")
    def review(sid: str, body: Review):
        with lock:
            item = editable(sid)
            item["review"] = body.model_dump()
            store.put(item)
            return item

    @app.post("/api/sessions/{sid}/finalize")
    def finalize(sid: str):
        with lock:
            item = store.get(sid)
            if item["status"] == "final":
                return item  # Idempotent after a lost response.
            if item["status"] != "review" or not item["report"]:
                raise HTTPException(409, "ต้องวิเคราะห์สำเร็จก่อนยืนยันบันทึก")
            if item["review"]["inspector_label"] and not item["review"]["inspector"].strip():
                raise HTTPException(422, "ระบุผู้ยืนยันผลคน หรือเว้นผลคนว่ายังไม่ยืนยัน")
            for view in item["images"]:
                path = store.root / view["path"]
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != view["sha256"]:
                    raise HTTPException(409, "ภาพต้นฉบับหายหรือเปลี่ยน ยังยืนยันบันทึกไม่ได้")
            item.update(status="final", finalized_at=now())
            store.put(item)
            return item

    @app.get("/api/sessions/{sid}/export")
    def export(sid: str):
        with lock:
            item = store.get(sid)
            for view in item["images"]:
                path = store.root / view["path"]
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != view["sha256"]:
                    raise HTTPException(409, "ส่งออกไม่ได้: ภาพต้นฉบับหายหรือเปลี่ยน")
            export_dir = store.root / "exports"
            export_dir.mkdir(exist_ok=True)
            handle, export_name = tempfile.mkstemp(suffix=".zip", dir=export_dir)
            os.close(handle)
            with zipfile.ZipFile(export_name, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("session.json", json.dumps(item, ensure_ascii=False, indent=2))
                table = io.StringIO(newline="")
                writer = csv.writer(table)
                writer.writerow(["session_id", "tire_id", "view_id", "AI", "Normal", "Warning", "Abnormal", "inspector_label", "inspector"])
                def safe(value):
                    value = str(value)
                    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
                for view in (item.get("report") or {}).get("views", []):
                    writer.writerow([safe(x) for x in [sid, item["tire_id"], view["view_id"], view["safety_prediction"],
                                     view["scores"]["Normal"], view["scores"]["Warning"], view["scores"]["Abnormal"],
                                     item["review"]["inspector_label"], item["review"]["inspector"]]])
                archive.writestr("results.csv", "\ufeff" + table.getvalue())
                for view in item["images"]:
                    archive.write(store.root / view["path"], "images/" + Path(view["path"]).name)
            return FileResponse(export_name, media_type="application/zip", filename=f"inspection-{sid}.zip",
                                background=BackgroundTask(Path(export_name).unlink, missing_ok=True))

    app.mount("/", StaticFiles(directory=ROOT / "ui", html=True), name="ui")
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8765, workers=1)
