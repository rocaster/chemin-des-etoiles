// Fluxo ponta a ponta (jsdom) dos formatos (conversa, história, biblioteca, cartas) contra o Flask offline na 5077.
// v6: <n> é a ETAPA da trilha (ordem em data/regioes/r1.json: 2 traversier, 6 cartas, 9 bardo, 10 biblioteca); o registro é pelo id de conteúdo.
// Uso: node fluxo.js <n> <teste|normal> <texto|voz|auto> [erros]   — erros: quantas respostas erradas de propósito
const { JSDOM, CookieJar } = require("jsdom");
const [n, quem, modo, nErr = "1"] = process.argv.slice(2);
const BASE = process.env.CHEMIN_TEST_BASE || "http://localhost:5077";
const jar = new CookieJar();
const sleep = ms => new Promise(r => setTimeout(r, ms));
let errosQuero = Number(nErr);
(async () => {
  if (quem === "teste") await JSDOM.fromURL(BASE + "/__login-teste?ir=/parada/1/" + n, { cookieJar: jar }).catch(() => {});
  const falas = [];
  const dom = await JSDOM.fromURL(BASE + "/parada/1/" + n, {
    cookieJar: jar, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addEventListener() {} });
      w.HTMLElement.prototype.scrollIntoView = function () {};
      w.HTMLMediaElement.prototype.play = function () { setTimeout(() => this.dispatchEvent(new w.Event("ended")), 3); return Promise.resolve(); };
      w.HTMLMediaElement.prototype.pause = function () {};
      w.__posts = [];
      w.fetch = async (url, o) => {
        const cookie = await jar.getCookieString(BASE);
        const r = await fetch(new URL(url, BASE), { ...o, headers: { ...(o.headers || {}), cookie } });
        const corpo = await r.text(); w.__posts.push({ url, status: r.status, body: o.body, resp: corpo });
        return { ok: r.ok, status: r.status, json: async () => JSON.parse(corpo) };
      };
      if (modo === "voz") {
        w.webkitSpeechRecognition = class { start() { setTimeout(() => { const t = falas.shift() || ""; this.onresult({ results: [[{ transcript: t }]] }); }, 5); } abort() {} };
      } else if (modo === "negado") {
        w.webkitSpeechRecognition = class { start() { setTimeout(() => this.onerror({ error: "not-allowed" }), 5); } abort() {} };
      }
    }
  });
  const w = dom.window, d = w.document;
  await new Promise(r => w.addEventListener("load", r));
  await sleep(50);
  const D = w.chemin_formato.dados;
  const $ = s => d.querySelector(s);
  const clique = el => el.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const log = [];
  const certasTexto = new Set();
  (D.perguntas || []).forEach(q => certasTexto.add(q.opcoes[q.correta]));
  (D.pergaminhos || []).forEach(p => certasTexto.add(p.pergunta.opcoes[p.pergunta.correta]));
  let respostaCerta = "", passos = 0, forjaErrei = false;
  const respostaAtual = () => {
    if (D.formato === "conversa") { const m = $(".fala-modelo"); return m ? m.textContent : ""; }
    if (D.formato === "cartas") { const s = $(".carta.sel"); return s ? D.cartas.find(c => c.id === s.dataset.id).fr : ""; }
    return "";
  };
  const responder = (via) => {
    const certo = respostaAtual(); const errar = errosQuero > 0; if (errar) errosQuero--;
    const txt = errar ? "je ne sais pas" : certo;
    log.push((errar ? "ERRO " : "ok ") + via + ": " + txt);
    if (via === "texto") { $("#resposta-texto").value = txt; clique($("#conferir")); }
    else if (via === "voz") { falas.push(txt); clique($("#falar")); }
    else clique($(errar ? "#auto-errado" : "#auto-certo"));
  };
  while (passos++ < 400) {
    await sleep(modo === "voz" ? 30 : 15);
    if ($("#ir-mapa")) break;
    if ($("#comecar")) { clique($("#comecar")); continue; }
    if ($("#continuar")) { clique($("#continuar")); continue; }
    if ($("#terminar")) { clique($("#terminar")); continue; }
    if ($("#forja-revelar") && !$("#forja-revelar").hidden) { clique($("#forja-revelar")); continue; }
    if ($("#forja-errei") && !$("#forja-errei").parentNode.hidden) { clique($(forjaErrei ? "#forja-facil" : "#forja-errei")); log.push("forja " + (forjaErrei ? "fácil" : "errei")); forjaErrei = true; await sleep(600); continue; }
    if (D.formato === "cartas" && !$(".carta.sel")) {
      const c = [...d.querySelectorAll(".carta")].find(b => !b.disabled && !b.classList.contains("saiu") && !b.classList.contains("espera") && !b.classList.contains("saindo"));
      if (c) { clique(c); continue; }
      await sleep(400); continue;
    }
    if ($("#auto-certo")) { responder("auto"); continue; }
    if ($("#falar") && modo === "voz") { responder("voz"); await sleep(40); continue; }
    if ($("#autoavaliar") && modo === "auto") { clique($("#autoavaliar")); continue; }
    if ($("#resposta-texto")) { responder("texto"); continue; }
    if ($("#falar")) { clique($("#falar")); await sleep(40); continue; }   /* negado: cai para texto */
    if ($("#conferir-ordem")) {
      const banco = $(".ordem-banco");
      for (let k = 0; k < 4; k++) clique(banco.querySelector(`[data-k="${k}"]`));
      clique($("#conferir-ordem")); log.push("ordenar"); continue;
    }
    if (D.formato === "biblioteca" && $(".pergaminho")) {
      const novos = [...d.querySelectorAll(".termo.nova[data-id]")];
      if (novos.length > 3) { clique(novos[0]); await sleep(5); if ($("#guardar")) { clique($("#guardar")); log.push("grimório + " + novos[0].dataset.id); } continue; }
    }
    const ops = [...d.querySelectorAll(".opcao:not([disabled])")];
    if (ops.length) {
      const errar = errosQuero > 0 && D.formato !== "historia" ? false : false;
      const alvo = ops.find(o => certasTexto.has(o.textContent)) || ops[0];
      if (errosQuero > 0) { errosQuero--; const e = ops.find(o => o !== alvo); clique(e); log.push("ERRO opção: " + e.textContent); }
      else { clique(alvo); log.push("ok opção: " + alvo.textContent); }
      continue;
    }
  }
  await sleep(300);
  const g = w.localStorage;
  const cfgP = JSON.parse(d.getElementById("cfg-parada").textContent), pre = cfgP.prefixo;
  console.log(JSON.stringify({
    parada: n, quem, modo, passos, fim: !!$("#ir-mapa"), estado: w.chemin_formato.estado,
    mapa: $("#ir-mapa") && $("#ir-mapa").getAttribute("href"), nota: $("#nota-salvar") && $("#nota-salvar").textContent,
    posts: w.__posts.map(p => ({ status: p.status, body: p.body, resp: p.resp.slice(0, 200) })),
    ls_atual: g.getItem(pre + "mapa_r1_atual"), ls_parada: JSON.parse(g.getItem(pre + "paradas") || "{}")[cfgP.pid], pid: cfgP.pid,
    grimorio: g.getItem(pre + "grimorio") ? Object.keys(JSON.parse(g.getItem(pre + "grimorio"))).length : 0,
    log
  }, null, 1));
  w.close();
})().catch(e => { console.error("FALHOU", e); process.exit(1); });
