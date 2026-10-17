(function (root) {
  "use strict";
  function looksLikeBarcode(text) {
    return text.includes("[)>") || /[\x1d␝\]]S/.test(text);
  }

  function keyAction(event, text, trailing = false) {
    if (event.isComposing) return {type: "pass"};
    const key = event.key;
    if (event.ctrlKey && !event.altKey && !event.metaKey) {
      if (key === "]" || event.code === "BracketRight") return {type: "insert", text: "␝"};
      if (key === "^" || (event.shiftKey && event.code === "Digit6")) return {type: "insert", text: "␞"};
      if (key.toLowerCase() === "d") return {type: "insert", text: "␄"};
      if (["m", "j"].includes(key.toLowerCase())) return {type: "submit"};
    }
    if (key === "Enter" && !event.shiftKey) return {type: "submit"};
    if (key === "Tab" && !event.shiftKey && (looksLikeBarcode(text) || trailing)) {
      return {type: "submit"};
    }
    // Bazı okuyucuların okuma sonunda yolladığı gezinme tuşları odağı kaydırmasın.
    if (trailing && ["End", "PageDown", "ArrowDown"].includes(key)) return {type: "suppress"};
    if (event.ctrlKey && key === "End" && looksLikeBarcode(text)) return {type: "suppress"};
    return {type: "pass"};
  }

  const api = {looksLikeBarcode, keyAction};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SFPScanner = api;
})(globalThis);
