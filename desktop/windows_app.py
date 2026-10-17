"""Windows masaüstü penceresi. EXE içinde Python ve pywebview paketlenir."""
import argparse
import ctypes
import json
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(PROJECT))
import serial_number as app

TITLE = "SFP Seri Numaraları"


def assets_root():
    if getattr(sys, "frozen", False):
        external = Path(sys.executable).resolve().parent
        if (external / "ui" / "index.html").is_file():
            return external
        return Path(sys._MEIPASS)
    return PROJECT


def data_directory():
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    return base / "SFP Seri Numaralari"


class DesktopBridge:
    def copy_serials(self, text):
        if not isinstance(text, str):
            raise ValueError("Geçersiz kopyalama isteği.")
        import pyperclip
        pyperclip.copy(text)
        return True


def acquire_instance():
    """Aynı Windows oturumunda ikinci pencere açmak yerine mevcut pencereyi getirir."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, "Local\\SFPSerialNumbersDesktop")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(handle)
        user = ctypes.WinDLL("user32")
        user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user.FindWindowW.restype = wintypes.HWND
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        window = user.FindWindowW(None, TITLE)
        if window:
            user.ShowWindow(window, 9)
            user.SetForegroundWindow(window)
        return None, kernel
    return handle, kernel


def smoke_test(result_path):
    """Paketlenmiş EXE'yi mevcut kullanıcı listesine dokunmadan denetler."""
    import http.client
    root = assets_root()
    for name in ("index.html", "app.js", "style.css"):
        if not (root / "ui" / name).is_file():
            raise RuntimeError(f"Arayüz dosyası eksik: {name}")
    assert app.extract_serial("␝SSMOKE001␝Q1") == "SMOKE001"
    with tempfile.TemporaryDirectory() as directory:
        store = app.SerialStore(Path(directory) / "smoke.sqlite3")
        server, url = app.start_server(store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request("GET", "/api/instance")
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read())["app"] == app.APP_ID
            # Windows CI also checks that the frozen native backend can be imported.
            if sys.platform == "win32":
                import webview.platforms.edgechromium
                import pyperclip
            Path(result_path).write_text(json.dumps({"ok": True, "assets": True, "backend": True}), encoding="utf-8")
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.smoke_test:
        if args.result is None:
            parser.error("--result gereklidir.")
        smoke_test(args.result)
        return 0
    if sys.platform != "win32":
        raise RuntimeError("Bu başlatıcı Windows içindir. Mac'te SFP Seri Numaraları.app dosyasını açın.")
    handle, kernel = acquire_instance()
    if handle is None:
        return 0
    server = None
    thread = None
    try:
        import webview
        app.ROOT = assets_root()
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        store = app.SerialStore(directory / "seri_numaralari.sqlite3")
        try:
            server, url = app.start_server(store, 8765)
        except ValueError:
            server, url = app.start_server(store, 0)
        if server is not None:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.create_window(TITLE, url, width=1180, height=860, min_size=(760, 600), js_api=DesktopBridge())
        webview.start(gui="edgechromium")
        return 0
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join()
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "masaustu.log").write_text(traceback.format_exc(), encoding="utf-8")
        if "--smoke-test" in sys.argv:
            if "--result" in sys.argv:
                result_path = Path(sys.argv[sys.argv.index("--result") + 1])
                result_path.write_text(json.dumps({"ok": False, "error": str(error)}), encoding="utf-8")
        elif sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(None, f"{error}\n\nAyrıntılar: {directory / 'masaustu.log'}", TITLE, 0x10)
        else:
            print(str(error), file=sys.stderr)
        sys.exit(2)
