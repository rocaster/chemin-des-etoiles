// DOM real emitido por Flask + JS real. JSDOM nao faz layout nem screenshots.
const fs=require('fs'),path=require('path'),{JSDOM,VirtualConsole}=require('jsdom');
const fixtures=JSON.parse(fs.readFileSync(process.argv[2])),root=process.argv[3];
const js=fs.readFileSync(path.join(root,'static/simulados/prova.js'),'utf8'),css=fs.readFileSync(path.join(root,'static/simulados/simulados.css'),'utf8');
let count=0;function chk(msg,v){if(!v)throw Error(msg);count++;}
async function abrir(nome,op={}){
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!/navigation/i.test(e.message))errors.push(e.message)});
 const dom=new JSDOM(fixtures[nome],{url:'http://offline.invalid/simulados/tcf',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
 const w=dom.window,d=w.document,requests=[],audios=[];
 const style=d.createElement('style');style.textContent=css;d.head.append(style);
 w.scrollTo=()=>{};w.confirm=()=>false;
 w.fetch=async(u,o)=>{requests.push({u,body:JSON.parse(o.body)});return{ok:true,json:async()=>({concluido:true,url:'/resultado-fake'})}};
 w.Audio=class{constructor(src){this.src=src;audios.push(this)}play(){return Promise.resolve()}pause(){}};
 if(op.storage)for(const [k,v]of Object.entries(op.storage))w.localStorage.setItem(k,v);
 if(op.remaining!=null){const n=d.getElementById('sim-config'),c=JSON.parse(n.textContent);c.server_now=c.deadline-op.remaining*1000;n.textContent=JSON.stringify(c)}
 w.eval(js);
 if(d.readyState==='loading')await new Promise(r=>d.addEventListener('DOMContentLoaded',r,{once:true}));
 await Promise.resolve();return{dom,w,d,requests,audios,errors,close(){dom.window.close()}};
}
(async()=>{
 for(const ex of ['tef','tcf']){
  const t=await abrir(ex+'_inicio'),d=t.d;
  chk(ex+' cinco marcadores',d.querySelectorAll('.marcadores [data-iniciar]').length===5);
  chk(ex+' prova completa primaria habilitada',d.querySelector('.principal[data-iniciar="completo"]').disabled===false);
  chk(ex+' tempo total correto',d.querySelector('.principal .duracao').textContent===(ex==='tef'?'2h55':'2h47'));
  chk(ex+' competencias com tempos',Array.from(d.querySelectorAll('.marcador:not(.principal) .duracao')).every(e=>/\d+ min/.test(e.textContent)));
  chk(ex+' voltar e rolo acessivel',!!d.querySelector('a[aria-label="Voltar ao mapa"] svg image[href*="missao/rolo.png"]'));
  chk(ex+' placa nao barra',!!d.querySelector('header.placa-exame')&&!d.querySelector('header.chrono'));
  chk(ex+' aviso no rodape',!!d.querySelector('footer .legal:not([open])'));
  chk(ex+' arte real de fundo',t.w.getComputedStyle(d.querySelector('.cenario-escrivao')).background.includes('escrivaninha-v2.webp'));
  chk(ex+' rodape sem caveat TCF',!d.querySelector('.conteudo-papel').textContent.includes('PDF oficial'));
  chk(ex+' sem erros de parse HTML/CSS',t.errors.length===0);t.close();
 }
 const a=await abrir('ativo');let confirmations=0;
 a.w.confirm=()=>{confirmations++;return false};a.d.getElementById('nova').click();
 chk('descartar exige confirmacao',confirmations===1&&a.requests.length===0);
 chk('descartar link discreto no rodape',!!a.d.querySelector('footer #nova.link-discreto'));
 chk('ativa nao parece prova completa desabilitada',!a.d.querySelector('.principal').disabled&&!!a.d.querySelector('.tentativa-ativa'));
 a.d.querySelector('.principal').click();await Promise.resolve();await Promise.resolve();
 chk('cancelar troca retoma sem descartar',a.requests[0].body.novo===false);
 a.w.confirm=()=>true;a.d.getElementById('nova').click();await Promise.resolve();await Promise.resolve();
 chk('confirmar descartar solicita completo novo',a.requests[1].body.novo===true&&a.requests[1].body.secao==='completo');a.close();
 const co=await abrir('co');
 chk('cronometro no prato de metal da ampulheta',!!co.d.querySelector('.chrono .placa-tempo time[role="timer"]')&&!!co.d.querySelector('.chrono img.relogio-arte'));
 chk('cronometro fixo com JS inicializado',co.w.getComputedStyle(co.d.getElementById('chrono')).position==='fixed'&&/^\d\d:\d\d$/.test(co.d.getElementById('tempo').textContent));
 chk('TCF inicialmente oculta alternativas',co.d.querySelectorAll('input[type="radio"]').length===0);
 co.d.getElementById('audio-unico').click();chk('uma escuta bloqueada imediatamente',co.d.getElementById('audio-unico').disabled);
 co.audios[0].onended();chk('quatro alternativas apos fim do audio',co.d.querySelectorAll('input[type="radio"]').length===4);
 chk('botoes dinamicos usam classe do jogo',Array.from(co.d.querySelectorAll('#conteudo button,#navegacao button')).every(b=>b.classList.contains('botao')));
 const storage={};for(let i=0;i<co.w.localStorage.length;i++){const k=co.w.localStorage.key(i);storage[k]=co.w.localStorage.getItem(k)}co.close();
 const reload=await abrir('co',{storage});chk('reload preserva audio consumido e seletores',reload.d.getElementById('audio-unico').disabled&&reload.d.querySelectorAll('input[type="radio"]').length===4);reload.close();
 for(const [remaining,cls]of [[240,'low'],[30,'urgent']]){const t=await abrir('co',{remaining});chk('aviso '+cls+' preservado na nova HUD',t.d.getElementById('chrono').classList.contains(cls)&&!!t.d.getElementById('timer-aviso').textContent);t.close()}
 const expired=await abrir('co',{remaining:0});await Promise.resolve();await Promise.resolve();chk('zero continua enviando automaticamente',expired.requests.some(r=>r.u.endsWith('/entregar'))&&expired.d.getElementById('tempo').textContent==='00:00');expired.close();
 const ee=await abrir('ee');chk('escrita TCF tem tres campos',ee.d.querySelectorAll('textarea.writing').length===3);chk('caveat TCF fora da tela EE',!ee.d.getElementById('conteudo').textContent.includes('PDF oficial'));ee.close();
 const eo=await abrir('eo');chk('oral mantem NPC e alternativa digitada',!!eo.d.querySelector('img.npc')&&!!eo.d.querySelector('textarea[aria-label="Intervenção do candidato em francês"]'));chk('oral mantem cronometro renderizado',/^\d\d:\d\d$/.test(eo.d.getElementById('tempo').textContent));eo.close();
 const r=await abrir('resultados');chk('resultado novo na mesma folha',!!r.d.querySelector('.folha-exame .cartao .acertos'));chk('resultado mantem estimativa nao oficial',r.d.querySelector('.cartao').textContent.includes('Estimativa não oficial'));chk('resultado tem saida e aviso discretos',!!r.d.querySelector('a.botao')&&!!r.d.querySelector('footer .legal'));r.close();
 chk('regra mobile e HUD fixa constam no CSS',css.includes('@media(max-width:700px)')&&/\.chrono\{[^}]*position:fixed/.test(css));
 console.log(count+' verificacoes UI/DOM OK — NAO e validacao visual ou screenshot');
})().catch(e=>{console.error(e);process.exit(1)});
