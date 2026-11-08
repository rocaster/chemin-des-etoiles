// DOM puro: usa o modo() real e as regras CSS reais; não é teste de layout de navegador.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),{JSDOM}=require('jsdom');
const fixtures=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));let checks=0;
function ok(cond,msg){assert(cond,msg);checks++}
for(const vista of ['mundo','regiao']){
 const dom=new JSDOM(fixtures[vista],{url:'http://offline.invalid/mapa'}),d=dom.window.document,nav=d.getElementById('simulado-entradas');
 ok(nav.children.length===2,'TEF e TCF mantidos');ok(nav.hidden===(vista!=='mundo'),'estado inicial correto');
 const source=fixtures[vista].match(/function modo\(m\) \{[^]*?\n    }/)[0];
 const context={body:d.body,document:d,podeArrastarMundo(){},painelMundo:d.createElement('aside'),painelRegiao:d.createElement('aside')};vm.createContext(context);vm.runInContext(source,context);
 for(const mode of ['vista-regiao','vista-mundo','vista-obra','transicao']){
  context.modo(mode);ok(nav.hidden===(mode!=='vista-mundo'),mode+' hidden');
  ok((dom.window.getComputedStyle(nav).display==='none')===(mode!=='vista-mundo'),mode+' CSS');
 }
 context.modo('vista-mundo');d.body.className='transicao';ok(dom.window.getComputedStyle(nav).display==='none','voo esconde imediatamente');
 context.modo('vista-mundo');ok(!nav.hidden&&dom.window.getComputedStyle(nav).display!=='none','voltar restaura');
 ok(d.querySelectorAll('.heroi-placas a').length===3,'entradas de personagem preservadas');dom.window.close();
}
console.log(`${checks} checks OK; 0 falhas`);
