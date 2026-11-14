"""Inference and Multi-View Whole-Tire Inspection Engine."""
import argparse, json, os, time
from pathlib import Path
R = Path(__file__).resolve().parent
os.environ['YOLO_CONFIG_DIR'] = str(R.parent / '.cache' / 'ultralytics')
from PIL import Image, ImageOps
if __package__:
    from .input_contract import classifier_scores, collect_files
else:
    from input_contract import classifier_scores, collect_files

SEVERITY = {'Normal': 0, 'Warning': 1, 'Abnormal': 2}
REV_SEVERITY = {0: 'Normal', 1: 'Warning', 2: 'Abnormal'}

def inspect_single_view(model, img_path, imgsz=224, abnormal_thresh=0.25, warning_thresh=0.35):
    with Image.open(img_path) as im:
        padded = ImageOps.pad(ImageOps.exif_transpose(im).convert('RGB'), (imgsz, imgsz), method=Image.Resampling.LANCZOS, color=(114, 114, 114))

    t0 = time.perf_counter()
    res = model.predict(padded, imgsz=imgsz, device='cpu', verbose=False)[0]
    lat_ms = (time.perf_counter() - t0) * 1000

    names = res.names
    scores = classifier_scores(res)
    argmax_pred = names[res.probs.top1]

    p_abn = scores['Abnormal']
    p_war = scores['Warning']
    p_nor = scores['Normal']

    if p_abn >= abnormal_thresh:
        safety_pred = 'Abnormal'
        reason = f"P(Abnormal)={p_abn*100:.1f}% >= {abnormal_thresh*100:.0f}%"
    elif p_war >= warning_thresh:
        safety_pred = 'Warning'
        reason = f"P(Warning)={p_war*100:.1f}% >= {warning_thresh*100:.0f}%"
    else:
        safety_pred = 'Normal'
        reason = f"P(Normal)={p_nor*100:.1f}% dominant"

    return dict(
        image=str(img_path),
        filename=Path(img_path).name,
        latency_ms=round(lat_ms, 1),
        scores={k: round(v, 4) for k, v in scores.items()},
        argmax_prediction=argmax_pred,
        safety_prediction=safety_pred,
        reason=reason
    )

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

def main():
    ap = argparse.ArgumentParser(description="Whole-Tire Multi-View Inspection Engine")
    ap.add_argument('--input', type=str, required=True, help="Directory containing tire images or comma-separated image paths")
    ap.add_argument('--model', type=str, default=None, help="Path to model weights")
    ap.add_argument('--imgsz', type=int, default=224, help="Image resolution")
    ap.add_argument('--json-out', type=str, default=None, help="Path to save output JSON")
    args = ap.parse_args()

    files = collect_files(args.input)

    # Find model
    if __package__:
        from .predict import find_default_model
    else:
        from predict import find_default_model
    model_path = Path(args.model) if args.model else find_default_model()
    if not model_path or not model_path.is_file():
        raise SystemExit("Model checkpoint not found.")

    import torch
    from ultralytics import YOLO
    torch.set_num_threads(4)
    model = YOLO(str(model_path))

    print("=" * 65)
    print(" AI Tire Inspection: Whole-Tire Circumference Analysis")
    print("=" * 65)
    print(f" Images Found : {len(files)} views")
    print(f" Model Used   : {model_path.name}")
    print("-" * 65)

    results = []
    for f in files:
        res = inspect_single_view(model, f, imgsz=args.imgsz)
        results.append(res)
        icon = "[FAIL]" if res['safety_prediction'] == 'Abnormal' else ("[WARN]" if res['safety_prediction'] == 'Warning' else "[PASS]")
        print(f" {icon} {res['filename']:<15} -> {res['safety_prediction']:<9} ({res['latency_ms']} ms) | {res['reason']}")

    report = aggregate_whole_tire(results)

    print("=" * 65)
    print(f" FINAL TIRE DECISION : >>> [ {report['overall_condition']} ] <<<")
    print(f" Summary Note        : {report['summary_note']}")
    print(f" View Breakdown      : Normal: {report['normal_views_count']} | Warning: {report['warning_views_count']} | Abnormal: {report['abnormal_views_count']}")
    print(f" Total Processing    : {report['total_latency_ms']} ms ({report['avg_latency_ms']} ms/view)")
    print("=" * 65)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"Report saved to {args.json_out}")

if __name__ == '__main__':
    main()

