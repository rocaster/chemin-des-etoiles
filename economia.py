"""Cristais no servidor, sem alterar motores, XP ou endpoint de conclusão.

Ledger por ID de conteúdo, na mesma operação ETag que o saldo. O hook só
reage à conclusão aceita pelo endpoint original. Reconciliar no menu recupera
créditos se houver falha entre salvar progresso e gravar o ledger, e reconhece
progresso legado uma única vez. Repetições não geram novos créditos de etapa.
"""
from copy import deepcopy
import json
from pathlib import Path
from flask import request, session
from contas_cosmos import ContasIndisponiveis

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'data/economia.json').read_text(encoding='utf-8'))
ORDEM=json.loads((ROOT/'data/regioes/r1.json').read_text(encoding='utf-8'))
ETAPAS={}
for n,pid in enumerate(ORDEM['ordem'],1):
    dado=json.loads((ROOT/'data/paradas'/f'{pid}.json').read_text(encoding='utf-8'))
    ETAPAS[pid]={'n':n,'formato':dado.get('formato','missao')}
AREAS=[{ORDEM['ordem'][n-1] for n in range(a['etapas'][0],a['etapas'][1]+1)} for a in ORDEM['regioes']]
BOSS=ORDEM['ordem'][39]


def creditar_estado(valor,eventos,teste=False):
    from loja import estado_cosmetico
    estado=estado_cosmetico(valor,teste)
    etapas=deepcopy(estado.get('etapas_creditadas',{}))
    bonus=deepcopy(estado.get('bonus_creditados',{}))
    if (not isinstance(etapas,dict) or not isinstance(bonus,dict)
            or any(type(v) is not int or v<0 for v in [*etapas.values(),*bonus.values()])):
        raise ContasIndisponiveis()
    ganhou=0
    for evento in eventos:
        pid=evento.get('id')
        if pid not in ETAPAS:
            continue
        if pid not in etapas:
            valor=CONFIG['cristais_por_formato'][ETAPAS[pid]['formato']]
            etapas[pid]=valor;ganhou+=valor
        if (evento.get('sem_erros') is True and 'nao-erra-uma' not in bonus):
            bonus['nao-erra-uma']=CONFIG['bonus_sem_erros'];ganhou+=CONFIG['bonus_sem_erros']
    def marco(id,condicao,valor):
        nonlocal ganhou
        if condicao and id not in bonus:
            bonus[id]=valor;ganhou+=valor
    conhecidos=set(etapas)&set(ETAPAS)
    for i,area in enumerate(AREAS,1):marco(f'area-{i}',area<=conhecidos,CONFIG['bonus_area'])
    marco('chevalier-noir',BOSS in conhecidos,CONFIG['bonus_boss'])
    marco('mapa-1',set(ETAPAS)<=conhecidos,CONFIG['bonus_mapa'])
    # Não materializa um estado vazio numa simples visita à loja.
    if not eventos and not etapas and not bonus:
        return estado
    estado.update(etapas_creditadas=etapas,bonus_creditados=bonus)
    estado['cristais']+=ganhou
    return estado


def creditar(contexto,eventos):
    from loja import estado_cosmetico
    teste=contexto['modo_teste']()
    uid=contexto['id_teste']() if teste else session.get('uid')
    metadados={'ganhos':0}
    def transformar(valor):
        antes=estado_cosmetico(valor,teste)
        depois=creditar_estado(valor,eventos,teste)
        metadados['ganhos']=depois['cristais']-antes['cristais']
        return depois
    estado=contexto['usuarios']().alterar_cosmeticos(uid,transformar)
    return estado,metadados['ganhos']


def eventos_perfil(perfil):
    progresso=perfil.get('paradas_progresso',{})
    if not isinstance(progresso,dict):return []
    eventos=[]
    for pid,reg in progresso.items():
        if pid not in ETAPAS or not isinstance(reg,dict) or not reg.get('concluida_em'):continue
        preciso=(type(reg.get('acertos')) is int and reg['acertos']>0 and type(reg.get('erros')) is int and reg['erros']==0)
        eventos.append({'id':pid,'sem_erros':preciso})
    return eventos


def reconciliar_perfil(contexto,perfil):
    eventos=eventos_perfil(perfil)
    if not eventos:return
    try:
        estado,_=creditar(contexto,eventos)
        perfil['cosmeticos']=estado
    except (ContasIndisponiveis,KeyError):
        # Progresso já salvo não se perde. Outra visita/conclusão tenta novamente.
        pass


def registrar_economia(app,contexto):
    @app.after_request
    def cristais_apos_conclusao(resposta):
        if (request.endpoint!='parada_concluir' or request.method!='POST'
                or resposta.status_code!=200 or not resposta.is_json):return resposta
        corpo=resposta.get_json(silent=True)
        if not isinstance(corpo,dict) or corpo.get('ok') is not True:return resposta
        args=request.view_args or {}
        if args.get('regiao')!=1:return resposta  # Este balanceamento é só o mapa 1.
        pid=contexto['id_parada'](1,args.get('n',0))
        if pid not in ETAPAS:return resposta
        entrada=request.get_json(silent=True) or {}
        evento={'id':pid,'sem_erros':type(entrada.get('acertos')) is int and entrada['acertos']>0 and entrada.get('erros')==0}
        try:
            estado,ganhos=creditar(contexto,[evento])
            corpo.update(cristais_ganhos=ganhos,cristais_total=estado['cristais'],cristais_pendentes=False)
        except (ContasIndisponiveis,KeyError):
            corpo.update(cristais_ganhos=0,cristais_pendentes=True)
        resposta.set_data(app.json.dumps(corpo))
        return resposta
