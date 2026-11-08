"""Espadas/cenário/pets e economia v2. Todas as contas são fake/offline."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image,ImageChops
from test_loja import ctx, post, abastecer, A, ROOT, CosmosFake, erro, ContasCosmos, ContasIndisponiveis
from loja import operar,estado_cosmetico
from economia import ETAPAS,AREAS,CONFIG,BOSS,creditar_estado


def creditos(fake,eventos):
    return ContasCosmos(lambda:fake).alterar_cosmeticos('real',lambda v:creditar_estado(v,eventos))

def evento(n,preciso=False):
    return {'id':A.id_parada(1,n),'sem_erros':preciso}

@pytest.mark.parametrize('n',[1,2,4,6,9,10])
def test_valores_por_formato(n):
    e=evento(n);s=creditar_estado(None,[e])
    assert s['cristais']==CONFIG['cristais_por_formato'][ETAPAS[e['id']]['formato']]
    assert s['etapas_creditadas']=={e['id']:s['cristais']}

def test_repeticao_idempotente():
    e=evento(1);s=creditar_estado(None,[e,e,e]);saldo=s['cristais']
    for _ in range(8):s=creditar_estado(s,[e])
    assert s['cristais']==saldo==18 and len(s['etapas_creditadas'])==1

def test_conquista_precisao_so_uma_vez():
    s=creditar_estado(None,[evento(1)])
    s=creditar_estado(s,[evento(1,True)])
    assert s['cristais']==38
    s=creditar_estado(s,[evento(1,True),evento(2,True)])
    assert s['cristais']==58 and s['bonus_creditados']['nao-erra-uma']==20

def test_tres_areas_exigem_todas_as_etapas():
    for area in AREAS:
        ids=sorted(area);s=creditar_estado(None,[{'id':pid} for pid in ids[:-1]])
        alvo='area-'+str(AREAS.index(area)+1)
        assert alvo not in s['bonus_creditados']
        antes=s['cristais'];s=creditar_estado(s,[{'id':ids[-1]}])
        assert s['bonus_creditados'][alvo]==75 and s['cristais']>=antes+75

def test_boss_sem_recompensar_mapa_incompleto():
    s=creditar_estado(None,[evento(40)])
    assert s['cristais']==162
    assert s['bonus_creditados']=={'chevalier-noir':150}
    assert creditar_estado(s,[evento(40)])==s

def test_mapa_completo_1220_e_nao_mais():
    ev=[evento(n,True) for n in range(1,41)]
    s=creditar_estado(None,ev)
    assert s['cristais']==1220 and len(s['etapas_creditadas'])==40
    assert sum(s['etapas_creditadas'].values())==650
    assert creditar_estado(s,ev)==s

def test_evento_desconhecido_nao_paga():
    s=creditar_estado(None,[{'id':'r9-p99','sem_erros':True}])
    assert s['cristais']==0 and not s.get('etapas_creditadas')

def test_conta_teste_pode_ganhar_mas_separada():
    s=creditar_estado(None,[evento(1,True)],True)
    assert s['cristais']==1038

def test_hook_endpoint_primeira_repeticao(ctx):
    fake,f=ctx;c,t=f(False)
    body={'acertos':10,'erros':0,'duracao_s':100,'fala_pendente':False}
    primeira=c.post('/parada/1/1/concluir',json=body)
    assert primeira.status_code==200 and primeira.json['cristais_ganhos']==38
    assert primeira.json['cristais_total']==38 and not primeira.json['cristais_pendentes']
    xp=fake.docs['real']['xp']
    repetida=c.post('/parada/1/1/concluir',json=body)
    assert repetida.json['cristais_ganhos']==0 and repetida.json['cristais_total']==38
    assert fake.docs['real']['xp']==xp

def test_erros_validacao_nao_geram_cristais(ctx):
    fake,f=ctx;c,t=f(False)
    assert c.post('/parada/1/1/concluir',json={'acertos':-1}).status_code==400
    assert 'cosmeticos' not in fake.docs['real']
    assert c.post('/parada/1/99/concluir',json={}).status_code==404
    assert 'cosmeticos' not in fake.docs['real']

def test_parada_e_simulado_get_nao_pagando(ctx):
    fake,f=ctx;c,t=f(False)
    for path in ['/parada/1/1','/simulados/tef','/mapa']:
        assert c.get(path).status_code==200
    assert 'cosmeticos' not in fake.docs['real']

def test_economia_nao_altera_campos_de_xp_ou_login(ctx):
    fake,_=ctx;original=copy.deepcopy(fake.docs['real'])
    creditos(fake,[evento(1,True)])
    for k,v in original.items():
        if not k.startswith('_'):assert fake.docs['real'][k]==v

def test_credito_concorrente_mesma_etapa(ctx):
    fake,_=ctx
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda _:creditos(fake,[evento(1,True)]),range(20)))
    s=fake.docs['real']['cosmeticos']
    assert s['cristais']==38 and len(s['etapas_creditadas'])==1

def test_creditos_concorrentes_mapa_completo(ctx):
    fake,_=ctx
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda n:creditos(fake,[evento(n,True)]),range(1,41)))
    s=fake.docs['real']['cosmeticos']
    assert s['cristais']==1220 and len(s['etapas_creditadas'])==40

def test_compra_e_ganho_concorrentes(ctx):
    fake,_=ctx;abastecer(fake);contas=ContasCosmos(lambda:fake)
    with ThreadPoolExecutor(2) as ex:
        futures=[ex.submit(creditos,fake,[evento(1,True)]),ex.submit(contas.alterar_cosmeticos,'real',lambda s:operar(s,'comprar','pet-dragao'))]
        for future in futures:future.result()
    s=fake.docs['real']['cosmeticos']
    assert s['cristais']==638 and s['comprados']==['pet-dragao']
    assert A.id_parada(1,1) in s['etapas_creditadas']

def test_retry_etag_preserva_compra(ctx):
    fake,_=ctx;abastecer(fake)
    def antes(uid,body):
        fake.before_replace=None
        atual=fake.docs[uid]['cosmeticos'];fake.alterar(uid,cosmeticos=operar(atual,'comprar','pet-dragao'))
    fake.before_replace=antes
    s=creditos(fake,[evento(1,True)])
    assert s['cristais']==638 and s['comprados']==['pet-dragao']

def test_falha_apos_progresso_reconciliada_no_menu(ctx):
    fake,f=ctx;c,t=f(False)
    def antes(uid,body):
        if 'cosmeticos' in body:
            fake.before_replace=None
            raise erro(503)
    fake.before_replace=antes
    r=c.post('/parada/1/1/concluir',json={'acertos':10,'erros':0,'duracao_s':100,'fala_pendente':False})
    assert r.status_code==200 and r.json['cristais_pendentes']
    assert 'paradas_progresso' in fake.docs['real'] and 'cosmeticos' not in fake.docs['real']
    assert c.get('/heroi').status_code==200
    assert fake.docs['real']['cosmeticos']['cristais']==38
    c.get('/heroi');assert fake.docs['real']['cosmeticos']['cristais']==38

def test_resposta_perdida_credito_nao_duplica(ctx,monkeypatch):
    fake,_=ctx;original=fake.replace_item
    def perder(**kwargs):original(**kwargs);raise erro(503)
    monkeypatch.setattr(fake,'replace_item',perder)
    with pytest.raises(ContasIndisponiveis):creditos(fake,[evento(1,True)])
    monkeypatch.setattr(fake,'replace_item',original)
    assert creditos(fake,[evento(1,True)])['cristais']==38

def test_legado_retroativo_uma_unica_vez(ctx):
    fake,f=ctx
    fake.alterar('real',paradas_progresso={A.id_parada(1,1):{'concluida_em':'ontem','acertos':3,'erros':1}})
    c,t=f(False)
    assert fake.docs['real']['cosmeticos']['cristais']==18
    c.get('/loja');c.get('/heroi')
    assert fake.docs['real']['cosmeticos']['cristais']==18

def test_ledger_corrompido_nao_reseta_saldo():
    s=estado_cosmetico(None);s['etapas_creditadas']=[]
    with pytest.raises(ContasIndisponiveis):creditar_estado(s,[evento(1)])

@pytest.mark.parametrize('avatar',sorted(A.AVATAR_IDS))
def test_hero_e_shop_usam_fontes_corretas_todas_as_paletas(ctx,avatar):
    _,f=ctx;c,t=f();A._PERFIS_TESTE['teste:teste']['avatar']=avatar
    html=c.get('/heroi').text
    from herois import sheet_heroi
    assert sheet_heroi(avatar) in html
    assert 'data-quadros="8"' in html
    assert 'class="moldura"' not in html and 'frames/moldura-' not in html
    assert 'diorama' in html and 'almofada.png' in html
    shop=c.get('/loja').text
    for paleta in ['esmeralda','ametista','rubi']:
        path=sheet_heroi(avatar,paleta);assert path in shop
        assert c.get('/static/'+path).status_code==200
        s=estado_cosmetico(None,True);s['comprados']=['paleta-'+paleta];s['equipados']={'personagem':'paleta-'+paleta}
        A._PERFIS_TESTE['teste:teste']['cosmeticos']=s
        assert path in c.get('/heroi').text

def test_diorma_so_no_heroi_e_mapa_mantem_molduras(ctx):
    _,f=ctx;c,t=f()
    assert 'heroi-v2.css' in c.get('/heroi').text
    assert 'heroi-v2.css' not in c.get('/loja').text
    mapa=c.get('/mapa').text
    assert 'ficha-borda' in mapa and 'bordas/borda-' in mapa
    assert 'herois/espada' not in c.get('/personagem').text

def test_idle_reduced_motion():
    css=(ROOT/'static/loja/heroi-v2.css').read_text(encoding='utf-8')
    assert all(x in css for x in ['prefers-reduced-motion','sprite-oito','background-position:0 0!important'])
    assert 'animation:none!important' in css

def test_8_assets_so_cavaleiro_sem_trocar_porte_ou_postura():
    folder=ROOT/'static/loja/herois/espada'
    assert len(list(folder.glob('*.png')))==8
    for avatar in ['cavaleiro-m']:
        original=Image.open(ROOT/f'static/fogueira/sprite-{avatar}-aberto.png')
        for sufixo in ['','-esmeralda','-ametista','-rubi']:
            aberto=Image.open(folder/f'{avatar}{sufixo}.png').convert('RGBA')
            fechado=Image.open(folder/f'{avatar}{sufixo}-fechado.png').convert('RGBA')
            assert aberto.size==original.size==fechado.size
            diff=ImageChops.difference(aberto,fechado).convert('RGB').getbbox()
            assert diff and diff[3]<aberto.height*.45  # só rosto, não roupa/corpo/arma
            # Reprodução na grade nativa 4 px, sem suavização/interpolação.
            up=aberto.resize((aberto.width//4,aberto.height//4),Image.Resampling.NEAREST).resize(aberto.size,Image.Resampling.NEAREST)
            assert ImageChops.difference(aberto,up).convert('RGB').getbbox() is None

def test_pets_silhuetas_e_animacoes_distintas():
    masks=[]
    for p in (ROOT/'static/loja/pets').glob('*.png'):
        im=Image.open(p).convert('RGBA');assert im.size==(384,48)
        frames=[im.crop((n*48,0,(n+1)*48,48)) for n in range(8)]
        masks.append(hashlib.sha256(frames[0].getchannel('A').tobytes()).hexdigest())
        assert len({f.tobytes() for f in frames})==8
    assert len(masks)==len(set(masks))==10

def test_pet_e_espada_juntos(ctx):
    _,f=ctx;c,t=f();post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    html=c.get('/heroi').text
    assert 'pet-idle' in html and 'heroi-idle' in html and 'pet-vazio' not in html
    assert 'loja/herois/poses-v5/cavaleiro-f.png' in html
    assert 'loja/herois/espada/' not in html

def test_duas_conclusoes_http_concorrentes_ledger_sem_perda(ctx):
    fake,f=ctx
    c1,t1=f(False);c2,t2=f(False)
    body={'acertos':5,'erros':0,'duracao_s':100,'fala_pendente':False}
    with ThreadPoolExecutor(2) as ex:
        futures=[ex.submit(c.post,f'/parada/1/{n}/concluir',json=body) for c,n in [(c1,1),(c2,2)]]
        respostas=[f.result() for f in futures]
    assert all(r.status_code==200 for r in respostas)
    s=fake.docs['real']['cosmeticos']
    assert s['cristais']==58 and len(s['etapas_creditadas'])==2

def test_recompensa_cliente_ignorada(ctx):
    fake,f=ctx;c,t=f(False)
    r=c.post('/parada/1/1/concluir',json={'acertos':5,'erros':1,'duracao_s':100,'fala_pendente':False,'cristais':999999,'cristais_ganhos':999999})
    assert r.json['cristais_ganhos']==18 and r.json['cristais_total']==18
