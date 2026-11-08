/* Praça de imersão "Flanar pela vila": tocar nas pessoas toca falas curtas (vozes variadas).
   Sem progresso, sem XP, nada é salvo (nem no servidor, nem no aparelho). */
(() => {
  "use strict";
  const D = JSON.parse(document.getElementById("dados-praca").textContent);
  const CFG = JSON.parse(document.getElementById("cfg-praca").textContent);
  const palco = document.getElementById("palco");
  const quem = document.getElementById("quem");
  const fr = document.getElementById("fala-fr");
  const pt = document.getElementById("fala-pt");
  const transc = document.getElementById("transcricao");
  const deNovo = document.getElementById("ouvir-de-novo");
  const btTransc = document.getElementById("mostrar-transcricao");
  const player = new Audio();
  const indice = {};
  let ultima = null, mostrar = !!CFG.transcricao;

  function pintar() {
    transc.hidden = !mostrar || !ultima;
    btTransc.setAttribute("aria-pressed", String(mostrar));
    btTransc.textContent = mostrar ? "Esconder transcrição" : "Mostrar transcrição";
  }
  function tocar(f) {
    player.pause(); player.src = CFG.audio + f.audio + ".mp3";
    const p = player.play(); if (p && p.catch) p.catch(() => {});
  }
  function falar(pessoa, semSom) {
    const k = indice[pessoa.id] = ((indice[pessoa.id] ?? -1) + 1) % pessoa.falas.length;
    const f = pessoa.falas[k];
    ultima = f;
    quem.textContent = pessoa.nome;
    fr.textContent = f.fr; pt.textContent = f.pt;
    deNovo.disabled = false;
    document.querySelectorAll(".pessoa").forEach(b => b.classList.toggle("falando", b.dataset.id === pessoa.id));
    pintar();
    if (!semSom) tocar(f);
  }
  D.pessoas.forEach(p => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "pessoa"; b.dataset.id = p.id;
    b.style.cssText = `left:${p.x}%;top:${p.y}%;width:${p.w}%;height:${p.h}%`;
    b.setAttribute("aria-label", p.nome + " — ouvir");
    b.innerHTML = '<span class="bolha" aria-hidden="true">…</span>';
    b.addEventListener("click", () => { if (!arrastou) falar(p); });
    palco.appendChild(b);
  });
  deNovo.addEventListener("click", () => { if (ultima) tocar(ultima); });
  btTransc.addEventListener("click", () => { mostrar = !mostrar; pintar(); });

  /* retrato: cena mais larga que a tela → arrastar para os lados (ou botões ‹ ›) */
  let pan = 0, arrastou = false;
  function limite() { const W = palco.getBoundingClientRect().width; return Math.max(0, (W - innerWidth) / 2); }
  function aplicar() { const L = limite(); pan = Math.max(-L, Math.min(L, pan)); palco.style.setProperty("--pan", pan + "px");
    document.querySelectorAll(".lado-pan").forEach(b => { b.hidden = L < 2; }); }
  let ini = null;
  palco.addEventListener("pointerdown", e => { ini = { x: e.clientX, p: pan }; arrastou = false; });
  addEventListener("pointermove", e => { if (!ini) return; const dx = e.clientX - ini.x; if (Math.abs(dx) > 6) arrastou = true; if (arrastou) { pan = ini.p + dx; aplicar(); } });
  addEventListener("pointerup", () => { ini = null; setTimeout(() => { arrastou = false; }, 0); });
  document.getElementById("pan-esq").addEventListener("click", () => { pan += innerWidth * 0.6; aplicar(); });
  document.getElementById("pan-dir").addEventListener("click", () => { pan -= innerWidth * 0.6; aplicar(); });
  addEventListener("resize", aplicar); aplicar();

  pintar();
  if (CFG.pessoa) {
    const p = D.pessoas.find(x => x.id === CFG.pessoa);
    if (p) { pan = palco.getBoundingClientRect().width * (0.5 - (p.x + p.w / 2) / 100); aplicar(); falar(p, true); }
  }
})();
