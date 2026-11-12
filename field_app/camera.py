"""One owner for Pi camera. No motor control and no coverage assumptions."""
import io
import threading


class PiCamera:
    def __init__(self):
        self.lock = threading.Lock()
        self.device = None

    def start(self):
        with self.lock:
            if self.device is not None:
                return
            from picamera2 import Picamera2
            device = Picamera2()
            try:
                device.configure(device.create_still_configuration(main={"size": (1280, 960)}))
                device.start()
                self.device = device
            except Exception:
                device.close()
                raise

    def jpeg(self):
        with self.lock:
            if self.device is None:
                raise RuntimeError("กล้องยังไม่เปิด กดเปิดกล้องก่อน")
            output = io.BytesIO()
            metadata = self.device.capture_file(output, format="jpeg")
            return output.getvalue(), {k: str(v) for k, v in (metadata or {}).items()}

    def close(self):
        with self.lock:
            if self.device is not None:
                try:
                    self.device.stop()
                finally:
                    self.device.close()
                    self.device = None
