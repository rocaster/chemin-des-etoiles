/* DOM/VM unit tests; no browser, network or private app state. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const {JSDOM}=require('jsdom');
const ROOT=process.argv[2], fixture=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let checks=0;function chk(v,msg){assert(v,msg);checks++}
function func(src,name){const re=new RegExp(`function ${name}\\([^]*?\\n  }`);const m=src.match(re);if(!m)throw Error(name);return m[0]}
async function scenario(engine,rec,resposta,options={}){
 const dom=new JSDOM('<main id="conteudo"></main><aside id="retorno"></aside>',{url:'http://offline.invalid'}),w=dom.window,d=w.document;
 const h=(tag,attrs={},...children)=>{const e=d.createElement(tag);for(const[k,v]of Object.entries(attrs)){if(k==='text')e.textContent=v;else if(typeof v!=='function')e.setAttribute(k==='class'?'class':k,v)};for(const c of children.flat(Infinity))if(c!=null)e.append(c);return e};
 const cfg={pid:'r1-p01',prefixo:'chemin_teste_',n:1,regiao:1,mapa:'/mapa',refazer:'/',concluir:'/concluir',estatico:'/static/',teste:true};let chamadas=0;
 const context={CFG:cfg,D:{recompensa:rec,vocabulario:[],formato:'cartas'},E:{acertos:5,erros:0,falaPendente:false,inicio:Date.now()},
  EM_PREVIA:!!options.previa,PRE:cfg.prefixo,reduz:false,localStorage:w.localStorage,h,conteudo:d.querySelector('main'),retorno:d.querySelector('aside'),
  estrelas:()=>3,calar(){},progresso(){},esconderRetorno(){},marcar(){},focar(){},topo(){},
  trocar:(el,...cc)=>{el.replaceChildren(...cc.flat(Infinity).filter(x=>x!=null))},
  fetch:async()=>{chamadas++;if(options.rede)throw Error('offline');return {ok:!options.http,json:async()=>resposta}}};
 const source=fs.readFileSync(`${ROOT}/static/parada/${engine}.js`,'utf8');vm.createContext(context);
 vm.runInContext(func(source,'salvar')+'\n'+func(source,'concluir')+'\nconcluir();',context);
 if(!options.previa)chk(d.querySelector('.xp').textContent==='Confirmando XP…',`${engine}: aguarda confirmação`);
 await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
 const text=d.querySelector('.xp').textContent;
 if(options.previa){chk(chamadas===0,'prévia não salva');chk(text===`+${rec.xp_pausado?0:(rec.xp_base??0)} XP · prévia`,'prévia respeita zero/pausa')}
 else if(options.rede||options.http||options.invalido){chk(text.startsWith('XP pendente'),'não inventa XP na falha');const reg=JSON.parse(w.localStorage.getItem(cfg.prefixo+'paradas'))[cfg.pid];chk(reg.xp_confirmado===false,'pendente não se diz confirmado')}
 else{chk(text.startsWith(`+${resposta.xp_ganho} XP`),'XP ganho vem do servidor, inclusive zero');
  const reg=JSON.parse(w.localStorage.getItem(cfg.prefixo+'paradas'))[cfg.pid];
  chk(reg.xp===resposta.xp_creditado_etapa,'registro mantém crédito vitalício por etapa');chk(reg.xp_ganho===resposta.xp_ganho&&reg.xp_confirmado===true,'registro confirmado');
  chk(chamadas===1,'uma conclusão envia uma chamada');if(engine==='formatos')chk(d.querySelector('#nota-salvar').dataset.ok==='1','nota confirmada sem ReferenceError')}
 dom.window.close();
}
(async()=>{
 for(const engine of ['motor','formatos']){
  for(const base of [0,20,25])await scenario(engine,{xp_base:base,xp_por_estrela:0},{ok:true,xp_ganho:base,xp_creditado_etapa:base,xp_total:base});
  await scenario(engine,{xp_base:25,xp_por_estrela:0},{ok:true,xp_ganho:0,xp_creditado_etapa:25,xp_total:25});
  await scenario(engine,{xp_base:25,xp_por_estrela:5,xp_pausado:true},{ok:true,xp_ganho:0,xp_creditado_etapa:0,xp_total:0});
  await scenario(engine,{}, {ok:true,xp_ganho:0,xp_creditado_etapa:0,xp_total:0});
  for(const option of ['rede','http','invalido'])await scenario(engine,{xp_base:25},{ok:true,xp_ganho:'25',xp_total:'25'},{[option]:true});
  await scenario(engine,{xp_base:25,xp_pausado:true},null,{previa:true});
 }
 const src=fixture.mapa,table=JSON.parse(src.match(/const XP_POR_ID = ([^;]+);/)[1]),bordas=JSON.parse(src.match(/const BORDAS = ([^;]+);/)[1]);
 const srcFun=src.match(/function xpLocal\([^]*?\n    }/)[0]+'\n'+src.match(/function nivelBorda\([^]*?\n    }/)[0];
 const storage=new Map(),ctx={XP_POR_ID:table,BORDAS:bordas,xpServidor:0,PREFIXO:'chemin_teste_',params:new URLSearchParams(),localStorage:{getItem:k=>storage.get(k)}};vm.createContext(ctx);vm.runInContext(srcFun,ctx);
 storage.set('chemin_teste_paradas',JSON.stringify({forjado:{xp:99999,concluida_em:'ok'},'r1-p01':{xp:99999,concluida_em:'ok'}}));
 chk(ctx.nivelBorda()===0,'servidor zero vence local forjado');chk(ctx.xpLocal()===25,'fallback recalcula tabela canônica, ignora desconhecidos');
 ctx.xpServidor=null;chk(ctx.nivelBorda()===0,'estimativa limitada pelo conteúdo');
 storage.set('chemin_teste_paradas',JSON.stringify(Object.fromEntries(Object.keys(table).map(pid=>[pid,{xp:9999,concluida_em:'ok'}]))));
 chk(ctx.xpLocal()===640,'fallback nunca inventa acima dos 640 do mapa');ctx.xpServidor=45;chk(ctx.nivelBorda()===1,'total servidor prevalece mesmo menor que o local');
 console.log(`${checks} verificações XP DOM/VM OK; 0 falhas`);
})().catch(e=>{console.error(e);process.exitCode=1});
