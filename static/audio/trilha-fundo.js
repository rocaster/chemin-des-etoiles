// Trilha de fundo em loop. Uso: <script src=".../trilha-fundo.js" data-trilha="URL.ogg" data-volume="0.2"></script>
// Navegadores bloqueiam som automático: a música começa no primeiro clique, toque ou tecla na página.
(function () {
  var s = document.currentScript;
  var url = s.getAttribute('data-trilha');
  var vol = parseFloat(s.getAttribute('data-volume') || '0.2');
  var CHAVE = 'chemin-musica-mudo';
  var audio = new Audio(url);
  audio.loop = true; audio.volume = vol; audio.preload = 'auto';
  var mudo = localStorage.getItem(CHAVE) === '1';
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Ligar ou desligar a música');
  btn.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:9999;width:42px;height:42px;border-radius:50%;' +
    'border:2px solid #7a5a2e;background:#f3e3bf;font-size:20px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.35)';
  function desenha() { btn.textContent = mudo ? '🔇' : '🎵'; btn.title = mudo ? 'Ligar música' : 'Desligar música'; }
  function tocar() { if (mudo) return; try { var r = audio.play(); if (r && r.catch) r.catch(function (e) { console.warn('trilha: play bloqueado', e); }); } catch (e) { console.warn('trilha:', e); } }
  btn.addEventListener('click', function (ev) {
    ev.stopPropagation(); mudo = !mudo; localStorage.setItem(CHAVE, mudo ? '1' : '0'); desenha();
    if (mudo) audio.pause(); else tocar();
  });
  audio.addEventListener('error', function () { console.error('trilha: arquivo não encontrado ou inválido:', url); });
  function primeiro() { tocar(); ['pointerdown', 'keydown', 'touchstart'].forEach(function (t) { document.removeEventListener(t, primeiro, true); }); }
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (t) { document.addEventListener(t, primeiro, true); });
  document.addEventListener('DOMContentLoaded', function () { document.body.appendChild(btn); desenha(); });
  if (document.body) { document.body.appendChild(btn); desenha(); }

  // --- Abaixa a música enquanto o microfone escuta (reconhecimento de voz ou gravação) e volta depois ---
  var VOL_MIC = 0.03, abertos = 0, fadeT = null, voltaT = null, travaT = null;
  function fade(alvo, ms) {
    clearInterval(fadeT); var ini = audio.volume, t0 = Date.now();
    fadeT = setInterval(function () { var k = Math.min(1, (Date.now() - t0) / ms); audio.volume = ini + (alvo - ini) * k; if (k >= 1) clearInterval(fadeT); }, 30);
  }
  function micLigou() { abertos++; clearTimeout(voltaT); fade(VOL_MIC, 150);
    clearTimeout(travaT); travaT = setTimeout(function () { abertos = 0; fade(vol, 800); }, 20000); }  // trava de segurança
  function micDesligou() { abertos = Math.max(0, abertos - 1); if (abertos) return; clearTimeout(travaT);
    clearTimeout(voltaT); voltaT = setTimeout(function () { fade(vol, 800); }, 400); }
  function vigiar(Classe, eventoFim) {
    if (!Classe || !Classe.prototype || Classe.prototype.__trilha) return;
    var start = Classe.prototype.start; Classe.prototype.__trilha = true;
    Classe.prototype.start = function () {
      var self = this, fechou = false;
      function fim() { if (fechou) return; fechou = true; micDesligou(); }
      micLigou();
      eventoFim.forEach(function (ev) { self.addEventListener(ev, fim); });
      try { return start.apply(this, arguments); } catch (e) { fim(); throw e; }
    };
  }
  vigiar(window.SpeechRecognition || window.webkitSpeechRecognition, ['end', 'error']);
  vigiar(window.MediaRecorder, ['stop', 'error']);
  window.trilhaFundo = { audio: audio, micLigou: micLigou, micDesligou: micDesligou };
  tocar(); // funciona se o navegador já permitir som neste site
})();
