// Interacoes reais do JS do template renderizado, sem navegador/rede/microfone.
const { JSDOM } = require("jsdom");
const fs = require("fs"), assert = require("assert");
const html = fs.readFileSync(process.argv[2], "utf8");
let checks = 0;
const chk = (cond, msg) => { assert.ok(cond, msg); checks++; };
function abrir(modelo) {
  const enviados = [];
  const dom = new JSDOM(html, { url: `http://localhost:5000/nivelamento?parte=3&modelo=${modelo}`, runScripts: "dangerously",
    beforeParse(w) {
      w.matchMedia = () => ({ matches: true, addEventListener() {} });
      w.fetch = async (url, opcoes) => { enviados.push(JSON.parse(opcoes.body)); return { ok: true }; };
    } });
  return { dom, d: dom.window.document, enviados };
}
const parte = d => d.querySelector(".folha.ativa").dataset.parte;
const rodada = () => new Promise(resolve => setImmediate(resolve));
function ficha(d) {
  for (const [id, value] of Object.entries({ "f-prenom": "Alex", "f-age": "25", "f-ville": "Recife", "f-nat": "brésilien" })) d.getElementById(id).value = value;
  const proximo = d.querySelector('.folha[data-parte="3"] .passos .seguir');
  if (proximo) proximo.click();
}
async function terminar(d, enviados) {
  d.getElementById("g-pular").click(); // Mantem a opcao oral existente, sem acionar microfone.
  d.querySelector('.folha[data-parte="4"] .entregar').click();
  await rodada();
  chk(enviados.length === 1, "envio unico do teste");
  chk(parte(d) === "5", "avanca para respostas registradas");
  chk(d.querySelector('.folha[data-parte="5"] a').getAttribute("href") === "/missao", "proximo destino continua pergaminho");
}
(async () => {
  for (const modelo of [1, 2, 3]) {
    let { dom, d, enviados } = abrir(modelo);
    chk(parte(d) === "3", "abre escrita");
    chk(d.getElementById("e-pular").classList.contains("sec"), "botao secundario");
    d.getElementById("e-pular").click();
    chk(parte(d) === "4", "pular com ficha/texto vazios avanca para fala");
    await terminar(d, enviados);
    chk(enviados[0].escrita_pulada === true && enviados[0].item8 === "", "payload marca escrita pulada, nao resposta errada");
    dom.window.close();

    for (const palavras of [24, 25, 40, 41]) {
      ({ dom, d, enviados } = abrir(modelo));
      ficha(d);
      d.getElementById("f-msg").value = Array(palavras).fill("bonjour").join(" ");
      d.querySelector('.folha[data-parte="3"] .entregar').click();
      if (palavras < 25 || palavras > 40) {
        chk(parte(d) === "3", "nao pular conserva limite de palavras");
        chk(d.querySelector('.folha[data-parte="3"] .aviso').textContent.includes("25 e 40"), "aviso de tamanho existente");
        chk(enviados.length === 0, "escrita invalida nao envia");
      } else {
        chk(parte(d) === "4", "25 e 40 palavras continuam validas");
        await terminar(d, enviados);
        chk(enviados[0].escrita_pulada === false, "envio normal nao marcado pulado");
      }
      dom.window.close();
    }
    ({ dom, d, enviados } = abrir(modelo));
    d.getElementById("f-msg").value = Array(25).fill("bonjour").join(" ");
    d.querySelector('.folha[data-parte="3"] .entregar').click();
    chk(parte(d) === "3", "continuar normal ainda exige ficha");
    dom.window.close();
  }
  console.log(`${checks} verificacoes JS OK — pular/continuar nos modelos 1, 2 e 3`);
})().catch(erro => { console.error(erro); process.exitCode = 1; });
