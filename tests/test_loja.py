"""Tudo offline: carrega app sem .env, CosmosFake no lugar da rede."""
import copy
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SUPORTE = ROOT / 'gen/formatos/teste'
if not (SUPORTE / 'cosmos_fake.py').exists():
    SUPORTE = ROOT.parent / 'gen/formatos/teste'
sys.path.insert(0, str(SUPORTE))
with patch('dotenv.load_dotenv', return_value=False):
    import app as A
from cosmos_fake import CosmosFake, erro
from contas_cosmos import ContasCosmos, ContasIndisponiveis, OperacaoCosmeticaInvalida
from loja import operar, estado_cosmetico, avaliar_conquistas, ITENS

@pytest.fixture
def ctx(monkeypatch):
    A.app.config['TESTING'] = True
    A.USUARIOS_TESTE.add('teste')
    A._PERFIS_TESTE.clear()
    fake = CosmosFake()
    monkeypatch.setattr(A, 'get_users_container', lambda: fake)
    fake.create_item(body={'id':'real','tipo':'conta','confirmado':True,'avatar':'cavaleiro-f',
        'nome_personagem':'Luna','onboarding_concluido_em':'agora','onboarding_versao':1,
        'nivelamento_concluido_em':'agora','xp':135,'senha_hash':'preservar','nonce':'preservar'})
    def cliente(teste=True):
        c=A.app.test_client()
        if teste:
            A._PERFIS_TESTE.setdefault('teste:teste', {'id':'teste:teste','teste':True,'avatar':'cavaleiro-f','xp':135,'nome_personagem':'Luna'})
        with c.session_transaction() as s:
            if teste:s['teste']='teste'
            else:s['uid']='real'
        html=c.get('/loja').get_data(as_text=True)
        token=re.search(r'name="csrf" value="([^"]+)"',html).group(1)
        return c,token
    return fake,cliente

def post(c,t,url='/loja/comprar',**kw):
    return c.post(url,json={'csrf':t,**kw})

@pytest.mark.parametrize('path',['/heroi','/loja','/conquistas','/loja?categoria=pets','/loja?categoria=particulas','/loja?categoria=titulos'])
def test_login_obrigatorio(ctx,path):
    assert A.app.test_client().get(path).status_code==302

@pytest.mark.parametrize('path',['/heroi','/loja','/loja?categoria=pets','/loja?categoria=titulos','/loja?categoria=particulas'])
def test_rotas(ctx,path):
    _,f=ctx;c,_=f();assert c.get(path).status_code==200

def test_teste_saldo_memoria_sem_cosmos(ctx):
    fake,f=ctx;c,t=f();before=copy.copy(fake.calls)
    assert post(c,t,item='pet-dragao').json['estado']['cristais']==600
    assert fake.calls==before
    assert A._PERFIS_TESTE['teste:teste']['xp']==135

def test_conta_real_zero(ctx):
    fake,f=ctx;c,t=f(False)
    assert '0</strong> cristais' in c.get('/heroi').text
    assert post(c,t,item='pet-dragao').status_code==409
    assert 'cosmeticos' not in fake.docs['real']

@pytest.mark.parametrize('url',['/loja/comprar','/loja/equipar','/loja/retirar'])
def test_csrf(ctx,url):
    _,f=ctx;c,t=f()
    assert c.post(url,json={'item':'pet-dragao'}).status_code==403
    assert post(c,t+'x',url,item='pet-dragao').status_code==403
    assert c.get(url).status_code==405

def test_csrf_outra_sessao(ctx):
    _,f=ctx;c,t=f();outro,t2=f()
    assert t!=t2
    assert post(outro,t,item='pet-dragao').status_code==403

def test_json_invalido(ctx):
    _,f=ctx;c,t=f()
    assert c.post('/loja/comprar',json=[]).status_code==400
    assert post(c,t,item=[]).status_code==400
    assert post(c,t,item='inexistente').status_code==404
    assert c.get('/loja?categoria=xxx').status_code==404

def test_compra_idempotente_e_preco_servidor(ctx):
    _,f=ctx;c,t=f()
    for _ in range(3):
        r=post(c,t,item='pet-dragao',preco=0,cristais=999999,xp=1)
        assert r.status_code==200 and r.json['estado']['cristais']==600
    assert r.json['estado']['comprados']==['pet-dragao']
    assert A._PERFIS_TESTE['teste:teste']['xp']==135

def test_equipar_retirar_idempotentes(ctx):
    _,f=ctx;c,t=f()
    assert post(c,t,'/loja/equipar',item='pet-dragao').status_code==403
    post(c,t,item='pet-dragao')
    for _ in range(2):
        j=post(c,t,'/loja/equipar',item='pet-dragao').json['estado']
        assert j['equipados']['pets']=='pet-dragao' and j['cristais']==600
    for _ in range(2):
        j=post(c,t,'/loja/retirar',categoria='pets').json['estado']
        assert j['equipados']=={} and j['cristais']==600
    assert post(c,t,'/loja/retirar',categoria='xx').status_code==400

def test_uma_escolha_por_categoria(ctx):
    _,f=ctx;c,t=f()
    for iid in ['pet-dragao','pet-raposa','titulo-voz']:
        post(c,t,item=iid);r=post(c,t,'/loja/equipar',item=iid)
    assert r.json['estado']['equipados']=={'pets':'pet-raposa','titulos':'titulo-voz'}
    assert r.json['estado']['cristais']==110

def test_falta_saldo(ctx):
    _,f=ctx;c,t=f()
    for iid in ['pet-dragao','pet-lobo']:
        assert post(c,t,item=iid).status_code==200
    assert post(c,t,item='pet-raposa').status_code==409
    assert A._PERFIS_TESTE['teste:teste']['cosmeticos']['cristais']==200

def test_forms_sem_javascript(ctx):
    _,f=ctx;c,t=f()
    r=c.post('/loja/comprar',data={'csrf':t,'item':'pet-dragao'})
    assert r.status_code==303 and 'categoria=pets' in r.location
    assert 'Compra guardada' in c.get(r.location).text
    r=c.post('/loja/equipar',data={'csrf':t,'item':'pet-lobo'})
    assert r.status_code==403 and 'Compre o item' in r.text

def test_render_titulo_pet_paleta_e_xss(ctx):
    _,f=ctx;c,t=f()
    A._PERFIS_TESTE['teste:teste']['nome_personagem']='<script>x</script>'
    for iid in ['titulo-voz','pet-raposa','paleta-rubi']:
        post(c,t,item=iid);post(c,t,'/loja/equipar',item=iid)
    html=c.get('/heroi').text
    assert 'Voix du village' in html and 'raposa.png' in html and 'cavaleiro-f-rubi.png' in html
    assert '&lt;script&gt;' in html and '<script>x</script>' not in html
    assert '135' in html and 'Nível visual' in html

def test_pet_no_perfil_sem_tocar_fogueira(ctx):
    _,f=ctx;c,t=f();post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    for path in ['/mapa','/parada/1/4']:
        assert 'loja/pets/dragao.png' in c.get(path).text
    assert 'loja/pets/' not in c.get('/personagem').text
    assert 'pet-idle' in c.get('/heroi').text
    assert c.get('/loja?categoria=pets').text.count('pet pet-idle sprite-oito')==10

def test_chuva_so_cenario_e_previa_sem_musica_nova(ctx):
    _,f=ctx;c,t=f()
    assert 'fx-chuva' not in c.get('/parada/1/4').text
    post(c,t,item='efeito-chuva');post(c,t,'/loja/equipar',item='efeito-chuva')
    assert 'fx-chuva' not in c.get('/parada/1/4').text
    assert 'fx-chuva' not in c.get('/parada/1/40').text
    assert 'fx-chuva' in c.get('/heroi').text
    assert 'fx-chuva' not in c.get('/parada/1/1').text

def test_css_reduced_motion_e_mapa(ctx):
    _,f=ctx;c,t=f()
    for path in ['/static/loja/loja.css','/static/loja/efeitos.css']:
        assert 'prefers-reduced-motion:reduce' in c.get(path).text
    m=c.get('/mapa').text
    assert 'heroi-placas' in m and 'href="/heroi"' in m and 'href="/conquistas"' in m
    css=c.get('/static/loja/mapa-entradas.css').text
    assert '.vista-regiao .heroi-placas' in css

def test_arte_existe():
    from PIL import Image
    for i in ITENS.values():
        if i['categoria']=='pets':assert Image.open(ROOT/'static'/i['sprite']).size==(384,48)
    assert len(list((ROOT/'static/loja/paletas').glob('*.png')))==24

def test_criterios_server():
    perfil={'paradas_progresso':{}}
    def selos():return {s['id']:s for s in avaliar_conquistas(perfil,['b1'],'boss')}
    assert not any(s['desbloqueada'] for s in selos().values())
    perfil['paradas_progresso']={'boss':{'concluida_em':'agora','erros':0,'acertos':11},'b1':{'concluida_em':'agora','tentativas':3,'erros':10}}
    s=selos()
    assert all(s[k]['desbloqueada'] for k in ['castelo','teimoso','preciso','atrapalhado'])
    assert all(not s[k]['rastreavel'] and not s[k]['desbloqueada'] for k in ['invicto','primeira','falador'])

def test_boss_id_real_e_sem_localstorage(ctx):
    _,f=ctx;c,t=f()
    A._PERFIS_TESTE['teste:teste']['paradas_progresso']={A.id_parada(1,40):{'concluida_em':'agora','erros':0,'acertos':11}}
    assert 'data-conquista="castelo"' in c.get('/heroi').text
    s=avaliar_conquistas(A._PERFIS_TESTE['teste:teste'],[],A.id_parada(1,40))
    assert s[0]['desbloqueada']

def test_progresso_malformado():
    for prog in [[],{'a':None},{'a':{'concluida_em':'x','erros':'10','acertos':True}}]:
        assert not any(s['desbloqueada'] for s in avaliar_conquistas({'paradas_progresso':prog},[],None))

def abastecer(fake):
    fake.alterar('real',cosmeticos=estado_cosmetico(None,True))

def test_persistencia_real_campos_login(ctx):
    fake,f=ctx;abastecer(fake);c,t=f(False)
    assert post(c,t,item='pet-dragao').status_code==200
    doc=fake.docs['real']
    assert doc['cosmeticos']['cristais']==600 and doc['xp']==135
    assert doc['senha_hash']=='preservar' and doc['nonce']=='preservar'
    assert fake.calls['replace_item']>=1

def test_retry_etag_preserva_progresso(ctx):
    fake,_=ctx;abastecer(fake)
    def concorrente(uid,body):
        fake.before_replace=None;fake.alterar(uid,xp=270,paradas_progresso={'novo':{'acertos':1}})
    fake.before_replace=concorrente
    estado=ContasCosmos(lambda:fake).alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-lobo'))
    assert estado['cristais']==600 and fake.docs['real']['xp']==270
    assert 'novo' in fake.docs['real']['paradas_progresso']

def test_compra_concorrente_mesmo_item(ctx):
    fake,_=ctx;abastecer(fake);contas=ContasCosmos(lambda:fake)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda _:contas.alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-lobo')),range(12)))
    assert fake.docs['real']['cosmeticos']['cristais']==600
    assert fake.docs['real']['cosmeticos']['comprados']==['pet-lobo']

def test_compra_concorrente_nao_negativa(ctx):
    fake,_=ctx;abastecer(fake);contas=ContasCosmos(lambda:fake)
    def compra(iid):
        try:contas.alterar_cosmeticos('real',lambda v:operar(v,'comprar',iid));return True
        except OperacaoCosmeticaInvalida:return False
    with ThreadPoolExecutor(5) as ex:result=list(ex.map(compra,['pet-lobo','pet-raposa','pet-dragao','pet-tigre','pet-corvo']))
    assert sum(result)==2 and fake.docs['real']['cosmeticos']['cristais']==200

@pytest.mark.parametrize('legado',[False,True])
def test_snapshot_velho_nao_desfaz_compra(ctx,legado):
    fake,_=ctx;abastecer(fake)
    if legado:fake.alterar('real',tipo='perfil')
    contas=ContasCosmos(lambda:fake);velho=contas.read_item('real')
    contas.alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-lobo'))
    velho['xp']=405;contas.upsert_item(velho)
    assert fake.docs['real']['xp']==405
    assert fake.docs['real']['cosmeticos']['cristais']==600

def test_snapshot_teste_nao_desfaz_compra(ctx):
    _,f=ctx;c,t=f();old=A._UsuariosTeste().read_item('teste:teste')
    post(c,t,item='pet-dragao');A._UsuariosTeste().upsert_item(old)
    assert A._PERFIS_TESTE['teste:teste']['cosmeticos']['cristais']==600

def test_indisponibilidade_sem_debito(ctx):
    fake,f=ctx;abastecer(fake);c,t=f(False);fake.down=True
    assert post(c,t,item='pet-dragao').status_code==503
    fake.down=False
    assert fake.docs['real']['cosmeticos']['cristais']==1000

def test_conflitos_esgotados(ctx):
    fake,_=ctx;abastecer(fake)
    def conflito(uid,body):raise erro(412)
    fake.before_replace=conflito
    with pytest.raises(ContasIndisponiveis):ContasCosmos(lambda:fake).alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-lobo'))
    assert fake.docs['real']['cosmeticos']['cristais']==1000

@pytest.mark.parametrize('corrupto',[{},[],{'versao':1,'cristais':True},{'versao':1,'cristais':-1}])
def test_estado_corrompido_nao_recredita(corrupto):
    with pytest.raises(ContasIndisponiveis):estado_cosmetico(corrupto,True)

def test_csrf_unicode_nao_causa_500(ctx):
    _,f=ctx;c,t=f()
    assert post(c,'❄',item='pet-dragao').status_code==403

def test_post_anonimo(ctx):
    assert A.app.test_client().post('/loja/comprar',json={'item':'pet-dragao'}).status_code==401

def test_item_de_outro_usuario_nao_vaza(ctx):
    fake,f=ctx;abastecer(fake);c,t=f(False)
    post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    outro,token=f(True)
    assert post(outro,token,'/loja/equipar',item='pet-dragao').status_code==403
    assert 'loja/pets/dragao.png' not in outro.get('/heroi').text

def test_resposta_perdida_retry_nao_cobra_duas_vezes(ctx,monkeypatch):
    fake,_=ctx;abastecer(fake);contas=ContasCosmos(lambda:fake)
    original=fake.replace_item
    def perder(**kwargs):
        original(**kwargs)
        raise erro(503)
    monkeypatch.setattr(fake,'replace_item',perder)
    with pytest.raises(ContasIndisponiveis):
        contas.alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-dragao'))
    monkeypatch.setattr(fake,'replace_item',original)
    estado=contas.alterar_cosmeticos('real',lambda v:operar(v,'comprar','pet-dragao'))
    assert estado['cristais']==600 and len(estado['comprados'])==1

def test_teimoso_apenas_batalha(ctx):
    p={'paradas_progresso':{'missao':{'concluida_em':'a','tentativas':20}}}
    assert not next(s for s in avaliar_conquistas(p,['batalha'],'boss') if s['id']=='teimoso')['desbloqueada']

def test_sem_erros_precisa_acertos(ctx):
    p={'paradas_progresso':{'x':{'concluida_em':'a','acertos':0,'erros':0}}}
    assert not next(s for s in avaliar_conquistas(p,[],'boss') if s['id']=='preciso')['desbloqueada']

def test_snapshot_credenciais_sem_cosmetico_forjado(ctx):
    fake,_=ctx;contas=ContasCosmos(lambda:fake)
    doc=contas.read_item('real');doc['cosmeticos']=estado_cosmetico(None,True)
    contas.upsert_item(doc)
    assert 'cosmeticos' not in fake.docs['real']
