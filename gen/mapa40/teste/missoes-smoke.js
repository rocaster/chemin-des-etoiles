// Fumaça (jsdom) das missões de blocos das etapas 12–38 no motor existente (motor.js, sem alterações):
// abre cada item de cada bloco pela prévia (?bloco=B&item=K), confere que o item aparece sem erro de JS;
// no diálogo, percorre o caminho certo até "fim"; e a tela de recompensa. Precisa do Flask offline na 5077.
const { JSDOM, VirtualConsole, CookieJar } = require("/workspace/ncl/gen/formatos/teste/node_modules/jsdom");
const BASE = process.env.CHEMIN_TEST_BASE || "http://localhost:5077";
const jar = new CookieJar();
const ETAPAS = [12, 15, 18, 21, 23, 25, 28, 30, 33, 36, 38];
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function abre(url) {
  const erros = []; const vc = new VirtualConsole(); vc.on("jsdomError", e => erros.push(String(e.message || e))); vc.on("error", e => erros.push(String(e)));
  const dom = await JSDOM.fromURL(BASE + url, { cookieJar:jar, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.matchMedia = () => ({ matches: true, addEventListener() {} }); w.HTMLElement.prototype.scrollIntoView = function () {};
      w.HTMLMediaElement.prototype.play = function () { setTimeout(() => this.dispatchEvent(new w.Event("ended")), 3); return Promise.resolve(); };
      w.HTMLMediaElement.prototype.pause = function () {}; w.fetch = async () => ({ ok: false, status: 503, json: async () => ({}) }); } });
  await new Promise(r => dom.window.addEventListener("load", r)); await sleep(80);
  return { w: dom.window, d: dom.window.document, erros };
}
(async () => {
  const login=await JSDOM.fromURL(BASE+"/__login-teste?ir=/mapa",{cookieJar:jar});login.window.close();
  let ok = 0, falhas = [];
  for (const n of ETAPAS) {
    const { w } = await abre(`/parada/1/${n}`); const D = w.chemin_parada.dados; w.close();
    for (let b = 1; b <= D.blocos.length; b++) for (let k = 1; k <= D.blocos[b - 1].itens.length; k++) {
      const it = D.blocos[b - 1].itens[k - 1];
      const { w, d, erros } = await abre(`/parada/1/${n}?bloco=${b}&item=${k}${it.tipo === "dialogo" ? "&estado=dialogo" : ""}`);
      const txt = (d.getElementById("conteudo") || d.body).textContent;
      const temItem = txt.length > 20 && (d.querySelectorAll(".opcao, .ficha, input, button").length > 0);
      let dialogoOk = true;
      if (it.tipo === "dialogo") {   /* caminho certo inteiro: clica sempre na 1ª opção sem erro */
        for (let passo = 0; passo < 8; passo++) {
          await sleep(60);
          const ops = [...d.querySelectorAll(".opcao")]; if (!ops.length) break;
          const no = Object.values(it.nos).find(x => d.body.textContent.includes(x.fala)); if (!no) break;
          const i = no.opcoes.findIndex(o => !o.erro); if (i < 0 || !ops[i]) { dialogoOk = false; break; }
          ops[i].click();
        }
      }
      if (temItem && !erros.length && dialogoOk) ok++; else falhas.push({ n, b, k, tipo: it.tipo, erros, temItem, dialogoOk });
      w.close();
    }
    const r = await abre(`/parada/1/${n}?tela=recompensa`);
    if (r.d.body.textContent.includes("Mission accomplie") || r.d.body.textContent.includes("concluída")) ok++; else falhas.push({ n, tela: "recompensa", erros: r.erros });
    r.w.close();
  }
  console.log(JSON.stringify({ ok, falhas }, null, 1));
  process.exit(falhas.length ? 1 : 0);
})();
