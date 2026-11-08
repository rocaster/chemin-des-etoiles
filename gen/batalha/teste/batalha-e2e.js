// Batalha ponta a ponta (jsdom) contra o Flask offline na 5077 — v4: 5 barras, dano 1/2/3, Spécial por classe e reutilizável
// (combo zera depois dele), contra-ataque com DEFESA (dizer a palavra; sem microfone: escrever o que ouviu ou escolher entre 3).
// v7: ETAPA=N escolhe a etapa de batalha (padrão 11 = batalha final da vila; 40 = chefe do Castelo). Registro pelo id de conteúdo.
// v5: a batalha é a parada 9 (/parada/1/9): vitória → POST de conclusão (real) + localStorage libera a 10; derrota não salva.
//     Timer da defesa: TIMER=N (segundos; padrão do jogo 5; 0 desliga); defesa 'T' = não responder (tempo esgota → dano).
//     OCULTAR=1: na 1ª defesa a aba fica escondida 2,5 s (o timer deve pausar).
// Uso: node batalha-e2e.js <ataques C/E> <defesas B/F> [personagem] [inimigo] [reduzido 0|1] [modo opcoes|texto|voz]
//   ex.: node batalha-e2e.js CCECC BF 3 renard 1 voz   — C/E: ataque certo/errado; B/F: bloqueia/falha a defesa
//   VIDA_INIMIGO=N força mais vida só no teste (para ver o combo zerar depois do Spécial).
const { JSDOM, CookieJar } = require("jsdom");
const [ataques, defesas = "", pers = "1", ini = "", red = "1", modo = "opcoes"] = process.argv.slice(2);
const BASE = process.env.CHEMIN_TEST_BASE || "http://localhost:5077";
const jar = new CookieJar();
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  await JSDOM.fromURL(BASE + "/__login-teste?ir=/mapa", { cookieJar: jar }).catch(() => {});
  const ETAPA = process.env.ETAPA || "11";
  const url = `${BASE}/parada/1/${ETAPA}?personagem=${pers}${ini ? "&inimigo=" + ini : ""}${process.env.TIMER != null ? "&timer=" + process.env.TIMER : ""}`;
  const tocados = [], escritas = [], redes = [], falas = [];
  const dom = await JSDOM.fromURL(url, {
    cookieJar: jar, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: red === "1", addEventListener() {} });
      w.HTMLMediaElement.prototype.play = function () { tocados.push(this.src.replace(BASE, "")); setTimeout(() => this.dispatchEvent(new w.Event("ended")), 3); return Promise.resolve(); };
      w.HTMLMediaElement.prototype.pause = function () {};
      w.fetch = async (u, o = {}) => {   /* vai ao servidor de verdade, com o cookie do usuário de teste */
        const cookie = await jar.getCookieString(BASE);
        const r = await fetch(new URL(u, BASE), { ...o, headers: { ...(o.headers || {}), cookie } }); const t = await r.text();
        redes.push({ url: String(u), status: r.status, body: o.body ? JSON.parse(o.body) : null, resp: (() => { try { return JSON.parse(t); } catch (e) { return t.slice(0, 80); } })() });
        return { ok: r.ok, status: r.status, json: async () => JSON.parse(t) };
      };
      let oculto = false; Object.defineProperty(w.Document.prototype, "hidden", { get: () => oculto, configurable: true });
      w.__ocultar = v => { oculto = v; w.document.dispatchEvent(new w.Event("visibilitychange")); };
      const set = w.Storage.prototype.setItem; w.Storage.prototype.setItem = function (k, v) { escritas.push(k); return set.call(this, k, v); };
      if (modo === "voz") w.webkitSpeechRecognition = class { start() { setTimeout(() => { const t = falas.shift() || ""; this.onresult({ results: [[{ transcript: t }]] }); }, Number(process.env.VOZ_ATRASO || 5)); } abort() {} };   /* VOZ_ATRASO=ms: resultado da voz demora */
    }
  });
  const w = dom.window, d = w.document, $ = s => d.querySelector(s);
  await new Promise(r => w.addEventListener("load", r)); await sleep(50);
  const B = w.chemin_batalha, E = B.estado;
  if (process.env.VIDA_INIMIGO) E.vidaI = Number(process.env.VIDA_INIMIGO);
  const clique = el => el.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const perguntadas = [], combos = [], log = [];
  let ia = 0, id = 0, defesasVistas = 0, contraAposFinal = false, painelDefesaLook = null, pausouOculto = null;
  clique($("#comecar"));
  for (let passo = 0; passo < 3000 && !E.fim; passo++) {
    await sleep(10);
    const def = $("#faixa-defesa");
    if (def && !(($("#falar-defesa") || $("#conferir-defesa") || $(".opcao")) || {}).disabled && E.defesaAtual && E.defesas.length < defesasVistas + 1) {
      if (id >= defesas.length) break;
      const letra = defesas[id++], it = E.defesaAtual, bloq = letra === "B"; defesasVistas++;
      if (letra === "T" || (process.env.OCULTAR && defesasVistas === 1)) {   /* não responder: espera o timer */
        const t0 = Date.now();
        if (process.env.OCULTAR && defesasVistas === 1) {
          await sleep(200); w.__ocultar(true); await sleep(2500); const aindaAberta = E.defesas.length < defesasVistas; w.__ocultar(false);
          log.push(`   aba escondida 2,5 s: defesa ainda aberta = ${aindaAberta}`); pausouOculto = aindaAberta;
        }
        const vh = E.vidaH; let t = 0; while (E.defesas.length < defesasVistas && t++ < 800) await sleep(20);
        log.push(`DT ${it.fr} (sem resposta) → ${E.defesas[E.defesas.length - 1].modo} em ${((Date.now() - t0) / 1000).toFixed(1)} s`);
        t = 0; while (!E.fim && !(E.atual && !E.ocupado && !$("#faixa-defesa")) && t++ < 300) await sleep(20);
        log.push(`   vidaH ${vh}->${E.vidaH}`);
        continue;
      }
      painelDefesaLook = painelDefesaLook || { classe: $("#pergunta").className, banner: def.textContent, alvo: $("#alvo-defesa").textContent };
      log.push(`D${bloq ? "B" : "F"} ${it.fr} (${it.tipo}) modo=${modo}`);
      if (modo === "voz") { falas.push(bloq ? (it.tipo === "numero" ? it.pt : it.fr) : "banane"); clique($("#falar-defesa")); }
      else if (modo === "texto") { if (!$("#resposta-defesa")) { clique($('button[data-modo="texto"]')); await sleep(10); } $("#resposta-defesa").value = bloq ? it.fr.toUpperCase() : "banane"; clique($("#conferir-defesa")); }
      else { const ops = [...d.querySelectorAll(".opcao")]; clique(ops.find(b => (b.dataset.fr === it.fr) === bloq)); }
      const vh = E.vidaH; let t = 0; while (E.defesaAtual && $("#faixa-defesa") && t++ < 300) { await sleep(20); if (!$("#faixa-defesa")) break; if (E.atual && !E.ocupado) break; }
      log.push(`   vidaH ${vh}->${E.vidaH} combo=${E.combo}`);
      continue;
    }
    const op = $(".opcao:not([disabled])");
    if (op && !def && !E.ocupado) {
      if (ia >= ataques.length) break;
      const p = ataques[ia++];
      perguntadas.push(E.atual.item.fr);
      const P = E.atual, certaI = P.opcoes.indexOf(P.item), i = p === "C" ? certaI : (certaI + 1) % 3;
      clique(d.querySelectorAll(".opcao")[i]);
      await sleep(5);
      combos.push($("#combo").hidden ? "-" : $("#combo-n").textContent + " " + $("#combo-tipo").textContent);
      log.push(`A${p} combo=${E.combo} vidaI=${E.vidaI}`);
    }
  }
  await sleep(red === "1" ? 600 : 4000);
  if (E.salvo) await E.salvo;
  const ls = k => w.localStorage.getItem(k);
  const fim = d.body.classList.contains("vitoria") ? "VITORIA" : d.body.classList.contains("derrota") ? "DERROTA" : "em-curso";
  if (fim === "VITORIA" && $("#faixa-defesa")) contraAposFinal = true;
  console.log(log.join("\n"));
  console.log(JSON.stringify({ fim, combos: combos.join(","), defesas: E.defesas.map(x => (x.ok ? "B:" : "F:") + x.fr + "/" + x.modo).join(","),
    repetidasDefesa: E.defesas.length - new Set(E.defesas.map(x => x.fr)).size, repetidasAtaque: perguntadas.length - new Set(perguntadas).size,
    contraAposFinal, painelDefesa: painelDefesaLook, painelSpecial: !!$('#legenda li[data-tipo="special"]'), comboFinal: E.combo,
    especiais: E.especiais || 0, danoTotal: E.danoTotal || 0, vidaH: E.vidaH, vidaI: E.vidaI,
    segmentos: d.querySelectorAll("#barra-inimigo i").length + "/" + d.querySelectorAll("#barra-heroi i").length,
    heroiImg: ([...d.querySelectorAll("style")].map(x => x.textContent).join("").match(/heroi-([a-z-]+)\.png/) || [])[1], inimigo: B.inimigo,
    sons: tocados.filter(s => s.includes("som-")).map(s => s.split("/").pop().replace(".wav", "")).join(","),
    pausouOculto, golpes: E.golpes, timerDefesa: E.timerDefesa ? E.timerDefesa.total / 1000 : null,
    mapaAtual: ls("chemin_teste_mapa_r1_atual"), registro: (JSON.parse(ls("chemin_teste_paradas") || "{}")[B.dados.id ? w.JSON.parse(d.getElementById("cfg-batalha").textContent).pid : ""] || null), etapa: ETAPA, vidaMaxI: B.dados.regras.vida_inimigo, chefe: d.body.classList.contains("chefe"), msgSub: (d.getElementById("msg-sub") || {}).textContent,
    voltar: $("#voltar-mapa").getAttribute("href"), msgSub: $("#msg-sub").textContent.slice(0, 90),
    vozesDefesa: tocados.filter(s => /\/n-\d\d\.mp3|bloque\.mp3/.test(s)).length, redes, escritas, msg: $("#msg-titulo").textContent }));
  process.exit(0);
})().catch(e => { console.error("FALHOU", e); process.exit(1); });
