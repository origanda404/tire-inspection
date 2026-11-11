"""Check default resolution without importing ML libraries or running a model."""
import ast, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class PackagingTests(unittest.TestCase):
    def test_default_is_packaged_production_model(self):
        path = ROOT / 'inference/predict.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'find_default_model')
        namespace = {'R': path.parent}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        self.assertEqual(namespace['find_default_model'](), ROOT / 'models/production_yolo11n_cls.pt')
    def test_missing_model_does_not_fall_back(self):
        from unittest.mock import patch
        with patch.object(Path, 'is_file', return_value=False):
            tree = ast.parse((ROOT/'inference/predict.py').read_text(encoding='utf-8'))
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'find_default_model')
            namespace = {'R': ROOT/'inference'}
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<packaging>', 'exec'), namespace)
            self.assertIsNone(namespace['find_default_model']())
if __name__ == '__main__': unittest.main()
