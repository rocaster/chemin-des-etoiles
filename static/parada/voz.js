/* Voz do jogador (reutilizável pelos templates de parada).
   - Web Speech API: SpeechRecognition / webkitSpeechRecognition, lang fr-CA (se o navegador recusar, tenta fr-FR).
   - Comparação tolerante: sem acentos/pontuação, números → palavras, Levenshtein + palavras encontradas.
   - Sem reconhecimento (Firefox, permissão negada, offline): escrever a resposta ou autoavaliação ("falei certo"). */
(() => {
  "use strict";
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const CHAVE_OFF = "chemin_voz_desligada";
  let lingua = "fr-CA";
  let desligada = false;
  try { desligada = sessionStorage.getItem(CHAVE_OFF) === "1"; } catch (e) { /* sem storage */ }

  const NUM = { 0: "zero", 1: "un", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 7: "sept", 8: "huit", 9: "neuf", 10: "dix", 20: "vingt" };
  function normaliza(s) {
    return String(s || "").toLowerCase().replace(/œ/g, "oe").replace(/æ/g, "ae")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/\$/g, " dollars ").replace(/\b(\d+)\b/g, (m, d) => NUM[d] || m)
      .replace(/[’'`´]/g, " ").replace(/[^a-z0-9 ]+/g, " ")
      .replace(/\b(euh|heu|hum|bah)\b/g, " ").replace(/\s+/g, " ").trim();
  }
  function lev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length; if (!m) return n; if (!n) return m;
    let prev = Array.from({ length: n + 1 }, (_, j) => j), cur = new Array(n + 1);
    for (let i = 1; i <= m; i++) {
      cur[0] = i;
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      [prev, cur] = [cur, prev];
    }
    return prev[n];
  }
  /* nota 0..1 de um texto ouvido contra um modelo: palavras de conteúdo encontradas (60%) + semelhança de letras (40%).
     Artigos e elisões (un, une, du, la, l', j'…) não contam: "pomme" vale "une pomme", mas "poire" não vale "pomme". */
  const VAZIAS = new Set(["un", "une", "du", "de", "des", "le", "la", "les", "l", "d", "j", "s", "qu", "a", "au", "et"]);
  const conteudo = s => s.split(" ").filter(w => w && !VAZIAS.has(w));
  function nota(ouvido, modelo) {
    const a = normaliza(ouvido), b = normaliza(modelo);
    if (!a || !b) return 0;
    let ca = conteudo(a), cb = conteudo(b);
    if (!cb.length) { ca = a.split(" "); cb = b.split(" "); }
    const achou = cb.filter(w => ca.some(x => x === w || (w.length >= 5 && lev(x, w) <= 1))).length / cb.length;
    const ja = ca.join(" "), jb = cb.join(" ");
    const r = 1 - lev(ja, jb) / Math.max(ja.length, jb.length, 1);
    const extra = Math.max(0, ca.length - cb.length - 2) * 0.08;   /* frase muito mais longa conta contra */
    return Math.max(0, 0.6 * achou + 0.4 * r - extra);
  }
  /* alvos: frases aceitas; chaves: trechos que bastam (ex.: "je m appelle" + qualquer nome) */
  function compara(ouvidos, alvos, chaves) {
    const lista = (Array.isArray(ouvidos) ? ouvidos : [ouvidos]).filter(Boolean);
    let melhor = { ok: false, nota: 0, ouvido: lista[0] || "" };
    for (const o of lista) {
      const n = " " + normaliza(o) + " ";
      if (chaves && chaves.length && chaves.every(c => n.includes(" " + normaliza(c) + " "))) return { ok: true, nota: 1, ouvido: o };
      for (const alvo of alvos) {
        const v = nota(o, alvo);
        if (v > melhor.nota) melhor = { ok: v >= 0.75, nota: v, ouvido: o };
      }
    }
    return melhor;
  }

  /* Uma escuta: resolve {alternativas:[...]} ou {erro:"..."} */
  function ouvir() {
    return new Promise(resolve => {
      if (!SR || desligada) { resolve({ erro: "indisponivel" }); return; }
      let feito = false;
      const rec = new SR();
      rec.lang = lingua; rec.interimResults = false; rec.maxAlternatives = 5; rec.continuous = false;
      const fim = r => { if (feito) return; feito = true; clearTimeout(t); try { rec.abort(); } catch (e) { /* já parou */ } resolve(r); };
      const t = setTimeout(() => fim({ erro: "no-speech" }), 9000);
      rec.onresult = e => {
        const res = e.results[0], alts = [];
        for (let i = 0; i < res.length; i++) alts.push(res[i].transcript);
        fim({ alternativas: alts });
      };
      rec.onerror = e => {
        if (e.error === "language-not-supported" && lingua === "fr-CA") { lingua = "fr-FR"; feito = true; clearTimeout(t); ouvir().then(resolve); return; }
        if (["not-allowed", "service-not-allowed", "audio-capture"].includes(e.error)) desligar();
        fim({ erro: e.error || "erro" });
      };
      rec.onend = () => fim({ erro: "no-speech" });
      try { rec.start(); } catch (e) { fim({ erro: "start" }); }
    });
  }
  function desligar() { desligada = true; try { sessionStorage.setItem(CHAVE_OFF, "1"); } catch (e) { /* sem storage */ } }
  const MSG = {
    "no-speech": "Não ouvi nada. Aperte o microfone e fale perto dele.",
    "not-allowed": "O microfone foi bloqueado. Você pode escrever ou se autoavaliar.",
    "service-not-allowed": "Este navegador não permite reconhecimento de voz aqui. Escreva ou se autoavalie.",
    "audio-capture": "Nenhum microfone encontrado. Escreva ou se autoavalie.",
    "network": "O reconhecimento de voz precisa de internet. Tente de novo ou escreva.",
    "aborted": "Escuta interrompida. Tente de novo."
  };

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

  /* Painel de resposta: microfone (se houver) + escrever + autoavaliação.
     opts: { alvos, chaves, modelo, ouvirModelo(), aoResultado({ok, ouvido, modo}), forcarTexto, dica } */
  function painel(opts) {
    const caixa = h("div", { class: "resposta-voz" });
    let respondido = false;
    const devolve = r => { if (respondido) return; respondido = true; opts.aoResultado(r); };
    function modoVoz(aviso) {
      const status = h("p", { class: "status-voz", role: "status", text: aviso || "" });
      const mic = h("button", { type: "button", class: "botao mic", id: "falar" }, h("i", { class: "icone-mic", "aria-hidden": "true" }), "Falar");
      mic.addEventListener("click", async () => {
        mic.disabled = true; caixa.classList.add("ouvindo"); status.textContent = "Ouvindo… fale agora.";
        const r = await ouvir();
        caixa.classList.remove("ouvindo"); mic.disabled = false;
        if (r.alternativas) { const c = compara(r.alternativas, opts.alvos, opts.chaves); devolve({ ok: c.ok, ouvido: c.ouvido, modo: "voz", nota: c.nota }); return; }
        const msg = MSG[r.erro] || "Não consegui ouvir. Tente de novo ou escreva.";
        if (desligada || r.erro === "indisponivel") modoTexto(msg); else status.textContent = msg;
      });
      caixa.replaceChildren(h("div", { class: "linha" }, mic,
        h("button", { type: "button", class: "botao sec", id: "prefiro-escrever", onclick: () => modoTexto("") }, "Prefiro escrever")), status);
    }
    function autoavaliar() {
      const ouvirM = opts.ouvirModelo ? h("button", { type: "button", class: "botao sec som", onclick: opts.ouvirModelo }, "Ouvir o modelo") : null;
      caixa.replaceChildren(h("p", { class: "instr", text: "Fale em voz alta, depois ouça o modelo e compare:" }),
        h("p", { class: "fala-modelo", lang: "fr", text: opts.modelo }),
        h("div", { class: "linha" }, ouvirM,
          h("button", { type: "button", class: "botao", id: "auto-certo", onclick: () => devolve({ ok: true, ouvido: "", modo: "auto" }) }, "Falei certo"),
          h("button", { type: "button", class: "botao sec", id: "auto-errado", onclick: () => devolve({ ok: false, ouvido: "", modo: "auto" }) }, "Preciso treinar")));
      if (opts.ouvirModelo) opts.ouvirModelo();
    }
    function modoTexto(aviso) {
      const campo = h("input", { class: "campo cheio", id: "resposta-texto", type: "text", lang: "fr", autocomplete: "off", autocapitalize: "off", spellcheck: "false",
        "aria-label": "Escreva o que você diria, em francês", placeholder: opts.dica || "Escreva em francês…" });
      const conferir = () => { if (!campo.value.trim()) { campo.focus(); return; } const c = compara(campo.value, opts.alvos, opts.chaves); devolve({ ok: c.ok, ouvido: campo.value, modo: "texto", nota: c.nota }); };
      campo.addEventListener("keydown", e => { if (e.key === "Enter") conferir(); });
      caixa.replaceChildren(...[
        aviso ? h("p", { class: "status-voz", role: "status", text: aviso }) : null,
        !SR ? h("p", { class: "sub", text: "Este navegador não reconhece voz (funciona no Chrome, Edge e Safari). Escreva, ou fale e se autoavalie." }) : null,
        h("div", { class: "linha linha-texto" }, campo, h("button", { type: "button", class: "botao", id: "conferir", onclick: conferir }, "Conferir")),
        h("div", { class: "linha", style: "margin-top:6px" },
          h("button", { type: "button", class: "botao sec", id: "autoavaliar", onclick: autoavaliar }, "Falei em voz alta"),
          SR && !desligada ? h("button", { type: "button", class: "botao sec", onclick: () => modoVoz("") }, "Usar o microfone") : null)
      ].filter(Boolean));
      setTimeout(() => campo.focus({ preventScroll: true }), 0);
    }
    if (SR && !desligada && !opts.forcarTexto) modoVoz(); else modoTexto("");
    return caixa;
  }

  window.ChemVoz = { get disponivel() { return !!SR && !desligada; }, get lingua() { return lingua; }, normaliza, nota, compara, ouvir, painel, desligar };
})();
