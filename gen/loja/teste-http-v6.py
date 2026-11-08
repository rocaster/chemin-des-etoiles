"""HTTP real somente contra o servidor offline dedicado. Não é screenshot."""
import json,re,sys
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor,Request
from http.cookiejar import CookieJar
BASE=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:5090'
assert BASE.startswith(('http://127.0.0.1:','http://localhost:'))
OUT=Path(__file__).resolve().parents[3]/'prints-loja/v6';OUT.mkdir(parents=True,exist_ok=True)
op=build_opener(HTTPCookieProcessor(CookieJar()));checks=0

def get(path):return op.open(BASE+path,timeout=10).read().decode()
def salvar(nome,h):
    h=re.sub(r'(name="csrf" value=")[^"]+',r'\1TOKEN_DE_TESTE_REMOVIDO',h)
    (OUT/nome).write_text(h, encoding='utf-8')
def post(url,**body):
    r=op.open(Request(BASE+url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=10)
    return json.load(r)
def chk(c):
    global checks
    assert c;checks+=1
get('/__login-teste?ir=/loja');h=get('/loja');salvar('loja-antes.html',h)
csrf=re.search(r'name="csrf" value="([^"]+)"',h)[1]
itens=['paleta-ametista','efeito-inverno','titulo-voz','pet-fenix'];precos=[150,250,90,400];saldo=1000;compras=[]
for iid,preco in zip(itens,precos):
    j=post('/loja/comprar',csrf=csrf,item=iid);saldo-=preco;chk(j['ok'] and j['estado']['cristais']==saldo)
    j=post('/loja/comprar',csrf=csrf,item=iid);chk(j['estado']['cristais']==saldo)
    compras.append({'item':iid,'preco':preco,'saldo':saldo})
salvar('loja-depois-compra.html',get('/loja?categoria=pets'))
for iid in itens:chk(post('/loja/equipar',csrf=csrf,item=iid)['ok'])
for url,arquivo in [('/loja','loja-equipada.html'),('/heroi','heroi-equipado.html'),('/mapa?vista=regiao','mapa-equipado.html'),('/parada/1/4','batalha-equipada.html')]:
    h=get(url);salvar(arquivo,h)
    for trecho in ['-ametista.png','fenix.png','Voix du village']:chk(trecho in h)
    chk(('fx-inverno' in h)==(url=='/heroi' or url.startswith('/loja')))
j=post('/parada/1/1/concluir',acertos=5,erros=1,fala_pendente=False,duracao_s=120)
chk(j['xp_ganho']==25 and j['cristais_ganhos']==18 and j['cristais_total']==saldo+18)
j2=post('/parada/1/1/concluir',acertos=5,erros=1,fala_pendente=False,duracao_s=120)
chk(j2['xp_ganho']==j2['cristais_ganhos']==0)
result={'verificacoes_http':checks,'falhas':0,'servidor_offline':BASE,'compras':compras,'primeira_conclusao':j,'repeticao':j2,'nota':'HTMLs são respostas HTTP, não capturas visuais; CSRF removido.'}
(OUT/'resultado-http.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
