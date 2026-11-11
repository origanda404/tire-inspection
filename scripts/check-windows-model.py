"""Integration check on existing research images; not independent accuracy evaluation."""
from pathlib import Path
import sys, json, hashlib, subprocess, os
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'inference'))
os.environ['YOLO_AUTOINSTALL']='false'
from inference_engine import inspect_single_view
from predict import find_default_model
import torch
from ultralytics import YOLO
OUT=R/'outputs/windows-check-2026-11-10'
INPUT=R/'data/input/smoke-2026-11-10'
torch.set_num_threads(4)
release=json.loads((R/'models/release.json').read_text())
assert find_default_model()==R/'models/production_yolo11n_cls.pt'
for name,h in release['sha256'].items():assert hashlib.sha256((R/'models'/name).read_bytes()).hexdigest()==h
results={}
for ext in ['pt','onnx']:
    model=YOLO(str(R/f'models/production_yolo11n_cls.{ext}'),task='classify')
    results[ext]=[inspect_single_view(model,p) for p in sorted(INPUT.glob('*.jpg'))]
assert len(results['pt'])==3
for a,b in zip(results['pt'],results['onnx']):
    assert set(a['scores'])==set(b['scores'])=={'Normal','Warning','Abnormal'}
    assert a['argmax_prediction']==b['argmax_prediction']
    assert a['safety_prediction']==b['safety_prediction']
    assert max(abs(a['scores'][k]-b['scores'][k]) for k in a['scores'])<=.001
results['note']='Compare exposed scores rounded to 4 decimals; tolerance 0.001. Three research images only.'
(OUT/'parity.json').write_text(json.dumps(results,indent=2))
commands=[['inference/predict.py','--image',str(INPUT/'Warning_26.jpg')],['inference/inference_engine.py','--input',str(INPUT),'--json-out',str(OUT/'mixed-images-plumbing-only.json')]]
for i,args in enumerate(commands):
    run=subprocess.run([sys.executable,*args],cwd=R,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    (OUT/f'cli-{i}.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0,run.stderr
assert json.loads((OUT/'mixed-images-plumbing-only.json').read_text())['total_views']==3
print('PASS: PT/ONNX decisions on 3 images; single-image CLI and multi-image JSON. Mixed images are NOT one tire.')
