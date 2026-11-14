import io
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from field_app.camera import PiCamera
from inference.input_contract import classifier_scores, collect_files
from inference.inference_engine import inspect_single_view


class Request:
    def __init__(self, device):
        self.device = device
    def make_image(self, name):
        im = Image.new('RGB', (1280, 960), 'white')
        im.paste('black', (640, 0, 1280, 960))
        return im
    def get_metadata(self):
        return {'SensorTimestamp': time.monotonic_ns(), 'ExposureTime': 1000}
    def release(self):
        self.device.released += 1


class Device:
    camera_controls = {}
    camera_properties = {'Model': 'test'}
    def __init__(self):
        self.failed = False
        self.closed = False
        self.released = 0
        self.calls = 0
    def create_preview_configuration(self, **kw):
        return kw
    def configure(self, config):
        self.config = config
    def camera_configuration(self):
        return self.config
    def start(self):
        pass
    def capture_request(self, **kwargs):
        self.calls += 1
        if self.failed:
            raise RuntimeError('disconnected')
        time.sleep(.005)
        request = Request(self)
        kwargs['signal_function'](request)
        return request
    def wait(self, job):
        return job
    def stop(self):
        pass
    def close(self):
        self.closed = True


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.devices = []
        def factory():
            device = Device()
            self.devices.append(device)
            return device
        self.camera = PiCamera(factory)
        self.camera.start()
    def tearDown(self):
        self.camera.close()
    def test_preview_capture_size_colour_and_cached_reads(self):
        preview, info = self.camera.preview()
        before = self.devices[0].calls
        for _ in range(10):
            self.camera.preview()
        self.assertLessEqual(self.devices[0].calls - before, 1)
        capture, metadata = self.camera.jpeg()
        self.assertGreater(metadata['frame_sequence'], info['sequence'])
        for data, size in ((preview, (640,480)), (capture,(1280,960))):
            with Image.open(io.BytesIO(data)) as im:
                self.assertEqual(im.size, size)
                self.assertGreater(im.getpixel((size[0]//4,20))[0], 245)
                self.assertLess(im.getpixel((size[0]*3//4,20))[0], 10)
        self.assertGreater(self.devices[0].released, 0)
    def test_reconnect_replaces_failed_device_and_rejects_stale_frame(self):
        self.camera.preview()
        old = self.devices[0]
        old.failed = True
        deadline = time.monotonic() + 2
        while not self.camera.error and time.monotonic() < deadline:
            time.sleep(.01)
        with self.assertRaisesRegex(RuntimeError, 'disconnected'):
            self.camera.preview()
        self.camera.restart()
        self.assertTrue(old.closed)
        self.assertIsNot(self.camera.device, old)
        self.assertTrue(self.camera.preview()[0])
    def test_close_wakes_readers_and_reopen(self):
        self.camera.close()
        with self.assertRaises(RuntimeError):
            self.camera.jpeg()
        self.camera.start()
        self.assertTrue(self.camera.preview()[0])
    def test_timed_out_capture_releases_late_camera_buffer(self):
        camera = PiCamera()
        camera.CAPTURE_TIMEOUT = .01
        class LateDevice(Device):
            def capture_request(self, **kwargs):
                self.timer = threading.Timer(.05, lambda: kwargs['signal_function'](Request(self)))
                self.timer.start()
        device = LateDevice()
        with self.assertRaises(TimeoutError):
            camera._capture_request(device)
        device.timer.join(timeout=1)
        self.assertEqual(device.released, 1)

    def test_read_timeout_is_bounded(self):
        self.camera.close()
        # A device which never publishes frames must not block HTTP indefinitely.
        self.camera.device = Device()
        self.camera.stop_event.clear()
        self.camera.FRAME_TIMEOUT = .03
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            self.camera.preview()
        self.assertLess(time.monotonic() - start, .5)


class InputTests(unittest.TestCase):
    def test_missing_list_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            present = Path(tmp)/'ok.JPG'
            present.touch()
            self.assertEqual(collect_files(tmp), [present])
            with self.assertRaises(FileNotFoundError):
                collect_files(str(present)+','+str(Path(tmp)/'missing.jpg'))
            with self.assertRaises(ValueError):
                collect_files(str(present)+',')
    def test_invalid_classes_or_probabilities_rejected(self):
        def result(names, values):
            return SimpleNamespace(names=names, probs=SimpleNamespace(data=values))
        names = {0:'Abnormal',1:'Normal',2:'Warning'}
        for item in [result({0:'cat',1:'dog',2:'bird'},[.2,.6,.2]),
                     result(names,[float('nan'),.6,.4]), result(names,[.1,.1,.1]),
                     result(names,[-.1,.8,.3]), result(names,[.5,.5])]:
            with self.assertRaises(ValueError):
                classifier_scores(item)
        self.assertEqual(classifier_scores(result(names,[.1,.7,.2]))['Normal'], .7)
    def test_legacy_inspection_rejects_wrong_model_and_keeps_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp)/'test.png'
            Image.new('RGB',(20,20)).save(image)
            class Model:
                def __init__(self, names, values):
                    self.result = SimpleNamespace(names=names, probs=SimpleNamespace(data=values,top1=1))
                def predict(self,*args,**kwargs):
                    return [self.result]
            with self.assertRaises(ValueError):
                inspect_single_view(Model({0:'cat',1:'dog',2:'bird'},[.1,.8,.1]),image)
            names={0:'Abnormal',1:'Normal',2:'Warning'}
            for values,expected in [([.25,.4,.35],'Abnormal'),([.1,.55,.35],'Warning'),([.1,.7,.2],'Normal')]:
                self.assertEqual(inspect_single_view(Model(names,values),image)['safety_prediction'],expected)
