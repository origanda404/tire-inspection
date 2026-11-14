import io
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from field_app.server import create_app
from inference.onnx_engine import OnnxEngine

HEADERS = {"X-Tire-Client": "field-ui"}
ROOT = Path(__file__).resolve().parents[1]


class OfflineCamera:
    device = None
    def start(self):
        raise RuntimeError("Camera disconnected")
    def jpeg(self):
        raise RuntimeError("Camera disconnected")
    def close(self):
        pass


class FieldAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = OnnxEngine()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(self.tmp.name, engine_factory=lambda: self.engine, camera=OfflineCamera())
        self.client = TestClient(self.app, headers=HEADERS)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def new(self, source="upload"):
        response = self.client.post('/api/sessions', json={"tire_id":"T-01", "operator":"3R", "source":source})
        self.assertEqual(response.status_code, 200)
        return response.json()['id']

    def upload(self, sid):
        image = Path(self.tmp.name) / 'synthetic.png'
        Image.new('RGB', (321, 173), (80, 90, 100)).save(image)
        with image.open('rb') as f:
            response = self.client.post(f'/api/sessions/{sid}/images', files={'file':('sample.jpg',f,'image/jpeg')})
        self.assertEqual(response.status_code, 200, response.text)
        return image, response.json()

    def analyze(self, sid):
        response = self.client.post(f'/api/sessions/{sid}/analyze')
        self.assertEqual(response.status_code, 200)
        for _ in range(200):
            item = self.client.get(f'/api/sessions/{sid}').json()
            if item['status'] != 'analyzing':
                return item
            time.sleep(.05)
        self.fail('Analysis timed out')

    def test_real_model_roundtrip_export_and_reopen(self):
        sid = self.new()
        image, _ = self.upload(sid)
        item = self.analyze(sid)
        self.assertEqual(item['status'], 'review', item)
        expected = self.engine.inspect(image)
        self.assertEqual(item['report']['views'][0]['scores'], expected['scores'])
        self.assertEqual(item['report']['overall_condition'], expected['safety_prediction'])
        self.assertEqual(item['coverage_status'], 'unverified')
        self.assertEqual(item['review']['inspector_label'], '')
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/finalize').status_code, 200)
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/finalize').status_code, 200)
        self.assertEqual(self.client.put(f'/api/sessions/{sid}/review', json={'notes':'overwrite'}).status_code,409)
        archive = self.client.get(f'/api/sessions/{sid}/export')
        self.assertEqual(archive.status_code,200)
        with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
            self.assertIn('results.csv', z.namelist())
            saved=json.loads(z.read('session.json'))
            self.assertEqual(saved['status'],'final')
            self.assertEqual(len([x for x in z.namelist() if x.startswith('images/')]),1)
        with TestClient(create_app(self.tmp.name,camera=OfflineCamera()),headers=HEADERS) as reopened:
            self.assertEqual(reopened.get(f'/api/sessions/{sid}').json()['status'],'final')

    def test_camera_preview_reconnect_capture_diagnostics(self):
        from field_app.camera import PiCamera
        from test_review_fixes import Device
        camera = PiCamera(Device)
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(directory, engine_factory=lambda: self.engine, camera=camera)
            with TestClient(app, headers=HEADERS) as client:
                self.assertEqual(client.post('/api/camera/reconnect').status_code, 200)
                response = client.get('/api/camera/preview')
                self.assertEqual(response.status_code, 200, response.text[:100])
                self.assertIn('x-frame-sequence', response.headers)
                self.assertEqual(Image.open(io.BytesIO(response.content)).size, (640,480))
                diagnostics = client.get('/api/camera/diagnostics').json()
                self.assertEqual(diagnostics['properties']['Model'], 'test')
                self.assertIn('field_app/camera.py', diagnostics['software_sha256'])
                sid = client.post('/api/sessions', json={
                    'tire_id':'camera-test','operator':'test','source':'camera'}).json()['id']
                item = client.post(f'/api/sessions/{sid}/capture').json()
                self.assertEqual(len(item['images']), 1)
                view = item['images'][0]
                image = client.get(f'/api/sessions/{sid}/images/{view["id"]}')
                self.assertEqual(Image.open(io.BytesIO(image.content)).size, (1280,960))
                self.assertIn('camera_configuration', view['camera_metadata'])
                old = camera.device
                self.assertEqual(client.post('/api/camera/reconnect').status_code, 200)
                self.assertTrue(old.closed)
                self.assertIsNot(camera.device, old)

    def test_bad_inputs_camera_and_cross_origin(self):
        sid=self.new()
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/analyze').status_code,422)
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/finalize').status_code,409)
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/images',files={'file':('bad.jpg',b'bad')}).status_code,422)
        self.assertEqual(self.client.get(f'/api/sessions/{sid}').json()['images'],[])
        self.assertEqual(self.client.post('/api/camera/start').status_code,503)
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/capture').status_code,409)
        self.assertEqual(self.client.post('/api/model/load',headers={'Origin':'https://other.example'}).status_code,403)

    def test_missing_image_never_finalizes(self):
        sid=self.new()
        _,item=self.upload(sid)
        self.analyze(sid)
        (Path(self.tmp.name)/item['images'][0]['path']).unlink()
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/finalize').status_code,409)
        self.assertEqual(self.client.get(f'/api/sessions/{sid}/export').status_code,409)
        item=self.analyze(sid)
        self.assertEqual(item['status'],'error')
        self.assertIsNone(item['report'])

    def test_recovery_and_review_validation(self):
        sid=self.new()
        self.upload(sid)
        self.analyze(sid)
        self.client.put(f'/api/sessions/{sid}/review',json={'inspector_label':'Warning'})
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/finalize').status_code,422)
        item=self.app.state.store.get(sid)
        item['status']='analyzing'
        self.app.state.store.put(item)
        with TestClient(create_app(self.tmp.name,camera=OfflineCamera()),headers=HEADERS) as reopened:
            item=reopened.get(f'/api/sessions/{sid}').json()
            self.assertEqual(item['status'],'error')
            self.assertIsNone(item['report'])
            self.assertEqual(len(item['images']),1)


if __name__=='__main__':
    unittest.main()
