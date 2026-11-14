"""One camera owner, bounded waits and latest-frame preview (no frame backlog)."""
import io
import json
import threading
import time
from importlib.metadata import version, PackageNotFoundError

from PIL import Image


class PiCamera:
    CAPTURE_TIMEOUT = 2.0
    FRAME_TIMEOUT = 3.0
    PREVIEW_PERIOD = 0.1

    def __init__(self, device_factory=None):
        self.lock = threading.RLock()  # lifecycle only, never held by HTTP frame readers
        self.condition = threading.Condition()
        self.device = None
        self.factory = device_factory
        self.worker = None
        self.stop_event = threading.Event()
        self.generation = 0
        self.sequence = 0
        self.frame = None
        self.error = ''
        self.active_until = 0
        self.configuration = {}
        self.properties = {}

    def start(self):
        with self.lock:
            if self.device is not None and self.worker and self.worker.is_alive() and not self.error:
                return
            self._close()
            self._open()

    def restart(self):
        with self.lock:
            self._close()
            self._open()

    def _open(self):
        if self.factory is None:
            from picamera2 import Picamera2
            device = Picamera2()
        else:
            device = self.factory()
        try:
            controls = {'FrameDurationLimits': (66666, 66666)}  # 15fps sensor target, verify on Pi
            if 'AfMode' in device.camera_controls:
                from libcamera import controls as lc_controls
                controls['AfMode'] = lc_controls.AfModeEnum.Continuous
            config = device.create_preview_configuration(
                main={'size': (1280, 960), 'format': 'BGR888'},
                raw=None, buffer_count=4, queue=False, controls=controls)
            device.configure(config)
            device.start()
            with self.condition:
                self.device = device
                self.configuration = json.loads(json.dumps(device.camera_configuration(), default=str))
                self.properties = json.loads(json.dumps(device.camera_properties, default=str))
                self.error = ''
                self.frame = None
                self.stop_event.clear()
                self.active_until = time.monotonic() + 1
                self.worker = threading.Thread(target=self._produce, args=(device,), daemon=True,
                                               name='tire-camera')
                self.worker.start()
        except Exception:
            device.close()
            self.device = None
            raise

    def _capture_request(self, device):
        # A timed-out synchronous capture can still complete later and retain a
        # camera buffer. The callback releases late results instead of leaking them.
        ready = threading.Event()
        guard = threading.Lock()
        result = {}
        abandoned = False

        def completed(job):
            try:
                request = device.wait(job)
            except Exception as exc:
                with guard:
                    result['error'] = exc
                    ready.set()
                return
            with guard:
                if abandoned:
                    request.release()
                else:
                    result['request'] = request
                ready.set()

        device.capture_request(wait=False, signal_function=completed, flush=True)
        if not ready.wait(self.CAPTURE_TIMEOUT):
            with guard:
                abandoned = True
                late = result.pop('request', None)
            if late is not None:
                late.release()
            raise TimeoutError('Timed out waiting for a camera frame')
        if 'error' in result:
            raise result['error']
        return result['request']

    def _produce(self, device):
        try:
            while not self.stop_event.is_set():
                with self.condition:
                    while time.monotonic() >= self.active_until and not self.stop_event.is_set():
                        self.condition.wait()
                if self.stop_event.is_set():
                    break
                started = time.monotonic()
                # flush requests a frame exposed after this call. Always release its buffer.
                request = self._capture_request(device)
                try:
                    full = request.make_image('main').copy()
                    metadata = json.loads(json.dumps(request.get_metadata(), default=str))
                finally:
                    request.release()
                preview = full.resize((640, 480), Image.Resampling.BILINEAR)
                output = io.BytesIO()
                preview.save(output, format='JPEG', quality=75)
                finished = time.monotonic()
                metadata['camera_configuration'] = self.configuration
                metadata['camera_properties'] = self.properties
                metadata['capture_pipeline_ms'] = round((finished - started) * 1000, 1)
                with self.condition:
                    if self.stop_event.is_set():
                        break
                    self.sequence += 1
                    self.frame = (self.sequence, full, output.getvalue(), metadata, finished, started)
                    self.condition.notify_all()
                self.stop_event.wait(max(0, self.PREVIEW_PERIOD - (time.monotonic() - started)))
        except Exception as exc:
            with self.condition:
                self.error = str(exc) or type(exc).__name__
                self.frame = None  # Never display an old image as a healthy live feed.
                self.condition.notify_all()

    def _read(self, fresh=False):
        requested = time.monotonic()
        deadline = requested + self.FRAME_TIMEOUT
        with self.condition:
            generation = self.generation
            self.active_until = deadline
            self.condition.notify_all()
            while True:
                if generation != self.generation or self.device is None or self.stop_event.is_set():
                    raise RuntimeError('กล้องยังไม่เปิดหรือกำลังเชื่อมต่อใหม่')
                if self.error:
                    raise RuntimeError('กล้องขัดข้อง กรุณาเชื่อมต่อใหม่: ' + self.error)
                frame = self.frame
                if frame and time.monotonic() - frame[4] < 1 and (not fresh or frame[5] >= requested):
                    self.active_until = time.monotonic() + 0.5
                    return frame
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('กล้องไม่ส่งภาพภายในเวลาที่กำหนด กรุณาเชื่อมต่อใหม่')
                self.condition.wait(remaining)

    def preview(self):
        frame = self._read()
        return frame[2], {'sequence': frame[0], 'age_ms': round((time.monotonic() - frame[4]) * 1000, 1)}

    def jpeg(self):
        # A full-size frame requested after the user's capture, never a preview JPEG.
        frame = self._read(fresh=True)
        output = io.BytesIO()
        frame[1].save(output, format='JPEG', quality=90)
        metadata = dict(frame[3], frame_sequence=frame[0], colour_processing='Picamera2 RGB; no inversion')
        return output.getvalue(), metadata

    def diagnostics(self):
        with self.condition:
            frame = self.frame
            try:
                package_version = version('picamera2')
            except PackageNotFoundError:
                package_version = 'not installed as a Python distribution'
            return {'open': self.device is not None, 'error': self.error,
                    'worker_alive': bool(self.worker and self.worker.is_alive()),
                    'picamera2_version': package_version, 'configuration': self.configuration,
                    'properties': self.properties, 'sequence': frame[0] if frame else None,
                    'frame_age_ms': round((time.monotonic() - frame[4]) * 1000, 1) if frame else None,
                    'metadata': frame[3] if frame else None,
                    'preview_size': [640, 480], 'capture_size': [1280, 960],
                    'colour_processing': 'Picamera2 make_image; no channel swap or inversion'}

    def _close(self):
        with self.condition:
            self.generation += 1
            self.stop_event.set()
            self.frame = None
            self.condition.notify_all()
        if self.worker:
            self.worker.join(timeout=self.FRAME_TIMEOUT + 1)
            if self.worker.is_alive():
                raise RuntimeError('กล้องหยุดไม่สำเร็จ กรุณาปิดและเปิดโปรแกรมใหม่')
        device = self.device
        try:
            if device is not None:
                try:
                    device.stop()
                finally:
                    device.close()
        finally:
            with self.condition:
                self.device = None
                self.worker = None
                self.frame = None
                self.condition.notify_all()

    def close(self):
        with self.lock:
            self._close()
