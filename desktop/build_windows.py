"""Windows'ta tek EXE ve düzenlenebilir ui klasörü içeren dağıtım üretir."""
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("EXE oluşturmak için bu dosyayı Windows'ta veya GitHub Actions Windows işinde çalıştırın.")
    build = PROJECT / ".build"
    environment = build / "windows-venv"
    python = environment / "Scripts" / "python.exe"
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(PROJECT / "desktop" / "requirements-windows.txt")], check=True)
    subprocess.run([
        str(python), "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "SFP Seri Numaralari", "--paths", str(PROJECT),
        "--add-data", f"{PROJECT / 'ui'}{os.pathsep}ui", "--collect-all", "webview", "--collect-all", "pythonnet",
        "--distpath", str(PROJECT / "dist" / "windows"), "--workpath", str(build / "pyinstaller"),
        "--specpath", str(build), str(PROJECT / "desktop" / "windows_app.py")
    ], cwd=PROJECT, check=True)
    package = PROJECT / "dist" / "SFP-Windows"
    package.mkdir(parents=True, exist_ok=True)
    executable = package / "SFP Seri Numaralari.exe"
    shutil.copy2(PROJECT / "dist" / "windows" / executable.name, executable)
    shutil.copytree(PROJECT / "ui", package / "ui", dirs_exist_ok=True)
    shutil.copy2(PROJECT / "METINLERI_DUZENLEME.md", package / "METINLERI_DUZENLEME.md")
    shutil.copy2(PROJECT / "desktop" / "WINDOWS_KULLANIM.md", package / "KULLANIM.md")
    result = build / "windows-smoke.json"
    result.unlink(missing_ok=True)
    subprocess.run([str(executable), "--smoke-test", "--result", str(result)], check=True, timeout=60)
    if json.loads(result.read_text(encoding="utf-8")).get("ok") is not True:
        raise RuntimeError("EXE doğrulaması tamamlanamadı.")
    print(f"Hazır: {package}")


if __name__ == "__main__":
    main()
