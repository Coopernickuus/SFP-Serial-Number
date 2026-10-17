#!/usr/bin/env python3
"""SFP karekodlarından seri numarası toplama. Yalnızca Python standart kütüphanesi."""

import argparse
import base64
import binascii
import csv
import errno
import http.client
import io
import json
import posixpath
import re
import secrets
import sqlite3
import sys
import webbrowser
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "seri_numaralari.sqlite3"
APP_ID = "sfp-serial-number"
APP_VERSION = "1.1.1"
GS, RS, EOT = "\x1d", "\x1e", "\x04"
MAX_UPLOAD = 20 * 1024 * 1024
MAX_EXPANDED = 60 * 1024 * 1024
CONTROL_PICTURES = str.maketrans({"␝": GS, "␞": RS, "␄": EOT})
CONTROL_ESCAPES = re.compile(r"_x(001d|001e|0004)_|\\x(1d|1e|04)|\\u(001d|001e|0004)", re.I)


def normalize(text):
    """Görünür, gerçek ve Excel/metin kaçışlı ayırıcıları ortak biçime getirir."""
    text = CONTROL_ESCAPES.sub(
        lambda m: chr(int(next(group for group in m.groups() if group), 16)), text
    )
    return text.translate(CONTROL_PICTURES)


def extract_serial(record):
    """GS veya okuyucunun ] ayracındaki S alanını, bir sonraki ayırıcıya kadar okur."""
    record = normalize(record)
    # Gerçek GS mevcutsa ] bir veri karakteri olabilir; onu değiştirmeyiz.
    separator = GS if GS in record else "]"
    escaped = re.escape(separator)
    fields = list(re.finditer(escaped + r"S([^" + escaped + r"\x1e\x04\r\n]*)" + escaped, record))
    starts = list(re.finditer(escaped + r"(?=S)", record))
    if len(starts) > 1:
        raise ValueError("Bir karekodda birden fazla S alanı var; kayıt kontrol edilmeli.")
    if not fields:
        if GS not in record and "]" not in record:
            raise ValueError("␝ (GS) veya ] ayırıcısı bulunamadı. Okuyucunun ayırıcıları ilettiğini kontrol edin.")
        raise ValueError("␝S…␝ veya ]S…] biçiminde tamamlanmış bir seri numarası alanı bulunamadı.")
    serial = fields[0].group(1)
    if not serial or len(serial) > 256 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in serial):
        raise ValueError("Seri numarası boş, çok uzun veya boşluk/kontrol karakteri içeriyor.")
    return serial


def parse_text(text, source="Okuyucu", ignore_other=False):
    normalized = normalize(text)
    # Hem satır başına bir karekodu hem de art arda gelen tam çerçeveleri destekler.
    records = [part.strip(' \t\r\n\ufeff\"') for part in
               re.split(r"(?=\[\)>)|\x04|\r\n|\r|\n", normalized)]
    records = [part for part in records if part]
    result = {"items": [], "errors": [], "ignored": 0}
    for index, record in enumerate(records, 1):
        location = source if len(records) == 1 else f"{source} / kayıt {index}"
        if ignore_other and GS not in record and "]S" not in record and "[)>" not in record:
            result["ignored"] += 1
            continue
        try:
            result["items"].append({"serial": extract_serial(record), "source": location})
        except ValueError as error:
            result["errors"].append({"source": location, "message": str(error)})
    return result


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def xml_read(archive, name):
    data = archive.read(name)
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Excel dosyasındaki XML bildirimi desteklenmiyor.")
    return ET.fromstring(data)


def xlsx_cells(data):
    """.xlsx hücrelerini formülleri çalıştırmadan, sayfa/hücre bilgisiyle okur."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED:
            raise ValueError("Excel dosyasının açılmış boyutu 60 MB sınırını aşıyor.")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in xml_read(archive, "xl/sharedStrings.xml"):
                strings.append("".join(node.text or "" for node in item.iter() if local_name(node) == "t"))
        workbook = xml_read(archive, "xl/workbook.xml")
        relationships = xml_read(archive, "xl/_rels/workbook.xml.rels")
        targets = {rel.attrib["Id"]: rel.attrib.get("Target", "") for rel in relationships
                   if rel.attrib.get("TargetMode") != "External"}
        for sheet in (node for node in workbook.iter() if local_name(node) == "sheet"):
            relation = next((value for key, value in sheet.attrib.items() if key.endswith("}id")), "")
            target = targets.get(relation, "")
            if not target:
                continue
            name = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
            if not name.startswith("xl/worksheets/"):
                continue
            for cell in (node for node in xml_read(archive, name).iter() if local_name(node) == "c"):
                if any(local_name(node) == "f" for node in cell):
                    continue
                value = next((node.text for node in cell if local_name(node) == "v"), None)
                if cell.attrib.get("t") == "s" and value is not None:
                    value = strings[int(value)]
                elif cell.attrib.get("t") == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter() if local_name(node) == "t")
                if value:
                    yield f"{sheet.attrib.get('name', 'Sayfa')}!{cell.attrib.get('r', '?')}", value


def decode_text(data):
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1254")


def parse_file(filename, data):
    if len(data) > MAX_UPLOAD:
        raise ValueError("Dosya en fazla 20 MB olabilir.")
    suffix = Path(filename).suffix.lower()
    filename = Path(filename.replace("\\", "/")).name
    if suffix == ".xlsx":
        cells = xlsx_cells(data)
    elif suffix in (".csv", ".tsv"):
        text = decode_text(data)
        delimiter = "\t" if suffix == ".tsv" else ";"
        try:
            delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
        except csv.Error:
            pass
        cells = ((f"satır {i}, sütun {j}", value)
                 for i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delimiter), 1)
                 for j, value in enumerate(row, 1) if value.strip())
    elif suffix == ".txt":
        cells = [("metin", decode_text(data))]
    else:
        raise ValueError(".xlsx, .csv, .tsv veya .txt seçin. Eski .xls dosyalarını Excel'de .xlsx olarak kaydedin.")
    result = {"items": [], "errors": [], "ignored": 0}
    try:
        for location, value in cells:
            parsed = parse_text(value, f"{filename} / {location}", ignore_other=suffix != ".txt")
            for key in ("items", "errors"):
                result[key].extend(parsed[key])
            result["ignored"] += parsed["ignored"]
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError, UnicodeError, csv.Error) as error:
        raise ValueError("Dosya okunamadı. Geçerli ve şifresiz bir dosya seçin.") from error
    if not result["items"] and not result["errors"]:
        result["errors"].append({"source": filename, "message": "Dosyada karekod bulunamadı."})
    return result


class ListChangedError(ValueError):
    pass


class SerialStore:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as database:
            database.execute("""CREATE TABLE IF NOT EXISTS serials (
                id INTEGER PRIMARY KEY, serial TEXT NOT NULL UNIQUE COLLATE BINARY,
                captured_at TEXT NOT NULL, source TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        database = sqlite3.connect(str(self.path), timeout=15)
        database.row_factory = sqlite3.Row
        try:
            with database:
                yield database
        finally:
            database.close()

    def save(self, parsed):
        added, duplicates = [], []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connect() as database:
            for item in parsed["items"]:
                cursor = database.execute(
                    "INSERT OR IGNORE INTO serials(serial, captured_at, source) VALUES (?, ?, ?)",
                    (item["serial"], now, item["source"]))
                (added if cursor.rowcount else duplicates).append(item["serial"])
        return {"added": added, "duplicates": duplicates,
                "errors": parsed["errors"], "ignored": parsed["ignored"], "total": self.count()}

    def count(self):
        with self.connect() as database:
            return database.execute("SELECT COUNT(*) FROM serials").fetchone()[0]

    def reset(self, expected_count):
        with self.connect() as database:
            database.execute("BEGIN IMMEDIATE")
            count = database.execute("SELECT COUNT(*) FROM serials").fetchone()[0]
            if count != expected_count:
                raise ListChangedError("Liste değişti. Güncel kayıtları kontrol edip tekrar sıfırlayın.")
            return database.execute("DELETE FROM serials").rowcount

    def records(self, limit=None):
        with self.connect() as database:
            query = "SELECT * FROM serials ORDER BY id DESC"
            return [dict(row) for row in database.execute(query + (" LIMIT ?" if limit else ""),
                                                         (limit,) if limit else ())]

    def serials(self):
        return [row["serial"] for row in reversed(self.records())]


def export_bytes(serials, format_name):
    if format_name == "txt":
        return ("\n".join(serials) + ("\n" if serials else "")).encode("utf-8")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(["Seri Numarası"])
    # Excel formül yorumlamasını engeller. Tam ham değerler TXT çıktısında korunur.
    for serial in serials:
        writer.writerow(["'" + serial if serial.startswith(("=", "+", "-", "@")) else serial])
    return stream.getvalue().encode("utf-8-sig")


def make_handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, data, content_type="application/json; charset=utf-8", filename=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "Geçersiz adres."})
            parts = urlsplit(self.path)
            if parts.path == "/api/instance":
                return self.send(200, {"app": APP_ID, "version": APP_VERSION, "database": str(store.path)})
            if parts.path == "/":
                content = (ROOT / "ui" / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", token)
                return self.send(200, content.encode("utf-8"), "text/html; charset=utf-8")
            if parts.path in ("/app.js", "/scanner_input.js", "/style.css"):
                file = ROOT / "ui" / parts.path[1:]
                return self.send(200, file.read_bytes(), "text/javascript; charset=utf-8" if file.suffix == ".js" else "text/css; charset=utf-8")
            if parts.path == "/api/records":
                return self.send(200, {"records": store.records(1000), "total": store.count()})
            if parts.path == "/api/serials":
                return self.send(200, {"serials": store.serials()})
            if parts.path == "/export":
                kind = parse_qs(parts.query).get("format", ["txt"])[0]
                if kind not in ("txt", "csv"):
                    return self.send(400, {"error": "Geçersiz çıktı biçimi."})
                return self.send(200, export_bytes(store.serials(), kind),
                                 "text/plain; charset=utf-8" if kind == "txt" else "text/csv; charset=utf-8",
                                 f"seri_numaralari.{kind}")
            return self.send(404, {"error": "Bulunamadı."})

        def do_POST(self):
            if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-SFP-Token", ""), token):
                return self.send(403, {"error": "Sayfayı yenileyip tekrar deneyin."})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_UPLOAD * 4 // 3 + 8192:
                    raise ValueError("İstek boş veya dosya 20 MB sınırını aşıyor.")
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("Geçersiz istek biçimi.")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("Geçersiz istek.")
                path = urlsplit(self.path).path
                if path == "/api/reset":
                    if payload.get("confirm") is not True:
                        raise ValueError("Listeyi sıfırlamak için onay gereklidir.")
                    expected_count = payload.get("expected_count")
                    if type(expected_count) is not int or expected_count < 0:
                        raise ValueError("Geçerli bir kayıt sayısı gereklidir. Sayfayı yenileyin.")
                    return self.send(200, {"deleted": store.reset(expected_count), "total": 0})
                if path == "/api/scan":
                    raw = payload.get("text")
                    if not isinstance(raw, str) or not raw.strip():
                        raise ValueError("Önce bir karekod okutun veya yapıştırın.")
                    parsed = parse_text(raw)
                elif path == "/api/import":
                    filename, encoded = payload.get("filename"), payload.get("data")
                    if not isinstance(filename, str) or not isinstance(encoded, str):
                        raise ValueError("Dosya bilgileri eksik.")
                    parsed = parse_file(filename, base64.b64decode(encoded, validate=True))
                else:
                    return self.send(404, {"error": "Bulunamadı."})
                return self.send(200, store.save(parsed))
            except ListChangedError as error:
                return self.send(409, {"error": str(error)})
            except (ValueError, UnicodeError, binascii.Error) as error:
                return self.send(400, {"error": str(error)})
            except (OSError, sqlite3.Error):
                return self.send(500, {"error": "Kayıt kaydedilemedi. Disk alanını ve klasör yazma iznini kontrol edin."})
    return Handler


def is_running_instance(port, database):
    """Dolu portun aynı uygulamaya ve aynı kayıt listesine ait olduğunu doğrular."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/api/instance")
        response = connection.getresponse()
        if response.status != 200:
            return False
        body = response.read(4097)
        if len(body) > 4096:
            return False
        identity = json.loads(body)
        return (isinstance(identity, dict) and identity.get("app") == APP_ID
                and identity.get("database") == str(Path(database).resolve()))
    except (OSError, http.client.HTTPException, ValueError, UnicodeError):
        return False
    finally:
        connection.close()


def start_server(store, port):
    """Yeni sunucuyu veya doğrulanmış mevcut uygulamanın adresini döndürür."""
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, secrets.token_hex(32)))
    except OSError as error:
        if error.errno not in (errno.EADDRINUSE, 10048):
            raise
        if is_running_instance(port, store.path):
            return None, f"http://127.0.0.1:{port}"
        alternative = port + 1 if port < 65535 else 8765
        raise ValueError(
            f"{port} portu başka bir uygulama veya kayıt listesi tarafından kullanılıyor. "
            f"Farklı portla başlatın: python3 serial_number.py --port {alternative}"
        ) from error
    return server, f"http://127.0.0.1:{server.server_port}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="SFP karekodlarından seri numarası ayıklar ve toplar.")
    parser.add_argument("--input", "-i", type=Path, help="Toplu okunacak .xlsx, .csv, .tsv veya .txt")
    parser.add_argument("--output", "-o", type=Path, help="Bu dosyadan bulunan benzersiz seriler için .txt veya .csv çıktı")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Kalıcı kayıt dosyası")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("Port 0 ile 65535 arasında olmalıdır.")
    if args.output and not args.input:
        parser.error("--output için --input gereklidir.")
    try:
        if args.input:
            output = args.output or ROOT / "outputs" / "seri_numaralari.txt"
            kind = output.suffix.lower().lstrip(".")
            if kind not in ("csv", "txt"):
                parser.error("Çıktı uzantısı .txt veya .csv olmalı.")
            if output.resolve() in (args.input.resolve(), args.db.resolve()):
                parser.error("Çıktı, kaynak veya veritabanı dosyasının üzerine yazılamaz.")
            if args.input.stat().st_size > MAX_UPLOAD:
                raise ValueError("Dosya en fazla 20 MB olabilir.")
            parsed = parse_file(args.input.name, args.input.read_bytes())
            report = SerialStore(args.db).save(parsed)
            serials = list(dict.fromkeys(item["serial"] for item in parsed["items"]))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(export_bytes(serials, kind))
            print(f"{len(serials)} seri bulundu. {len(report['added'])} yeni kayıt, {len(report['duplicates'])} tekrar.")
            print(f"Çıktı: {output.resolve()}")
            for error in report["errors"]:
                print(f"UYARI: {error['source']}: {error['message']}", file=sys.stderr)
            return 1 if report["errors"] else 0
        store = SerialStore(args.db)
        server, url = start_server(store, args.port)
        if server is None:
            print(f"Uygulama zaten açık: {url}", flush=True)
            if not args.no_browser:
                if not webbrowser.open(url):
                    print("Tarayıcı otomatik açılamadı. Yukarıdaki adresi tarayıcınızda açın.")
            return 0
        print(f"SFP Seri Numaraları: {url}")
        print(f"Kayıtlar: {store.path}\nDurdurmak için Ctrl+C.", flush=True)
        if not args.no_browser:
            timer = Timer(0.5, webbrowser.open, args=(url,))
            timer.daemon = True
            timer.start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nUygulama kapatıldı. Kayıtlar saklandı.")
        finally:
            server.server_close()
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Hata: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
