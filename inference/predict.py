"""Predict tire condition from an image using the model packaged in this workspace."""
import argparse, os, time
from pathlib import Path
R = Path(__file__).resolve().parent
os.environ['YOLO_CONFIG_DIR'] = str(R.parent / '.cache' / 'ultralytics')
from PIL import Image, ImageOps
if __package__:
    from .input_contract import classifier_scores
else:
    from input_contract import classifier_scores

def find_default_model():
    # Use the packaged model, never an experimental fold or external workspace.
    model_path = R.parent / 'models' / 'production_yolo11n_cls.pt'
    return model_path if model_path.is_file() else None


def main():
    ap = argparse.ArgumentParser(description="AI Tire Inspection: Image Prediction CLI")
    ap.add_argument('--image', type=str, required=True, help="Path to tire image (.jpg, .png, etc.)")
    ap.add_argument('--model', type=str, default=None, help="Path to model weights (.pt or .onnx)")
    ap.add_argument('--imgsz', type=int, default=224, help="Input resolution (224 or 320)")
    ap.add_argument('--abnormal-thresh', type=float, default=0.25, help="Safety threshold for Abnormal")
    ap.add_argument('--warning-thresh', type=float, default=0.35, help="Safety threshold for Warning")
    args = ap.parse_args()

    img_path = Path(args.image).resolve()
    if not img_path.is_file():
        raise SystemExit(f"Error: Image not found at {img_path}")

    model_path = Path(args.model).resolve() if args.model else find_default_model()
    if not model_path or not model_path.is_file():
        raise SystemExit(f"Error: Model not found at {model_path}")

    print("=" * 60)
    print(" AI Tire Inspection - Prediction Tool")
    print("=" * 60)
    print(f" Image : {img_path.name}")
    print(f" Model : {model_path.parent.parent.name}/{model_path.name}")
    print(f" Size  : {args.imgsz}x{args.imgsz}")

    # Load and preprocess
    with Image.open(img_path) as im:
        padded = ImageOps.pad(ImageOps.exif_transpose(im).convert('RGB'), (args.imgsz, args.imgsz), method=Image.Resampling.LANCZOS, color=(114, 114, 114))

    # Load model
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(4)
    model = YOLO(str(model_path))

    # Inference with timing
    t0 = time.perf_counter()
    res = model.predict(padded, imgsz=args.imgsz, device='cpu', verbose=False)[0]
    lat_ms = (time.perf_counter() - t0) * 1000

    names = res.names
    scores = classifier_scores(res)
    argmax_pred = names[res.probs.top1]

    # Safety-First Logic
    p_abn = scores['Abnormal']
    p_war = scores['Warning']
    p_nor = scores['Normal']

    if p_abn >= args.abnormal_thresh:
        safety_pred = 'Abnormal'
        safety_reason = f"P(Abnormal) = {p_abn*100:.1f}% >= {args.abnormal_thresh*100:.0f}%"
    elif p_war >= args.warning_thresh:
        safety_pred = 'Warning'
        safety_reason = f"P(Warning) = {p_war*100:.1f}% >= {args.warning_thresh*100:.0f}%"
    else:
        safety_pred = 'Normal'
        safety_reason = f"Normal dominant ({p_nor*100:.1f}%)"

    print("-" * 60)
    print(f" Latency: {lat_ms:.1f} ms (CPU 4 threads)")
    print("-" * 60)
    print(" Probabilities:")
    print(f"   • Normal   : {p_nor*100:5.2f}%")
    print(f"   • Warning  : {p_war*100:5.2f}%")
    print(f"   • Abnormal : {p_abn*100:5.2f}%")
    print("-" * 60)
    print(f" Standard Decision (Argmax) : [{argmax_pred}]")
    print(f" Safety-First Decision      : [{safety_pred}] ({safety_reason})")
    print("=" * 60)

if __name__ == '__main__':
    main()

