"""Meta1.200 garantida; precisão+20, sem retroativo ou novo crédito em replay."""
import copy,json
from unittest.mock import patch
import pytest
from test_loja import ctx,A,post,ROOT
import economia

EVENTOS=[{'id':pid,'sem_erros':False} for pid in economia.ORDEM['ordem']]

@pytest.mark.parametrize('precisao',[False,True])
def test_mapa_novo_credita1200_ou1220_uma_vez(precisao):
    eventos=[dict(e,sem_erros=precisao) for e in EVENTOS]
    s=economia.creditar_estado(None,eventos)
    assert s['cristais']==1200+20*precisao
    assert sum(s['etapas_creditadas'].values())==650
    assert [s['bonus_creditados'][f'area-{i}'] for i in range(1,4)]==[75]*3
    assert s['bonus_creditados']['chevalier-noir']==150 and s['bonus_creditados']['mapa-1']==175
    assert economia.creditar_estado(s,eventos)==s

@pytest.mark.parametrize('precisao',[False,True])
def test_ledger_antigo_nao_recebe_diferenca_retroativa(precisao):
    antigo=dict(economia.CONFIG,bonus_area=50,bonus_boss=100,bonus_mapa=100)
    eventos=[dict(e,sem_erros=precisao) for e in EVENTOS]
    with patch.object(economia,'CONFIG',antigo):s=economia.creditar_estado(None,eventos)
    antes=copy.deepcopy(s)
    assert s['cristais']==1000+20*precisao
    assert economia.creditar_estado(s,eventos)==antes
    assert economia.creditar_estado(s,[])==antes

@pytest.mark.parametrize('teste',[True,False])
def test_mapa_sem_precisao_compra_um_de_cada_categoria_sem_saldo_demo(ctx,teste):
    fake,f=ctx;c,t=f(teste)
    if teste:A._PERFIS_TESTE['teste:teste']['cosmeticos']={'versao':1,'cristais':0,'comprados':[],'equipados':{}}
    respostas=[c.post(f'/parada/1/{n}/concluir',json={'acertos':5,'erros':1,'fala_pendente':False,'duracao_s':120}).json for n in range(1,41)]
    assert sum(j['cristais_ganhos'] for j in respostas)==1200
    assert respostas[-1]['cristais_total']==1200
    for iid in ['pet-dragao','efeito-inverno','paleta-rubi','titulo-voz','cenario-floresta']:
        assert post(c,t,item=iid).status_code==200
        assert post(c,t,'/loja/equipar',item=iid).status_code==200
    perfil=A._PERFIS_TESTE['teste:teste'] if teste else fake.docs['real']
    assert perfil['cosmeticos']['cristais']==10
    assert all(c.post(f'/parada/1/{n}/concluir',json={'acertos':5,'erros':1,'fala_pendente':False,'duracao_s':120}).json['cristais_ganhos']==0 for n in range(1,41))
