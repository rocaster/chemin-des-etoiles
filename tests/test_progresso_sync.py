"""Hotfix: progresso do mapa sincronizado com o servidor (trocar de navegador nao perde as paradas feitas).
Offline: CosmosFake, sem .env/rede. O trecho real do mapa.html que calcula a etapa atual roda no Node
com um localStorage vazio (navegador novo) ou pre-preenchido."""
import json
import re
import shutil
import subprocess
import pytest
from test_loja import A, ctx  # noqa: F401  (fixture)
from xp import ORDEM

NODE = shutil.which('node')
CONCLUIDA = {'concluida_em': '2026-11-01T10:00:00+00:00', 'acertos': 5, 'erros': 0, 'fala_pendente': False,
             'estrelas': 3, 'melhor_estrelas': 3, 'xp': 15, 'xp_versao': 6, 'duracao_s': 90, 'tentativas': 1}


def progresso(n):
    """As n primeiras etapas da trilha concluidas (pelo id de conteudo)."""
    return {pid: dict(CONCLUIDA) for pid in ORDEM[:n]}


def dados_servidor(html):
    m = re.search(r'const PROGRESSO_SERVIDOR = (.*?);\n', html)
    assert m, 'mapa.html precisa receber PROGRESSO_SERVIDOR'
    return json.loads(m.group(1))


def rodar_mapa(html, local=None):
    """Roda o inicio do script do mapa (ate a etapa atual) no Node; devolve (atual, localStorage)."""
    if not NODE:
        pytest.skip('node indisponivel')
    js = html[html.index('const TOTAL = '):html.index('let paradas = [];')]
    stub = """
const _ls = new Map(Object.entries(%s));
globalThis.localStorage = { getItem: k => _ls.has(k) ? _ls.get(k) : null, setItem: (k, v) => _ls.set(k, String(v)),
  removeItem: k => _ls.delete(k) };
globalThis.location = { search: "" };
globalThis.matchMedia = () => ({ matches: false });
globalThis.document = { documentElement: { classList: { add() {} } }, body: {}, getElementById: () => ({}) };
""" % json.dumps(local or {})
    fim = '\nconsole.log(JSON.stringify({ atual, ls: Object.fromEntries(_ls) }));'
    r = subprocess.run([NODE, '-e', stub + '(() => {\n' + js + fim + '\n})();'], capture_output=True,
                       text=True, encoding='utf-8', timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    return out['atual'], out['ls']


def cliente_real(fake, prog):
    fake.alterar('real', paradas_progresso=prog)
    c = A.app.test_client()
    with c.session_transaction() as s:
        s['uid'] = 'real'
    return c


def cliente_teste(prog):
    A._PERFIS_TESTE['teste:teste'] = {'id': 'teste:teste', 'teste': True, 'avatar': 'cavaleiro-f', 'xp': 135,
                                      'nome_personagem': 'Luna', 'paradas_progresso': prog}
    c = A.app.test_client()
    with c.session_transaction() as s:
        s['teste'] = 'teste'
    return c


def test_template_recebe_progresso_do_servidor(ctx):
    fake, _ = ctx
    html = cliente_real(fake, progresso(5)).get('/mapa').get_data(as_text=True)
    dados = dados_servidor(html)
    assert set(dados) == set(ORDEM[:5])
    for reg in dados.values():
        assert reg['concluida_em'] and reg['xp_confirmado'] is True and reg['estrelas'] == 3
    assert '"chemin_"' in html


def test_so_paradas_concluidas_e_conhecidas_vao_para_a_pagina(ctx):
    fake, _ = ctx
    prog = progresso(2)
    prog[ORDEM[2]] = {'acertos': 1}                       # sem concluida_em: nao conta
    prog['r9-p99'] = dict(CONCLUIDA)                      # id fora da trilha
    prog[ORDEM[3]] = 'lixo'
    html = cliente_real(fake, prog).get('/mapa').get_data(as_text=True)
    assert set(dados_servidor(html)) == set(ORDEM[:2])


def test_navegador_novo_mostra_etapa_atual_do_servidor(ctx):
    fake, _ = ctx
    html = cliente_real(fake, progresso(7)).get('/mapa').get_data(as_text=True)
    atual, ls = rodar_mapa(html, {})
    assert atual == 8
    assert ls['chemin_mapa_r1_atual'] == '8'
    assert set(json.loads(ls['chemin_paradas'])) == set(ORDEM[:7])
    assert not any(k.startswith('chemin_teste_') for k in ls)


def test_uniao_com_progresso_local(ctx):
    """Servidor tem 1..3, este navegador tem 1..5 (ainda nao enviado): nada se perde."""
    fake, _ = ctx
    html = cliente_real(fake, progresso(3)).get('/mapa').get_data(as_text=True)
    local = {'chemin_paradas': json.dumps(progresso(5)), 'chemin_mapa_r1_atual': '6', 'chemin_mapa_r1_versao': '3'}
    atual, ls = rodar_mapa(html, local)
    assert atual == 6
    assert set(json.loads(ls['chemin_paradas'])) == set(ORDEM[:5])


def test_servidor_completa_o_que_falta_no_local(ctx):
    fake, _ = ctx
    html = cliente_real(fake, progresso(6)).get('/mapa').get_data(as_text=True)
    local = {'chemin_paradas': json.dumps(progresso(2)), 'chemin_mapa_r1_atual': '3', 'chemin_mapa_r1_versao': '3'}
    atual, ls = rodar_mapa(html, local)
    assert atual == 7
    assert set(json.loads(ls['chemin_paradas'])) == set(ORDEM[:6])


def test_sem_progresso_no_servidor_mantem_comportamento(ctx):
    fake, _ = ctx
    html = cliente_real(fake, {}).get('/mapa').get_data(as_text=True)
    assert dados_servidor(html) == {}
    assert rodar_mapa(html, {})[0] == 1


def test_modo_teste_usa_prefixo_de_teste(ctx):
    cliente = cliente_teste(progresso(4))
    html = cliente.get('/mapa').get_data(as_text=True)
    assert set(dados_servidor(html)) == set(ORDEM[:4])
    atual, ls = rodar_mapa(html, {'chemin_paradas': json.dumps(progresso(1))})
    assert atual == 5
    assert set(json.loads(ls['chemin_teste_paradas'])) == set(ORDEM[:4])
    assert set(json.loads(ls['chemin_paradas'])) == set(ORDEM[:1])   # progresso real intocado


def test_perfil_indisponivel_cai_no_localstorage(ctx, monkeypatch):
    fake, _ = ctx
    c = cliente_real(fake, progresso(7))
    monkeypatch.setattr(A, 'perfil_do_mapa', lambda: None)
    html = c.get('/mapa').get_data(as_text=True)
    assert dados_servidor(html) is None
    assert re.search(r'let xpServidor = null;', html)
    assert rodar_mapa(html, {})[0] == 1
    local = {'chemin_paradas': json.dumps(progresso(3)), 'chemin_mapa_r1_atual': '4', 'chemin_mapa_r1_versao': '3'}
    atual, ls = rodar_mapa(html, local)
    assert atual == 4 and set(json.loads(ls['chemin_paradas'])) == set(ORDEM[:3])


def test_funcao_progresso_do_perfil():
    assert A.progresso_do_perfil(None) == {}
    assert A.progresso_do_perfil({'paradas_progresso': []}) == {}
    p = A.progresso_do_perfil({'paradas_progresso': {ORDEM[0]: dict(CONCLUIDA, segredo='x')}})
    assert 'segredo' not in p[ORDEM[0]] and p[ORDEM[0]]['xp_confirmado'] is True


def test_renderizar_mapa_nao_altera_o_progresso(ctx):
    fake, _ = ctx
    c = cliente_real(fake, progresso(3))
    antes = json.dumps(fake.docs['real']['paradas_progresso'], sort_keys=True)
    c.get('/mapa')
    assert set(fake.docs['real']['paradas_progresso']) == set(ORDEM[:3])
    assert json.loads(antes).keys() == fake.docs['real']['paradas_progresso'].keys()
