"""Partículas somente no diorama e prévias; nenhuma mudança nos ledgers."""
import copy
from html.parser import HTMLParser
import pytest
from test_loja import ctx,A,post,ROOT,abastecer
from loja import ITENS

class Camadas(HTMLParser):
    def __init__(self,html):
        super().__init__();self.pilha=[];self.fx=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        if tag in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:return
        a=dict(attrs);classes=set(a.get('class','').split())
        if 'fx' in classes:self.fx.append(tuple(self.pilha))
        self.pilha.append((tag,classes))
    def handle_endtag(self,tag):
        for i in range(len(self.pilha)-1,-1,-1):
            if self.pilha[i][0]==tag:
                del self.pilha[i:];break

PARTICULAS=[i for i,v in ITENS.items() if v['categoria']=='particulas']
NEGATIVAS=['/mapa?vista=mundo','/mapa?vista=regiao&parada=1','/mapa?vista=regiao&parada=12','/mapa?vista=regiao&parada=25','/parada/1/4','/parada/1/11','/parada/1/40','/parada/1/1','/parada/1/2','/parada/1/6','/parada/1/9','/parada/1/10','/personagem','/nivelamento','/missao','/simulados/tef','/simulados/tcf']

def perfil(fake,teste):return A._PERFIS_TESTE['teste:teste'] if teste else fake.docs['real']

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('iid',PARTICULAS)
def test_particula_persistida_so_em_cena_e_previas_sem_contaminar_perfil(ctx,teste,iid):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste)
    assert not Camadas(c.get('/heroi').text).fx
    assert post(c,t,item=iid).status_code==200
    assert post(c,t,'/loja/equipar',item=iid).status_code==200
    antes=copy.deepcopy(perfil(fake,teste));c2,t2=f(teste)
    h=c2.get('/heroi').text;camadas=Camadas(h).fx
    assert len(camadas)==1 and any('diorama' in classes for _,classes in camadas[0])
    assert any('particulas-cena' in classes for _,classes in camadas[0])
    for cat in ['personagem','pets','titulos','cenarios','particulas']:
        html=c2.get('/loja?categoria='+cat).text;camadas=Camadas(html).fx
        assert len(camadas)==(6 if cat=='particulas' else 1)
        assert all(any(classes & {'perfil-resumo','amostra'} for _,classes in pais) for pais in camadas)
    for path in NEGATIVAS:
        r=c2.get(path);esperado=302 if path=='/missao' and not teste else 200
        assert r.status_code==esperado,(path,r.status_code)
        assert not Camadas(r.text).fx,path
        assert 'fx-'+ITENS[iid]['efeito'] not in r.text,path
    assert perfil(fake,teste)==antes
    # Restauração da apresentação não apaga posse, moeda ou o item equipado.
    assert perfil(fake,teste)['cosmeticos']['equipados']['particulas']==iid
    assert post(c2,t2,'/loja/retirar',categoria='particulas').status_code==200
    assert not Camadas(c2.get('/heroi').text).fx
    assert not Camadas(c2.get('/loja?categoria=personagem').text).fx
    assert len(Camadas(c2.get('/loja?categoria=particulas').text).fx)==5
    e=perfil(fake,teste)['cosmeticos'];assert iid in e['comprados'] and e['cristais']==750


def test_css_contem_decoracao_e_movimento_reduzido_sem_mudar_efeitos_do_jogo():
    css=(ROOT/'static/loja/perfil-v6.css').read_text(encoding='utf-8')
    assert '.particulas-cena{position:absolute;inset:0;overflow:hidden;pointer-events:none;' in css
    assert '.particulas-cena .fx{position:absolute;' in css
    assert '@media(prefers-reduced-motion:reduce){.particulas-cena{display:none!important}}' in css
    assert 'top:calc(100% + 20px)' in css
    assert "loja-particulas-cena.html" not in (ROOT/'templates/loja-base.html').read_text(encoding='utf-8')
    assert "loja-efeito.html" not in (ROOT/'templates/loja-base.html').read_text(encoding='utf-8')
    # Arte, dados, engines e templates congelados são auditados por SHA no auditor v7b.
