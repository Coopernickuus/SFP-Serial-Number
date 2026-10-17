const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const scanner = require('../ui/scanner_input.js');
const raw = '[)>6]1P471880A.101]SHA20230240976]Q1]10D2023]52PMXPD-243SI01]1V9W]18VLENSN]4LCN';

test('okuyucu Tab ve Enter sonlandırıcılarını kaydeder; normal klavye gezinmesini korur', () => {
  assert.equal(scanner.keyAction({key:'Tab'}, raw).type, 'submit');
  assert.equal(scanner.keyAction({key:'Enter'}, raw).type, 'submit');
  assert.equal(scanner.keyAction({key:'Tab'}, '').type, 'pass');
  assert.equal(scanner.keyAction({key:'Tab', shiftKey:true}, raw).type, 'pass');
  assert.equal(scanner.keyAction({key:'Enter', shiftKey:true}, raw).type, 'pass');
  assert.equal(scanner.keyAction({key:'Enter', isComposing:true}, raw).type, 'pass');
});

test('okutma sonu gezinme tuşlarını tüketir, sonraki normal gezinmeye izin verir', () => {
  for (const key of ['Tab','End','PageDown','ArrowDown']) {
    assert.notEqual(scanner.keyAction({key}, '', true).type, 'pass');
    assert.equal(scanner.keyAction({key}, '', false).type, 'pass');
  }
  assert.equal(scanner.keyAction({key:'End', ctrlKey:true}, raw).type, 'suppress');
});

test('eski GS tuş birleşimlerini ve yeni düz ] karakterini ayırır', () => {
  assert.deepEqual(scanner.keyAction({key:']', code:'BracketRight', ctrlKey:true}, raw), {type:'insert', text:'␝'});
  assert.equal(scanner.keyAction({key:']', code:'BracketRight'}, raw).type, 'pass');
  assert.equal(scanner.keyAction({key:'m', ctrlKey:true}, raw).type, 'submit');
});

function createUI() {
  const elements = new Map();
  const posted = [];
  const document = {activeElement:null};
  class Element {
    constructor() { this.value=''; this.listeners={}; this.children={}; this.scrollLeft=50; this.scrollTop=50; this.classList={toggle(){}}; }
    addEventListener(name, handler) { this.listeners[name]=handler; }
    querySelector(name) { return this.children[name] ||= new Element(); }
    replaceChildren() {}
    append() {}
    focus(options) { document.activeElement=this; this.focusOptions=options; }
    setRangeText(text) { this.value+=text; }
  }
  document.getElementById = (id) => { if (!elements.has(id)) elements.set(id,new Element()); return elements.get(id); };
  document.querySelector = () => ({content:'token'});
  document.createElement = () => new Element();
  const fetch = async (url, options) => {
    let result;
    if (url === '/api/scan') {
      posted.push(JSON.parse(options.body));
      result={added:['DEMO'+posted.length],duplicates:[],errors:[],ignored:0,total:posted.length};
    } else {
      result={records:posted.map((_,i)=>({serial:'DEMO'+i,captured_at:'2026-10-17T08:00:00Z',source:'Okuyucu'})),total:posted.length};
    }
    return {ok:true,json:async()=>result};
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../ui/app.js'),'utf8'), {
    document, fetch, SFPScanner:scanner, performance:{now:()=>1000},
    window:{confirm:()=>false}, navigator:{clipboard:{writeText:async()=>{}}}
  });
  const input = document.getElementById('scan');
  const key = (name, extra={}) => {
    const event={key:name,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;},...extra};
    input.listeners.keydown(event);
    if (name === 'Tab' && !event.defaultPrevented) document.activeElement = document.getElementById('save');
    return event;
  };
  return {input, key, posted, document, elements};
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('gerçek giriş kodu Tab sonrası odağı korur ve yalnız bir kayıt isteği gönderir', async () => {
  const ui=createUI();
  await settle();
  ui.input.value=raw;
  ui.input.focus();
  assert.equal(ui.key('Tab').defaultPrevented,true);
  assert.equal(ui.input.value,'');
  assert.equal(ui.document.activeElement,ui.input);
  assert.equal(ui.input.focusOptions.preventScroll,true);
  assert.equal(ui.input.scrollLeft,0);
  ui.key('Tab');
  ui.key('End',{ctrlKey:true});
  await settle();
  assert.deepEqual(ui.posted,[{text:raw}]);
  assert.equal(ui.document.activeElement,ui.input);
});

test('peş peşe okutmalar yanıt beklenirken kaybolmaz', async () => {
  const ui=createUI();
  await settle();
  ui.input.value=raw;
  ui.key('Enter');
  const second=raw.replace('HA20230240976','MA18210960908');
  ui.input.value=second;
  ui.key('Tab');
  await settle();
  assert.deepEqual(ui.posted,[{text:raw},{text:second}]);
  assert.equal(ui.elements.get('total').textContent,'2');
});
