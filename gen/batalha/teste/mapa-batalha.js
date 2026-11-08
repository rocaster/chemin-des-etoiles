// Mapa (jsdom) v6: batalhas nas ETAPAS 4, 8 e 11 da trilha (selo de espadas + anel + "Étape N"), sem ponto solto; praça intacta.
// Uso: node mapa-batalha.js [atual] — LS='{"chave":"valor"}' pré-carrega o localStorage (ex.: progresso antigo, para testar a migração).
const { JSDOM, CookieJar, VirtualConsole } = require("jsdom");
const BASE = process.env.CHEMIN_TEST_BASE || "http://localhost:5077", jar = new CookieJar(), sleep = ms => new Promise(r => setTimeout(r, ms));
const atual = process.argv[2] || "";
(async () => {
  await JSDOM.fromURL(BASE + "/__login-teste?ir=/mapa", { cookieJar: jar }).catch(() => {});
  const nav = []; const vc = new VirtualConsole();
  vc.on("jsdomError", e => { if (/navigation/i.test(e.message)) nav.push(e.message); else console.log("ERRO JS", e.message); });
  const dom = await JSDOM.fromURL(BASE + "/mapa?vista=regiao", { cookieJar: jar, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.matchMedia = () => ({ matches: false, addEventListener() {} }); w.requestAnimationFrame = f => setTimeout(() => f(w.performance.now()), 16);
      if (atual) { w.localStorage.setItem("chemin_teste_mapa_r1_atual", atual); w.localStorage.setItem("chemin_teste_mapa_r1_versao", "2"); }
      Object.entries(JSON.parse(process.env.LS || "{}")).forEach(([k, v]) => w.localStorage.setItem(k, v));
      w.fetch = async (u, o) => { const r = await fetch(new URL(u, BASE), o); const t = await r.text(); return { ok: r.ok, status: r.status, json: async () => JSON.parse(t), text: async () => t }; }; } });
  const w = dom.window, d = w.document;
  await new Promise(r => w.addEventListener("load", r)); await sleep(800);
  const ps = [...d.querySelectorAll(".parada")], pos = await (await fetch(BASE + "/static/mapa/regiao-1-paradas.json")).json();
  const lista = Array.isArray(pos) ? pos : (pos.paradas || []);
  const r = {
    paradas: ps.length,
    sem_ponto_solto: !d.getElementById("batalha-ponto") && !d.querySelector(".batalha-ponto"),
    praca: !!d.getElementById("praca-ponto") && d.getElementById("praca-ponto").getAttribute("href") === "/praca/1",
    batalhas: ps.map((b, i) => b.classList.contains("batalha") && b.querySelector(".selo-batalha") ? i + 1 : 0).filter(Boolean).join(","),
    etiquetas_batalha: [4, 8, 11].map(n => ps[n - 1].querySelector(".etq").textContent).join(","),
    aria_4: ps[3].getAttribute("aria-label"),
    trilha_intacta: lista.length === ps.length && ps.every((b, i) => b.style.left === lista[i].x + "%" && b.style.top === lista[i].y + "%"),
    estados_1a12: ps.slice(0, 12).map(b => ({ feita: "F", atual: "A", bloqueada: "-" })[["feita", "atual", "bloqueada"].find(c => b.classList.contains(c))]).join(""),
    ls_atual: w.localStorage.getItem("chemin_teste_mapa_r1_atual"), ls_versao: w.localStorage.getItem("chemin_teste_mapa_r1_versao"),
    painel: d.getElementById("p-parada").textContent
  };
  const clique = el => el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  nav.length = 0; clique(ps[3]); await sleep(50); r.clique_4_navega = nav.length > 0;
  console.log(JSON.stringify(r)); w.close();
})();
