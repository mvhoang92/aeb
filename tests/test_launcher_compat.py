import subprocess
import unittest
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = Path("/usr/bin/python3")


class LauncherCompatibilityTests(unittest.TestCase):
    def _check(self, script_name):
        return subprocess.run(
            [str(SYSTEM_PYTHON), script_name, "--check"],
            cwd=str(AEB_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )

    def test_historical_entry_point_matches_canonical_launcher(self):
        canonical = self._check("launcher.py")
        historical = self._check("laucher.py")

        self.assertEqual(canonical.returncode, 0, canonical.stderr)
        self.assertEqual(historical.returncode, canonical.returncode, historical.stderr)
        self.assertEqual(historical.stdout, canonical.stdout)


if __name__ == "__main__":
    unittest.main()
