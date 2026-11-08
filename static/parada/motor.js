/* Motor de paradas do Chemin des Étoiles.
   Lê o JSON da parada (blocos → itens) e monta cada atividade com um dos 8 componentes:
   imagem, pares, texto, audio, ordenar, lacuna (banco | digitar | ditado), dialogo, producao.
   Erro: mostra a resposta certa + explicação e devolve o item ao fim do bloco (nova chance), sem vidas.
   O bloco marcado "recuperar" recebe os itens errados da parada antes dos seus próprios itens. */
(() => {
  "use strict";
  const D = JSON.parse(document.getElementById("dados-parada").textContent);
  const CFG = JSON.parse(document.getElementById("cfg-parada").textContent);
  const PREVIA = CFG.previa || {};
  const EM_PREVIA = Object.keys(PREVIA).length > 0;
  const reduz = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const conteudo = document.getElementById("conteudo");
  const retorno = document.getElementById("retorno");
  const npc = document.getElementById("npc");
  const balao = document.getElementById("balao");
  const balaoTexto = document.getElementById("balao-texto");
  const cartao = document.getElementById("cartao");

  /* ---------- utilidades ---------- */
  function h(tag, attrs, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const f of filhos.flat()) if (f != null) e.append(f instanceof Node ? f : document.createTextNode(String(f)));
    return e;
  }
  /* replaceChildren ignorando null (blocos opcionais) */
  const trocar = (el, ...filhos) => el.replaceChildren(...filhos.flat().filter(f => f != null));
  const img = chave => CFG.estatico + D.imagens[chave].src;
  const embaralhar = (lista, semente) => {
    const a = lista.slice();
    let s = semente || 1;
    const rnd = EM_PREVIA ? () => ((s = (s * 9301 + 49297) % 233280) / 233280) : Math.random;
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  };
  const limpa = s => String(s).toLowerCase().replace(/[’`´]/g, "'").replace(/[.,!?;:…"«»()\-–—]/g, " ").replace(/\s+/g, " ").trim();
  const semAcento = s => limpa(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  function confere(valor, respostas) {
    if (respostas.some(r => limpa(r) === limpa(valor))) return "ok";
    if (respostas.some(r => semAcento(r) === semAcento(valor))) return "acento";
    return "nao";
  }

  /* ---------- áudio + NPC ---------- */
  const player = new Audio();
  player.preload = "auto";
  player.addEventListener("ended", () => npc.classList.remove("fala"));
  player.addEventListener("pause", () => npc.classList.remove("fala"));
  const VOZ_NPC = (D.cenario && D.cenario.npc && D.cenario.npc.voz) || "odile";
  function tocar(chave) {
    if (!chave || !D.audios[chave]) return;
    player.pause();
    player.src = CFG.audio + chave + ".mp3";
    if (D.audios[chave].voz === VOZ_NPC) npc.classList.add("fala");
    player.play().catch(() => npc.classList.remove("fala"));
  }
  function falar(texto) { balaoTexto.textContent = texto || "♪ …"; balao.hidden = false; }
  function calar() { balao.hidden = true; }
  const botaoSom = (chave, rotulo) => h("button", { type: "button", class: "botao sec som", onclick: () => tocar(chave) }, rotulo || "Ouvir");

  /* Pan da cena no retrato: mantém o NPC visível */
  function pan() {
    const vw = innerWidth, vh = innerHeight, W = Math.max(vw, vh * 16 / 9);
    const sobra = W - vw;
    const p = sobra > 1 ? Math.max(-sobra / 2, Math.min(sobra / 2, W * (0.5 - D.cenario.npc.x / 100 - 0.04))) : 0;
    document.getElementById("palco").style.setProperty("--pan", p + "px");
    /* balão: à direita da cabeça do NPC; se não couber, abaixo do HUD à direita */
    const H = Math.max(vh, vw * 9 / 16), n = D.cenario.npc;
    const esq = vw / 2 - W / 2 + p, topo = vh / 2 - H / 2;
    let x = esq + W * (n.x + n.w * 0.42) / 100, y = topo + H * (n.y - 1) / 100;
    const hud = document.querySelector(".hud").getBoundingClientRect().bottom + 8;
    const livre = vw - x - 10;
    if (livre < 170) { x = Math.max(10, vw - Math.min(260, vw * 0.6) - 10); y = Math.max(y, hud); balao.style.maxWidth = Math.min(260, vw * 0.6) + "px"; }
    else balao.style.maxWidth = Math.min(livre, 360) + "px";
    balao.style.left = x + "px"; balao.style.top = Math.max(y, hud) + "px";
  }
  addEventListener("resize", pan); pan();

  /* ---------- estado ---------- */
  const E = {
    bloco: 0, fila: [], acertos: 0, erros: 0, feitos: 0,
    erradas: new Map(), falaPendente: false, inicio: Date.now()
  };
  const totalPlanejado = () => {
    let resto = E.fila.length;
    for (let i = E.bloco + 1; i < D.blocos.length; i++) resto += D.blocos[i].itens.length + (D.blocos[i].recuperar ? E.erradas.size : 0);
    return E.feitos + resto;
  };
  function progresso(fim) {
    const v = fim ? 100 : Math.round(E.feitos / Math.max(1, totalPlanejado()) * 100);
    document.getElementById("barra-fill").style.width = v + "%";
    document.getElementById("barra").setAttribute("aria-valuenow", v);
    const lis = document.querySelectorAll("#etapas li"), nb = lis.length;
    lis.forEach((li, i) => {
      li.className = fim || i < E.bloco ? "feito" : i === E.bloco ? "atual" : "";
      if (!fim && i === E.bloco) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
    });
    /* Marcador na trilha das etapas: anda dentro do bloco atual e salta para o próximo quando ele acaba */
    const feitosBloco = Math.max(0, E.feitos - (E._f0 || 0));
    const totalBloco = feitosBloco + E.fila.length;
    const frac = fim ? 1 : feitosBloco / Math.max(1, totalBloco);
    const m = document.getElementById("marcador-etapa");
    if (m) {
      const pos = fim ? nb - 0.5 : E.bloco + 0.12 + 0.76 * frac;
      if (m._bloco !== undefined && m._bloco !== E.bloco && !fim) { m.classList.remove("pula"); void m.offsetWidth; m.classList.add("pula"); }
      const primeira = m._bloco === undefined;
      m._bloco = E.bloco;
      if (primeira) m.style.transition = "none";   /* ao abrir a lição: já nasce no lugar, sem deslizar */
      m.style.left = (pos / nb * 100) + "%";
      if (primeira) { void m.offsetWidth; m.style.transition = ""; }
      const nItem = Math.min(totalBloco, feitosBloco + 1);
      const cont = document.getElementById("etapa-cont");
      if (cont) cont.textContent = fim ? "✓" : `${nItem}/${Math.max(1, totalBloco)}`;
      const nome = D.blocos[Math.min(E.bloco, nb - 1)].nome;
      document.getElementById("barra").setAttribute("aria-valuetext", fim ? "Parada concluída" : `Etapa ${E.bloco + 1} de ${nb} (${nome}), atividade ${nItem} de ${Math.max(1, totalBloco)}`);
    }
  }
  const clone = (o, extra) => Object.assign(JSON.parse(JSON.stringify(o)), extra || {});

  /* ---------- fluxo ---------- */
  function iniciarBloco(i, pularIntro, pularItens) {
    E.bloco = i; E._f0 = E.feitos;
    const b = D.blocos[i];
    E.fila = [];
    if (b.recuperar) for (const it of E.erradas.values()) E.fila.push(clone(it, { _revisao: true }));
    E.fila.push(...b.itens.map(it => clone(it)));
    if (pularItens) E.fila.splice(0, pularItens);
    progresso();
    retorno.hidden = true; calar();
    if (pularIntro) { proximo(); return; }
    trocar(conteudo, 
      h("p", { class: "sub", text: `Bloco ${i + 1} de ${D.blocos.length} · ~${String(b.minutos).replace(".", ",")} min` }),
      h("h2", { text: b.nome }),
      h("p", { class: "instr", text: b.intro }),
      b.recuperar && E.erradas.size ? h("p", { class: "sub", text: `${E.erradas.size} ${E.erradas.size === 1 ? "item volta" : "itens voltam"} para uma nova chance.` }) : null,
      h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "comecar", onclick: proximo }, i === 0 ? "Começar a missão" : "Começar"))
    );
    focar("#comecar");
  }
  function proximo() {
    retorno.hidden = true; calar();
    if (!E.fila.length) {
      if (E.bloco + 1 < D.blocos.length) iniciarBloco(E.bloco + 1);
      else concluir();
      return;
    }
    const item = E.fila[0];
    progresso();
    const comp = COMP[item.tipo];
    trocar(conteudo, );
    if (item._revisao) conteudo.append(h("p", { class: "sub", text: "Nova chance · revisão" }));
    comp(item, conteudo, res => responder(item, res));
    cartao.scrollTop = 0;
  }
  function marcarErrada(item) {
    if (item._revisao || D.blocos[E.bloco].recuperar) return;
    if (!E.erradas.has(item.id)) E.erradas.set(item.id, item);
  }
  /* res = { ok, erros?, correta?, explicacao?, transcricao?, aviso?, revisoes? } */
  function responder(item, res) {
    E.fila.shift();
    (res.revisoes || []).forEach(id => { const r = D.itens_revisao && D.itens_revisao[id]; if (r && !E.erradas.has(id)) E.erradas.set(id, r); });
    if (res.ok) {
      E.acertos++; E.feitos++;
      if (res.erros) { E.erros += res.erros; if (item.tipo !== "dialogo") marcarErrada(item); }
    } else {
      E.erros++;
      marcarErrada(item);
      E.fila.push(clone(item, { _nova: true }));
    }
    progresso();
    mostrarRetorno(res);
  }
  function mostrarRetorno(res) {
    retorno.className = "retorno" + (res.ok ? "" : " erro");
    trocar(retorno, 
      h("h3", { text: res.ok ? (res.aviso ? "Certo — com um detalhe" : "Isso!") : "Quase…" }),
      !res.ok && res.correta ? h("p", {}, "Resposta certa: ", h("span", { class: "fr", text: res.correta })) : null,
      res.aviso ? h("p", { text: res.aviso }) : null,
      res.transcricao ? h("p", {}, "O áudio dizia: ", h("span", { class: "fr", text: res.transcricao })) : null,
      res.explicacao ? h("p", { text: res.explicacao }) : null,
      !res.ok ? h("p", { class: "sub", text: "Esse item volta daqui a pouco para uma nova chance." }) : null,
      h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "continuar", onclick: proximo }, "Continuar"))
    );
    retorno.hidden = false;
    retorno.scrollIntoView({ block: "nearest", behavior: reduz ? "auto" : "smooth" });
    focar("#continuar");
  }
  function focar(sel) { setTimeout(() => { const e = document.querySelector(sel); if (e) e.focus({ preventScroll: true }); }, 30); }
  const travar = area => area.querySelectorAll("button.opcao, button.ficha, input, textarea").forEach(b => { b.disabled = true; });
  const cab = (area, item) => area.append(h("p", { class: "instr", text: item.instrucao }));

  /* ---------- componentes ---------- */
  const COMP = {};

  /* 1. palavra ↔ imagem */
  COMP.imagem = (item, area, fim) => {
    cab(area, item);
    area.append(h("div", { class: "linha" }, botaoSom(item.audio), item.mostrar_texto === false ? null : h("span", { class: "fr", style: "font-size:1.25rem", text: item.texto_fr })));
    const grade = h("div", { class: "opcoes imgs", role: "group", "aria-label": "Escolha a imagem" });
    item.opcoes.forEach((k, i) => {
      const b = h("button", { type: "button", class: "opcao", "aria-label": `Imagem ${i + 1}: ${D.imagens[k].pt}` }, h("img", { src: img(k), alt: "" }), h("span", { class: "rot" }));
      b.addEventListener("click", () => {
        travar(area);
        const ok = k === item.correta;
        b.classList.add(ok ? "certa" : "errada");
        grade.children[item.opcoes.indexOf(item.correta)].classList.add("certa");
        [...grade.children].forEach((c, j) => { c.querySelector(".rot").textContent = D.imagens[item.opcoes[j]].fr; });
        const c = D.imagens[item.correta];
        fim({ ok, correta: `${c.fr} = ${c.pt}`, explicacao: item.explicacao });
      });
      grade.append(b);
    });
    area.append(grade);
    tocar(item.audio);
  };

  /* 2. pares */
  COMP.pares = (item, area, fim) => {
    cab(area, item);
    let sel = null, erros = 0, feitos = 0;
    const colA = h("div", { class: "col" }), colB = h("div", { class: "col" });
    const tentar = (a, b) => {
      if (a.dataset.k === b.dataset.k) {
        [a, b].forEach(x => { x.classList.remove("sel"); x.classList.add("par-ok"); x.disabled = true; });
        if (++feitos === item.pares.length) fim({ ok: true, erros, explicacao: item.explicacao, aviso: erros ? `Você trocou ${erros} ${erros === 1 ? "par" : "pares"} no caminho — esse item volta na revisão.` : null });
      } else {
        erros++;
        [a, b].forEach(x => { x.classList.remove("sel"); x.classList.remove("par-erro"); void x.offsetWidth; x.classList.add("par-erro"); });
      }
      sel = null;
    };
    const escolher = btn => {
      if (btn.disabled) return;
      if (btn.dataset.lado === "a") tocar(btn.dataset.audio);
      if (sel && sel.dataset.lado !== btn.dataset.lado) { const [a, b] = sel.dataset.lado === "a" ? [sel, btn] : [btn, sel]; tentar(a, b); return; }
      if (sel) sel.classList.remove("sel");
      sel = btn; btn.classList.add("sel");
    };
    embaralhar(item.pares, 3).forEach(p => colA.append(h("button", { type: "button", class: "opcao fr", "data-k": p.img, "data-lado": "a", "data-audio": p.audio, onclick: e => escolher(e.currentTarget) }, p.fr)));
    embaralhar(item.pares, 7).forEach(p => colB.append(h("button", { type: "button", class: "opcao", "data-k": p.img, "data-lado": "b", "aria-label": D.imagens[p.img].pt, onclick: e => escolher(e.currentTarget) }, h("img", { src: img(p.img), alt: "" }))));
    area.append(h("div", { class: "pares" }, colA, colB));
  };

  /* escolha de opções (texto ou imagem) — usada por 3 e 4 */
  function escolhas(area, item, extra, fim) {
    const ehImg = Array.isArray(item.opcoes_img);
    const lista = ehImg ? item.opcoes_img : item.opcoes;
    const grade = h("div", { class: "opcoes " + (ehImg ? "imgs" : "textos"), role: "group", "aria-label": item.pergunta });
    lista.forEach((op, i) => {
      const b = ehImg
        ? h("button", { type: "button", class: "opcao", "aria-label": D.imagens[op].pt }, h("img", { src: img(op), alt: "" }), h("span", { class: "rot" }))
        : h("button", { type: "button", class: "opcao" + (/[a-z]/i.test(op) && item.opcoes_fr ? " fr" : "") }, op);
      b.addEventListener("click", () => {
        travar(area);
        const certo = ehImg ? item.correta : item.correta;
        const ok = ehImg ? op === certo : i === certo;
        b.classList.add(ok ? "certa" : "errada");
        grade.children[ehImg ? lista.indexOf(certo) : certo].classList.add("certa");
        if (ehImg) [...grade.children].forEach((c, j) => { c.querySelector(".rot").textContent = D.imagens[lista[j]].fr; });
        const correta = ehImg ? `${D.imagens[certo].fr} = ${D.imagens[certo].pt}` : lista[certo];
        fim(Object.assign({ ok, correta, explicacao: item.explicacao }, extra ? extra() : {}));
      });
      grade.append(b);
    });
    area.append(h("p", { class: "instr", style: "margin:10px 0 0;font-weight:700", text: item.pergunta }), grade);
  }

  /* 3. texto curto + pergunta */
  COMP.texto = (item, area, fim) => {
    cab(area, item);
    if (item.texto_fr && item.texto_fr.length) {
      area.append(h("div", { class: "nota", lang: "fr" }, item.texto_fr.map(l => {
        const m = l.match(/^([^:]{1,20})\s:\s(.*)$/);
        return m ? h("p", {}, h("b", { text: m[1] + " : " }), m[2]) : h("p", { text: l });
      })));
    }
    escolhas(area, item, null, fim);
  };

  /* 4. áudio + escolha (sem transcrição antes de responder) */
  COMP.audio = (item, area, fim) => {
    cab(area, item);
    let vezes = 1;
    const cont = h("span", { class: "sub", text: "" });
    area.append(h("div", { class: "linha" }, h("button", { type: "button", class: "botao som", onclick: () => { tocar(item.audio); cont.textContent = `ouvido ${++vezes}×`; } }, "Ouvir de novo"), cont));
    if (D.audios[item.audio] && D.audios[item.audio].voz === VOZ_NPC) falar("♪ …");
    escolhas(area, item, () => ({ transcricao: D.audios[item.audio] && D.audios[item.audio].texto }), res => { calar(); fim(res); });
    tocar(item.audio);
  };

  /* 5. banco de palavras / ordenar */
  COMP.ordenar = (item, area, fim) => {
    cab(area, item);
    area.append(h("p", { class: "sub", text: "Toque nas palavras ou arraste-as. Na frase, arraste para mudar a ordem (ou use ← → no teclado; Delete devolve)." }));
    const resp = h("div", { class: "resposta", "aria-label": "Sua frase", role: "group" });
    const banco = h("div", { class: "banco", "aria-label": "Banco de palavras", role: "group" });
    const verificar = h("button", { type: "button", class: "botao", disabled: true }, "Verificar");
    const fichasResp = () => [...resp.children].filter(c => c.classList.contains("ficha"));
    const atualizar = () => { verificar.disabled = fichasResp().length === 0; };
    const devolver = (c) => { const o = c._origem; c.remove(); o.classList.remove("usada"); o.disabled = false; atualizar(); };
    function colocar(origem, indice) {
      const c = h("button", { type: "button", class: "ficha", lang: "fr" }, origem.textContent);
      c._origem = origem;
      c.addEventListener("click", () => { if (!c._arrastou) devolver(c); });
      c.addEventListener("keydown", e => {
        const lista = fichasResp(), k = lista.indexOf(c);
        if (e.key === "ArrowLeft" && k > 0) { resp.insertBefore(c, lista[k - 1]); c.focus(); e.preventDefault(); }
        else if (e.key === "ArrowRight" && k < lista.length - 1) { resp.insertBefore(c, lista[k + 1].nextSibling); c.focus(); e.preventDefault(); }
        else if (e.key === "Delete" || e.key === "Backspace") { const prox = lista[k + 1] || lista[k - 1]; devolver(c); if (prox) prox.focus(); e.preventDefault(); }
      });
      arrastavel(c);
      const lista = fichasResp();
      resp.insertBefore(c, indice == null || indice >= lista.length ? null : lista[indice]);
      origem.classList.add("usada"); origem.disabled = true;
      atualizar();
      return c;
    }
    /* Arrastar com Pointer Events (mouse e toque); um toque sem movimento continua sendo clique */
    const marcador = h("span", { class: "marcador", "aria-hidden": "true" });
    function arrastavel(ficha) {
      ficha.addEventListener("pointerdown", ev => {
        if (ficha.disabled || ev.button > 0) return;
        const x0 = ev.clientX, y0 = ev.clientY; let fantasma = null;
        ficha._arrastou = false;
        const mover = e => {
          if (!fantasma) {
            if (Math.hypot(e.clientX - x0, e.clientY - y0) < 6) return;
            ficha._arrastou = true;
            const r = ficha.getBoundingClientRect();
            fantasma = ficha.cloneNode(true); fantasma.className = "ficha arrasto";
            fantasma.style.width = r.width + "px";
            document.body.append(fantasma);
            ficha.classList.add("fantasma");
          }
          fantasma.style.left = (e.clientX - fantasma.offsetWidth / 2) + "px";
          fantasma.style.top = (e.clientY - fantasma.offsetHeight / 2) + "px";
          if (sobre(resp, e)) {
            const outras = fichasResp().filter(c => c !== ficha);
            const k = indiceInsercao(outras.map(c => c.getBoundingClientRect()), e.clientX, e.clientY);
            resp.insertBefore(marcador, outras[k] || null);
          } else marcador.remove();
        };
        const soltar = e => {
          removeEventListener("pointermove", mover); removeEventListener("pointerup", soltar); removeEventListener("pointercancel", soltar);
          if (!fantasma) return;
          fantasma.remove(); ficha.classList.remove("fantasma");
          const naFrase = marcador.parentNode === resp && e.type === "pointerup";
          const k = naFrase ? fichasResp().filter(c => c !== ficha).indexOf(marcador.nextElementSibling) : -1;
          marcador.remove();
          const emResp = ficha.parentNode === resp;
          if (naFrase) {
            if (emResp) { const outras = fichasResp().filter(c => c !== ficha); resp.insertBefore(ficha, k < 0 ? null : outras[k]); }
            else colocar(ficha, k < 0 ? null : k);
          } else if (emResp && e.type === "pointerup") devolver(ficha);
          atualizar();
          setTimeout(() => { ficha._arrastou = false; }, 0);
        };
        addEventListener("pointermove", mover); addEventListener("pointerup", soltar); addEventListener("pointercancel", soltar);
      });
    }
    const sobre = (el, e) => { const r = el.getBoundingClientRect(); return e.clientX >= r.left - 12 && e.clientX <= r.right + 12 && e.clientY >= r.top - 16 && e.clientY <= r.bottom + 16; };
    embaralhar(item.palavras.concat(item.extras || []), 11).forEach((p, i) => {
      const f = h("button", { type: "button", class: "ficha", lang: "fr", "data-i": i }, p);
      f.addEventListener("click", () => { if (!f._arrastou && !f.disabled) colocar(f, null); });
      arrastavel(f);
      banco.append(f);
    });
    verificar.addEventListener("click", () => {
      const frase = fichasResp().map(c => c.textContent).join(" ");
      const ok = limpa(frase) === limpa(item.palavras.join(" "));
      travar(area); verificar.disabled = true;
      if (ok) tocar(item.audio);
      fim({ ok, correta: item.palavras.join(" "), explicacao: item.explicacao });
    });
    area.append(resp, banco, h("div", { class: "linha" }, verificar));
  };
  /* Posição de inserção numa linha de fichas que quebra em várias linhas (função pura, testável) */
  function indiceInsercao(rects, x, y) {
    for (let i = 0; i < rects.length; i++) {
      const r = rects[i];
      if (y < r.top) return i;                                   /* linha acima desta ficha */
      if (y <= r.bottom && x < r.left + r.width / 2) return i;   /* mesma linha, antes do meio */
    }
    return rects.length;
  }
  window.chemin_indiceInsercao = indiceInsercao;

  /* 6. lacuna (banco | digitar) ou ditado */
  COMP.lacuna = (item, area, fim) => {
    cab(area, item);
    const modo = item.modo || "digitar";
    const certa = item.respostas[0];
    const fraseCerta = item.frase ? item.frase.replace("___", certa) : certa;
    const terminar = valor => {
      const r = confere(valor, item.respostas);
      travar(area);
      if (r !== "nao") tocar(item.audio);
      fim({
        ok: r !== "nao", correta: fraseCerta, explicacao: item.explicacao,
        aviso: r === "acento" ? `Atenção ao acento: ${certa}.` : null
      });
    };
    if (modo === "ditado") {
      const campo = h("input", { class: "campo cheio", type: "text", lang: "fr", autocomplete: "off", autocapitalize: "off", spellcheck: "false", "aria-label": "O que você ouviu" });
      const ver = h("button", { type: "button", class: "botao", onclick: () => campo.value.trim() && terminar(campo.value) }, "Verificar");
      campo.addEventListener("keydown", e => { if (e.key === "Enter" && campo.value.trim()) terminar(campo.value); });
      area.append(h("div", { class: "linha" }, botaoSom(item.audio, "Ouvir")), h("div", { class: "linha", style: "margin-top:10px" }, campo), h("div", { class: "linha", style: "margin-top:10px" }, ver));
      tocar(item.audio);
      if (!EM_PREVIA) setTimeout(() => campo.focus({ preventScroll: true }), 60);
      return;
    }
    const [antes, depois] = item.frase.split("___");
    if (modo === "banco") {
      const vaga = h("span", { class: "vaga", text: "…" });
      area.append(h("p", { class: "frase-lacuna", lang: "fr" }, antes, vaga, depois));
      const banco = h("div", { class: "banco" });
      embaralhar(item.banco, 5).forEach(p => banco.append(h("button", { type: "button", class: "ficha", lang: "fr", onclick: () => { vaga.textContent = p; terminar(p); } }, p)));
      area.append(banco);
      return;
    }
    const campo = h("input", { class: "campo inline", type: "text", lang: "fr", autocomplete: "off", autocapitalize: "off", spellcheck: "false", "aria-label": "Palavra que falta" });
    campo.addEventListener("keydown", e => { if (e.key === "Enter" && campo.value.trim()) terminar(campo.value); });
    const dica = h("span", { class: "sub" });
    area.append(h("p", { class: "frase-lacuna", lang: "fr" }, antes, campo, depois),
      h("div", { class: "linha" },
        h("button", { type: "button", class: "botao", onclick: () => campo.value.trim() && terminar(campo.value) }, "Verificar"),
        item.dica ? h("button", { type: "button", class: "botao sec", onclick: () => { dica.textContent = item.dica; } }, "Dica") : null, dica));
    if (!EM_PREVIA) setTimeout(() => campo.focus({ preventScroll: true }), 60);
  };

  /* 7. diálogo ramificado com o NPC */
  COMP.dialogo = (item, area, fim) => {
    cab(area, item);
    const nomeNpc = D.cenario.npc.nome;
    const log = h("ol", { class: "conversa", "aria-label": "Conversa" });
    const palco = h("div");
    area.append(log, palco);
    let erros = 0; const revisoes = [];
    const ir = (id, automatico) => {
      if (id === "fim") { calar(); fim({ ok: true, erros, revisoes, explicacao: item.explicacao, aviso: erros ? `Você escolheu ${erros} ${erros === 1 ? "resposta que não funcionava" : "respostas que não funcionavam"} — tudo bem, faz parte.` : null }); return; }
      const no = item.nos[id];
      log.append(h("li", { class: "de-npc", lang: "fr" }, h("b", { text: nomeNpc + " : " }), no.fala));
      falar(no.fala); tocar(no.audio);
      const opcoes = h("div", { class: "opcoes textos", role: "group", "aria-label": "O que você diz?" });
      const aviso = h("div");
      no.opcoes.forEach(op => {
        const b = h("button", { type: "button", class: "opcao fr", lang: "fr" }, op.fr);
        b.addEventListener("click", () => {
          if (op.erro) {
            erros++; if (op.revisao) revisoes.push(op.revisao);
            b.classList.add("errada"); b.disabled = true;
            trocar(aviso, h("p", { class: "aviso-inline", text: op.feedback }));
            return;
          }
          [...opcoes.children].forEach(x => { x.disabled = true; });
          b.classList.add("certa");
          log.append(h("li", { class: "de-eu", lang: "fr" }, h("b", { text: "Você : " }), op.fr));
          trocar(aviso, h("p", { class: "aviso-inline " + (op.aviso ? "meio" : "ok"), text: op.feedback }),
            h("div", { class: "linha", style: "margin-top:8px" }, h("button", { type: "button", class: "botao", id: "dlg-seguir", onclick: () => ir(op.vai) }, "Continuar")));
          focar("#dlg-seguir");
        });
        opcoes.append(b);
      });
      trocar(palco, h("p", { class: "instr", style: "margin:6px 0 0;font-weight:700", text: "O que você diz?" }), opcoes, aviso);
      log.scrollTop = log.scrollHeight;
      if (automatico && PREVIA.estado === "erro") { const errada = no.opcoes.findIndex(o => o.erro); if (errada >= 0) opcoes.children[errada].click(); }
    };
    ir(item.inicio, true);
    if (PREVIA.estado === "dialogo") { const p = item.nos[item.inicio].opcoes.findIndex(o => !o.erro && !o.aviso); palco.querySelectorAll(".opcao")[p].click(); }
  };

  /* 8. produção curta: gravada (MediaRecorder) ou escrita */
  COMP.producao = (item, area, fim) => {
    if (item._escrita || item.modo === "escrever") { producaoEscrita(item, area, fim); return; }
    cab(area, item);
    area.append(
      h("p", { class: "sub", text: "Diga em voz alta:" }),
      h("ul", { class: "check" }, item.checklist.map(c => h("li", { lang: "fr" }, "▸ ", c))),
      h("div", { class: "linha" }, botaoSom(item.audio_modelo, "Ouvir um exemplo"))
    );
    const grav = h("div", { class: "gravador" });
    const status = h("span", { class: "tempo", text: "" });
    const btGravar = h("button", { type: "button", class: "botao" }, h("i", { class: "rec" }), "Gravar");
    const btPular = h("button", { type: "button", class: "botao sec", onclick: pular }, "Não posso falar agora");
    grav.append(btGravar, status);
    const resultado = h("div");
    area.append(grav, resultado, h("div", { class: "linha", style: "margin-top:6px" }, btPular));
    let rec = null, partes = [], timer = 0, t0 = 0, stream = null;
    function pular() {
      if (rec && rec.state === "recording") rec.stop();
      E.falaPendente = true;
      trocar(area, h("p", { class: "aviso-inline meio", text: "Sem problema: a fala fica pendente (não conta como feita) e você pode gravar depois. Por agora, escreva a resposta." }));
      producaoEscrita(item, area, fim, true);
    }
    function estadoGravando() {
      grav.classList.add("gravando");
      trocar(btGravar, h("i", { class: "rec" }), "Parar");
      t0 = Date.now();
      status.textContent = "Gravando… 0 s";
      timer = setInterval(() => {
        const s = Math.floor((Date.now() - t0) / 1000);
        status.textContent = `Gravando… ${s} s`;
        if (s >= (item.max_segundos || 15) && rec) rec.stop();
      }, 250);
    }
    function terminouGravacao(blob) {
      clearInterval(timer); grav.classList.remove("gravando");
      trocar(btGravar, h("i", { class: "rec" }), "Gravar de novo");
      status.textContent = "";
      const url = URL.createObjectURL(blob);
      const marcas = item.checklist.map(c => h("li", {}, h("label", {}, h("input", { type: "checkbox" }), " ", h("span", { lang: "fr", text: c }))));
      trocar(resultado, 
        h("p", { class: "sub", text: "Ouça a sua gravação e compare com o exemplo. Ela fica só neste aparelho." }),
        h("audio", { controls: true, src: url }),
        h("p", { class: "instr", style: "margin:8px 0 2px", text: "Você disse…" }), h("ul", { class: "check" }, marcas),
        h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "fala-ok", onclick: () => {
          travar(area); btGravar.disabled = true; btPular.disabled = true;
          fim({ ok: true, fala: true, correta: item.modelo, explicacao: "Gravado! Exemplo: " + item.modelo });
        } }, "Pronto, terminei"))
      );
      focar("#fala-ok");
    }
    btGravar.addEventListener("click", async () => {
      if (rec && rec.state === "recording") { rec.stop(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) { semMicrofone("Este navegador não grava áudio."); return; }
      try {
        stream = stream || await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) { semMicrofone("Não consegui acessar o microfone."); return; }
      partes = [];
      rec = new MediaRecorder(stream);
      rec.ondataavailable = e => { if (e.data.size) partes.push(e.data); };
      rec.onstop = () => terminouGravacao(new Blob(partes, { type: rec.mimeType || "audio/webm" }));
      rec.start();
      estadoGravando();
    });
    function semMicrofone(msg) {
      trocar(resultado, h("p", { class: "aviso-inline", text: msg + " Use “Não posso falar agora” para seguir pela escrita — a fala fica pendente." }));
      focar(".gravador + div + div .botao");
    }
    if (PREVIA.estado === "gravando") estadoGravando();
  };
  function producaoEscrita(item, area, fim, depoisDePular) {
    const esc = item.escrita || {};
    if (!depoisDePular) cab(area, item);
    const campo = h("textarea", { class: "campo", lang: "fr", "aria-label": "Sua resposta por escrito", placeholder: esc.placeholder || (item.modelo || "").split(" ").slice(0, 2).join(" ") + "…" });
    const ver = h("button", { type: "button", class: "botao" }, "Verificar");
    ver.addEventListener("click", () => {
      if (!campo.value.trim()) return;
      const t = semAcento(campo.value);
      const faltam = (esc.palavras_chave || []).filter(g => !g.some(p => t.includes(semAcento(p))));
      travar(area); ver.disabled = true;
      fim({ ok: faltam.length === 0, correta: item.modelo, explicacao: esc.explicacao, aviso: E.falaPendente ? "A fala ficou pendente: grave a sua fala numa próxima visita." : null });
    });
    area.append(h("p", { class: "instr", text: esc.instrucao || "Escreva a sua resposta." }), campo, h("div", { class: "linha", style: "margin-top:8px" }, ver));
    item._escrita = true;
  }

  /* ---------- fim da parada ---------- */
  function estrelas(erros) {
    for (const f of (D.recompensa && D.recompensa.estrelas) || []) if (erros >= f.min_erros && erros <= f.max_erros) return f.estrelas;
    return 1;
  }
  function salvar(registro) {
    try {
      const PRE = CFG.prefixo || "chemin_";   /* usuário de teste usa chemin_teste_ */
      const chaveMapa = `${PRE}mapa_r${CFG.regiao}_atual`;
      const atual = Number(localStorage.getItem(chaveMapa)) || 1;
      localStorage.setItem(chaveMapa, String(Math.max(atual, CFG.n + 1)));
      const todas = JSON.parse(localStorage.getItem(PRE + "paradas") || "{}");
      todas[CFG.pid] = registro;
      localStorage.setItem(PRE + "paradas", JSON.stringify(todas));
    } catch (e) { /* armazenamento indisponível: segue sem travar */ }
    return fetch(CFG.concluir, {
      method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin",
      body: JSON.stringify({ acertos: registro.acertos, erros: registro.erros, fala_pendente: registro.fala_pendente, duracao_s: registro.duracao_s })
    }).then(async r => {
      if (!r.ok) return false;
      const resposta = await r.json();
      if (resposta.ok !== true || !Number.isFinite(resposta.xp_ganho) || !Number.isFinite(resposta.xp_total)) return false;
      registro.xp = Number.isFinite(resposta.xp_creditado_etapa) ? resposta.xp_creditado_etapa : registro.xp;
      registro.xp_ganho = resposta.xp_ganho; registro.xp_confirmado = true; registro.xp_versao = 6;
      try {
        const pre = CFG.prefixo || "chemin_";
        const todas = JSON.parse(localStorage.getItem(pre + "paradas") || "{}");
        todas[CFG.pid] = registro;
        localStorage.setItem(pre + "paradas", JSON.stringify(todas));
      } catch (_) { /* progresso continua salvo no servidor */ }
      return resposta;
    }).catch(() => false);
  }
  function concluir(demo) {
    calar();
    progresso(true);
    const reg = demo || {
      concluida_em: new Date().toISOString(), acertos: E.acertos, erros: E.erros,
      fala_pendente: E.falaPendente, duracao_s: Math.round((Date.now() - E.inicio) / 1000)
    };
    const n = estrelas(reg.erros);
    const rec = D.recompensa || {};
    const xp = rec.xp_pausado ? 0 : Math.max(0, (rec.xp_base ?? 0) + (rec.xp_por_estrela ?? 0) * n);
    reg.estrelas = n; reg.xp = xp; reg.xp_versao = 6; reg.xp_confirmado = false;
    const xpLinha = h("p", { class: "xp", text: EM_PREVIA ? `+${xp} XP · prévia` : "Confirmando XP…" });
    const nota = h("p", { class: "sub", text: EM_PREVIA ? "Prévia: nada foi salvo." : "Salvando…" });
    trocar(conteudo, h("div", { class: "recompensa" },
      h("p", { class: "sub", text: `Étape ${CFG.n} concluída` }),
      h("h2", { text: "Mission accomplie !" }),
      h("div", { class: "estrelas", role: "img", "aria-label": `${n} de 3 estrelas` },
        [1, 2, 3].map(i => h("img", { src: CFG.estatico + (i <= n ? "parada/estrela-cheia.png" : "parada/estrela-vazia.png"), alt: "", class: i <= n ? "cheia" : "" }))),
      xpLinha,
      h("p", { text: `${reg.acertos} acertos · ${reg.erros} ${reg.erros === 1 ? "erro" : "erros"} · ${Math.max(1, Math.round(reg.duracao_s / 60))} min` }),
      reg.fala_pendente ? h("p", { class: "pendente", text: "Fala pendente: grave a sua fala numa próxima visita a esta parada." }) : null,
      h("p", { class: "instr", style: "margin:10px 0 0;font-weight:700", text: "Você aprendeu:" }),
      h("ul", { class: "vocab" }, D.vocabulario.map(v => h("li", {},
        v.img ? h("img", { src: img(v.img), alt: "" }) : null,
        h("span", {}, h("span", { class: "fr", lang: "fr", text: v.fr }), " — ", v.pt),
        h("button", { type: "button", class: "botao sec som", "aria-label": "Ouvir " + v.fr, onclick: () => tocar(v.audio) }, "")))),
      nota,
      h("div", { class: "linha centro" },
        h("a", { class: "botao", id: "ir-mapa", href: CFG.mapa }, "Voltar ao mapa"),
        h("a", { class: "botao sec", href: CFG.refazer }, "Refazer parada"))
    ));
    retorno.hidden = true;
    focar("#ir-mapa");
    if (EM_PREVIA) return;
    salvar(reg).then(resposta => {
      xpLinha.textContent = resposta ? `+${resposta.xp_ganho} XP` + (xp > 0 && resposta.xp_ganho === 0 ? " · etapa já concluída" : "") : "XP pendente · confirme quando o servidor voltar";
      nota.textContent = resposta ? (CFG.teste ? "Modo teste: progresso salvo só nesta sessão de teste." : "Progresso salvo.") : "Progresso salvo neste aparelho (servidor indisponível agora).";
    });
  }

  /* Estado exposto só para testes/depuração (somente leitura na prática) */
  window.chemin_parada = { estado: E, dados: D };

  /* ---------- início ---------- */
  if (PREVIA.tela === "recompensa") {
    E.bloco = D.blocos.length - 1;
    concluir({ concluida_em: new Date().toISOString(), acertos: 18, erros: 2, fala_pendente: true, duracao_s: 590 });
  } else if (PREVIA.bloco) {
    iniciarBloco(PREVIA.bloco - 1, !!PREVIA.item || !!PREVIA.estado, PREVIA.item ? PREVIA.item - 1 : 0);
    if (PREVIA.estado === "erro") {
      const it = E.fila[0];
      setTimeout(() => {
        if (it && (it.tipo === "imagem" || it.tipo === "audio" || it.tipo === "texto")) {
          const ops = [...conteudo.querySelectorAll(".opcao")];
          const correta = it.tipo === "imagem" ? it.opcoes.indexOf(it.correta) : Array.isArray(it.opcoes_img) ? it.opcoes_img.indexOf(it.correta) : it.correta;
          ops[(correta + 1) % ops.length].click();
        }
      }, 50);
    }
  } else {
    iniciarBloco(0);
  }
})();
