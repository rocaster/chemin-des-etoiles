/* Motor exclusivo de simulados; nao modifica static/parada/motor.js. */
(function(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.SimExam = api; if (root.document) api.boot(root); }
})(typeof window === "undefined" ? globalThis : window, function() {
  "use strict";
  const restantes = (deadline, agora) => Math.max(0, Math.ceil((deadline - agora) / 1000));
  const formato = s => `${String(Math.floor(s / 60)).padStart(2,"0")}:${String(s % 60).padStart(2,"0")}`;
  const nivelAviso = s => s <= 60 ? "urgent" : s <= 300 ? "low" : "normal";
  const livre = secao => secao === "ce";
  const palavras = t => (String(t).match(/[\p{L}\p{N}'’-]+/gu) || []).length;
  function marcarAudio(draft,id) { if (draft.played[id]) return false; draft.played[id] = true; return true; }
  class Cronometro {
    constructor(deadline, agora, pintar, expirar) { Object.assign(this,{deadline,agora,pintar,expirar,feito:false}); }
    tick() { const s = restantes(this.deadline,this.agora()); this.pintar(s,nivelAviso(s)); if (!s && !this.feito) { this.feito = true; this.expirar(); } return s; }
  }
  function falaNPC(texto, etapa, transcript) {
    const t = texto.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
    if (etapa === "eob") {
      const obj = ["Mais 85 dollars, cela me paraît cher. Comment justifiez-vous cette dépense?", "Le mardi soir, je suis souvent fatigué. Pourquoi faire cet effort?", "Je ne connais personne dans ce groupe. Qu'est-ce que cela peut m'apporter?", "Je pourrais apprendre gratuitement sur Internet. Pourquoi choisir cet atelier?"];
      return obj[transcript.filter(x => x.papel === "candidato").length % obj.length];
    }
    if (etapa === "eo1") return ["Quel type de travail ou d'études faites-vous?", "Que faites-vous habituellement pendant vos loisirs?", "Parlez-moi d'un projet qui vous tient à cœur.", "Qu'appréciez-vous dans votre quartier?"][transcript.filter(x=>x.papel==="candidato").length%4];
    if (etapa === "eo3") return transcript.filter(x=>x.papel==="candidato").length%3 === 0 ? "Pouvez-vous donner un exemple concret et envisager un point de vue différent?" : "Je vous écoute. Développez votre argument.";
    if (/prix|cout|combien|tarif/.test(t)) return "Le tarif total est de 85 dollars pour les six rencontres. Le matériel est prêté.";
    if (/heure|quand|horaire|jour|duree/.test(t)) return "Les rencontres ont lieu le mardi à 18 heures 30, pendant six semaines. La sortie finale se déroule le dernier samedi.";
    if (/lieu|adresse|ou |metro|transport/.test(t)) return "Nous nous retrouvons à la bibliothèque Rosemont, à Montréal. Une station de métro est accessible à pied.";
    if (/inscri|reser|place|payer/.test(t)) return "Vous pouvez vous inscrire à l'accueil de la bibliothèque ou sur notre site. Le paiement confirme la place.";
    if (/materiel|appareil|debut|niveau/.test(t)) return "Aucune expérience n'est nécessaire. Nous prêtons le matériel; vous pouvez aussi apporter votre appareil.";
    return "Pour cet atelier, je peux vous renseigner sur le tarif, les horaires, le lieu, le matériel ou l'inscription. Quelle précision souhaitez-vous?";
  }
  function boot(w) {
    const d=w.document, base=w.SIM_BASE, status=d.getElementById("status");
    const h=(tag,txt,attrs={})=>{const e=d.createElement(tag);if(tag==="button")e.className="botao";if(txt!=null)e.textContent=txt;for(const [k,v]of Object.entries(attrs)){if(k.startsWith("on"))e.addEventListener(k.slice(2),v);else e.setAttribute(k,k==="class"&&tag==="button"?"botao "+v:v);}return e;};
    async function post(path,body) { const r=await w.fetch(base+path,{method:"POST",headers:{"Content-Type":"application/json"},credentials:"same-origin",body:JSON.stringify(body)}); if(!r.ok) throw new Error("Não foi possível salvar (HTTP "+r.status+"). Seu rascunho continua neste navegador. Entre novamente se a sessão expirou."); return r.json(); }
    d.querySelectorAll("[data-iniciar]").forEach(b=>b.addEventListener("click",async()=>{b.disabled=true;try{const r=await post("/iniciar",{secao:b.dataset.iniciar,novo:!!w.SIM_ATIVA&&w.confirm("Descartar a tentativa ativa e iniciar a seção escolhida? Cancelar retoma a tentativa atual.")});w.location.assign(r.url);}catch(e){status.textContent=e.message;b.disabled=false;}}));
    const nova=d.getElementById("nova");if(nova)nova.onclick=async()=>{if(w.confirm("Descartar a tentativa ativa e iniciar uma prova completa nova?")){try{const r=await post("/iniciar",{secao:"completo",novo:true});w.location.assign(r.url);}catch(e){status.textContent=e.message;}}};
    const node=d.getElementById("sim-config");if(!node)return;
    let cfg=JSON.parse(node.textContent),draft,key,clock,interval,busy=false,currentAudio=null,autoAudio=null,offset=0,rec=null,gravando=false;
    const box=d.getElementById("conteudo"),nav=d.getElementById("navegacao"),submit=d.getElementById("entregar");
    function persistir(){try{w.localStorage.setItem(key,JSON.stringify(draft));}catch(e){status.textContent="Armazenamento local indisponível: mantenha esta página aberta; o cronômetro continua no servidor.";}}
    function carregar(c) {
      if(rec){rec.onend=null;rec.onresult=null;try{rec.abort();}catch(e){}rec=null;gravando=false;}
      if(interval)w.clearInterval(interval);if(autoAudio)w.clearTimeout(autoAudio);
      if(currentAudio){currentAudio.pause();currentAudio=null;}if(w.speechSynthesis)w.speechSynthesis.cancel();
      cfg=c;offset=cfg.server_now-Date.now();key="chemin_sim_"+cfg.id+"_"+cfg.indice;
      draft={pos:0,respostas:{},played:{},finished:{},textos:{},transcript:[],checklist:[]};
      try{const old=JSON.parse(w.localStorage.getItem(key)||"null");if(old)Object.assign(draft,old);}catch(e){}
      // Depois de recarregar, uma escuta interrompida nunca e repetida.
      Object.keys(draft.played).forEach(id=>draft.finished[id]=true);
      d.getElementById("etapa-titulo").textContent=cfg.examen.toUpperCase()+" Canada · "+cfg.etapa.titulo;
      d.getElementById("titulo").textContent=cfg.etapa.titulo;submit.disabled=cfg.etapa.id==="prep";
      const competencia=id=>id==="prep"?"eo":id.startsWith("ee")?"ee":id.startsWith("eo")?"eo":id;
      let acrescimo=0;for(const proxima of cfg.plano.slice(cfg.indice+1)){if(competencia(proxima.id)!==competencia(cfg.etapa.id))break;acrescimo+=proxima.segundos*1000;}
      render();clock=new Cronometro(cfg.deadline,()=>Date.now()+offset,(s,alerta)=>{d.getElementById("tempo").textContent=formato(s);const sec=d.getElementById("tempo-secao");if(sec)sec.textContent="Seção "+competencia(cfg.etapa.id).toUpperCase()+" · "+formato(restantes(cfg.deadline+acrescimo,Date.now()+offset));d.getElementById("chrono").className="chrono "+alerta;d.getElementById("timer-aviso").textContent=!s?"Tempo esgotado — enviando automaticamente":s<=60?"Último minuto desta parte":s<=300?"Até 5 min nesta parte":"Tempo contínuo; recarregar não reinicia";},()=>{box.querySelectorAll("input,textarea,button,select").forEach(el=>el.disabled=true);nav.querySelectorAll("button").forEach(el=>el.disabled=true);entregar(true);});
      interval=w.setInterval(()=>clock.tick(),500);clock.tick();
    }
    function render(){box.replaceChildren();nav.replaceChildren();const sid=cfg.etapa.id;
      d.getElementById("instrucao").textContent=sid==="co"?"Uma única escuta por item, sem retorno. Não há desconto por erro.":sid==="ce"?"Quatro alternativas; uma correta. Navegação livre nesta seção.":"O cronômetro não pausa durante a atividade.";
      if(cfg.itens)questao();else if(cfg.tarefas)escrita();else oral();
    }
    function questao(){
      const sid=cfg.etapa.id;draft.pos=Math.max(0,Math.min(cfg.itens.length-1,draft.pos||0));const x=cfg.itens[draft.pos];
      box.append(h("p",`Questão ${draft.pos+1} / ${cfg.itens.length} · ${x.niveau} (dificuldade editorial)`));
      if(sid==="ce")box.append(h("div",x.texte,{class:"doc",lang:"fr"}));
      const pergunta=h("div"),podeMostrar=sid!=="co"||cfg.examen!=="tcf"||draft.finished[x.id];
      if(podeMostrar){pergunta.append(h("h2",x.question,{lang:"fr"}));const op=h("div",null,{class:"escolhas"});x.choix.forEach((txt,i)=>{const label=h("label");const input=h("input",null,{type:"radio",name:"resposta",value:i});input.checked=draft.respostas[x.id]===i;input.onchange=()=>{draft.respostas[x.id]=i;persistir();};label.append(input,h("span",String.fromCharCode(65+i)+" · "+txt,{lang:"fr"}));op.append(label);});pergunta.append(op);}
      else pergunta.append(h("p","TCF: a pergunta aparece após a gravação (também lida no áudio)."));
      if(sid==="co"){
        const b=h("button",draft.played[x.id]?"Áudio já consumido":"Écouter une seule fois",{id:"audio-unico",type:"button"});b.disabled=!!draft.played[x.id];
        const st=h("p",draft.played[x.id]&&!draft.finished[x.id]?"Écoute en cours…":"",{id:"audio-status",role:"status"});
        const stageKey=key;
        b.onclick=()=>{
          if(!marcarAudio(draft,x.id))return;b.disabled=true;persistir();currentAudio=new w.Audio("/static/"+x.audio+"?v=1");st.textContent="Écoute en cours…";
          currentAudio.onended=()=>{if(key!==stageKey)return;draft.finished[x.id]=true;persistir();render();};
          currentAudio.onerror=()=>{if(key!==stageKey)return;draft.finished[x.id]=true;persistir();status.textContent="Falha técnica de áudio. Item consumido; registre o problema no treino.";render();};
          const promessa=currentAudio.play();if(promessa&&promessa.catch)promessa.catch(e=>{if(key!==stageKey)return;if(e.name==="NotAllowedError"){delete draft.played[x.id];persistir();b.disabled=false;st.textContent="O navegador bloqueou o início. Clique para autorizar a primeira escuta.";}else{draft.finished[x.id]=true;persistir();status.textContent="Áudio indisponível; sem replay. Anote esta falha técnica.";render();}});
        };box.append(b,st);
        if(autoAudio)w.clearTimeout(autoAudio);
        if(cfg.examen==="tef"&&!draft.played[x.id])autoAudio=w.setTimeout(()=>b.click(),5000);
      }
      box.append(pergunta);
      if(livre(sid)){
        const numeros=h("div",null,{class:"numeros",role:"navigation","aria-label":"Questões de leitura"});cfg.itens.forEach((q,i)=>{const b=h("button",String(i+1),{type:"button",class:(i===draft.pos?"atual ":"")+(draft.respostas[q.id]!=null?"respondida":"")});b.onclick=()=>{draft.pos=i;persistir();render();};numeros.append(b);});nav.append(numeros);
        const anterior=h("button","Anterior",{type:"button"});anterior.disabled=!draft.pos;anterior.onclick=()=>{draft.pos--;persistir();render();};nav.append(anterior);
      }
      const prox=h("button","Próxima",{type:"button",id:"proxima"});prox.disabled=draft.pos>=cfg.itens.length-1||(sid==="co"&&!draft.finished[x.id]);prox.onclick=()=>{draft.pos++;persistir();render();};nav.append(prox);
    }
    function escrita(){
      cfg.tarefas.forEach(t=>{const card=h("section",null,{class:"cartao"});card.append(h("h2",t.titre,{lang:"fr"}),h("p",t.consigne,{lang:"fr"}));t.documents.forEach(doc=>card.append(h("div",doc,{class:"doc",lang:"fr"})));
        const a=h("textarea",null,{class:"writing",lang:"fr",maxlength:6000,"aria-label":t.titre}),count=h("p",null,{class:"contagem"});a.value=draft.textos[t.id]||"";const contar=()=>{const n=palavras(a.value);count.textContent=`${n} palavras · mínimo ${t.min}`+(t.max?`, máximo ${t.max}`:"");count.classList.toggle("fora",n<t.min||!!t.max&&n>t.max);};a.oninput=()=>{draft.textos[t.id]=a.value;persistir();contar();};contar();card.append(a,count);box.append(card);});
      box.append(h("h2","Autoavaliação (não é correção)"));for(const texto of ["Atendi à consigne","Organizei o texto","Usei argumentos/exemplos","Revisei gramática e vocabulário"]){const l=h("label"),input=h("input",null,{type:"checkbox"});input.checked=draft.checklist.includes(texto);input.onchange=()=>{draft.checklist=Array.from(box.querySelectorAll("input:checked")).map(x=>x.dataset.check);persistir();};input.dataset.check=texto;l.append(input,d.createTextNode(" "+texto));box.append(l,h("br"));}
    }
    function oral(){
      const o=cfg.oral;box.append(h("img",null,{class:"npc",src:"/static/parada/r1-p07/npc.png",alt:"Maître Anselme, examinador de treino"}),h("p",o.consigne,{lang:"fr"}),h("div",o.document,{class:"doc",lang:"fr"}));
      if(o.preparacao){const notes=h("textarea",null,{class:"writing","aria-label":"Notas de preparação"});notes.value=draft.notes||"";notes.oninput=()=>{draft.notes=notes.value;persistir();};box.append(h("p","Preparação: o diálogo abre automaticamente ao terminar os 2 minutos."),notes);return;}
      if(!draft.transcript.length){draft.transcript.push({papel:"examinador",texto:o.ouverture,modo:"texto"});persistir();}
      const log=h("div",null,{class:"transcript","aria-live":"polite"});draft.transcript.forEach(t=>log.append(h("p",(t.papel==="candidato"?"Vous: ":"Examinateur: ")+t.texto,{lang:"fr"})));box.append(log);
      const texto=h("textarea",null,{class:"writing",maxlength:1500,"aria-label":"Intervenção do candidato em francês",placeholder:"Alternativa digitada (identificada como texto no resultado)."});texto.value=draft.rascunho_oral||"";texto.oninput=()=>{draft.rascunho_oral=texto.value;persistir();};
      const enviar=h("button","Enviar intervenção digitada",{type:"button"}),mic=h("button","Falar / gravar intervenção",{type:"button"}),ler=h("button","Ouvir examinador",{type:"button",class:"sec"});
      function responder(t,modo){if(!t.trim())return;draft.transcript.push({papel:"candidato",texto:t.slice(0,5000),modo});const resposta=falaNPC(t,cfg.etapa.id,draft.transcript);draft.transcript.push({papel:"examinador",texto:resposta,modo:"texto"});draft.rascunho_oral="";persistir();render();if(w.speechSynthesis){w.speechSynthesis.cancel();const u=new w.SpeechSynthesisUtterance(resposta);u.lang="fr-CA";w.speechSynthesis.speak(u);}}
      enviar.onclick=()=>responder(texto.value,"texto");
      mic.disabled=!(w.ChemVoz&&w.ChemVoz.disponivel);
      mic.onclick=()=>{
        if(rec&&gravando){gravando=false;mic.disabled=true;try{rec.stop();}catch(e){rec.onend();}return;}
        const SR=w.SpeechRecognition||w.webkitSpeechRecognition;if(!SR)return;
        const old=key;rec=new SR();rec.lang=w.ChemVoz.lingua||"fr-CA";rec.continuous=true;rec.interimResults=false;
        gravando=true;draft.rascunho_voz="";let segmentos=0;mic.textContent="Parar e enviar intervenção";
        status.textContent="Ouvindo continuamente. Fale em francês; pare para ouvir a resposta do examinador. O tempo não pausa.";
        rec.onresult=e=>{
          if(key!==old)return;
          for(let i=e.resultIndex;i<e.results.length;i++)if(e.results[i].isFinal){draft.rascunho_voz+=(draft.rascunho_voz?" ":"")+e.results[i][0].transcript;segmentos++;}
          persistir();status.textContent="Ouvindo… "+palavras(draft.rascunho_voz)+" palavras reconhecidas (rascunho salvo).";
          if(cfg.etapa.id==="eo3"&&segmentos>=3){gravando=false;mic.disabled=true;try{rec.stop();}catch(e){}}
        };
        rec.onend=()=>{
          if(key!==old||!rec)return;
          if(gravando&&Date.now()+offset<cfg.deadline){try{rec.start();return;}catch(e){gravando=false;}}
          const ouvido=draft.rascunho_voz||"";draft.rascunho_voz="";rec=null;gravando=false;mic.disabled=false;mic.textContent="Falar / gravar intervenção";persistir();
          if(ouvido.trim())responder(ouvido,"voz");else status.textContent="Nenhuma fala reconhecida. Tente novamente ou use a alternativa digitada.";
        };
        rec.onerror=e=>{const anterior=rec;rec=null;gravando=false;if(anterior){anterior.onend=null;anterior.onresult=null;try{anterior.abort();}catch(x){}}mic.disabled=false;mic.textContent="Falar / gravar intervenção";
          const parcial=draft.rascunho_voz||"";draft.rascunho_voz="";if(parcial.trim())responder(parcial,"voz");persistir();status.textContent="Reconhecimento indisponível ("+e.error+"). Use a alternativa digitada ou tente novamente.";};
        try{if(w.speechSynthesis)w.speechSynthesis.cancel();rec.start();}catch(e){gravando=false;rec=null;mic.disabled=false;status.textContent="Não foi possível abrir o microfone. Use a alternativa digitada.";}
      };
      ler.onclick=()=>{if(!w.speechSynthesis)return;w.speechSynthesis.cancel();const last=[...draft.transcript].reverse().find(t=>t.papel==="examinador");const u=new w.SpeechSynthesisUtterance(last.texto);u.lang="fr-CA";w.speechSynthesis.speak(u);};box.append(texto,h("p","Examinador roteirizado por palavras-chave: não é uma pessoa nem uma avaliação de pronúncia. Reconhecimento contínuo enquanto o navegador permitir; pare para enviar a intervenção. A contagem não mede sua proficiência."),mic,enviar,ler);
    }
    async function entregar(auto){
      if(busy)return;if(!auto&&!w.confirm("Encerrar esta seção/parte e enviar as respostas atuais?"))return;
      busy=true;submit.disabled=true;
      if(autoAudio)w.clearTimeout(autoAudio);if(currentAudio)currentAudio.pause();if(w.speechSynthesis)w.speechSynthesis.cancel();
      if(rec){rec.onend=null;rec.onresult=null;try{rec.abort();}catch(e){}rec=null;gravando=false;}
      if(draft.rascunho_voz&&draft.rascunho_voz.trim()){draft.transcript.push({papel:"candidato",texto:draft.rascunho_voz,modo:"voz"});draft.rascunho_voz="";}
      if(draft.rascunho_oral&&draft.rascunho_oral.trim()){draft.transcript.push({papel:"candidato",texto:draft.rascunho_oral,modo:"texto"});draft.rascunho_oral="";}
      persistir();
      try{const r=await post("/entregar",{tentativa:cfg.id,indice:cfg.indice,respostas:draft.respostas,textos:draft.textos,transcript:draft.transcript,checklist:draft.checklist});try{w.localStorage.removeItem(key);}catch(e){}busy=false;if(r.concluido){w.clearInterval(interval);w.location.assign(r.url);}else carregar(r.config);}
      catch(e){busy=false;submit.disabled=false;status.textContent=e.message;if(auto)w.setTimeout(()=>entregar(true),5000);}
    }
    submit.onclick=()=>entregar(false);carregar(cfg);
  }
  return {restantes,formato,nivelAviso,livre,palavras,marcarAudio,Cronometro,falaNPC,boot};
});
