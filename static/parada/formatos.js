/* Templates data-driven das paradas (campo "formato" no JSON):
   conversa  — NPC fala primeiro; só aparece o texto a dizer; voz do jogador (Web Speech) com correção "Je pense que vous vouliez dire…"
   historia  — bardo narra em trechos com pausas; sim/não → múltipla escolha → resumo + ordenar
   biblioteca — pergaminhos lidos pelo monge; termos tocáveis; grimório com selos 1–4; Forja da Memória (SRS simples)
   cartas    — 9 cartas de objetos da vila; tocar e dizer o nome; erro vai para o fim da fila, acerto fica verde e sai
   Conclusão igual às paradas 1–4: POST em CFG.concluir + localStorage com o prefixo do usuário (teste: chemin_teste_). */
(() => {
  "use strict";
  const D = JSON.parse(document.getElementById("dados-parada").textContent);
  const CFG = JSON.parse(document.getElementById("cfg-parada").textContent);
  const PREVIA = CFG.previa || {};
  const EM_PREVIA = Object.keys(PREVIA).length > 0;
  const PRE = CFG.prefixo || "chemin_";
  const V = window.ChemVoz;
  const reduz = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const conteudo = document.getElementById("conteudo");
  const retorno = document.getElementById("retorno");
  const npc = document.getElementById("npc");
  const balao = document.getElementById("balao");
  const balaoTexto = document.getElementById("balao-texto");
  const cartao = document.getElementById("cartao");
  const NOME = D.cenario.npc.nome;

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
  const trocar = (el, ...filhos) => el.replaceChildren(...filhos.flat().filter(f => f != null));
  let semente = 7;
  const rnd = () => EM_PREVIA ? ((semente = (semente * 9301 + 49297) % 233280) / 233280) : Math.random();
  const embaralhar = lista => { const a = lista.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const sorteia = lista => lista[Math.floor(rnd() * lista.length)];
  const focar = sel => setTimeout(() => { const e = document.querySelector(sel); if (e) e.focus({ preventScroll: true }); }, 30);
  const topo = () => { cartao.scrollTop = 0; };

  /* ---------- áudio + NPC ---------- */
  const player = new Audio();
  player.preload = "auto";
  let fimAtual = null;
  function tocar(chave) {
    return new Promise(resolve => {
      if (fimAtual) fimAtual();
      if (!chave || !D.audios[chave]) { resolve(); return; }
      let feito = false;
      const fim = () => { if (feito) return; feito = true; clearTimeout(t); npc.classList.remove("fala"); if (fimAtual === fim) fimAtual = null; resolve(); };
      fimAtual = fim;
      const t = setTimeout(fim, 20000);
      player.pause();
      player.onended = fim; player.onerror = fim;
      player.src = CFG.audio + chave + ".mp3";
      if (D.audios[chave].voz === D.cenario.npc.voz) npc.classList.add("fala");
      try { const p = player.play(); if (p && p.catch) p.catch(fim); } catch (e) { fim(); }
    });
  }
  const tocarSeguido = async (...chaves) => { for (const c of chaves) await tocar(c); };
  const auto = (...chaves) => { if (!EM_PREVIA) tocarSeguido(...chaves); };   /* prévia não toca sozinha */
  function falar(texto) { balaoTexto.textContent = texto || "♪ …"; balao.hidden = false; }
  function calar() { balao.hidden = true; }
  const botaoSom = (chave, rotulo, attrs) => h("button", Object.assign({ type: "button", class: "botao sec som", onclick: () => tocar(chave) }, attrs || {}), rotulo || "Ouvir");

  /* cena em cobertura: mantém o NPC visível no retrato; balão ao lado da cabeça (mesma regra do motor) */
  function pan() {
    const vw = innerWidth, vh = innerHeight, W = Math.max(vw, vh * 16 / 9);
    const sobra = W - vw, n = D.cenario.npc;
    const p = sobra > 1 ? Math.max(-sobra / 2, Math.min(sobra / 2, W * (0.5 - n.x / 100 - 0.04))) : 0;
    document.getElementById("palco").style.setProperty("--pan", p + "px");
    const H = Math.max(vh, vw * 9 / 16);
    const esq = vw / 2 - W / 2 + p, top = vh / 2 - H / 2;
    let x = esq + W * (n.x + n.w * 0.42) / 100, y = top + H * (n.y - 1) / 100;
    const hud = document.querySelector(".hud").getBoundingClientRect().bottom + 8;
    const livre = vw - x - 10;
    if (livre < 170) { x = Math.max(10, vw - Math.min(260, vw * 0.6) - 10); y = Math.max(y, hud); balao.style.maxWidth = Math.min(260, vw * 0.6) + "px"; }
    else balao.style.maxWidth = Math.min(livre, 360) + "px";
    balao.style.left = x + "px"; balao.style.top = Math.max(y, hud) + "px";
  }
  addEventListener("resize", pan); pan();

  /* ---------- etapas + barra ---------- */
  function etapas(nomes) {
    trocar(document.getElementById("etapas"), nomes.map((n, i) => h("li", { "data-i": i, text: n })));
  }
  function marcar(i, total, fim) {
    const lis = document.querySelectorAll("#etapas li");
    lis.forEach((li, k) => {
      li.classList.toggle("feito", fim || k < i); li.classList.toggle("atual", !fim && k === i);
      if (!fim && k === i) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
    });
    const v = fim ? 100 : Math.round(i / Math.max(1, total || lis.length) * 100);
    document.getElementById("barra-fill").style.width = v + "%";
    document.getElementById("barra").setAttribute("aria-valuenow", v);
  }
  function mostrarRetorno(tipo, titulo, ...linhas) {
    retorno.className = "retorno" + (tipo === "erro" ? " erro" : tipo === "meio" ? " erro meio" : "");
    trocar(retorno, h("h3", { text: titulo }), linhas);
    retorno.hidden = false;
  }
  const esconderRetorno = () => { retorno.hidden = true; trocar(retorno); };
  const continuar = (fn, rotulo) => h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "continuar", onclick: () => { esconderRetorno(); fn(); } }, rotulo || "Continuar"));

  /* ---------- estado e conclusão (mesma rota das paradas 1–4) ---------- */
  const E = { acertos: 0, erros: 0, falaPendente: false, inicio: Date.now() };
  function estrelas(erros) {
    for (const f of (D.recompensa && D.recompensa.estrelas) || []) if (erros >= f.min_erros && erros <= f.max_erros) return f.estrelas;
    return 1;
  }
  function salvar(reg) {
    try {
      const chaveMapa = `${PRE}mapa_r${CFG.regiao}_atual`;
      const atual = Number(localStorage.getItem(chaveMapa)) || 1;
      localStorage.setItem(chaveMapa, String(Math.max(atual, CFG.n + 1)));
      const todas = JSON.parse(localStorage.getItem(PRE + "paradas") || "{}");
      todas[CFG.pid] = reg;
      localStorage.setItem(PRE + "paradas", JSON.stringify(todas));
    } catch (e) { /* armazenamento indisponível */ }
    return fetch(CFG.concluir, {
      method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin",
      body: JSON.stringify({ acertos: reg.acertos, erros: reg.erros, fala_pendente: reg.fala_pendente, duracao_s: reg.duracao_s })
    }).then(async r => {
      if (!r.ok) return false;
      const resposta = await r.json();
      if (resposta.ok !== true || !Number.isFinite(resposta.xp_ganho) || !Number.isFinite(resposta.xp_total)) return false;
      reg.xp = Number.isFinite(resposta.xp_creditado_etapa) ? resposta.xp_creditado_etapa : reg.xp;
      reg.xp_ganho = resposta.xp_ganho; reg.xp_confirmado = true; reg.xp_versao = 6;
      try {
        const pre = CFG.prefixo || "chemin_";
        const todas = JSON.parse(localStorage.getItem(pre + "paradas") || "{}");
        todas[CFG.pid] = reg;
        localStorage.setItem(pre + "paradas", JSON.stringify(todas));
      } catch (_) { /* progresso continua salvo no servidor */ }
      return resposta;
    }).catch(() => false);
  }
  function concluir(demo) {
    calar(); esconderRetorno();
    marcar(0, 1, true);
    const reg = demo || { concluida_em: new Date().toISOString(), acertos: E.acertos, erros: E.erros, fala_pendente: E.falaPendente, duracao_s: Math.round((Date.now() - E.inicio) / 1000) };
    const n = estrelas(reg.erros);
    const rec = D.recompensa || {};
    const xp = rec.xp_pausado ? 0 : Math.max(0, (rec.xp_base ?? 0) + (rec.xp_por_estrela ?? 0) * n);
    reg.estrelas = n; reg.xp = xp; reg.xp_versao = 6; reg.xp_confirmado = false;
    const xpLinha = h("p", { class: "xp", text: EM_PREVIA ? `+${xp} XP · prévia` : "Confirmando XP…" });
    reg.formato = D.formato;
    const nota = h("p", { class: "sub", id: "nota-salvar", text: EM_PREVIA ? "Prévia: nada foi salvo." : "Salvando…" });
    trocar(conteudo, h("div", { class: "recompensa" },
      h("p", { class: "sub", text: `Étape ${CFG.n} concluída` }),
      h("h2", { text: "Mission accomplie !" }),
      h("div", { class: "estrelas", role: "img", "aria-label": `${n} de 3 estrelas` },
        [1, 2, 3].map(i => h("img", { src: CFG.estatico + (i <= n ? "parada/estrela-cheia.png" : "parada/estrela-vazia.png"), alt: "", class: i <= n && !reduz ? "cheia" : "" }))),
      xpLinha,
      h("p", { text: `${reg.acertos} acertos · ${reg.erros} ${reg.erros === 1 ? "erro" : "erros"} · ${Math.max(1, Math.round(reg.duracao_s / 60))} min` }),
      reg.fala_pendente ? h("p", { class: "pendente", text: "Fala pendente: sem microfone, você escreveu ou se autoavaliou. Volte para falar em voz alta." }) : null,
      D.vocabulario && D.vocabulario.length ? [
        h("p", { class: "instr", style: "margin:10px 0 0;font-weight:700", text: "Você aprendeu:" }),
        h("ul", { class: "vocab" }, D.vocabulario.map(v => h("li", {},
          v.img && D.imagens[v.img] ? h("img", { src: CFG.estatico + D.imagens[v.img].src, alt: "" }) : null,
          h("span", {}, h("span", { class: "fr", lang: "fr", text: v.fr }), " — ", v.pt),
          v.audio ? h("button", { type: "button", class: "botao sec som", "aria-label": "Ouvir " + v.fr, onclick: () => tocar(v.audio) }, "") : null)))] : null,
      nota,
      h("div", { class: "linha centro" },
        h("a", { class: "botao", id: "ir-mapa", href: CFG.mapa }, "Voltar ao mapa"),
        h("a", { class: "botao sec", href: CFG.refazer }, "Refazer parada"))));
    topo(); focar("#ir-mapa");
    if (EM_PREVIA) return;
    salvar(reg).then(resposta => {
      xpLinha.textContent = resposta ? `+${resposta.xp_ganho} XP` + (xp > 0 && resposta.xp_ganho === 0 ? " · etapa já concluída" : "") : "XP pendente · confirme quando o servidor voltar";
      nota.textContent = resposta ? (CFG.teste ? "Modo teste: progresso salvo só nesta sessão de teste." : "Progresso salvo.") : "Progresso salvo neste aparelho (servidor indisponível agora).";
      nota.dataset.ok = resposta ? "1" : "0";
    });
  }
  function abertura(texto, aoComecar) {
    const vozInfo = V.disponivel
      ? `Voz: o navegador vai pedir o microfone (reconhecimento em ${V.lingua}). Se preferir, dá para escrever.`
      : "Este navegador não reconhece voz: você vai escrever a resposta ou falar e se autoavaliar.";
    trocar(conteudo,
      h("h2", { text: D.titulo_fr }), h("p", { class: "instr", text: D.instrucao }),
      texto ? h("p", { class: "sub", text: texto }) : null,
      aoComecar.voz ? h("p", { class: "sub", text: vozInfo }) : null,
      h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "comecar", onclick: aoComecar.fn }, "Começar")));
    focar("#comecar");
  }

  /* =====================================================================
     Formato 2 · conversa ao vivo
     ===================================================================== */
  function conversa() {
    const T = D.turnos;
    etapas(T.map((_, i) => String(i + 1)));
    let i = 0;
    function turno(corrigido) {
      const t = T[i];
      marcar(i, T.length);
      falar(corrigido ? `Je pense que vous vouliez dire : « ${t.modelo} »` : "♪ …");
      const dica = h("div", { class: "sub dica-pt", hidden: true }, h("p", { style: "margin:0", text: "O que ele disse: " + t.contexto_pt }), h("p", { style: "margin:0", text: "A sua frase: " + t.modelo_pt }));
      trocar(conteudo,
        h("p", { class: "instr" }, h("b", { text: NOME }), corrigido ? " corrige com gentileza. Ouça e repita." : " fala com você."),
        h("div", { class: "linha" },
          botaoSom(corrigido ? null : t.npc, "Ouvir de novo", { id: "ouvir-npc", onclick: null }),
          h("button", { type: "button", class: "botao sec mini", id: "dica", "aria-expanded": "false", onclick: e => { dica.hidden = !dica.hidden; e.currentTarget.setAttribute("aria-expanded", String(!dica.hidden)); } }, "Dica em português")),
        dica,
        h("p", { class: "instr", style: "margin:10px 0 2px", text: corrigido ? "Repita:" : "Sua vez — diga:" }),
        h("div", { class: "dizer" }, h("p", { class: "fala-modelo", lang: "fr", text: t.modelo })),
        V.painel({ alvos: [t.modelo], chaves: t.chaves, modelo: t.modelo, ouvirModelo: () => tocar(t.modelo_audio),
          forcarTexto: PREVIA.estado === "digitar", aoResultado: r => resultado(r, corrigido) }));
      const ouvirNpc = document.getElementById("ouvir-npc");
      ouvirNpc.addEventListener("click", () => corrigido ? tocarSeguido(D.correcao, t.modelo_audio) : tocar(t.npc));
      topo();
      if (corrigido) auto(D.correcao, t.modelo_audio);
      else if (i === 0) auto(D.abertura, t.npc); else auto(t.npc);
    }
    function resultado(r, corrigido) {
      const t = T[i];
      if (r.modo !== "voz") E.falaPendente = true;
      const ouvi = r.ouvido ? h("p", { class: "ouvido" }, (r.modo === "voz" ? "Ouvi: “" : "Você escreveu: “") + r.ouvido + "”") : null;
      const proximo = () => { i++; if (i < T.length) turno(false); else final(); };
      if (r.ok) {
        E.acertos++;
        falar(sorteia(["Très bien !", "Parfait !", "Oui, c'est ça !"]));
        mostrarRetorno("ok", "Très bien !", ouvi, continuar(proximo, i + 1 < T.length ? "Continuar" : "Desembarcar"));
        focar("#continuar");
      } else if (!corrigido) {
        E.erros++;
        mostrarRetorno("erro", "Je pense que vous vouliez dire…", ouvi, h("p", { text: `O capitão diz o modelo: “${t.modelo}”. Ouça e repita.` }));
        turno(true);
      } else {
        mostrarRetorno("meio", "Quase! Vamos seguir viagem.", ouvi, h("p", { text: `Treine depois: “${t.modelo}” (${t.modelo_pt}).` }), continuar(proximo));
        focar("#continuar");
      }
    }
    function final() {
      marcar(T.length, T.length);
      falar("Bonne journée à Québec !");
      tocar(D.fecho);
      concluir();
    }
    if (PREVIA.tela === "recompensa") return concluir({ acertos: 6, erros: 1, fala_pendente: false, duracao_s: 190 });
    if (PREVIA.passo) {
      i = Math.min(T.length, PREVIA.passo) - 1;
      turno(false);
      if (PREVIA.estado === "erro") resultado({ ok: false, ouvido: "Je vais au marché.", modo: "voz" }, false);
      return;
    }
    abertura(`${T.length} falas · cerca de 3 minutos · ${D.cenario.veiculo ? D.cenario.veiculo.fr + " = " + D.cenario.veiculo.pt : ""}`, { voz: true, fn: () => turno(false) });
  }

  /* =====================================================================
     Formato 3 · história do bardo
     ===================================================================== */
  function historia() {
    const passos = [];
    D.segmentos.forEach((s, k) => {
      passos.push({ tipo: "seg", s, k });
      D.perguntas.filter(q => q.apos === k + 1).forEach(q => passos.push({ tipo: "perg", q }));
    });
    if (D.ordenar) passos.push({ tipo: "ordenar" });
    etapas([...D.segmentos.map((_, k) => "Trecho " + (k + 1)), "Resumo"]);
    const etapaDe = p => p.tipo === "seg" ? p.k : p.tipo === "perg" ? (p.q.tipo === "resumo" ? D.segmentos.length : p.q.apos - 1) : D.segmentos.length;
    let i = 0;
    const seguir = () => { i++; if (i < passos.length) mostrar(); else final(); };
    function mostrar() {
      const p = passos[i];
      marcar(etapaDe(p), D.segmentos.length + 1);
      esconderRetorno(); topo();
      if (p.tipo === "seg") return trecho(p);
      if (p.tipo === "perg") return pergunta(p.q);
      return ordenar();
    }
    function trecho(p) {
      falar("♪ …");
      const pt = h("span", { class: "pt", hidden: true, text: p.s.pt });
      trocar(conteudo,
        h("p", { class: "sub", text: `${NOME} · trecho ${p.k + 1} de ${D.segmentos.length}` }),
        h("div", { class: "dialogo-bardo", lang: "fr" }, p.s.fr, pt),
        h("div", { class: "linha", style: "margin-top:8px" },
          botaoSom(p.s.audio, "Ouvir de novo", { id: "ouvir-trecho" }),
          h("button", { type: "button", class: "botao sec mini", id: "traducao", onclick: () => { pt.hidden = !pt.hidden; } }, "Tradução"),
          h("button", { type: "button", class: "botao", id: "continuar", onclick: seguir }, "Continuar")));
      if (p.k === 0) auto(D.abertura, p.s.audio); else auto(p.s.audio);
      focar("#continuar");
    }
    function pergunta(q) {
      falar(q.fr);
      const ops = q.tipo === "simnao" ? q.opcoes.map((o, k) => ({ o, k })) : embaralhar(q.opcoes.map((o, k) => ({ o, k })));
      const botoes = ops.map(({ o, k }) => h("button", { type: "button", class: "opcao", lang: "fr", "data-k": k, onclick: () => escolher(k) }, o));
      function escolher(k) {
        botoes.forEach(b => { b.disabled = true; const bk = Number(b.dataset.k); if (bk === q.correta) b.classList.add("certa"); else if (bk === k) b.classList.add("errada"); });
        if (k === q.correta) { E.acertos++; falar("Bravo !"); mostrarRetorno("ok", "Bravo !", h("p", { text: q.explicacao }), continuar(seguir)); }
        else { E.erros++; falar("Hmm… pas tout à fait."); mostrarRetorno("erro", "Pas tout à fait…", h("p", { text: q.explicacao }), continuar(seguir)); }
        focar("#continuar");
      }
      const rotulo = q.tipo === "simnao" ? "Pergunta de sim ou não" : q.tipo === "resumo" ? "Resumo da história" : "Escolha a resposta";
      trocar(conteudo,
        h("p", { class: "sub", text: rotulo }),
        h("p", { class: "fala-npc", lang: "fr" }, q.fr, " ", botaoSom(q.audio, "", { "aria-label": "Ouvir a pergunta", class: "botao sec som mini" })),
        h("p", { class: "sub", text: q.pt }),
        h("div", { class: q.tipo === "simnao" ? "simnao" : "opcoes lista" }, botoes));
      auto(q.audio);
      if (PREVIA.estado === "erro") botoes.find(b => Number(b.dataset.k) !== q.correta).click();
    }
    function ordenar() {
      const o = D.ordenar;
      falar(o.fr);
      const alvo = h("div", { class: "ordem-alvo", "aria-label": "Sua ordem" });
      const banco = h("div", { class: "ordem-banco" });
      const conferir = h("button", { type: "button", class: "botao", id: "conferir-ordem", disabled: true }, "Conferir");
      embaralhar(o.eventos.map((e, k) => ({ e, k }))).forEach(({ e, k }) => {
        const b = h("button", { type: "button", class: "opcao", lang: "fr", "data-k": k, title: e.pt }, e.fr);
        b.addEventListener("click", () => { (b.parentNode === banco ? alvo : banco).append(b); conferir.disabled = banco.children.length > 0; });
        banco.append(b);
      });
      conferir.addEventListener("click", () => {
        const ordem = [...alvo.children].map(b => Number(b.dataset.k));
        const ok = ordem.every((k, j) => k === j);
        [...alvo.children].forEach((b, j) => { b.disabled = true; b.classList.add(Number(b.dataset.k) === j ? "certa" : "errada"); });
        conferir.disabled = true;
        if (ok) { E.acertos++; mostrarRetorno("ok", "C'est la bonne histoire !", continuar(final, "Terminar")); }
        else { E.erros++; mostrarRetorno("erro", "A ordem certa era:", h("ol", {}, o.eventos.map(e => h("li", { lang: "fr", text: e.fr }))), continuar(final, "Terminar")); }
        focar("#continuar");
      });
      trocar(conteudo,
        h("p", { class: "fala-npc", lang: "fr" }, o.fr, " ", botaoSom(o.audio, "", { "aria-label": "Ouvir", class: "botao sec som mini" })),
        h("p", { class: "sub", text: o.pt + " Toque nos acontecimentos na ordem em que aconteceram." }),
        alvo, banco, h("div", { class: "linha", style: "margin-top:8px" }, conferir));
      auto(o.audio);
    }
    function final() { falar("Merci, mes amis !"); tocar(D.fecho); concluir(); }
    if (PREVIA.tela === "recompensa") return concluir({ acertos: 6, erros: 1, fala_pendente: false, duracao_s: 250 });
    if (PREVIA.passo) { i = Math.min(passos.length, PREVIA.passo) - 1; return mostrar(); }
    abertura(`${D.segmentos.length} trechos curtos · perguntas de sim/não, escolha e resumo`, { voz: false, fn: mostrar });
  }

  /* =====================================================================
     Formato 4 · biblioteca (leitura + grimório + Forja da Memória)
     ===================================================================== */
  function biblioteca() {
    const G = D.glossario, PG = D.pergaminhos;
    const CHAVE_G = PRE + "grimorio";
    const DIA = 86400000;
    let memoria = null;   /* prévia: grimório só em memória */
    function lerG() { if (memoria) return memoria; try { return JSON.parse(localStorage.getItem(CHAVE_G) || "{}"); } catch (e) { return {}; } }
    function gravarG(g) { if (memoria) { memoria = g; return; } try { localStorage.setItem(CHAVE_G, JSON.stringify(g)); } catch (e) { memoria = g; } }
    if (EM_PREVIA) {
      memoria = {};
      if (PREVIA.estado === "aberta" || PREVIA.tela === "forja") {
        const agora = Date.now(), ids = Object.keys(G);
        [[ids[1], 2], [ids[2], 1], [ids[5], 3], [ids[8], 1]].forEach(([id, s]) => { memoria[id] = { fr: G[id].fr, pt: G[id].pt, estado: "aprendendo", selos: s, intervalo: 0, proxima: agora - 1 }; });
        memoria[ids[0]] = { fr: G[ids[0]].fr, pt: G[ids[0]].pt, estado: "conhecida", selos: 4, intervalo: 8, proxima: agora + 8 * DIA };
      }
    }
    const estadoDe = id => { const r = lerG()[id]; return r ? r.estado : "nova"; };
    etapas([...PG.map((_, k) => "Pergaminho " + (k + 1)), "Forja"]);
    let k = 0, aberto = null;

    function marcaTermo(b) {
      const id = b.dataset.id, r = lerG()[id], est = r ? r.estado : "nova";
      b.className = "termo " + est + (aberto === id ? " ativo" : "");
      b.style.setProperty("--selos", r ? r.selos : 0);
      const txt = est === "aprendendo" ? "aprendendo, " + r.selos + (r.selos === 1 ? " selo" : " selos") : est === "conhecida" ? "conhecida" : "nova";
      b.setAttribute("aria-label", `${b.dataset.txt} — ${txt}. Ver tradução`);
      let m = b.querySelector(".marca");
      if (est === "nova") { if (m) m.remove(); return; }
      if (!m) { m = h("span", { class: "marca", "aria-hidden": "true" }); b.append(m); }
      m.textContent = est === "conhecida" ? "✓" : "◆" + r.selos;
    }
    const atualizarTermos = () => { document.querySelectorAll(".termo[data-id]").forEach(marcaTermo); const c = document.getElementById("grimorio-cont"); if (c) c.textContent = contagem(); };
    function contagem() {
      const g = lerG(), v = Object.values(g);
      return `Grimório: ${v.filter(r => r.estado === "aprendendo").length} aprendendo · ${v.filter(r => r.estado === "conhecida").length} conhecidas`;
    }
    /* frase → nós de texto + botões de termo (maior termo primeiro, sem sobreposição) */
    function frasePartes(texto, termos) {
      const marcas = [];
      [...termos].sort((a, b) => G[b].fr.length - G[a].fr.length).forEach(id => {
        const esc = G[id].fr.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const re = new RegExp(`(?<![\\p{L}])${esc}(?![\\p{L}])`, "giu");
        let m;
        while ((m = re.exec(texto))) {
          const a = m.index, b = a + m[0].length;
          if (!marcas.some(x => a < x.b && b > x.a)) marcas.push({ a, b, id });
        }
      });
      marcas.sort((x, y) => x.a - y.a);
      const out = []; let pos = 0;
      for (const mk of marcas) {
        if (mk.a > pos) out.push(texto.slice(pos, mk.a));
        const t = texto.slice(mk.a, mk.b);
        const b = h("button", { type: "button", class: "termo", "data-id": mk.id, "data-txt": t, onclick: () => abrir(mk.id) }, t);
        out.push(b);
        pos = mk.b;
      }
      if (pos < texto.length) out.push(texto.slice(pos));
      return out;
    }
    function mudar(id, fn) { const g = lerG(); fn(g); gravarG(g); atualizarTermos(); abrir(id, true); }
    function abrir(id, semSom) {
      aberto = id;
      const t = G[id], r = lerG()[id], est = r ? r.estado : "nova";
      const glosa = document.getElementById("glosa");
      const agora = Date.now();
      let controles;
      if (est === "nova") controles = h("div", { class: "linha" },
        h("button", { type: "button", class: "botao", id: "guardar", onclick: () => mudar(id, g => { g[id] = { fr: t.fr, pt: t.pt, estado: "aprendendo", selos: 1, intervalo: 0, proxima: agora, origem: CFG.pid }; }) }, "Guardar no grimório"),
        h("button", { type: "button", class: "botao sec", id: "ja-conheco", onclick: () => mudar(id, g => { g[id] = { fr: t.fr, pt: t.pt, estado: "conhecida", selos: 4, intervalo: 30, proxima: agora + 30 * DIA, origem: CFG.pid }; }) }, "Já conheço"));
      else if (est === "aprendendo") controles = h("div", {},
        h("div", { class: "selos", role: "group", "aria-label": "Selos de aprendizado (1 a 4)" }, h("span", { class: "sub", style: "margin:0 4px 0 0", text: "Selos:" }),
          [1, 2, 3, 4].map(s => h("button", { type: "button", class: "selo" + (s <= r.selos ? " on" : ""), "aria-pressed": String(s <= r.selos), "aria-label": s + (s === 1 ? " selo" : " selos"),
            onclick: () => mudar(id, g => { g[id].selos = s; }) }, "◆"))),
        h("div", { class: "linha", style: "margin-top:6px" },
          h("button", { type: "button", class: "botao", id: "marcar-conhecida", onclick: () => mudar(id, g => { g[id].estado = "conhecida"; g[id].selos = 4; }) }, "Conhecida ✓"),
          h("button", { type: "button", class: "botao sec", onclick: () => mudar(id, g => { delete g[id]; }) }, "Tirar do grimório")));
      else controles = h("div", { class: "linha" },
        h("button", { type: "button", class: "botao sec", onclick: () => mudar(id, g => { g[id].estado = "aprendendo"; g[id].selos = 3; g[id].proxima = agora; }) }, "Voltar a aprender"),
        h("button", { type: "button", class: "botao sec", onclick: () => mudar(id, g => { delete g[id]; }) }, "Tirar do grimório"));
      trocar(glosa,
        h("div", { class: "linha" }, h("span", { class: "fr", lang: "fr", text: t.fr }), botaoSom(t.audio, "", { "aria-label": "Ouvir " + t.fr, class: "botao sec som mini" }),
          h("span", { class: "pt", text: "— " + t.pt })),
        h("p", { class: "ex" }, h("span", { lang: "fr", text: t.exemplo }), " ", botaoSom(t.exemplo_audio, "", { "aria-label": "Ouvir o exemplo", class: "botao sec som mini" }), h("br"), h("i", { text: t.exemplo_pt })),
        controles);
      glosa.hidden = false;
      atualizarTermos();
      if (!semSom) tocar(t.audio);
    }
    function pergaminho() {
      const p = PG[k];
      aberto = null;
      marcar(k, PG.length + 1); esconderRetorno(); calar();
      const linhas = p.frases.map((f, j) => h("p", { class: "frase", "data-j": j, lang: "fr" },
        botaoSom(f.audio, "", { "aria-label": "Ouvir a frase " + (j + 1), class: "botao sec som mini" }), h("span", {}, frasePartes(f.fr, p.termos))));
      const lerTudo = async () => {
        falar("♪ …");
        for (const [j, l] of linhas.entries()) { l.classList.add("lendo"); await tocar(p.frases[j].audio); l.classList.remove("lendo"); }
        calar();
      };
      const q = p.pergunta;
      const opcoes = q.opcoes.map((o, n) => h("button", { type: "button", class: "opcao", lang: "fr", "data-k": n, onclick: () => responder(n) }, o));
      function responder(n) {
        opcoes.forEach(b => { b.disabled = true; const bk = Number(b.dataset.k); if (bk === q.correta) b.classList.add("certa"); else if (bk === n) b.classList.add("errada"); });
        const ok = n === q.correta; if (ok) E.acertos++; else E.erros++;
        const prox = k + 1 < PG.length ? () => { k++; pergaminho(); } : forja;
        mostrarRetorno(ok ? "ok" : "erro", ok ? "Exactement !" : "Pas tout à fait…", h("p", { lang: "fr", text: `« ${q.opcoes[q.correta]} »` }),
          continuar(prox, k + 1 < PG.length ? "Próximo pergaminho" : "Ir à Forja da Memória"));
        focar("#continuar");
      }
      trocar(conteudo,
        h("div", { class: "pergaminho" },
          h("h3", {}, p.titulo, " ", h("span", { text: "· " + p.titulo_pt })),
          linhas),
        h("div", { class: "linha", style: "margin-top:8px" },
          h("button", { type: "button", class: "botao sec som", id: "ler-tudo", onclick: lerTudo }, "Frère Anselme lê"),
          h("span", { class: "grimorio-cont", id: "grimorio-cont", text: contagem() })),
        h("ul", { class: "legenda", "aria-label": "Legenda" },
          h("li", {}, h("span", { class: "termo nova" }, "palavra"), " nova"),
          h("li", {}, h("span", { class: "termo aprendendo", style: "--selos:2" }, "palavra", h("span", { class: "marca" }, "◆2")), " aprendendo (1–4 selos)"),
          h("li", {}, h("span", { class: "termo conhecida" }, "palavra", h("span", { class: "marca" }, "✓")), " conhecida")),
        h("div", { class: "glosa", id: "glosa", hidden: true, "aria-live": "polite" }),
        h("p", { class: "instr", style: "margin:12px 0 4px;font-weight:700" }, "Compreensão: ", h("span", { lang: "fr", text: q.fr }), " ", botaoSom(q.audio, "", { "aria-label": "Ouvir a pergunta", class: "botao sec som mini" })),
        h("p", { class: "sub", text: q.pt }),
        h("div", { class: "opcoes lista" }, opcoes));
      atualizarTermos(); topo();
      if (k === 0) auto(D.abertura);
      if (PREVIA.estado === "aberta") abrir(p.termos[1], true);
    }
    function forja() {
      marcar(PG.length, PG.length + 1); esconderRetorno();
      falar("La forge de la mémoire…");
      const agora = Date.now();
      const g = lerG();
      const fila = Object.entries(g).filter(([, r]) => r.estado === "aprendendo" && r.proxima <= agora).sort((a, b) => a[1].proxima - b[1].proxima).slice(0, 10).map(([id]) => id);
      const bau = () => h("div", { class: "bau" + (fila.length ? " aberto" : ""), "aria-hidden": "true" }, h("i", { class: "tampa" }), h("i", { class: "corpo" }), h("i", { class: "faixa e" }), h("i", { class: "faixa d" }), h("i", { class: "fecho" }));
      const terminar = () => { tocar(D.fecho); concluir(); };
      let revisadas = 0;
      function vazia() {
        trocar(conteudo, h("div", { class: "forja" },
          h("h2", { text: "Forja da Memória" }), bau(),
          h("p", { text: revisadas ? `Pronto: ${revisadas} ${revisadas === 1 ? "carta forjada" : "cartas forjadas"}. O monge guardou cada uma para o dia certo.` : "O baú está vazio: nada para revisar agora. Guarde palavras no grimório e volte outro dia." }),
          h("p", { class: "sub", text: contagem() }),
          h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "terminar", onclick: terminar }, "Concluir parada"))));
        focar("#terminar");
      }
      function carta() {
        if (!fila.length) return vazia();
        const id = fila[0], t = G[id] || g[id];
        const verso = h("div", { hidden: true }, h("p", { class: "pt", style: "font-size:1.1rem;margin:6px 0 0", text: t.pt }),
          G[id] ? h("p", { class: "sub", style: "margin:4px 0 0" }, h("span", { lang: "fr", text: G[id].exemplo }), " — ", G[id].exemplo_pt) : null);
        const ficha = h("div", { class: "ficha-forja" }, h("div", { class: "linha", style: "justify-content:center" }, h("span", { class: "fr", lang: "fr", text: t.fr }),
          G[id] ? botaoSom(G[id].audio, "", { "aria-label": "Ouvir " + t.fr, class: "botao sec som mini" }) : null), verso);
        const notas = h("div", { class: "linha", hidden: true, style: "margin-top:10px" },
          h("button", { type: "button", class: "botao sec", id: "forja-errei", onclick: () => avaliar("errei") }, "Errei"),
          h("button", { type: "button", class: "botao sec", id: "forja-dificil", onclick: () => avaliar("dificil") }, "Difícil"),
          h("button", { type: "button", class: "botao", id: "forja-facil", onclick: () => avaliar("facil") }, "Fácil"));
        const revelar = h("button", { type: "button", class: "botao", id: "forja-revelar", onclick: () => { verso.hidden = false; notas.hidden = false; revelar.hidden = true; focar("#forja-facil"); } }, "Revelar");
        const aviso = h("p", { class: "sub", id: "forja-aviso", role: "status" });
        function avaliar(n) {
          const gg = lerG(), r = gg[id]; if (!r) { fila.shift(); return carta(); }
          const agora2 = Date.now();
          let msg;
          if (n === "errei") { r.selos = Math.max(1, r.selos - 1); r.intervalo = 0; r.proxima = agora2 + 10 * 60000; fila.splice(Math.min(3, fila.length), 0, fila.shift()); msg = "O monge devolve esta carta logo, ainda nesta sessão."; }
          else if (n === "dificil") { r.intervalo = 1; r.proxima = agora2 + DIA; fila.shift(); msg = "Volta amanhã."; }
          else { r.intervalo = Math.max(3, Math.round((r.intervalo || 1) * 2.5)); r.proxima = agora2 + r.intervalo * DIA; r.selos = Math.min(4, r.selos + 1); fila.shift(); msg = `Volta em ${r.intervalo} dias.`; }
          gravarG(gg); revisadas++;
          aviso.textContent = msg;
          if (reduz) { carta(); return; }
          ficha.classList.add("volta");
          setTimeout(carta, 460);
        }
        trocar(conteudo, h("div", { class: "forja" },
          h("h2", { text: "Forja da Memória" }),
          h("p", { class: "sub", text: `${NOME} tira as cartas do baú · ${fila.length} para revisar` }),
          bau(), ficha, h("div", { class: "linha", style: "margin-top:10px" }, revelar), notas, aviso,
          h("div", { class: "linha", style: "margin-top:6px" }, h("button", { type: "button", class: "botao sec mini", onclick: () => { fila.length = 0; vazia(); } }, "Parar a revisão"))));
        topo(); focar("#forja-revelar");
      }
      carta();
    }
    if (PREVIA.tela === "recompensa") return concluir({ acertos: 3, erros: 0, fala_pendente: false, duracao_s: 380 });
    if (PREVIA.tela === "forja") return forja();
    if (PREVIA.passo) { k = Math.min(PG.length, PREVIA.passo) - 1; return pergaminho(); }
    abertura(`${PG.length} pergaminhos · toque nas palavras sublinhadas · nada vira "conhecida" sozinho: você decide`, { voz: false, fn: pergaminho });
  }

  /* =====================================================================
     Formato 5 · cartas com voz
     ===================================================================== */
  function cartas() {
    const C = D.cartas, F = D.falas;
    etapas(C.map(() => "◆"));
    const S = C.map(c => ({ c, estado: "ativa", esperaAte: 0, el: null }));
    let tentativas = 0, sel = null, ultimos = [];
    const mesa = h("div", { class: "mesa", role: "group", "aria-label": "Cartas na mesa" });
    const painelArea = h("div", { class: "painel-carta" });
    const placar = h("p", { class: "sub", id: "placar", role: "status" });
    const feitas = () => S.filter(s => s.estado === "feita").length;
    function atualizarPlacar() {
      placar.textContent = `${feitas()} de ${C.length} cartas · ${S.filter(s => s.estado === "espera").length} esperando no fim da fila`;
      marcar(feitas(), C.length);
    }
    S.forEach((s, i) => {
      const b = h("button", { type: "button", class: "carta", "data-id": s.c.id, "aria-label": `Carta ${i + 1}: ${s.c.pt}. Diga o nome em francês` },
        h("span", { class: "lado face", "aria-hidden": "true" }, h("img", { src: CFG.estatico + D.imagens[s.c.img].src, alt: "" })),
        h("span", { class: "lado tras", "aria-hidden": "true" }, h("b", { class: "sinal" }), h("span", { class: "nome", lang: "fr" })),
        h("span", { class: "lado verso", "aria-hidden": "true" }));
      b.addEventListener("click", () => escolher(s));
      s.el = b; mesa.append(b);
    });
    function escolher(s) {
      if (s.estado !== "ativa") return;
      S.forEach(x => x.el.classList.toggle("sel", x === s));
      sel = s;
      esconderRetorno();
      trocar(painelArea,
        h("p", { class: "instr", style: "margin:8px 0 0" }, "Como se diz isto em francês? ", h("i", { class: "sub", text: "(" + s.c.pt + ")" })),
        V.painel({ alvos: s.c.aceita, modelo: s.c.fr, ouvirModelo: () => tocar(s.c.audio), forcarTexto: PREVIA.estado === "digitar", aoResultado: r => resultado(s, r) }));
      const alvo = painelArea.querySelector("#falar, #resposta-texto");
      if (alvo) alvo.scrollIntoView({ block: "nearest" });
    }
    function liberar(recente) {
      const ativas = S.filter(x => x.estado === "ativa").length;
      S.forEach(x => {
        if (x.estado === "espera" && (tentativas >= x.esperaAte || ativas === 0)) {
          x.estado = "ativa";
          const volta = () => { if (x.estado === "ativa") { x.el.classList.remove("espera", "virada", "errada"); x.el.disabled = false; } };
          if (x === recente) setTimeout(volta, reduz ? 600 : 1600); else volta();   /* deixa ver o erro antes de voltar */
        }
      });
    }
    function resultado(s, r) {
      if (r.modo !== "voz") E.falaPendente = true;
      tentativas++;
      s.el.classList.remove("sel"); sel = null;
      s.el.querySelector(".nome").textContent = s.c.fr;
      s.el.disabled = true;
      ultimos.push(r.ok); ultimos = ultimos.slice(-3);
      const ouvi = r.ouvido ? h("p", { class: "ouvido" }, (r.modo === "voz" ? "Ouvi: “" : "Você escreveu: “") + r.ouvido + "”") : null;
      trocar(painelArea);
      if (r.ok) {
        E.acertos++; s.estado = "feita";
        s.el.querySelector(".sinal").textContent = "✓";
        s.el.classList.add("virada");
        tocar(s.c.audio);
        mostrarRetorno("ok", `Oui ! ${s.c.fr}`, ouvi);
        setTimeout(() => { s.el.classList.add("saindo"); setTimeout(() => { s.el.classList.add("saiu"); s.el.setAttribute("aria-hidden", "true"); s.el.tabIndex = -1; }, reduz ? 0 : 500); }, reduz ? 300 : 900);
      } else {
        E.erros++; s.estado = "espera";
        s.el.querySelector(".sinal").textContent = "✗";
        s.el.classList.add("virada", "errada");
        const outras = S.filter(x => x.estado === "ativa").length;
        s.esperaAte = tentativas + Math.max(1, outras);
        falar("Non… ce n'est pas ça.");
        tocarSeguido(F.erro, s.c.audio);
        mostrarRetorno("erro", `Era “${s.c.fr}”`, ouvi, h("p", { text: "A carta volta para o fim da fila. Ouça e tente de novo daqui a pouco." }));
        setTimeout(() => { if (s.estado === "espera") { s.el.classList.remove("virada", "errada"); s.el.classList.add("espera"); } }, reduz ? 600 : 1600);
      }
      liberar(s);
      atualizarPlacar();
      const restam = C.length - feitas();
      if (!restam) { setTimeout(final, reduz ? 400 : 1300); return; }
      if (restam === 1 && r.ok) { falar("Plus qu'une carte…"); setTimeout(() => tocar(F.ultima), 700); }
      else if (tentativas % (D.comentar_a_cada || 3) === 0) {
        const boa = ultimos.every(Boolean), chave = sorteia(boa ? F.boa : F.mista);
        falar(D.audios[chave].texto); setTimeout(() => tocar(chave), r.ok ? 700 : 2600);
      }
    }
    function final() { falar("Je vois… un bel avenir en français !"); tocar(F.fecho); concluir(); }
    function mostrarMesa() {
      esconderRetorno();
      falar("Touchez une carte…");
      trocar(conteudo, h("p", { class: "instr", text: D.instrucao }), placar, mesa, painelArea);
      atualizarPlacar();
    }
    if (PREVIA.tela === "recompensa") return concluir({ acertos: 9, erros: 2, fala_pendente: true, duracao_s: 230 });
    if (PREVIA.passo) {
      S.slice(0, Math.min(C.length - 1, PREVIA.passo)).forEach(s => { s.estado = "feita"; s.el.classList.add("saiu"); s.el.tabIndex = -1; });
      mostrarMesa();
      const s = S.find(x => x.estado === "ativa");
      if (PREVIA.estado === "erro") { escolher(s); resultado(s, { ok: false, ouvido: "une poire", modo: "voz" }); }
      else if (PREVIA.estado === "digitar") escolher(s);
      return;
    }
    abertura("9 cartas · erro volta para o fim da fila · acerto fica verde e sai da mesa", { voz: true, fn: () => { mostrarMesa(); auto(F.abertura); } });
  }

  window.chemin_formato = { estado: E, dados: D };
  ({ conversa, historia, biblioteca, cartas })[D.formato]();
})();
