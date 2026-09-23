import subprocess
import unittest
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = Path("/usr/bin/python3")
CARLA_VENV_PYTHON = AEB_ROOT.parent / "venv" / "bin" / "python"


class LauncherTests(unittest.TestCase):
    def test_canonical_launcher_prerequisites(self):
        result = subprocess.run(
            [str(SYSTEM_PYTHON), "launcher.py", "--check"],
            cwd=str(AEB_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CARLA script       OK", result.stdout)
        self.assertIn("YOLO Python        OK", result.stdout)
        self.assertIn("Scenarios          66", result.stdout)

    def test_carla_venv_falls_back_to_gui_python(self):
        result = subprocess.run(
            [str(CARLA_VENV_PYTHON), "launcher.py", "--check"],
            cwd=str(AEB_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Scenarios          66", result.stdout)

    def test_misspelled_launcher_is_removed(self):
        self.assertFalse((AEB_ROOT / "laucher.py").exists())
        self.assertTrue((AEB_ROOT / "launcher.py").is_file())


if __name__ == "__main__":
    unittest.main()
