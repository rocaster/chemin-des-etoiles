/* Batalha (protótipo) — regras confirmadas pelo Alex:
   - acerto = ataque; o tipo vem do combo: 1 = Léger (corte), 2 seguidos = Fort (golpe), 3+ = Spécial (animação da classe). Sem botões de ataque.
   - barras de 5 segmentos. Dano: Léger 1, Fort 2, Spécial 3 (nunca abaixo de 0). Ex.: 3 acertos seguidos = 1+2+3 = vitória.
   - Spécial diferente por classe (cavaleiro, arqueiro, mago, bardo; masculino e feminino da classe dividem a animação).
   - Spécial é reutilizável e fica sempre no painel; depois de cada Spécial o combo volta a zero
     (o próximo acerto é Léger de novo e são precisos mais 3 seguidos para outro Spécial).
   - erro zera o combo e o herói perde 1 segmento; 5 erros = derrota.
   - barras configuráveis por batalha (regras.vida_heroi / vida_inimigo). Chefe (cenario.chefe, etapa 40 · Castelo): 20 barras,
     sprite maior (quadros de 128×96), fundo do salão do castelo; mensagens.vitoria/derrota.sub trocam o texto final.
   - contra-ataque: depois de cada pergunta de ataque, se o inimigo ainda está de pé, ele prepara o golpe e aparece a DEFESA:
     dizer em voz alta uma palavra/número em francês (voz.js, fr-CA, comparação tolerante). Sem microfone: escrever o que ouviu
     ou escolher entre 3 (a palavra fica escondida nesses modos — só áudio + dica). Acertou = bloqueio (sem dano);
     errou = o golpe acerta (−1 barra). A defesa NÃO mexe no combo. Não há contra-ataque depois do golpe final.
   - dor do inimigo = exatamente 2 quadros: rosto de dor + flash branco, depois idle.
   - vitória: inimigo cai e fica no chão, herói comemora; derrota: herói cai, tela escurece, mensagem. Volta ao mapa.
   - defesa com timer (padrão 5 s, ?timer=N; ?timer=0 desliga): começa depois que o aviso e o áudio terminam; tempo esgotado = golpe.
     Se o reconhecimento de voz está no meio de um resultado em 0 s, há 0,7 s de tolerância. Aba escondida pausa o timer.
   - é a PARADA 9 da região 1: vitória conclui a parada pela mesma rota das outras (POST /parada/1/9/concluir + localStorage
     do prefixo do usuário) e libera a 10; XP pausado = 0 (só conclusão + estrelas). Derrota: nada é salvo, volta ao mesmo ponto. */
(() => {
  "use strict";
  const D = JSON.parse(document.getElementById("dados-batalha").textContent);
  const CFG = JSON.parse(document.getElementById("cfg-batalha").textContent);
  const reduz = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = id => document.getElementById(id);
  const heroi = $("heroi"), inimigo = $("inimigo"), conteudo = $("conteudo"), efeito = $("efeito"), efeitoHeroi = $("efeito-heroi");
  const comboEl = $("combo"), numero = $("numero"), flash = $("flash"), escuro = $("escuro"), msg = $("mensagem");
  const QH = { idle: [0, 1], ataque: [2, 3], dor: [4, 5], queda: [6, 7, 8], festa: [9, 10, 11] };
  const QI = { idle: [0, 1], dor: [2], queda: [3, 4], prep: 5, golpe: 6 };
  const espera = ms => new Promise(r => setTimeout(r, reduz ? Math.min(ms, 120) : ms));

  function h(tag, attrs, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v === true ? "" : v);
    }
    for (const f of filhos.flat()) if (f != null) e.append(f instanceof Node ? f : document.createTextNode(String(f)));
    return e;
  }
  const embaralhar = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

  /* ---------- inimigo ---------- */
  const ids = Object.keys(D.inimigos);
  const idInimigo = CFG.inimigo || ids[Math.floor(Math.random() * ids.length)];
  const INI = D.inimigos[idInimigo];
  inimigo.style.backgroundImage = `url("${CFG.estatico}${INI.img}")`;
  $("nome-inimigo").textContent = INI.nome;
  $("nome-inimigo").title = INI.pt;
  document.body.dataset.inimigo = idInimigo;

  /* ---------- sprites ---------- */
  const quadro = (el, f) => { el.classList.remove("idle"); el.style.setProperty("--f", f); el.style.backgroundPosition = ""; };
  const ocioso = el => { el.style.removeProperty("--f"); el.classList.add("idle"); };
  async function anima(el, fs, ms) { for (const f of fs) { quadro(el, f); await espera(ms); } }
  async function efeitoEm(el, tipo) {
    el.className = "efeito " + tipo; el.hidden = false;
    if (reduz) { el.style.setProperty("--f", 1); await espera(250); }
    else for (let f = 0; f < 4; f++) { el.style.setProperty("--f", f); await espera(70); }
    el.hidden = true;
  }

  /* ---------- áudio ---------- */
  const voz = new Audio(), sfx = new Audio();
  function tocar(player, src) {
    return new Promise(res => {
      let ok = false; const fim = () => { if (!ok) { ok = true; res(); } };
      player.onended = fim; player.onerror = fim; setTimeout(fim, 4000);
      try { player.pause(); player.src = src; const p = player.play(); if (p && p.catch) p.catch(fim); } catch (e) { fim(); }
    });
  }
  const som = nome => { tocar(sfx, `${CFG.estatico}batalha/som-${nome}.wav`); };
  const fala = chave => tocar(voz, CFG.audio_batalha + chave + ".mp3");
  const palavra = item => tocar(voz, CFG.audio + item.audio);

  /* ---------- barras ---------- */
  const E = { vidaH: D.regras.vida_heroi, vidaI: D.regras.vida_inimigo, combo: 0, acertos: 0, erros: 0, fila: [], ocupado: false, fim: false, defesas: [], filaD: [],
             golpes: 0, inicio: Date.now(), salvo: null };
  function barra(id, vida, antes) {   /* antes: vida anterior — pisca todos os segmentos perdidos de uma vez */
    const b = $(id), seg = [...b.children];
    seg.forEach((s, i) => { s.classList.toggle("vazio", i >= vida); s.classList.remove("perde"); });
    if (antes != null) seg.slice(vida, antes).forEach(x => { void x.offsetWidth; x.classList.add("perde"); });
    b.setAttribute("aria-valuenow", vida);
  }
  const tipoCombo = c => c >= D.regras.combo.special ? "special" : c >= D.regras.combo.fort ? "fort" : "leger";
  const NOME_TIPO = { leger: "Léger", fort: "Fort", special: "Spécial" };
  function mostrarCombo() {
    document.querySelectorAll("#legenda li").forEach(li => li.classList.toggle("ativo", E.combo > 0 && li.dataset.tipo === tipoCombo(E.combo)));
    if (!E.combo) { comboEl.hidden = true; return; }
    comboEl.hidden = false; comboEl.className = "combo " + tipoCombo(E.combo);
    $("combo-n").textContent = "×" + E.combo; $("combo-tipo").textContent = NOME_TIPO[tipoCombo(E.combo)];
    if (!reduz) { void comboEl.offsetWidth; comboEl.classList.add("pula"); }
  }

  function comboZerado() {   /* mostra "×0" até a próxima resposta de ataque, para o jogador ver que o combo recomeçou */
    comboEl.hidden = false; comboEl.className = "combo zerado";
    $("combo-n").textContent = "×0"; $("combo-tipo").textContent = "Combo zéro";
  }

  /* ---------- perguntas (vocabulário das etapas que a batalha revisa: data/batalhas/<id>.json) ---------- */
  function montarFila() { E.fila = embaralhar(D.perguntas); }
  function proximaPergunta() {
    if (!E.fila.length) montarFila();
    const item = E.fila.shift();
    const modo = Math.random() < 0.5 && item.pt.length <= 28 ? "pt" : "fr";   /* pt: "Que veut dire « une clé » ?" — fr: "Comment dit-on « chave » en français ?" */
    const campo = modo === "fr" ? "fr" : "pt";
    const mesmos = D.perguntas.filter(p => p !== item && p[campo] !== item[campo]);
    const parecidos = embaralhar(mesmos.filter(p => p.origem === item.origem));
    const distr = [...parecidos, ...embaralhar(mesmos)].filter((p, i, a) => a.findIndex(x => x[campo] === p[campo]) === i).slice(0, 2);
    const opcoes = embaralhar([item, ...distr]);
    return { item, modo, opcoes, campo };
  }
  function mostrarPergunta() {
    const P = proximaPergunta();
    E.atual = P;
    const enunciado = P.modo === "fr" ? `Comment dit-on « ${P.item.pt} » en français ?` : `Que veut dire « ${P.item.fr} » ?`;
    const dica = P.modo === "fr" ? "Escolha a palavra em francês." : "Escolha o significado em português.";
    const botoes = P.opcoes.map((o, i) => h("button", { type: "button", class: "opcao", "data-i": i, lang: P.modo === "fr" ? "fr" : "pt", onclick: () => responder(i) },
      h("b", { text: "ABC"[i] + ")" }), o[P.campo]));
    conteudo.replaceChildren(
      h("p", { class: "enunciado", lang: "fr", text: enunciado }),
      h("p", { class: "dica", text: dica }),
      h("div", { class: "opcoes", role: "group", "aria-label": "Opções" }, botoes),
      h("p", { class: "retorno", id: "retorno", role: "status" }));
    E.ocupado = false;
    botoes[0].focus({ preventScroll: true });
  }
  addEventListener("keydown", e => {
    if (E.ocupado || E.fim || !E.atual) return;
    const i = { a: 0, b: 1, c: 2, 1: 0, 2: 1, 3: 2 }[e.key.toLowerCase()];
    if (i != null) responder(i);
  });

  async function responder(i) {
    if (E.ocupado || E.fim) return;
    E.ocupado = true;
    const P = E.atual, escolhida = P.opcoes[i], certa = escolhida === P.item;
    const botoes = [...conteudo.querySelectorAll(".opcao")];
    botoes.forEach((b, k) => { b.disabled = true; if (P.opcoes[k] === P.item) b.classList.add("certa"); else if (k === i) b.classList.add("errada"); });
    const ret = $("retorno");
    if (certa) {
      E.combo++; E.acertos++; mostrarCombo();
      const tipo = tipoCombo(E.combo);
      ret.className = "retorno"; ret.textContent = `${NOME_TIPO[tipo]} ! « ${P.item.fr} » = ${P.item.pt}`;
      await ataque(tipo);
    } else {
      E.combo = 0; E.erros++; mostrarCombo();
      ret.className = "retorno erro"; ret.textContent = `Raté… a resposta era « ${P.item.fr} » (${P.item.pt}).`;
      await golpeNoHeroi();
    }
    await palavra(P.item);   /* áudio fr-CA da palavra certa depois de cada resposta */
    await espera(350);
    if (E.vidaI <= 0) return vitoria();   /* golpe final: sem contra-ataque */
    if (E.vidaH <= 0) return derrota();
    if (D.regras.contra_ataque && (certa || D.regras.contra_apos_erro)) {
      await turnoInimigo();
      if (E.vidaH <= 0) return derrota();
    }
    mostrarPergunta();
  }
  /* dor do inimigo: 2 quadros — rosto de dor com flash branco curto, depois idle. O dano depende do ataque. */
  async function feridaInimigo(tipo) {
    const dano = D.regras.dano[tipo], antes = E.vidaI;
    quadro(inimigo, QI.dor[0]); inimigo.classList.add("branco");
    await espera(90); inimigo.classList.remove("branco");
    E.vidaI = Math.max(0, E.vidaI - dano); E.danoTotal = (E.danoTotal || 0) + (antes - E.vidaI); barra("barra-inimigo", E.vidaI, antes);
    numero.hidden = false; numero.textContent = "-" + dano; numero.dataset.tipo = tipo;
    numero.style.animation = "none"; void numero.offsetWidth; numero.style.animation = "";
    await espera(230);
    if (E.vidaI > 0) ocioso(inimigo);
  }
  async function ataque(tipo) {
    await anima(heroi, QH.ataque, 120);
    if (tipo === "special") await especial();
    else {
      som(tipo);
      const efeitoP = efeitoEm(efeito, { leger: "corte", fort: "golpe" }[tipo]);
      await feridaInimigo(tipo);
      await efeitoP;
    }
    ocioso(heroi);
    numero.hidden = true;
  }
  /* Spécial da classe: camada da arena com 10 quadros (steps), faixa com o nome, clarão na cor da classe, tremida no impacto */
  const CLASSE = CFG.heroi.split("-")[0], ESP = D.especiais[CLASSE];
  const IMPACTO = { cavaleiro: 4, arqueiro: 4, mago: 5, bardo: 6 }[CLASSE];
  const camada = $("especial"), faixa = $("faixa-especial");
  function mostrarFaixa() {
    $("faixa-nome").textContent = ESP.nome + " !"; $("faixa-pt").textContent = "Spécial · " + ESP.pt;
    faixa.hidden = false; faixa.style.animation = "none"; void faixa.offsetWidth; faixa.style.animation = "";
  }
  async function especial() {
    E.especiais = (E.especiais || 0) + 1;
    tocar(sfx, CFG.estatico + ESP.som);
    mostrarFaixa(); quadro(heroi, QH.ataque[1]);
    flash.classList.remove("classe"); void flash.offsetWidth; flash.classList.add("classe");
    camada.hidden = false;
    if (reduz) {   /* sem movimento: só um quadro do impacto, parado */
      camada.style.setProperty("--f", IMPACTO + 1); await feridaInimigo("special"); await espera(500);
    } else {
      let ferida;
      for (let f = 0; f < 10; f++) {
        camada.style.setProperty("--f", f);
        if (f === IMPACTO) { ferida = feridaInimigo("special"); const ar = $("arena"); ar.classList.remove("treme"); void ar.offsetWidth; ar.classList.add("treme"); }
        await espera(f < IMPACTO ? 95 : 85);
      }
      await ferida;
      $("arena").classList.remove("treme");
    }
    camada.hidden = true; faixa.hidden = true;
    E.combo = 0; mostrarCombo(); comboZerado();   /* depois do Spécial o combo zera */
  }
  async function golpeNoHeroi(dano = D.regras.dano_erro) {
    quadro(inimigo, QI.prep); await espera(110);
    quadro(inimigo, QI.golpe); inimigo.classList.add("ataca"); await espera(140);
    som("dano"); flash.classList.remove("vermelho"); void flash.offsetWidth; flash.classList.add("vermelho");
    const ef = efeitoEm(efeitoHeroi, "dano");
    await anima(heroi, QH.dor, 160);
    inimigo.classList.remove("ataca"); ocioso(inimigo);
    const antes = E.vidaH; E.vidaH = Math.max(0, E.vidaH - dano); E.golpes++; barra("barra-heroi", E.vidaH, antes);
    if (E.vidaH > 0) ocioso(heroi);
    await ef;
  }

  /* ---------- contra-ataque do inimigo: DEFESA (dizer a palavra) ---------- */
  const caixaPergunta = $("pergunta"), efeitoBloq = $("efeito-bloqueio"), bloqueado = $("bloqueado");
  const NUMFR = {}; D.defesa.filter(x => x.tipo === "numero").forEach(x => { NUMFR[x.pt] = x.fr; });
  const numPalavra = t => String(t || "").replace(/\b(\d{1,2})\b/g, (m, d) => NUMFR[Number(d)] || m);   /* "17" → "dix-sept" (voz.js só traduz 0–10 e 20) */
  const Voz = window.ChemVoz;
  const MSGV = { "no-speech": "Não ouvi nada. Aperte Falar e diga perto do microfone.", "network": "O reconhecimento precisa de internet. Tente de novo ou escreva.", "aborted": "Escuta interrompida. Tente de novo." };
  let modoDefesa = null;   /* a escolha do jogador (voz / texto / opções) vale até o fim da batalha */
  function proximaDefesa() { if (!E.filaD.length) E.filaD = embaralhar(D.defesa); return E.filaD.shift(); }   /* sem repetir até esgotar o banco */
  function aceita(item, ouvidos) {
    const lista = (Array.isArray(ouvidos) ? ouvidos : [ouvidos]).map(numPalavra);
    const c = Voz.compara(lista, item.aceitos.map(numPalavra));
    return { ok: c.ok, ouvido: (Array.isArray(ouvidos) ? ouvidos[0] : ouvidos) || "", nota: c.nota };
  }
  function opcoesDefesa(item) {
    let outros = item.parecidos && item.parecidos.length ? item.parecidos.slice(0, 2)
      : embaralhar(D.defesa.filter(x => x.tipo === item.tipo && x.fr !== item.fr)).slice(0, 2).map(x => x.fr);
    return embaralhar([item.fr, ...outros]);
  }
  /* timer da defesa: ?timer=N (segundos) ou o padrão dos dados; ?timer=0 desliga (testes) */
  const TEMPO_DEF = (() => { const q = new URLSearchParams(location.search).get("timer"); const v = q == null ? D.regras.timer_defesa_s : Number(q); return isFinite(v) ? Math.max(0, Math.min(60, v)) : 5; })();
  const GRACA_MS = Math.round((D.regras.timer_graca_s || 0.7) * 1000);
  function defender(item, modoForcado, opts = {}) {
    return new Promise(resolve => {
      let feito = false, ouvindo = false; E.defesaAtual = item;
      const T = { total: TEMPO_DEF * 1000, resta: TEMPO_DEF * 1000, ativo: false, ultimo: 0, id: 0, esgotou: false };
      const pararT = () => { clearInterval(T.id); T.ativo = false; document.removeEventListener("visibilitychange", visivel); };
      const fim = (ok, ouvido, modo) => { if (feito) return; feito = true; pararT(); E.defesas.push({ fr: item.fr, ok, modo, ouvido }); resolve({ ok, ouvido, modo }); };
      function desenharT() {
        const el = $("timer-defesa"); if (!el) return;
        const frac = T.total ? Math.max(0, T.resta) / T.total : 1;
        el.querySelector("i").style.width = (Math.ceil(frac * 20) / 20 * 100) + "%";   /* 20 degraus: encolhe "em pixels" */
        el.querySelector("b").textContent = T.total ? Math.max(0, Math.ceil(T.resta / 1000)) + " s" : "";
        el.classList.toggle("urgente", T.resta <= 2000); el.classList.toggle("parado", !T.ativo);
        el.setAttribute("aria-valuenow", Math.max(0, Math.ceil(T.resta / 1000)));
      }
      function tick() {
        const agora = performance.now();
        if (!document.hidden && T.ativo) T.resta -= agora - T.ultimo;   /* aba escondida: não desconta */
        T.ultimo = agora; desenharT();
        if (T.resta <= 0 && !T.esgotou) esgotar();
      }
      function visivel() { T.ultimo = performance.now(); }
      function iniciarT() {
        if (!T.total || feito || T.ativo || opts.congelar != null) return;
        T.ativo = true; T.ultimo = performance.now(); T.id = setInterval(tick, 100);
        document.addEventListener("visibilitychange", visivel); desenharT();
      }
      function esgotar() {
        T.esgotou = true; pararT(); desenharT();
        if (ouvindo) setTimeout(() => fim(false, "", "tempo"), GRACA_MS);   /* resultado da voz chegando: pequena tolerância */
        else fim(false, "", "tempo");
      }
      E.timerDefesa = T;
      caixaPergunta.classList.add("defesa");
      const render = (modo, reiniciar) => {
        if (modo === "voz" && !(Voz && Voz.disponivel)) modo = "opcoes";
        modoDefesa = modo;
        const AT = D.ataques_inimigo[idInimigo];
        const banner = h("p", { class: "faixa-defesa", id: "faixa-defesa" }, h("i", { class: "ic-escudo", "aria-hidden": "true" }),
          modo === "voz" ? "Bloqueie ! Diga :" : modo === "texto" ? "Bloqueie ! Escreva o que você ouve :" : "Bloqueie ! Qual você ouviu ?",
          h("small", { lang: "fr", text: AT.fr }));
        const alvo = modo === "voz" ? h("p", { class: "alvo-defesa", id: "alvo-defesa", lang: "fr", text: `« ${item.fr} »` })
                                    : h("p", { class: "alvo-defesa oculto", id: "alvo-defesa", text: "« ? »" });
        const dica = h("p", { class: "dica", text: item.tipo === "numero" ? `(o número ${item.pt})` : `(${item.pt})` });
        const status = h("p", { class: "retorno", id: "retorno-defesa", role: "status" });
        const ouvirBtn = h("button", { type: "button", class: "botao sec", id: "ouvir-defesa", onclick: () => palavra(item) }, modo === "voz" ? "▶ Ouvir" : "▶ Ouvir de novo");
        let corpo;
        if (modo === "voz") {
          const mic = h("button", { type: "button", class: "botao mic", id: "falar-defesa" }, "◉ Falar");
          mic.addEventListener("click", async () => {
            if (feito) return;
            mic.disabled = true; ouvindo = true; caixaPergunta.classList.add("ouvindo"); status.className = "retorno"; status.textContent = "Ouvindo… diga agora.";
            const r = await Voz.ouvir();
            ouvindo = false; caixaPergunta.classList.remove("ouvindo"); mic.disabled = false;
            if (feito) return;   /* o tempo já acabou */
            if (r.alternativas) { const c = aceita(item, r.alternativas); fim(c.ok, c.ouvido, "voz"); return; }
            if (T.esgotou) { fim(false, "", "tempo"); return; }
            if (!Voz.disponivel || r.erro === "indisponivel") { render("opcoes", true); return; }   /* microfone negado/sem API: escolher entre 3, tempo cheio de novo */
            status.textContent = MSGV[r.erro] || "Não consegui ouvir. Tente de novo.";   /* falha técnica não conta como erro */
          });
          corpo = h("div", { class: "linha" }, mic, ouvirBtn);
        } else if (modo === "texto") {
          const campo = h("input", { class: "campo-defesa", id: "resposta-defesa", type: "text", lang: "fr", autocomplete: "off", autocapitalize: "off", spellcheck: "false",
            "aria-label": "Escreva em francês o que você ouviu", placeholder: "Escreva em francês…" });
          const conferir = () => { if (feito) return; if (!campo.value.trim()) { campo.focus(); return; } const c = aceita(item, campo.value); fim(c.ok, campo.value, "texto"); };
          campo.addEventListener("keydown", e => { if (e.key === "Enter") conferir(); });
          corpo = h("div", { class: "linha linha-texto" }, campo, h("button", { type: "button", class: "botao", id: "conferir-defesa", onclick: conferir }, "Bloquear"), ouvirBtn);
          setTimeout(() => campo.focus({ preventScroll: true }), 0);
        } else {
          corpo = h("div", {}, h("div", { class: "opcoes", role: "group", "aria-label": "Opções de defesa" },
            opcoesDefesa(item).map((o, k) => h("button", { type: "button", class: "opcao", lang: "fr", "data-fr": o, onclick: () => fim(o === item.fr, o, "opcoes") }, h("b", { text: "ABC"[k] + ")" }), o))),
            h("div", { class: "linha", style: "margin-top:calc(var(--u)*2)" }, ouvirBtn));
        }
        const outros = [["voz", "Usar o microfone"], ["texto", "Escrever"], ["opcoes", "Escolher entre 3"]]
          .filter(([m]) => m !== modo && (m !== "voz" || (Voz && Voz.disponivel)))
          .map(([m, t]) => h("button", { type: "button", "data-modo": m, onclick: () => { if (!feito) render(m); } }, t));
        const relogio = T.total ? h("div", { class: "timer-defesa", id: "timer-defesa", role: "timer", "aria-label": "Tempo para bloquear (segundos)",
          "aria-valuemin": "0", "aria-valuemax": String(TEMPO_DEF) }, h("i", { "aria-hidden": "true" }), h("b", {})) : null;
        conteudo.replaceChildren(banner, relogio, alvo, dica, corpo, status, h("p", { class: "trocar" }, modo === "voz" ? "Sem microfone? " : "Ou: ", outros));
        if (reiniciar) { pararT(); T.resta = T.total; T.esgotou = false; }
        if (opts.congelar != null) { T.resta = opts.congelar * 1000; desenharT(); return; }
        desenharT();
        /* o timer começa quando o aviso aparece e o áudio da palavra termina; trocar de modo não zera o tempo */
        if (!T.ativo) palavra(item).then(() => { if (!feito) iniciarT(); });
        else if (modo !== "voz") palavra(item);
      };
      render(modoForcado || modoDefesa || (Voz && Voz.disponivel ? "voz" : "opcoes"));
    });
  }
  async function turnoInimigo() {
    const item = proximaDefesa();
    quadro(inimigo, QI.prep); som("preparo");
    const r = await defender(item);
    conteudo.querySelectorAll("button, input").forEach(b => { b.disabled = true; });
    conteudo.querySelectorAll('.opcao').forEach(b => { if (b.dataset.fr === item.fr) b.classList.add("certa"); else if (b.dataset.fr === r.ouvido) b.classList.add("errada"); });
    $("alvo-defesa").textContent = `« ${item.fr} »`; $("alvo-defesa").classList.remove("oculto");
    const st = $("retorno-defesa");
    if (r.ok) { st.className = "retorno bloq"; st.textContent = `Bloqué ! Nenhum dano.`; await bloqueio(); }
    else {
      st.className = "retorno erro";
      st.textContent = r.modo === "tempo" ? `Temps écoulé ! ${D.ataques_inimigo[idInimigo].fr} Era « ${item.fr} ».`
        : `${D.ataques_inimigo[idInimigo].fr} Era « ${item.fr} »${r.ouvido && r.modo !== "opcoes" ? ` — entendi « ${r.ouvido} »` : ""}.`;
      await golpeNoHeroi(D.regras.dano_defesa);
    }
    await palavra(item);
    await espera(450);
    caixaPergunta.classList.remove("defesa");
  }
  async function bloqueio() {
    quadro(inimigo, QI.golpe); inimigo.classList.add("ataca"); await espera(120);
    tocar(sfx, CFG.estatico + "batalha/som-bloqueio.wav");
    quadro(heroi, QH.ataque[0]);   /* aparar */
    bloqueado.hidden = false; bloqueado.style.animation = "none"; void bloqueado.offsetWidth; bloqueado.style.animation = "";
    const ef = efeitoEm(efeitoBloq, "escudo");
    await espera(160); inimigo.classList.remove("ataca"); ocioso(inimigo);
    await ef; await fala("bloque");
    ocioso(heroi); bloqueado.hidden = true;
  }
  function final(tipo, titulo, pt, sub, previa) {
    E.fim = true;
    document.body.classList.add(tipo);
    msg.className = "mensagem " + tipo; msg.hidden = false;
    $("msg-titulo").textContent = titulo; $("msg-pt").textContent = pt; $("msg-sub").textContent = sub;
    if (!previa) $("voltar-mapa").focus({ preventScroll: true });
  }
  async function vitoria(previa) {
    E.fim = true;
    if (!previa) som("vitoria");
    if (!reduz && !previa) await anima(inimigo, QI.queda, 260); else quadro(inimigo, QI.queda[QI.queda.length - 1]);
    quadro(inimigo, QI.queda[QI.queda.length - 1]);   /* fica no chão */
    if (!previa) fala(D.mensagens.vitoria.audio);
    if (!reduz && !previa) for (let k = 0; k < 3; k++) await anima(heroi, QH.festa, 150);
    quadro(heroi, previa || reduz ? QH.festa[1] : QH.festa[0]);
    const M = D.mensagens.vitoria;
    const nEst = estrelasBatalha(E.golpes);
    final("vitoria", M.fr, M.pt, `Étape ${CFG.n} concluída · ${"★".repeat(nEst)}${"☆".repeat(3 - nEst)} · ${INI.nome} foi derrotado(a). ${M.sub ? M.sub + " " : ""}${previa ? "Prévia: nada foi salvo." : "Salvando…"}`, previa);
    $("voltar-mapa").href = CFG.mapa_vitoria;
    if (!previa) {
      E.salvo = salvarVitoria(nEst).then(ok => {
        const sub = $("msg-sub");
        sub.textContent = sub.textContent.replace("Salvando…", CFG.teste ? "Modo teste: progresso separado." : ok ? "Progresso salvo." : "Progresso salvo neste aparelho.");
        return ok;
      });
    }
    voltarDepois(previa, CFG.mapa_vitoria);
  }
  function estrelasBatalha(erros) {
    for (const f of (CFG.recompensa && CFG.recompensa.estrelas) || []) if (erros >= f.min_erros && erros <= f.max_erros) return f.estrelas;
    return 1;
  }
  /* mesma persistência das outras paradas: localStorage do prefixo (libera a próxima) + POST na rota de conclusão
     (servidor: Cosmos para usuário real, memória para o usuário de teste). XP pausado: a parada 9 vale 0 XP. */
  function salvarVitoria(nEst) {
    const reg = { concluida_em: new Date().toISOString(), acertos: E.acertos + E.defesas.filter(x => x.ok).length, erros: E.golpes,
      fala_pendente: E.defesas.length > 0 && !E.defesas.some(x => x.modo === "voz"), duracao_s: Math.min(86400, Math.round((Date.now() - E.inicio) / 1000)),
      estrelas: nEst, xp: 0, formato: "batalha" };
    try {
      const PRE = CFG.prefixo || "chemin_", chaveMapa = `${PRE}mapa_r${CFG.regiao}_atual`;
      localStorage.setItem(chaveMapa, String(Math.max(Number(localStorage.getItem(chaveMapa)) || 1, CFG.n + 1)));
      const todas = JSON.parse(localStorage.getItem(PRE + "paradas") || "{}");
      todas[CFG.pid] = reg; localStorage.setItem(PRE + "paradas", JSON.stringify(todas));
    } catch (e) { /* armazenamento indisponível */ }
    return fetch(CFG.concluir, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin",
      body: JSON.stringify({ acertos: reg.acertos, erros: reg.erros, fala_pendente: reg.fala_pendente, duracao_s: reg.duracao_s }) })
      .then(r => r.ok).catch(() => false);
  }
  async function derrota(previa) {
    E.fim = true;
    if (!previa) som("derrota");
    if (!reduz && !previa) await anima(heroi, QH.queda, 300);
    quadro(heroi, QH.queda[QH.queda.length - 1]);
    escuro.classList.add("on");
    await espera(previa ? 0 : 700);
    if (!previa) fala(D.mensagens.derrota.audio);
    const M = D.mensagens.derrota;
    final("derrota", M.fr, M.pt, M.sub || "Você volta ao mesmo ponto do mapa. Nada desta etapa foi salvo; tente de novo quando quiser.", previa);
    voltarDepois(previa);
  }
  function voltarDepois(previa, destino = CFG.mapa) {
    if (previa) return;
    let s = 10; const sub = $("msg-sub");
    const t = setInterval(() => { s--; sub.textContent = sub.textContent.replace(/ Voltando ao mapa em \d+ s…$/, "") + ` Voltando ao mapa em ${s} s…`; if (s <= 0) { clearInterval(t); location.href = destino; } }, 1000);
    $("voltar-mapa").addEventListener("click", () => clearInterval(t));
  }

  /* ---------- início ---------- */
  window.chemin_batalha = { estado: E, dados: D, inimigo: idInimigo };
  barra("barra-heroi", E.vidaH); barra("barra-inimigo", E.vidaI);
  ocioso(heroi); ocioso(inimigo); mostrarCombo();
  if (reduz) { heroi.classList.remove("idle"); inimigo.classList.remove("idle"); }
  if (CFG.tela === "vitoria") {
    E.vidaI = 0; E.combo = 3; barra("barra-inimigo", 0); mostrarCombo(); vitoria(true); return;
  }
  if (CFG.tela === "derrota") {
    E.vidaH = 0; barra("barra-heroi", 0); barra("barra-inimigo", 2); derrota(true); return;
  }
  const params = new URLSearchParams(location.search);
  if (params.get("demo") === "especial") {   /* prévia: um quadro parado do Spécial da classe (?quadro=0..9) */
    montarFila(); mostrarPergunta(); E.combo = 3; mostrarCombo(); E.ocupado = true;
    const f = Math.min(9, Math.max(0, Number(params.get("quadro") ?? IMPACTO + 2)));
    E.vidaI = Math.max(0, E.vidaI - (f >= IMPACTO ? D.regras.dano.special : 0)); barra("barra-inimigo", E.vidaI);
    heroi.classList.remove("idle"); quadro(heroi, QH.ataque[1]);
    if (f >= IMPACTO && f <= IMPACTO + 1) { quadro(inimigo, QI.dor[0]); inimigo.classList.add("branco"); }
    else if (f > IMPACTO + 1 && f <= IMPACTO + 3) quadro(inimigo, QI.dor[0]);
    camada.hidden = false; camada.style.setProperty("--f", f); mostrarFaixa(); faixa.style.animation = "none";
    if (f >= IMPACTO) { numero.hidden = false; numero.textContent = "-" + D.regras.dano.special; numero.style.animation = "none"; }
    return;
  }
  if (params.get("demo") === "defesa" || params.get("demo") === "bloqueio") {   /* prévias da defesa (?modo=voz|texto|opcoes) */
    E.ocupado = true; heroi.classList.remove("idle"); quadro(heroi, 0);
    const v = (params.get("vidas") || "").split(",").map(Number);
    if (v.length === 2 && v[0] >= 1 && v[0] <= D.regras.vida_heroi && v[1] >= 1 && v[1] <= D.regras.vida_inimigo) { E.vidaH = v[0]; E.vidaI = v[1]; barra("barra-heroi", E.vidaH); barra("barra-inimigo", E.vidaI); }
    if (params.get("combo")) { E.combo = Number(params.get("combo")) || 0; mostrarCombo(); }
    const item = D.defesa.find(x => x.fr === params.get("palavra")) || D.defesa.find(x => x.fr === "sept");
    quadro(inimigo, QI.prep);
    defender(item, params.get("modo") || "voz", { congelar: params.get("restante") != null ? Number(params.get("restante")) : TEMPO_DEF });
    if (params.get("demo") === "bloqueio") {
      conteudo.querySelectorAll("button, input").forEach(b => { b.disabled = true; });
      const st = $("retorno-defesa"); st.className = "retorno bloq"; st.textContent = "Bloqué ! Nenhum dano.";
      quadro(inimigo, QI.golpe); inimigo.classList.add("ataca"); quadro(heroi, QH.ataque[0]);
      efeitoBloq.className = "efeito escudo"; efeitoBloq.hidden = false; efeitoBloq.style.setProperty("--f", 2);
      bloqueado.hidden = false; bloqueado.style.animation = "none";
    }
    return;
  }
  if (params.get("demo") === "pergunta") {
    montarFila(); mostrarPergunta(); if (params.get("combo")) { E.combo = Number(params.get("combo")) || 0; mostrarCombo(); }
    if (params.get("apos") === "especial") {   /* prévia: logo depois de um Spécial — combo zerado, aviso no retorno */
      E.combo = 0; mostrarCombo(); comboZerado();
      $("retorno").textContent = `${ESP.nome} ! Combo zerado: o próximo acerto volta a ser Léger.`;
    }
    const v = (params.get("vidas") || "").split(",").map(Number);   /* prévia: ?vidas=heroi,inimigo */
    if (v.length === 2 && v[0] >= 1 && v[0] <= D.regras.vida_heroi && v[1] >= 1 && v[1] <= D.regras.vida_inimigo) { E.vidaH = v[0]; E.vidaI = v[1]; barra("barra-heroi", E.vidaH); barra("barra-inimigo", E.vidaI); }
    return;
  }
  conteudo.replaceChildren(
    h("p", { class: "enunciado", lang: "fr", text: `${INI.nome} bloque le chemin !` }),
    h("p", { class: "dica", text: `${INI.pt} quer lutar. Acertos seguidos viram combo: Léger (−1) → Fort (−2) → Spécial (−3, ${ESP.pt}!). Cada erro custa 1 barra; ${D.regras.vida_heroi} erros e você recua.${D.regras.vida_inimigo > 5 ? ` Chefe: ${D.regras.vida_inimigo} barras.` : ""}` }),
    h("div", { class: "linha" }, h("button", { type: "button", class: "botao", id: "comecar", onclick: () => { E.inicio = Date.now(); fala(INI.intro); montarFila(); mostrarPergunta(); } }, "Commencer !"),
      h("a", { class: "botao sec", href: CFG.mapa }, "Agora não")));
  $("comecar").focus({ preventScroll: true });
})();
