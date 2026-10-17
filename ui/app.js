"use strict";
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="sfp-token"]').content;
let records = [];
let total = 0;
let scanQueue = Promise.resolve();
let pendingScans = 0;
let importBusy = false;
let resetBusy = false;
let scannerTailUntil = 0;

function focusScanner() {
  const input = $("scan");
  input.focus({preventScroll: true});
  if (!input.value) {
    input.scrollLeft = 0;
    input.scrollTop = 0;
  }
}

function updateControls() {
  $("scan").disabled = resetBusy;
  $("save").disabled = resetBusy;
  $("file").disabled = resetBusy || importBusy;
  $("reset").disabled = resetBusy || importBusy || pendingScans > 0 || total === 0;
}

function feedback(title, detail = "", mode = "", errors = []) {
  $("feedback").hidden = false;
  $("feedback").className = `feedback ${mode}`;
  $("feedback-title").textContent = title;
  $("feedback-detail").textContent = detail;
  $("feedback-errors").replaceChildren(...errors.map((error) => {
    const li = document.createElement("li");
    li.textContent = `${error.source}: ${error.message}`;
    return li;
  }));
}

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json", "X-SFP-Token": token},
    body: JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "İşlem tamamlanamadı.");
  return result;
}

function render() {
  const query = $("search").value.toLocaleUpperCase("tr");
  const filtered = records.filter((r) => r.serial.toLocaleUpperCase("tr").includes(query));
  $("total").textContent = total.toLocaleString("tr-TR");
  $("list-info").textContent = total > 1000
    ? `Son 1.000 kayıt gösterilir · İndirme ve kopyalama tüm listeyi içerir`
    : `${filtered.length.toLocaleString("tr-TR")} kayıt gösteriliyor`;
  $("records").replaceChildren(...filtered.map((record) => {
    const tr = document.createElement("tr");
    const date = new Date(record.captured_at).toLocaleString("tr-TR");
    for (const text of [record.serial, date, record.source]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.append(td);
    }
    return tr;
  }));
  $("empty").hidden = filtered.length > 0;
  $("empty").querySelector("strong").textContent = total
    ? "Aramanızla eşleşen kayıt yok." : "İlk seri numaranızı ekleyin.";
  $("empty").querySelector("p").hidden = total > 0;
  updateControls();
}

async function refresh() {
  const data = await api("/api/records");
  records = data.records;
  total = data.total;
  render();
}

function showReport(report) {
  const counts = `${report.added.length} yeni seri eklendi. ${report.duplicates.length} tekrar atlandı. ${report.errors.length} hatalı kayıt.`;
  const summary = report.added.length ? report.added.join(" · ")
    : report.duplicates.length ? `Zaten kayıtlı: ${report.duplicates.join(" · ")}` : "";
  feedback(counts, summary, report.errors.length ? "error" : report.duplicates.length ? "warning" : "", report.errors);
}

function submitScan() {
  if (resetBusy) return;
  const text = $("scan").value;
  if (!text.trim()) return;
  // Girdi hemen boşalır; ikinci okuma ilk isteğin yanıtı beklenirken de korunur.
  $("scan").value = "";
  scannerTailUntil = performance.now() + 250;
  focusScanner();
  pendingScans += 1;
  updateControls();
  scanQueue = scanQueue.then(async () => {
    try {
      const report = await api("/api/scan", {text});
      showReport(report);
      await refresh();
    } catch (error) {
      // Ağ/disk hatasında okutulan metni kaybetme.
      $("scan").value = text + ($("scan").value ? "\n" + $("scan").value : "");
      feedback("Kayıt tamamlanamadı.", `${error.message} Okutulan metin giriş alanına geri kondu.`, "error");
    } finally {
      pendingScans -= 1;
      updateControls();
    }
  });
}

function insertControl(character) {
  const input = $("scan");
  input.setRangeText(character, input.selectionStart, input.selectionEnd, "end");
}

$("save").addEventListener("click", submitScan);
$("scan").addEventListener("keydown", (event) => {
  const action = SFPScanner.keyAction(event, $("scan").value, performance.now() < scannerTailUntil);
  if (action.type === "pass") return;
  event.preventDefault();
  if (action.type === "insert") insertControl(action.text);
  else if (action.type === "submit") submitScan();
});
$("scan").addEventListener("paste", (event) => {
  const text = event.clipboardData.getData("text/plain");
  if (text) { event.preventDefault(); insertControl(text); }
});
for (const name of ["focus", "blur"]) $("scan").addEventListener(name, () => {
  const focused = document.activeElement === $("scan");
  $("focus-state").textContent = focused ? "Okuyucu hazır" : "Okutmak için alana tıklayın";
  $("focus-state").classList.toggle("inactive", !focused);
});
$("search").addEventListener("input", render);
$("file").addEventListener("change", async () => {
  const file = $("file").files[0];
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) {
    feedback("Dosya alınamadı.", "En fazla 20 MB büyüklüğünde bir dosya seçin.", "error");
    $("file").value = ""; return;
  }
  importBusy = true;
  updateControls();
  feedback("Dosya okunuyor…", file.name);
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("Dosya okunamadı."));
      reader.readAsDataURL(file);
    });
    showReport(await api("/api/import", {filename: file.name, data: dataUrl.split(",")[1]}));
    await refresh();
  } catch (error) { feedback("Dosya alınamadı.", error.message, "error"); }
  finally { $("file").value = ""; importBusy = false; updateControls(); focusScanner(); }
});
$("copy").addEventListener("click", async () => {
  try {
    const data = await api("/api/serials");
    const text = data.serials.join("\n");
    if (window.webkit?.messageHandlers?.copySerials) {
      await window.webkit.messageHandlers.copySerials.postMessage(text);
    } else if (window.pywebview?.api?.copy_serials) {
      await window.pywebview.api.copy_serials(text);
    } else {
      await navigator.clipboard.writeText(text);
    }
    feedback(`${data.serials.length} seri numarası kopyalandı.`, "Excel'e yapıştırabilirsiniz.");
  } catch (error) { feedback("Kopyalanamadı.", "TXT indir düğmesini kullanabilirsiniz. " + error.message, "error"); }
});
$("reset").addEventListener("click", async () => {
  if (resetBusy || importBusy || pendingScans > 0 || total === 0) return;
  resetBusy = true;
  updateControls();
  try {
    await refresh();
    if (total === 0) {
      feedback("Liste zaten boş.");
      return;
    }
    const confirmed = window.confirm(
      `Kayıtlı ${total.toLocaleString("tr-TR")} seri numarasının tamamı silinecek.\n` +
      "Bu işlem geri alınamaz.\n\nListeyi sıfırlamak istiyor musunuz?"
    );
    if (!confirmed) return;
    const report = await api("/api/reset", {confirm: true, expected_count: total});
    $("search").value = "";
    records = [];
    total = 0;
    render();
    feedback(`${report.deleted} kayıt silindi. Liste sıfırlandı.`, "Yeni karekodlar okutabilirsiniz.");
    await refresh();
  } catch (error) {
    feedback("Liste sıfırlanamadı.", error.message, "error");
    await refresh().catch(() => {});
  } finally {
    resetBusy = false;
    updateControls();
    focusScanner();
  }
});
refresh().catch((error) => feedback("Liste yüklenemedi.", "Uygulamanın çalıştığını kontrol edin. " + error.message, "error"));
