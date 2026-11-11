"""Check packaged assets without running inference or requiring ML libraries."""
import ast, hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'models/release.json').read_text(encoding='utf-8'))
for name, expected in manifest['sha256'].items():
    assert hashlib.sha256((root / 'models' / name).read_bytes()).hexdigest() == expected, name
for path in (root / 'inference').glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('PASS: packaged model hashes and Python syntax. This does not certify accuracy or Pi performance.')
