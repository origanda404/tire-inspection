"""CPU-only ONNX runner. Same packaged model, preprocessing and decision policy."""
import argparse
import ast
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SEVERITY = {'Normal': 0, 'Warning': 1, 'Abnormal': 2}
REV_SEVERITY = {v: k for k, v in SEVERITY.items()}

def preprocess(path):
    # Match the original EXIF correction and grey padding. Its subsequent
    # Ultralytics resize/crop is a no-op on this already square 224px image.
    with Image.open(path) as im:
        im = ImageOps.pad(ImageOps.exif_transpose(im).convert('RGB'),
                          (224, 224), method=Image.Resampling.LANCZOS,
                          color=(114, 114, 114))
    return np.ascontiguousarray(np.asarray(im, dtype=np.float32).transpose(2, 0, 1)[None] / np.float32(255))

def decide(scores):
    # Preserve priority and inclusive boundaries, using unrounded probabilities.
    if scores['Abnormal'] >= .25:
        return 'Abnormal', f"P(Abnormal)={scores['Abnormal']*100:.1f}% >= 25%"
    if scores['Warning'] >= .35:
        return 'Warning', f"P(Warning)={scores['Warning']*100:.1f}% >= 35%"
    return 'Normal', f"P(Normal)={scores['Normal']*100:.1f}% dominant"

class OnnxEngine:
    def __init__(self):
        model = ROOT / 'models/production_yolo11n_cls.onnx'
        release = json.loads((ROOT / 'models/release.json').read_text(encoding='utf-8'))
        if hashlib.sha256(model.read_bytes()).hexdigest() != release['sha256'][model.name]:
            raise ValueError('Model hash differs from the approved release')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model), sess_options=options, providers=['CPUExecutionProvider'])
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or inputs[0].shape != [1, 3, 224, 224] or inputs[0].type != 'tensor(float)':
            raise ValueError('Unexpected model input contract')
        self.input_name = inputs[0].name
        self.names = ast.literal_eval(self.session.get_modelmeta().custom_metadata_map['names'])
        if self.names != {0: 'Abnormal', 1: 'Normal', 2: 'Warning'}:
            raise ValueError('Unexpected model class mapping')

    def probabilities(self, path):
        tensor = preprocess(path)
        values = np.asarray(self.session.run(None, {self.input_name: tensor})[0])
        # The exported classifier already returns softmax probabilities.
        # Applying softmax again would change scores and threshold decisions.
        if values.shape != (1, 3) or not np.isfinite(values).all():
            raise ValueError('Invalid model output')
        if (values < 0).any() or (values > 1).any() or abs(float(values.sum()) - 1) > 1e-4:
            raise ValueError('Output is not a probability distribution')
        return {self.names[i]: float(values[0, i]) for i in range(3)}

    def inspect(self, path):
        start = time.perf_counter()
        scores = self.probabilities(path)
        elapsed = (time.perf_counter() - start) * 1000
        prediction, reason = decide(scores)
        return dict(image=str(path), filename=Path(path).name,
                    latency_ms=round(elapsed, 1),
                    scores={k: round(v, 4) for k, v in scores.items()},
                    argmax_prediction=max(scores, key=scores.get),
                    safety_prediction=prediction, reason=reason)

def aggregate_whole_tire(view_results):
    if not view_results:
        return {'status': 'No views provided', 'overall_condition': 'Unknown'}

    max_sev = max(SEVERITY[v['safety_prediction']] for v in view_results)
    overall_condition = REV_SEVERITY[max_sev]

    abnormal_views = [v['filename'] for v in view_results if v['safety_prediction'] == 'Abnormal']
    warning_views = [v['filename'] for v in view_results if v['safety_prediction'] == 'Warning']
    normal_views = [v['filename'] for v in view_results if v['safety_prediction'] == 'Normal']

    avg_lat = sum(v['latency_ms'] for v in view_results) / len(view_results)
    total_lat = sum(v['latency_ms'] for v in view_results)

    summary_note = []
    if abnormal_views:
        summary_note.append(f"Abnormal condition detected in {len(abnormal_views)} view(s): {', '.join(abnormal_views[:3])}")
    if warning_views:
        summary_note.append(f"Wear/Warning detected in {len(warning_views)} view(s): {', '.join(warning_views[:3])}")
    if not abnormal_views and not warning_views:
        summary_note.append("All views evaluated as Normal condition.")

    return dict(
        total_views=len(view_results),
        overall_condition=overall_condition,
        summary_note=" | ".join(summary_note),
        abnormal_views_count=len(abnormal_views),
        warning_views_count=len(warning_views),
        normal_views_count=len(normal_views),
        total_latency_ms=round(total_lat, 1),
        avg_latency_ms=round(avg_lat, 1),
        views=view_results
    )

def collect_files(value):
    path = Path(value)
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
    else:
        files = [path] if path.is_file() else [Path(p.strip()) for p in value.split(',')]
    if not files:
        raise ValueError('No images supplied')
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f'Image not found: {path}')
    return files

def main():
    parser = argparse.ArgumentParser(description='ONNX CPU inference for supplied tire views')
    parser.add_argument('--input', required=True, help='Image, directory or comma-separated images')
    parser.add_argument('--json-out')
    args = parser.parse_args()
    files = collect_files(args.input)
    engine = OnnxEngine()
    report = aggregate_whole_tire([engine.inspect(p) for p in files])
    report['timing_scope'] = 'Image decode + preprocessing + inference; excludes model loading, capture and UI'
    report['coverage_note'] = 'Aggregation of supplied views only; tire identity and full circumference are not verified'
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding='utf-8')
    print(payload)

if __name__ == '__main__':
    main()
