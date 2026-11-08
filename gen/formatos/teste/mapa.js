// Mapa (jsdom): 40 paradas, 5–8 reais, ponto da praça fora da trilha, clique navega, arrasto não navega.
const { JSDOM, CookieJar, VirtualConsole } = require("jsdom");
const BASE = process.env.CHEMIN_TEST_BASE || "http://localhost:5077", jar = new CookieJar(), sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  await JSDOM.fromURL(BASE + "/__login-teste?ir=/mapa", { cookieJar: jar }).catch(() => {});
  const nav = [], erros = []; const vc = new VirtualConsole();
  vc.on("jsdomError", e => { if (/navigation/i.test(e.message)) nav.push(e.message); else erros.push(e.message); });
  const dom = await JSDOM.fromURL(BASE + "/mapa?vista=regiao", { cookieJar: jar, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.HTMLMediaElement.prototype.play=()=>Promise.resolve(); w.HTMLMediaElement.prototype.pause=()=>{}; w.PointerEvent = class extends w.MouseEvent { constructor(t, o) { super(t, o); this.pointerId = o.pointerId; this.isPrimary = true; this.pointerType = "mouse"; } }; w.Element.prototype.setPointerCapture = function () {}; w.Element.prototype.releasePointerCapture = function () {}; w.Element.prototype.hasPointerCapture = function () { return true; }; w.matchMedia = () => ({ matches: false, addEventListener() {} }); w.requestAnimationFrame = f => setTimeout(() => f(w.performance.now()), 16);
      w.fetch = async (u, o) => { const r = await fetch(new URL(u, BASE), o); const t = await r.text(); return { ok: r.ok, status: r.status, json: async () => JSON.parse(t), text: async () => t }; }; } });
  const w = dom.window, d = w.document;
  await new Promise(r => w.addEventListener("load", r)); await sleep(800);
  const paradas = d.querySelectorAll(".parada"), ponto = d.getElementById("praca-ponto");
  const r = {};
  r.paradas = paradas.length; r.ponto = !!ponto; r.ponto_href = ponto && ponto.getAttribute("href");
  r.ponto_sem_numero = ponto && !/\d/.test(ponto.textContent);
  r.ponto_nao_desabilitado = ponto && !ponto.hasAttribute("disabled");
  const clique = el => el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  nav.length = 0; clique(paradas[4]); await sleep(50); r.clique_parada5_navega = nav.length > 0;
  nav.length = 0; clique(ponto); await sleep(50); r.clique_praca_navega = nav.length > 0;
  // arrasto começando no ponto da praça
  nav.length = 0;
  const vp = d.getElementById("vp");
  const pe = (tipo, x, alvo) => (alvo || vp).dispatchEvent(new w.PointerEvent(tipo, { bubbles: true, cancelable: true, clientX: x, clientY: 300, pointerId: 1, button: 0, buttons: 1, isPrimary: true }));
  if (w.PointerEvent) { pe("pointerdown", 400, ponto); await sleep(20); pe("pointermove", 430); await sleep(20); pe("pointermove", 480); await sleep(20); pe("pointerup", 480); clique(ponto); await sleep(50); r.arrasto_nao_navega = nav.length === 0; }
  else r.arrasto_nao_navega = "PointerEvent indisponível no jsdom";
  r.js_sem_erros=erros.length===0;
  if(r.paradas!==40 || r.ponto_href!=="/praca/1" || Object.entries(r).some(([k,v])=>!["paradas","ponto_href"].includes(k)&&v!==true))throw Error(JSON.stringify({r,erros}));
  console.log(JSON.stringify(r));
  w.close();
})().catch(e=>{console.error(e);process.exitCode=1});
