"""XP v6: só primeira conclusão, progresso + XP atômicos com ETag.
Fonte servidor; não importa totais/XP/localStorage recebidos do navegador.
"""
from copy import deepcopy
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'data/xp.json').read_text(encoding='utf-8'))

def valor_xp(dados):
    rec=dados.get('recompensa') or {}
    if rec.get('xp_pausado'):return 0
    v=rec.get('xp_base',CONFIG['primeira_conclusao'].get(dados.get('formato','missao'),0))
    return v if type(v) is int and v>=0 else 0

ORDEM=json.loads((ROOT/'data/regioes/r1.json').read_text(encoding='utf-8'))['ordem']
XP_POR_ID={pid:valor_xp(json.loads((ROOT/'data/paradas'/f'{pid}.json').read_text(encoding='utf-8'))) for pid in ORDEM}

def numero(n):return n if type(n) is int and n>=0 else 0

def normalizar(perfil):
    doc=deepcopy(perfil);progresso=doc.get('paradas_progresso')
    if not isinstance(progresso,dict):progresso={}
    concluidos={pid:r for pid,r in progresso.items() if pid in XP_POR_ID and isinstance(r,dict) and r.get('concluida_em')}
    mapa=sum(XP_POR_ID[pid] for pid in concluidos)
    antigo=sum(numero(r.get('xp')) for r in concluidos.values())
    total=numero(doc.get('xp'))
    if doc.get('xp_regras_versao')==6:
        extra=max(0,total-numero(doc.get('xp_mapa_contabilizado')))
    else:
        # Não reduz XP legítimo já salvo no servidor, nem elimina XP externo.
        extra=max(0,total-antigo,total-mapa)
    for pid,r in concluidos.items():
        if r.get('xp_versao')!=6:r['xp_antes_v6']=numero(r.get('xp'))
        r.update(xp=XP_POR_ID[pid],xp_versao=6)
    doc.update(paradas_progresso=progresso,xp=extra+mapa,xp_mapa_contabilizado=mapa,xp_externo_legado=extra,xp_regras_versao=6)
    return doc

def reconciliar(contexto,perfil):
    progresso=(perfil or {}).get('paradas_progresso')
    if not isinstance(progresso,dict) or not any(isinstance(r,dict) and r.get('concluida_em') and pid in XP_POR_ID for pid,r in progresso.items()):return perfil
    if normalizar(perfil)==perfil:return perfil
    atualizado=contexto['usuarios']().alterar_perfil(perfil['id'],normalizar)
    perfil.clear();perfil.update(atualizado)
    return perfil

def concluir(perfil,pid,dados,entrada,agora,estrelas,borda_por_xp,bordas):
    doc=normalizar(perfil);antes=doc['xp'];progresso=doc['paradas_progresso']
    anterior=progresso.get(pid);anterior=anterior if isinstance(anterior,dict) else {}
    primeira=not bool(anterior.get('concluida_em'));xp=valor_xp(dados)
    ja_falou=bool(anterior) and anterior.get('fala_pendente') is False
    progresso[pid]={
        'concluida_em':agora,'primeira_conclusao_em':anterior.get('primeira_conclusao_em',agora),
        'acertos':entrada['acertos'],'erros':entrada['erros'],'fala_pendente':entrada['fala_pendente'] and not ja_falou,
        'estrelas':estrelas,'melhor_estrelas':max(estrelas,numero(anterior.get('melhor_estrelas'))),
        'xp':xp,'xp_versao':6,'duracao_s':entrada['duracao_s'],'tentativas':numero(anterior.get('tentativas'))+1}
    if 'xp_antes_v6' in anterior:progresso[pid]['xp_antes_v6']=anterior['xp_antes_v6']
    ganho=xp if primeira else 0
    doc['xp']=antes+ganho;doc['xp_mapa_contabilizado']=sum(XP_POR_ID[p] for p,r in progresso.items() if p in XP_POR_ID and isinstance(r,dict) and r.get('concluida_em'))
    borda=borda_por_xp(doc['xp']);doc['borda_mapa']=bordas[borda]['id']
    return doc,dict(xp=ganho,xp_ganho=ganho,xp_creditado_etapa=xp,xp_total=doc['xp'],xp_versao=6,estrelas=estrelas,borda=doc['borda_mapa'],borda_nova=borda>borda_por_xp(antes))
