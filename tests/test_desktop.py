import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop import windows_app


class DesktopPackagingTests(unittest.TestCase):
    def test_frozen_app_prefers_editable_ui_and_has_bundled_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, bundled = root / "package", root / "bundled"
            (package / "ui").mkdir(parents=True)
            page = package / "ui" / "index.html"
            page.write_text("Editable UI", encoding="utf-8")
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", str(package / "SFP.exe")), \
                 patch.object(sys, "_MEIPASS", str(bundled), create=True):
                self.assertEqual(windows_app.assets_root(), package.resolve())
                page.unlink()
                self.assertEqual(windows_app.assets_root(), bundled)

    def test_windows_data_survives_executable_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}):
                self.assertEqual(windows_app.data_directory(), Path(directory) / "SFP Seri Numaralari")

    def test_packaged_backend_smoke_check_uses_temporary_database(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "smoke.json"
            windows_app.smoke_test(result)
            self.assertEqual(json.loads(result.read_text()), {"ok": True, "assets": True, "backend": True})


if __name__ == "__main__":
    unittest.main()
