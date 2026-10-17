import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop import build_windows, windows_app


class WindowsBuildTests(unittest.TestCase):
    def test_python315_build_does_not_reuse_old_python_environment(self):
        with tempfile.TemporaryDirectory(prefix="SFP build ") as directory:
            root = Path(directory)
            old_python = root / ".build" / "windows-venv" / "Scripts" / "python.exe"
            old_python.parent.mkdir(parents=True)
            old_python.write_bytes(b"old Python 3.12")
            (root / "ui").mkdir()
            (root / "ui" / "index.html").write_text("UI", encoding="utf-8")
            (root / "desktop").mkdir()
            for name in ("METINLERI_DUZENLEME.md", "OKUYUCU_NOTLARI.md", "desktop/WINDOWS_KULLANIM.md"):
                (root / name).write_text("Guide", encoding="utf-8")

            def create_environment(path):
                python = path / "Scripts" / "python.exe"
                python.parent.mkdir(parents=True)
                python.write_bytes(b"Python 3.15")

            def run(command, **kwargs):
                if "PyInstaller" in command:
                    executable = root / "dist" / "windows" / "SFP Seri Numaralari.exe"
                    executable.parent.mkdir(parents=True)
                    executable.write_bytes(b"built EXE")
                if "--smoke-test" in command:
                    Path(command[-1]).write_text('{"ok": true}', encoding="utf-8")

            with patch.object(build_windows, "PROJECT", root), \
                 patch.object(sys, "platform", "win32"), \
                 patch.object(sys, "version_info", (3, 15, 0, "final", 0)), \
                 patch.object(sys, "version", "3.15.0 (test)"), \
                 patch.object(build_windows.sysconfig, "get_platform", return_value="win-amd64"), \
                 patch.object(build_windows.sysconfig, "get_config_var", return_value=0), \
                 patch.object(build_windows.venv, "EnvBuilder") as builder, \
                 patch.object(build_windows.subprocess, "run", side_effect=run) as process:
                builder.return_value.create.side_effect = create_environment
                build_windows.main()

            environment = root / ".build" / "windows-venv-py315-win-amd64"
            python = str(environment / "Scripts" / "python.exe")
            builder.return_value.create.assert_called_once_with(environment)
            commands = [call.args[0] for call in process.call_args_list]
            self.assertEqual(len(commands), 4)
            self.assertTrue(all(command[0] == python for command in commands[:3]))
            self.assertIn("PyInstaller", commands[2])
            self.assertIn("--smoke-test", commands[3])
            self.assertEqual(old_python.read_bytes(), b"old Python 3.12")
            package = root / "dist" / "SFP-Windows"
            self.assertEqual((package / "SFP Seri Numaralari.exe").read_bytes(), b"built EXE")
            self.assertIn("Python 3.15.0", (package / "SURUM.txt").read_text(encoding="utf-8"))

    def test_unsupported_python_stops_before_creating_environment(self):
        for version in ((3, 10), (3, 16)):
            with self.subTest(version=version), \
                 patch.object(sys, "platform", "win32"), \
                 patch.object(sys, "version_info", version), \
                 patch.object(build_windows.venv, "EnvBuilder") as builder, \
                 patch.object(build_windows.subprocess, "run") as process:
                with self.assertRaisesRegex(SystemExit, "3.11–3.15"):
                    build_windows.main()
                builder.assert_not_called()
                process.assert_not_called()


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
