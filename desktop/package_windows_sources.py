"""Yerel kayıtları dahil etmeden Windows EXE oluşturma kaynaklarını paketler."""
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from serial_number import APP_VERSION


def main():
    files = [PROJECT / name for name in (
        "serial_number.py", "README.md", "METINLERI_DUZENLEME.md", "OKUYUCU_NOTLARI.md",
        "Windows_EXE_Olustur.bat", "Baslat.bat", ".gitignore")]
    for folder in ("ui", "desktop", "tests", ".github"):
        files.extend(path for path in (PROJECT / folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts
                     and path.suffix != ".pyc" and path.name != ".DS_Store")
    output = PROJECT / "outputs" / f"SFP-Windows-Olusturma-v{APP_VERSION}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(PROJECT).as_posix())
    print(f"Windows {APP_VERSION} kaynak paketi: {output}")


if __name__ == "__main__":
    main()
