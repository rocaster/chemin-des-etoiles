// jsdom valida estrutura/contratos, NÃO layout ou renderização visual.
const {JSDOM} = require('jsdom');
const fs=require('node:fs'),path=require('node:path');
const dir=process.argv[2];let n=0;
function check(msg,v){if(!v)throw Error(msg);n++;console.log('OK',msg)}
function doc(name){return new JSDOM(fs.readFileSync(path.join(dir,name+'.html'),'utf8')).window.document}
let h=doc('heroi');
check('pose nova de corpo inteiro',h.querySelector('.heroi-pose').style.backgroundImage.includes('poses-v5/cavaleiro-f.png'));
check('refúgio sem moldura redonda',!!h.querySelector('.diorama')&&!h.querySelector('.moldura'));
check('oito quadros articulados',h.querySelector('.heroi-pose').dataset.quadros==='8'&&!h.querySelector('.corpo-fechado'));
check('lugar reservado sem pet',!!h.querySelector('.pet-vazio img')); 
check('três estatísticas separadas',h.querySelectorAll('.estatisticas dd').length===3);
check('nome e título abaixo',h.querySelector('.nome-heroi').nextElementSibling.className==='titulo-heroi');
check('sete conquistas com estado legível',h.querySelectorAll('.selo .estado-selo').length===7);
check('três selos sem dados explicitamente indisponíveis',[...h.querySelectorAll('.estado-selo')].filter(x=>x.textContent.includes('não rastreável')).length===3);
check('âncora de baú funciona',!!h.querySelector('#conquistas'));
check('atalhos mapa, loja e baú',h.querySelectorAll('.atalhos a').length===3 && h.querySelector('.voltar').getAttribute('href')==='/mapa');
check('pular conteúdo acessível',h.querySelector('.pular').getAttribute('href')==='#principal');
check('sem pet não há animação',!h.querySelector('.pet-idle'));
for(const [cat,total] of [['personagem',3],['particulas',5],['titulos',4],['pets',10],['cenarios',7]]){
 const d=doc(cat);
 check(cat+' tem cinco categorias',d.querySelectorAll('.abas a').length===5);
 check(cat+' identifica aba atual',d.querySelectorAll('.abas [aria-current=page]').length===1 && d.querySelector('.abas [aria-current]').href.endsWith(cat));
 check(cat+' contém catálogo completo',d.querySelectorAll('.produto').length===total);
 check(cat+' compra POST sem JavaScript',[...d.querySelectorAll('.produto form')].every(f=>f.method==='post' && f.action.endsWith('/loja/comprar')));
 check(cat+' todas as compras têm CSRF',[...d.querySelectorAll('.produto form')].every(f=>f.querySelector('[name=csrf]').value.length>30));
 check(cat+' preço explícito em cristais',d.querySelectorAll('.preco small').length===(cat==='cenarios'?6:total));
}
let d=doc('pets');
check('pets articulados na loja',d.querySelectorAll('.pet.sprite-oito').length===10&&d.querySelectorAll('.pet-idle').length===10);
d=doc('equipado');
check('só um pet equipado',d.querySelectorAll('.pet-idle').length===1);
check('título comprado abaixo do nome',d.querySelector('.titulo-heroi').textContent==='Voix du village');
check('pose da cavaleira com paleta rubi',d.querySelector('.heroi-pose').style.backgroundImage.includes('poses-v5/cavaleiro-f-rubi.png'));
check('sheet único sem flash de paleta',d.querySelector('.heroi-pose').dataset.quadros==='8'&&!d.querySelector('.corpo-fechado'));
check('pet tem nome acessível',d.querySelector('.pet-idle').getAttribute('aria-label')==='Dragão bebê');
d=doc('loja-equipado');
check('equipado não permite recompra',!!d.querySelector('[data-item="pet-dragao"] .em-uso')&&!d.querySelector('[data-item="pet-dragao"] form'));
check('restaurar padrão via POST',d.querySelector('.prateleira-topo form').action.endsWith('/loja/retirar'));
d=doc('comprado');
check('recompra não aparece: só equipar',d.querySelector('[data-item="pet-dragao"] form').action.endsWith('/loja/equipar'));
d=doc('sem-saldo');
check('sem saldo botões desabilitados',[...d.querySelectorAll('.produto button')].every(b=>b.disabled));
check('sem scripts dependentes de terceiros',!d.querySelector('script[src]'));
check('seis molduras não compráveis',doc('heroi').querySelectorAll('[data-moldura]').length===6&&!doc('heroi').querySelector('#molduras form'));
check('renomear pet tem CSRF e limite 16',doc('equipado').querySelector('#nome-pet [name=csrf]').value.length>30&&doc('equipado').querySelector('#pet-nome').maxLength===16);
// v7b: seleção persistida não significa decoração no mapa/HUD/batalha.
let cena=doc('heroi-particula');
check('partículas somente dentro do diorama',cena.querySelectorAll('.fx').length===1&&!!cena.querySelector('.diorama > .particulas-cena .fx-chuva'));
check('sem partículas em header, estatísticas, baú ou página inteira',!cena.querySelector('body > .fx, header .fx, .ficha .fx, .bau .fx'));
let previa=doc('loja-particula');
check('partícula equipada limitada à prévia da loja',previa.querySelectorAll('.fx').length===1&&!!previa.querySelector('.perfil-resumo > .particulas-cena .fx-chuva'));
check('cinco amostras da loja e uma prévia equipada',doc('loja-particulas').querySelectorAll('.amostra .fx').length===5&&doc('loja-particulas').querySelectorAll('.fx').length===6);
for(const nome of ['mapa-mundo-particula','mapa-regiao-particula','batalha-particula','chefe-particula'])check(nome+' sem camada cosmética',!doc(nome).querySelector('.fx'));
const visual=new JSDOM(cena.documentElement.outerHTML),vw=visual.window;
const estilo=vw.document.createElement('style');
estilo.textContent=fs.readFileSync(path.join(__dirname,'../../static/loja/efeitos.css'),'utf8')+'\n'+fs.readFileSync(path.join(__dirname,'../../static/loja/perfil-v6.css'),'utf8');vw.document.head.append(estilo);
check('camada absoluta, nunca fixa na tela',vw.getComputedStyle(vw.document.querySelector('.particulas-cena .fx')).position==='absolute');
const contida=vw.getComputedStyle(vw.document.querySelector('.particulas-cena'));
check('recorte do próprio cenário',contida.position==='absolute'&&contida.overflow==='hidden');
check('decoração não captura cliques',contida.pointerEvents==='none');
check('movimento reduzido esconde toda camada',estilo.textContent.includes('@media(prefers-reduced-motion:reduce){.particulas-cena{display:none!important}}'));
vw.close();
const pares={
 'titulo-viajante':['Voyageur des étoiles','Voyageuse des étoiles','Viajante das Estrelas'],
 'titulo-guardiao':['Gardien des mots','Gardienne des mots','Guardiã das Palavras'],
 'titulo-voz':['Voix du village','Voix du village','Voz do Vilarejo'],
 'titulo-coroa':['Couronne de l’entêtement','Couronne de l’entêtement','Coroa da Teimosia']};
for(const [iid,[m,f,pt]] of Object.entries(pares)){
 const card=doc('titulos').querySelector(`[data-item="${iid}"]`),masc=doc('titulos-m').querySelector(`[data-item="${iid}"]`);
 check(iid+' prévia feminina FR',card.querySelector('.preview-titulo [lang=fr]').textContent===f&&card.querySelector('.preview-titulo small').textContent==='Luna');
 check(iid+' prévia masculina FR',masc.querySelector('.preview-titulo [lang=fr]').textContent===m);
 check(iid+' pergaminho PT e tradução FR',card.querySelector('h3').textContent===pt&&card.querySelector('.produto-texto>p').textContent.includes('Tradução de '+f));
}
check('quatro descrições PT diferentes',new Set([...doc('titulos').querySelectorAll('.produto-texto>p')].map(e=>e.textContent)).size===4);
check('padrão feminino em francês',doc('heroi').querySelector('.titulo-heroi').textContent==='Voyageuse sans titre');
check('padrão masculino em francês',doc('heroi-m').querySelector('.titulo-heroi').textContent==='Voyageur sans titre');
console.log(`${n} verificações UI/DOM da loja OK (sem validação visual)`);
