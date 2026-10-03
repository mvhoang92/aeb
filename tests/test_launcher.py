import subprocess
import unittest
from pathlib import Path

from ci_support import CARLA_INSTALL_REASON, ci_requires


AEB_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = Path("/usr/bin/python3")
CARLA_VENV_PYTHON = AEB_ROOT.parent / "venv" / "bin" / "python"
CARLA_INSTALLED = (
    CARLA_VENV_PYTHON.is_file() and (AEB_ROOT.parent / "CarlaUE4.sh").is_file()
)


class LauncherTests(unittest.TestCase):
    @ci_requires(CARLA_INSTALLED, CARLA_INSTALL_REASON)
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

    @ci_requires(CARLA_INSTALLED, CARLA_INSTALL_REASON)
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
