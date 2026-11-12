"""Windows compatibility evidence, not model accuracy or Pi performance."""
import argparse, hashlib, json, sys, platform, importlib.metadata
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'inference'))
from onnx_engine import OnnxEngine, preprocess, decide, aggregate_whole_tire, collect_files
from inference_engine import inspect_single_view
import torch
from ultralytics import YOLO

parser = argparse.ArgumentParser()
parser.add_argument('--images', default=str(R / 'data/input/smoke-2026-11-10'))
parser.add_argument('--output', default=str(R / 'outputs/onnx-runner-check-2026-11-13'))
args = parser.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
files = sorted(p for p in Path(args.images).rglob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
# Deduplicate identical files (full_dataset may repeat train/val copies).
unique = {}
for p in files:
    unique.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), p)
files = list(unique.values())
assert files, 'No test images'
synthetic = out / 'synthetic'
synthetic.mkdir(exist_ok=True)
for name, size, mode in [('portrait',(91,317),'RGB'),('landscape',(419,103),'RGB'),('grey',(55,99),'L'),('alpha',(333,75),'RGBA')]:
    a = np.random.default_rng(42).integers(0,256,(size[1],size[0],4),dtype=np.uint8)
    Image.fromarray(a, 'RGBA').convert(mode).save(synthetic / (name+'.png'))
im = Image.open(synthetic / 'landscape.png'); exif=im.getexif(); exif[274]=6
im.save(synthetic/'rotated.jpg',exif=exif)
files += sorted(synthetic.iterdir())
torch.set_num_threads(4)
engine=OnnxEngine()
models={ext: YOLO(str(R/f'models/production_yolo11n_cls.{ext}'), task='classify') for ext in ['pt','onnx']}
rows=[]
for p in files:
    raw=engine.probabilities(p)
    references={}
    for ext,model in models.items():
        with Image.open(p) as im:
            padded=ImageOps.pad(ImageOps.exif_transpose(im).convert('RGB'),(224,224),method=Image.Resampling.LANCZOS,color=(114,114,114))
        result=model.predict(padded,imgsz=224,device='cpu',verbose=False)[0]
        scores={result.names[i]:float(result.probs.data[i]) for i in range(3)}
        error=max(abs(raw[k]-scores[k]) for k in raw)
        assert error <= 1e-5, (str(p),ext,error)
        assert decide(raw)[0] == decide(scores)[0]
        assert max(raw,key=raw.get)==result.names[result.probs.top1]
        references[ext]={'scores':scores,'max_abs_error':error}
    rows.append({'image':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'onnx_direct':raw,'decision':decide(raw)[0],'references':references})
# Boundary tests guard priority, >= behavior and the Normal fallback.
for scores,expected in [({'Abnormal':.25,'Warning':.35,'Normal':.4},'Abnormal'),({'Abnormal':.249,'Warning':.35,'Normal':.401},'Warning'),({'Abnormal':.249,'Warning':.349,'Normal':.402},'Normal')]:
    assert decide(scores)[0]==expected
try:
    collect_files(str(files[0])+','+str(out/'missing.jpg'))
except FileNotFoundError:
    pass
else:
    raise AssertionError('Missing input silently accepted')
assert aggregate_whole_tire([{'safety_prediction':s,'filename':s,'latency_ms':1} for s in ['Normal','Warning','Abnormal']])['overall_condition']=='Abnormal'
summary={'platform':platform.platform(),'python':sys.version,'versions':{k:importlib.metadata.version(k) for k in ['onnxruntime','numpy','Pillow','torch','ultralytics']},'image_count':len(rows),'synthetic_count':5,'max_abs_error':max(v['max_abs_error'] for r in rows for v in r['references'].values()),'decisions_match':True,'pi_verified':False,'note':'Research and synthetic compatibility checks only, not independent accuracy or Pi timing','rows':rows}
(out/'parity.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
