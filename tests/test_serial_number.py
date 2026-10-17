import base64
import http.client
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import serial_number as app


SAMPLES = [
    ("[)>␞06␝1P471880A.101␝S1000082001138␝10D2309␝52PMXPD-243SI01␝1V9W␝18VLENSN␝4LCN␞␄", "1000082001138"),
    ("[)>␞06␝1P471880A.101␝SFR202936065␝Q1␝10D2029␝52PRTXM191-404-C40␝18VLENSN␝4LCN␞␄", "FR202936065"),
    ("[)>␞06␝1P471880A.101␝SHA20230240976␝Q1␝10D2023␝52PMXPD-243SI01␝1V9W␝18VLENSN␝4LCN␞␄", "HA20230240976"),
    ("[)>␞06␝1P471880A.101␝SMA18210960908␝Q1␝10D1821␝52PMXPD-243SI01␝1V9W␝18VLENSN␝4LCN␞␄", "MA18210960908"),
    ("[)>␞06␝1P471880A.101␝SHA20230241879␝10D2023␝52PMXPD-243SI01␝1V9W␝18VLENSN␝4LCN␞␄", "HA20230241879"),
]


class ExtractionTests(unittest.TestCase):
    def test_all_user_samples_and_encodings(self):
        for raw, expected in SAMPLES:
            for separator in ("␝", "\x1d", "_x001D_", r"\x1d", r"\u001d"):
                with self.subTest(serial=expected, separator=separator):
                    self.assertEqual(app.extract_serial(raw.replace("␝", separator)), expected)

    def test_only_field_prefix_is_removed(self):
        for serial in ("0000123", "S123", "s123", "AB-123.4/5"):
            self.assertEqual(app.extract_serial(f"␝S{serial}␝Q1"), serial)

    def test_rejects_invalid_and_ambiguous_fields(self):
        for raw in ("S123", "␝S␝", "␝S123", "␝S123␞", "␝S12 3␝", "␝S12\t3␝",
                    "␝S123␝S456␝", "␝S123␝Q1␝S456␝", "␝S" + "a" * 257 + "␝"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                app.extract_serial(raw)

    def test_multiple_records_with_and_without_line_breaks(self):
        for delimiter in ("", "\n", "\r\n"):
            parsed = app.parse_text(delimiter.join(raw for raw, _ in SAMPLES))
            self.assertEqual([item["serial"] for item in parsed["items"]], [s for _, s in SAMPLES])
            self.assertEqual(parsed["errors"], [])

    def test_partial_failure_is_reported(self):
        parsed = app.parse_text(SAMPLES[0][0] + "\n[)>06Sbroken\n" + SAMPLES[1][0])
        self.assertEqual(len(parsed["items"]), 2)
        self.assertEqual(len(parsed["errors"]), 1)


class FileTests(unittest.TestCase):
    def test_real_user_workbook(self):
        source = app.ROOT / "SFP Seri Numaralar.xlsx"
        if not source.exists():
            self.skipTest("Kullanıcının kaynak dosyası yok")
        parsed = app.parse_file(source.name, source.read_bytes())
        self.assertEqual([item["serial"] for item in parsed["items"]], [s for _, s in SAMPLES])
        self.assertEqual(parsed["errors"], [])
        self.assertTrue(parsed["items"][0]["source"].endswith("Sayfa1!A1"))

    def test_csv_and_utf16_txt(self):
        csv_data = ("Başlık;Not\r\n\"" + SAMPLES[0][0] + "\";başka sütun\r\n").encode("utf-8-sig")
        parsed = app.parse_file("input.csv", csv_data)
        self.assertEqual([i["serial"] for i in parsed["items"]], [SAMPLES[0][1]])
        self.assertGreater(parsed["ignored"], 0)
        self.assertEqual(app.parse_file("input.txt", SAMPLES[1][0].encode("utf-16"))["items"][0]["serial"], SAMPLES[1][1])

    def test_multi_sheet_inline_shared_and_formula_skip(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("xl/workbook.xml", '<workbook xmlns:r="urn:rel"><sheets><sheet name="A" r:id="r1"/><sheet name="B" r:id="r2"/></sheets></workbook>')
            archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="r1" Target="worksheets/a.xml"/><Relationship Id="r2" Target="/xl/worksheets/b.xml"/></Relationships>')
            archive.writestr("xl/sharedStrings.xml", '<sst><si><t>␝S000123␝Q1</t></si></sst>')
            archive.writestr("xl/worksheets/a.xml", '<worksheet><sheetData><row><c r="C2" t="s"><v>0</v></c></row></sheetData></worksheet>')
            archive.writestr("xl/worksheets/b.xml", '<worksheet><sheetData><row><c r="A5" t="inlineStr"><is><r><t>␝SABC</t></r><r><t>123␝Q1</t></r></is></c><c r="A6" t="str"><f>ignored</f><v>␝SMUST_NOT_IMPORT␝</v></c></row></sheetData></worksheet>')
        parsed = app.parse_file("sample.xlsx", output.getvalue())
        self.assertEqual([i["serial"] for i in parsed["items"]], ["000123", "ABC123"])
        self.assertIn("B!A5", parsed["items"][1]["source"])

    def test_corrupt_unsupported_empty_and_oversize(self):
        with self.assertRaises(ValueError):
            app.parse_file("bad.xlsx", b"not a zip")
        with self.assertRaises(ValueError):
            app.parse_file("bad.xls", b"binary")
        with self.assertRaises(ValueError):
            app.parse_file("big.txt", b"a" * (app.MAX_UPLOAD + 1))
        self.assertTrue(app.parse_file("empty.csv", b"header\n")["errors"])


class PersistenceTests(unittest.TestCase):
    def test_duplicates_reopen_order_and_text_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "test.sqlite3"
            store = app.SerialStore(path)
            parsed = app.parse_text("␝S000123␝\n␝SCase␝\n␝Scase␝\n␝S000123␝")
            report = store.save(parsed)
            self.assertEqual(report["added"], ["000123", "Case", "case"])
            self.assertEqual(report["duplicates"], ["000123"])
            reopened = app.SerialStore(path)
            self.assertEqual(reopened.serials(), ["000123", "Case", "case"])
            self.assertEqual(reopened.save(parsed)["added"], [])

    def test_reset_persists_and_accepts_previously_seen_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            store = app.SerialStore(path)
            store.save(app.parse_text(SAMPLES[0][0]))
            self.assertEqual(store.reset(1), 1)
            reopened = app.SerialStore(path)
            self.assertEqual(reopened.count(), 0)
            self.assertEqual(reopened.reset(0), 0)
            self.assertEqual(reopened.save(app.parse_text(SAMPLES[0][0]))["added"], [SAMPLES[0][1]])

    def test_export_preserves_identifiers_and_csv_formula_safety(self):
        serials = ["000123", "HA20230241879", "=1+1"]
        self.assertEqual(app.export_bytes(serials, "txt").decode(), "000123\nHA20230241879\n=1+1\n")
        self.assertTrue(app.export_bytes(serials, "csv").startswith(b"\xef\xbb\xbf"))
        self.assertIn("'=1+1", app.export_bytes(serials, "csv").decode("utf-8-sig"))

    def test_cli_output_even_if_already_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, db = root / "input.txt", root / "result.txt", root / "data.sqlite3"
            source.write_text(SAMPLES[0][0], encoding="utf-8")
            args = ["--input", str(source), "--output", str(output), "--db", str(db)]
            self.assertEqual(app.main(args), 0)
            self.assertEqual(app.main(args), 0)
            self.assertEqual(output.read_text().strip(), SAMPLES[0][1])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = app.SerialStore(Path(self.directory.name) / "data.sqlite3")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(self.store, "test-token"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, method, path, payload=None, token="test-token", host=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        headers = {"Content-Type": "application/json", "X-SFP-Token": token}
        if host:
            headers["Host"] = host
        connection.request(method, path, json.dumps(payload) if payload is not None else None, headers)
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    def test_scan_import_and_export(self):
        self.assertEqual(self.request("GET", "/")[0], 200)
        status, data = self.request("POST", "/api/scan", {"text": SAMPLES[0][0]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["added"], [SAMPLES[0][1]])
        status, data = self.request("POST", "/api/import", {"filename": "input.txt", "data": base64.b64encode(SAMPLES[1][0].encode()).decode()})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["added"], [SAMPLES[1][1]])
        self.assertEqual(json.loads(self.request("GET", "/api/records")[1])["total"], 2)
        self.assertEqual(self.request("GET", "/export?format=txt")[1].decode().splitlines(), [s for _, s in SAMPLES[:2]])

    def test_reset_requires_confirmation_and_current_count(self):
        self.store.save(app.parse_text(SAMPLES[0][0]))
        for payload in ({}, {"confirm": False, "expected_count": 1},
                        {"confirm": True}, {"confirm": True, "expected_count": True},
                        {"confirm": True, "expected_count": -1}):
            with self.subTest(payload=payload):
                self.assertEqual(self.request("POST", "/api/reset", payload)[0], 400)
                self.assertEqual(self.store.count(), 1)
        payload = {"confirm": True, "expected_count": 1}
        self.assertEqual(self.request("POST", "/api/reset", payload, token="wrong")[0], 403)
        self.assertEqual(self.request("GET", "/api/reset")[0], 404)
        self.store.save(app.parse_text(SAMPLES[1][0]))
        self.assertEqual(self.request("POST", "/api/reset", payload)[0], 409)
        self.assertEqual(self.store.count(), 2)

    def test_reset_clears_all_records_and_exports(self):
        self.store.save(app.parse_text("\n".join(raw for raw, _ in SAMPLES)))
        status, data = self.request("POST", "/api/reset", {"confirm": True, "expected_count": 5})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), {"deleted": 5, "total": 0})
        self.assertEqual(json.loads(self.request("GET", "/api/records")[1]), {"records": [], "total": 0})
        self.assertEqual(self.request("GET", "/export?format=txt")[1], b"")
        self.assertEqual(self.request("GET", "/export?format=csv")[1].decode("utf-8-sig"), "Seri Numarası\r\n")
        status, data = self.request("POST", "/api/scan", {"text": SAMPLES[0][0]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["added"], [SAMPLES[0][1]])

    def test_starting_again_opens_existing_app_and_preserves_records(self):
        self.store.save(app.parse_text(SAMPLES[0][0]))
        args = ["--port", str(self.server.server_port), "--db", str(self.store.path)]
        with patch.object(app.webbrowser, "open", return_value=True) as open_browser:
            self.assertEqual(app.main(args), 0)
            open_browser.assert_called_once_with(f"http://127.0.0.1:{self.server.server_port}")
        self.assertEqual(self.store.serials(), [SAMPLES[0][1]])
        self.assertEqual(json.loads(self.request("GET", "/api/records")[1])["total"], 1)

    def test_reuse_honors_no_browser_and_database_identity(self):
        args = ["--port", str(self.server.server_port), "--db", str(self.store.path), "--no-browser"]
        with patch.object(app.webbrowser, "open") as open_browser:
            self.assertEqual(app.main(args), 0)
            open_browser.assert_not_called()
        other_store = app.SerialStore(Path(self.directory.name) / "other.sqlite3")
        with self.assertRaisesRegex(ValueError, "Farklı portla başlatın"):
            app.start_server(other_store, self.server.server_port)

    def test_unrelated_or_malformed_http_server_is_not_reused(self):
        from http.server import BaseHTTPRequestHandler

        for body in (b'{"app":"different-app"}', b'[]', b'<html>other program</html>'):
            with self.subTest(body=body):
                class UnrelatedHandler(BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass

                    def do_GET(self):
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(body)

                other = ThreadingHTTPServer(("127.0.0.1", 0), UnrelatedHandler)
                thread = threading.Thread(target=other.serve_forever, daemon=True)
                thread.start()
                try:
                    with self.assertRaisesRegex(ValueError, "Farklı portla başlatın"):
                        app.start_server(self.store, other.server_port)
                finally:
                    other.shutdown()
                    other.server_close()
                    thread.join()

    def test_unused_port_starts_new_server_with_identity(self):
        new_server, url = app.start_server(self.store, 0)
        thread = threading.Thread(target=new_server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(url, f"http://127.0.0.1:{new_server.server_port}")
            self.assertTrue(app.is_running_instance(new_server.server_port, self.store.path))
        finally:
            new_server.shutdown()
            new_server.server_close()
            thread.join()

    def test_invalid_requests_do_not_modify_records(self):
        self.assertEqual(self.request("POST", "/api/scan", {"text": SAMPLES[0][0]}, token="wrong")[0], 403)
        self.assertEqual(self.request("GET", "/api/records", host="external.example")[0], 403)
        self.assertEqual(self.request("POST", "/api/scan", {"text": ""})[0], 400)
        self.assertEqual(self.request("POST", "/api/import", {"filename": "a.txt", "data": "!@#$"})[0], 400)
        self.assertEqual(self.store.count(), 0)


if __name__ == "__main__":
    unittest.main()
