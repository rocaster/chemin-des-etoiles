"""HTTP local v7: cinco categorias, nomes, cenas e vistas. Sem captura visual."""
import json,re,sys
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor,Request
from http.cookiejar import CookieJar
BASE=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:5091'
assert BASE.startswith(('http://127.0.0.1:','http://localhost:'))
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).resolve().parents[3]/'prints-loja/v7'
OUT.mkdir(parents=True,exist_ok=True)
op=build_opener(HTTPCookieProcessor(CookieJar()));checks=0

def get(path):return op.open(BASE+path,timeout=10).read().decode('utf-8')
def post(url,**body):
    r=op.open(Request(BASE+url,data=json.dumps(body).encode('utf-8'),headers={'Content-Type':'application/json'}),timeout=10)
    return json.load(r)
def salvar(nome,h):
    h=re.sub(r'(name="csrf" value=")[^"]+',r'\1TOKEN_DE_TESTE_REMOVIDO',h)
    (OUT/nome).write_text(h,encoding='utf-8')
def chk(ok):
    global checks
    assert ok;checks+=1
get('/__login-teste?ir=/loja');h=get('/loja');salvar('loja-antes.html',h)
csrf=re.search(r'name="csrf" value="([^"]+)"',h)[1]
# A conta teste parte de 1.000. Um mapa perfeito demonstra +1.220, idempotente.
res=[post(f'/parada/1/{n}/concluir',acertos=5,erros=0,fala_pendente=False,duracao_s=120) for n in range(1,41)]
chk(sum(j['xp_ganho'] for j in res)==640);chk(sum(j['cristais_ganhos'] for j in res)==1220)
itens=['paleta-ametista','efeito-inverno','titulo-voz','pet-fenix','cenario-jardim-japones'];precos=[150,250,90,400,300];saldo=2220
for iid,preco in zip(itens,precos):
    j=post('/loja/comprar',csrf=csrf,item=iid);saldo-=preco;chk(j['estado']['cristais']==saldo)
    chk(post('/loja/comprar',csrf=csrf,item=iid)['estado']['cristais']==saldo)
    chk(post('/loja/equipar',csrf=csrf,item=iid)['ok'])
salvar('loja-depois-compra.html',get('/loja?categoria=cenarios'))
salvar('loja-titulos.html',get('/loja?categoria=titulos'))
j=post('/loja/pet/nome',csrf=csrf,item='pet-fenix',nome='Étoile de Feu');chk(j['estado']['nomes_pets']['pet-fenix']=='Étoile de Feu');chk(j['estado']['cristais']==1030)
for url,nome in [('/heroi','heroi-equipado.html'),('/loja?categoria=pets','loja-pets-renomeado.html'),('/mapa?vista=regiao','mapa-regiao.html'),('/mapa?vista=mundo','mapa-mundo.html'),('/parada/1/4','batalha-equipada.html')]:
    h=get(url);salvar(nome,h)
    for parte in ['-ametista.png','fenix.png','Voix du village']:chk(parte in h)
    chk(('fx-inverno' in h)==(url=='/heroi' or url.startswith('/loja')))
    if '/heroi'==url:chk('cenario/jardim-japones.png' in h and 'Étoile de Feu' in h)
    elif not url.startswith('/loja'):chk('cenario/jardim-japones.png' not in h)
    if 'mapa?' in url:
        nav=re.search(r'<nav[^>]+id="simulado-entradas"[^>]*>',h)[0];chk((' hidden' in nav)==('regiao' in url))
r=post('/parada/1/1/concluir',acertos=5,erros=0,fala_pendente=False,duracao_s=120);chk(r['xp_ganho']==r['cristais_ganhos']==0)
result={'verificacoes_http':checks,'falhas':0,'saldo_final':saldo,'xp_mapa':640,'cristais_ganhos':1220,'categorias_compradas_equipadas':5,'nota':'HTTP offline; HTMLs com CSRF removido. Não são screenshots.'}
(OUT/'resultado-http.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
