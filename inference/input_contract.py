"""Fail closed for incomplete inputs and incompatible classifier outputs."""
import math
from pathlib import Path


def collect_files(value):
    path = Path(value)
    if path.is_dir():
        files = sorted(p for p in path.iterdir()
                       if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
    elif path.is_file():
        files = [path]
    else:
        parts = value.split(',')
        if any(not p.strip() for p in parts):
            raise ValueError('Empty image path in input list')
        files = [Path(p.strip()) for p in parts]
    if not files:
        raise ValueError('No images supplied')
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError('Image(s) not found: ' + ', '.join(missing))
    return files


def classifier_scores(result):
    names = result.names
    if isinstance(names, (list, tuple)):
        names = dict(enumerate(names))
    if (not isinstance(names, dict) or set(names) != {0, 1, 2}
            or set(names.values()) != {'Normal', 'Warning', 'Abnormal'}):
        raise ValueError('Unexpected model classes; expected Normal, Warning, Abnormal')
    probs = getattr(result, 'probs', None)
    if probs is None or len(probs.data) != 3:
        raise ValueError('Expected three classification probabilities')
    values = [float(value) for value in probs.data]
    if (not all(math.isfinite(v) and 0 <= v <= 1 for v in values)
            or abs(sum(values) - 1) > 1e-4):
        raise ValueError('Invalid classification probability distribution')
    return {names[i]: values[i] for i in range(3)}
