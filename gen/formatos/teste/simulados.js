const assert=require("assert"),fs=require("fs");
const {JSDOM,VirtualConsole}=require("jsdom");
const root=process.argv[3],cfg=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const engine=require(root+"/static/simulados/prova.js");
let checks=0;function chk(v,m){assert.ok(v,m);checks++;}
chk(engine.restantes(2000,1001)===1,"ceil restante");chk(engine.restantes(1000,2000)===0,"zero sem negativo");
chk(engine.nivelAviso(299)==="low"&&engine.nivelAviso(59)==="urgent","avisos 5 e 1 minuto");
let now=0,exp=0;const timer=new engine.Cronometro(1000,()=>now,()=>{},()=>exp++);timer.tick();now=1000;timer.tick();timer.tick();chk(exp===1,"auto-submit unico em zero");
chk(engine.livre("ce")&&!engine.livre("co"),"regras navegacao");
let draft={played:{}};chk(engine.marcarAudio(draft,"co01")&&!engine.marcarAudio(draft,"co01"),"audio nao repete");
chk(engine.falaNPC("Quel est le prix?","eoa",[]).includes("85"),"NPC responde por intencao");
chk(engine.falaNPC("Venez avec moi","eob",[{papel:"candidato"}]).includes("mardi"),"NPC levanta objecao");
const html=`<header id="chrono"><b id="etapa-titulo"></b><small id="timer-aviso"></small><time id="tempo"></time><small id="tempo-secao"></small></header><p id="status"></p><h1 id="titulo"></h1><p id="instrucao"></p><div id="conteudo"></div><div id="navegacao"></div><button id="entregar"></button><script id="sim-config" type="application/json">CONFIG</script>`;
function pagina(c,stored={}) {
 const requests=[],audios=[],intervals=[],recs=[];let now=c.server_now;
 const vc=new VirtualConsole();vc.on("jsdomError",e=>{if(!/navigation/.test(e.message))throw e;});
 const dom=new JSDOM(html.replace("CONFIG",JSON.stringify(c)),{url:"http://localhost:5077/simulados/tef/prova",runScripts:"outside-only",virtualConsole:vc});
 const w=dom.window;w.SIM_BASE="/simulados/"+c.examen;w.Date.now=()=>now;w.confirm=()=>true;
 w.setInterval=f=>{intervals.push(f);return intervals.length;};w.clearInterval=()=>{};w.setTimeout=()=>1;w.clearTimeout=()=>{};
 Object.entries(stored).forEach(([k,v])=>w.localStorage.setItem(k,v));
 w.ChemVoz={disponivel:true,lingua:"fr-CA"};
 w.SpeechRecognition=class{constructor(){recs.push(this);}start(){this.iniciou=true;}stop(){if(this.onend)this.onend();}abort(){}};
 w.Audio=class{constructor(){audios.push(this);this.plays=0;}play(){this.plays++;return Promise.resolve();}pause(){this.paused=true;}};
 w.fetch=async(url,o)=>{requests.push({url,body:JSON.parse(o.body)});return{ok:true,json:async()=>({concluido:true,url:"/simulados/resultados/fake"})};};
 w.eval(fs.readFileSync(root+"/static/simulados/prova.js","utf8"));
 return {dom,w,d:w.document,requests,audios,intervals,recs,setNow:v=>{now=v;}};
}
(async()=>{
 let p=pagina(cfg);let b=p.d.getElementById("audio-unico");
 chk(!b.disabled,"primeiro play liberado");chk(p.d.getElementById("proxima").disabled,"nao avanca antes da escuta");
 b.click();b.click();chk(p.audios.length===1&&p.audios[0].plays===1&&b.disabled,"play inicia uma vez e desativa");
 const armazenado={};for(let i=0;i<p.w.localStorage.length;i++){let k=p.w.localStorage.key(i);armazenado[k]=p.w.localStorage.getItem(k);}
 p.audios[0].onended();chk(!p.d.getElementById("proxima").disabled,"avanca depois de audio");
 chk(![...p.d.querySelectorAll("button")].some(b=>b.textContent==="Anterior"),"CO sem voltar");
 p.d.getElementById("proxima").click();chk(p.d.getElementById("conteudo").textContent.includes("Questão 2"),"CO avanca sequencialmente");
 const recarga=pagina({...cfg,server_now:cfg.server_now+11000},armazenado);
 chk(recarga.d.getElementById("audio-unico").disabled&&recarga.audios.length===0,"recarregar nao libera replay");
 chk(recarga.d.getElementById("tempo").textContent===engine.formato(engine.restantes(cfg.deadline,cfg.server_now+11000)),"recarregar usa deadline persistido");recarga.dom.window.close();
 p.setNow(cfg.deadline);p.intervals[0]();p.intervals[0]();await new Promise(r=>setImmediate(r));
 chk(p.requests.length===1&&p.requests[0].url.endsWith("/entregar"),"tempo zero autoenvia uma vez");chk(p.d.getElementById("tempo").textContent==="00:00","tempo permanece visivel em zero");chk([...p.d.querySelectorAll("#conteudo input")].every(x=>x.disabled)&&p.audios[0].paused,"zero bloqueia respostas e encerra audio");p.dom.window.close();
 const tcf={...cfg,examen:"tcf"};p=pagina(tcf);const pergunta=cfg.itens[0].question;
 chk(!p.d.getElementById("conteudo").textContent.includes(pergunta),"TCF pergunta oculta antes do audio");p.d.getElementById("audio-unico").click();p.audios[0].onended();chk(p.d.getElementById("conteudo").textContent.includes(pergunta),"TCF pergunta apos audio");p.dom.window.close();
 const ce={...cfg,etapa:{...cfg.etapa,id:"ce"},itens:cfg.itens.map(x=>({...x,texte:"Document original de lecture."}))};p=pagina(ce);chk(p.d.querySelectorAll(".numeros button").length===40,"CE todos numeros navegaveis");p.d.querySelectorAll(".numeros button")[20].click();chk(p.d.getElementById("conteudo").textContent.includes("Questão 21"),"CE navega livre");p.dom.window.close();
 const eo={...cfg,itens:undefined,deadline:cfg.server_now+300000,indice:0,plano:[{id:"eoa",segundos:300},{id:"eob",segundos:600}],etapa:{id:"eoa",titulo:"EO A",segundos:300},oral:{consigne:"Posez des questions",document:"Atelier photo: 85 dollars.",ouverture:"Bonjour",preparacao:false}};
 p=pagina(eo);chk(p.d.getElementById("tempo").textContent==="05:00"&&p.d.getElementById("tempo-secao").textContent.includes("15:00"),"timer da parte e total da competencia aparecem juntos");let micro=[...p.d.querySelectorAll("button")].find(b=>b.textContent.includes("Falar /"));micro.click();
 chk(p.recs[0].continuous===true&&p.recs[0].lang==="fr-CA","reconhecimento continuo reutiliza idioma da infraestrutura");
 p.recs[0].onresult({resultIndex:0,results:[{0:{transcript:"Combien coûte cet atelier?"},isFinal:true,length:1}]});micro.click();
 chk(p.d.querySelector(".transcript").textContent.includes("Combien")&&p.d.querySelector(".transcript").textContent.includes("85"),"voz gera transcript e resposta NPC");
 chk(p.d.getElementById("tempo").textContent!=="--:--","cronometro visivel durante oral");p.dom.window.close();
 const prep={...eo,etapa:{id:"prep",titulo:"Preparacao",segundos:120},oral:{...eo.oral,preparacao:true}};p=pagina(prep);chk(p.d.getElementById("entregar").disabled&&!p.d.querySelector(".npc button"),"preparacao possui tempo proprio sem encerrar cedo");p.dom.window.close();
 const css=fs.readFileSync(root+"/static/simulados/simulados.css","utf8");chk(/\.chrono\{[^}]*position:fixed/.test(css)&&css.includes("@media(max-width:700px)"),"timer fixo e CSS mobile (nao validacao visual)");
 console.log(`${checks} verificacoes JS OK`);
})().catch(e=>{console.error(e);process.exitCode=1;});
