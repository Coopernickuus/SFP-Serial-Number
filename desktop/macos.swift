import Cocoa
import WebKit
import UniformTypeIdentifiers

final class ProbeResult: @unchecked Sendable { var ready = false }

final class AppDelegate: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandlerWithReply {
    let project = Bundle.main.bundleURL.deletingLastPathComponent().resolvingSymlinksInPath()
    let address = URL(string: "http://127.0.0.1:8765")!
    var window: NSWindow!
    var webView: WKWebView!
    var backend: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "SFP Seri Numaraları"
        window.contentMinSize = NSSize(width: 760, height: 600)
        window.isReleasedWhenClosed = false
        let loading = NSTextField(labelWithString: "Uygulama açılıyor…")
        loading.alignment = .center
        loading.frame = NSRect(x: 30, y: 400, width: 1120, height: 30)
        loading.autoresizingMask = [.width, .minYMargin, .maxYMargin]
        window.contentView?.addSubview(loading)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        DispatchQueue.global(qos: .userInitiated).async { self.startBackend() }
    }

    func buildMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem()
        menu.addItem(appItem)
        let appMenu = NSMenu()
        let reload = NSMenuItem(title: "Arayüzü yenile", action: #selector(reloadPage), keyEquivalent: "r")
        reload.target = self
        appMenu.addItem(reload)
        let folder = NSMenuItem(title: "Proje klasörünü aç", action: #selector(openProject), keyEquivalent: "")
        folder.target = self
        appMenu.addItem(folder)
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "SFP uygulamasını kapat", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        let editItem = NSMenuItem()
        menu.addItem(editItem)
        let edit = NSMenu(title: "Düzenle")
        for (title, action, key) in [("Kes", "cut:", "x"), ("Kopyala", "copy:", "c"),
                                      ("Yapıştır", "paste:", "v"), ("Tümünü seç", "selectAll:", "a")] {
            edit.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        editItem.submenu = edit
        NSApp.mainMenu = menu
    }

    @objc func reloadPage() { webView?.reload() }
    @objc func openProject() { NSWorkspace.shared.open(project) }

    func isReady() -> Bool {
        let semaphore = DispatchSemaphore(value: 0)
        let result = ProbeResult()
        var request = URLRequest(url: address.appendingPathComponent("api/instance"))
        request.timeoutInterval = 1
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let task = URLSession.shared.dataTask(with: request) { data, response, _ in
            if let data = data, let http = response as? HTTPURLResponse, http.statusCode == 200,
               let identity = try? JSONSerialization.jsonObject(with: data) as? [String: String] {
                result.ready = identity["app"] == "sfp-serial-number"
                    && identity["database"] == self.project.appendingPathComponent("data/seri_numaralari.sqlite3").path
            }
            semaphore.signal()
        }
        task.resume()
        if semaphore.wait(timeout: .now() + 1.5) == .timedOut { task.cancel(); return false }
        return result.ready
    }

    func startBackend() {
        if isReady() { DispatchQueue.main.async { self.showInterface() }; return }
        do {
            let script = project.appendingPathComponent("serial_number.py")
            guard FileManager.default.fileExists(atPath: script.path) else {
                throw NSError(domain: "SFP", code: 1, userInfo: [NSLocalizedDescriptionKey:
                    "Uygulamayı serial_number.py ve ui klasörünün yanına yerleştirin."])
            }
            let candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3",
                              "/Library/Frameworks/Python.framework/Versions/Current/bin/python3", "/usr/bin/python3"]
            guard let python = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) else {
                throw NSError(domain: "SFP", code: 2, userInfo: [NSLocalizedDescriptionKey: "Python 3 bulunamadı."])
            }
            let dataDirectory = project.appendingPathComponent("data")
            try FileManager.default.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
            let logURL = dataDirectory.appendingPathComponent("masaustu.log")
            if !FileManager.default.fileExists(atPath: logURL.path) { FileManager.default.createFile(atPath: logURL.path, contents: nil) }
            let log = try FileHandle(forWritingTo: logURL)
            try log.seekToEnd()
            defer { try? log.close() }
            let process = Process()
            process.executableURL = URL(fileURLWithPath: python)
            process.arguments = [script.path, "--no-browser"]
            process.currentDirectoryURL = project
            process.standardInput = FileHandle.nullDevice
            process.standardOutput = log
            process.standardError = log
            try process.run()
            DispatchQueue.main.sync { self.backend = process }
            let deadline = Date().addingTimeInterval(15)
            while Date() < deadline {
                if isReady() { DispatchQueue.main.async { self.showInterface() }; return }
                if !process.isRunning { break }
                Thread.sleep(forTimeInterval: 0.15)
            }
            if process.isRunning { process.interrupt() }
            throw NSError(domain: "SFP", code: 3, userInfo: [NSLocalizedDescriptionKey:
                "Uygulama başlatılamadı. 8765 portunu kontrol edin. Ayrıntılar: data/masaustu.log"])
        } catch {
            DispatchQueue.main.async { self.showError(error.localizedDescription, quit: true) }
        }
    }

    func showInterface() {
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.addScriptMessageHandler(self, contentWorld: .page, name: "copySerials")
        webView = WKWebView(frame: window.contentView!.bounds, configuration: configuration)
        webView.uiDelegate = self
        webView.navigationDelegate = self
        webView.autoresizingMask = [.width, .height]
        window.contentView = webView
        webView.load(URLRequest(url: address, cachePolicy: .reloadIgnoringLocalCacheData))
    }

    func showError(_ message: String, quit: Bool = false) {
        let alert = NSAlert()
        alert.messageText = "SFP Seri Numaraları"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Tamam")
        alert.beginSheetModal(for: window) { _ in if quit { NSApp.terminate(nil) } }
    }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage,
                               replyHandler: @escaping (Any?, String?) -> Void) {
        guard message.name == "copySerials", message.frameInfo.isMainFrame,
              message.frameInfo.request.url?.host == "127.0.0.1", let text = message.body as? String else {
            replyHandler(nil, "Geçersiz kopyalama isteği."); return
        }
        NSPasteboard.general.clearContents()
        if NSPasteboard.general.setString(text, forType: .string) { replyHandler(true, nil) }
        else { replyHandler(nil, "Panoya kopyalanamadı.") }
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert()
        alert.messageText = "Listeyi sıfırla"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Vazgeç")
        alert.addButton(withTitle: "Listeyi sıfırla")
        alert.beginSheetModal(for: window) { response in completionHandler(response == .alertSecondButtonReturn) }
    }

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.allowedContentTypes = ["xlsx", "csv", "tsv", "txt"].compactMap { UTType(filenameExtension: $0) }
        panel.beginSheetModal(for: window) { response in completionHandler(response == .OK ? panel.urls : nil) }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.host == address.host && url.port == address.port && url.path == "/export" {
            decisionHandler(.cancel)
            saveExport(url)
        } else if url.host == address.host && url.port == address.port {
            decisionHandler(.allow)
        } else { decisionHandler(.cancel) }
    }

    func saveExport(_ url: URL) {
        let format = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "format" })?.value == "csv" ? "csv" : "txt"
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "seri_numaralari.\(format)"
        panel.allowedContentTypes = [UTType(filenameExtension: format)!]
        panel.beginSheetModal(for: window) { response in
            guard response == .OK, let target = panel.url else { return }
            URLSession.shared.dataTask(with: url) { data, response, error in
                do {
                    if let error = error { throw error }
                    guard let data = data, (response as? HTTPURLResponse)?.statusCode == 200 else {
                        throw NSError(domain: "SFP", code: 4, userInfo: [NSLocalizedDescriptionKey: "Çıktı alınamadı."])
                    }
                    try data.write(to: target, options: .atomic)
                } catch { DispatchQueue.main.async { self.showError(error.localizedDescription) } }
            }.resume()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) {
        if let process = backend, process.isRunning { process.interrupt(); process.waitUntilExit() }
    }
}

let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
