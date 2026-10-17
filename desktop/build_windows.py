"""Windows'ta tek EXE ve düzenlenebilir ui klasörü içeren dağıtım üretir."""
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from serial_number import APP_VERSION


def check_runtime():
    if sys.platform != "win32":
        raise SystemExit("EXE oluşturmak için bu dosyayı Windows'ta veya GitHub Actions Windows işinde çalıştırın.")
    if sys.implementation.name != "cpython" or not (3, 11) <= sys.version_info[:2] < (3, 16):
        raise SystemExit("EXE oluşturmak için Python 3.11–3.15 (CPython) gerekir; Python 3.15 desteklenir.")


def environment_path(build):
    major, minor = sys.version_info[:2]
    abi = "t" if sysconfig.get_config_var("Py_GIL_DISABLED") else ""
    return build / f"windows-venv-py{major}{minor}{abi}-{sysconfig.get_platform()}"


def main():
    check_runtime()
    print(f"SFP {APP_VERSION} — Python {sys.version.split()[0]}: {sys.executable}", flush=True)
    build = PROJECT / ".build"
    # Farklı Python sürümleri ve mimarileri aynı sanal ortamı paylaşmamalıdır.
    environment = environment_path(build)
    python = environment / "Scripts" / "python.exe"
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    print(f"Derleme ortamı: {environment}", flush=True)
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
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
    shutil.copy2(PROJECT / "OKUYUCU_NOTLARI.md", package / "OKUYUCU_NOTLARI.md")
    shutil.copy2(PROJECT / "desktop" / "WINDOWS_KULLANIM.md", package / "KULLANIM.md")
    (package / "SURUM.txt").write_text(
        f"SFP Seri Numaraları {APP_VERSION}\nPython {sys.version.split()[0]} ile oluşturuldu.\n"
        "GS ve ] ayırıcıları desteklenir.\n"
        "Okuma sonu Enter/Tab desteklenir; giriş odağı korunur.\n", encoding="utf-8")
    result = build / "windows-smoke.json"
    result.unlink(missing_ok=True)
    subprocess.run([str(executable), "--smoke-test", "--result", str(result)], check=True, timeout=60)
    if json.loads(result.read_text(encoding="utf-8")).get("ok") is not True:
        raise RuntimeError("EXE doğrulaması tamamlanamadı.")
    print(f"SFP {APP_VERSION} hazır: {package}")


if __name__ == "__main__":
    main()
