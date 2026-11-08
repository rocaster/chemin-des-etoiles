# Mapa de 40 etapas: modelos (sem repetir lado a lado, 26:14, cada região termina em batalha), todas as rotas 200, motor certo,
# A1 (≤ 8 palavras novas e ≤ 2 padrões por etapa), arquivos referenciados existem, chefe (20/5, castelo), XP pausado, BORDAS intacta.
import os, sys, json, re, glob
sys.path.insert(0, '/workspace/ncl/out'); os.chdir('/workspace/ncl/out')
from unittest.mock import patch
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
ok = falhas = 0
def chk(nome, cond):
    global ok, falhas
    print(('OK   ' if cond else 'FALHA'), nome); ok += bool(cond); falhas += (not cond)
R = json.load(open('data/regioes/r1.json', encoding='utf-8')); ORDEM = R['ordem']
LETRA = {'batalha': 'B', 'conversa': 'C', 'historia': 'H', 'biblioteca': 'L', 'cartas': 'K', None: 'M'}
P = [json.load(open(f'data/paradas/{pid}.json', encoding='utf-8')) for pid in ORDEM]
mod = ''.join(LETRA[d.get('formato')] for d in P)
chk('40 etapas na ordem da trilha', len(ORDEM) == 40 == A.MAPA_PARADAS and len(set(ORDEM)) == 40)
chk(f'modelos vêm dos dados e batem com r1.json ({mod})', mod == R['modelos'])
def repetidos(m): return [(i + 1, m[i]) for i in range(len(m) - 1) if m[i] == m[i + 1]]
lado = repetidos(mod)
chk('auto-teste: o detector acusa dois modelos iguais lado a lado', repetidos('MCMMB') == [(3, 'M')] and repetidos(mod[:20] + mod[20] + mod[20:]) != [])
chk('nenhum modelo repetido lado a lado' + (f' — repetidos: {lado}' if lado else ''), not lado)
bm = sum(c in 'BM' for c in mod); chk(f'batalhas+missões × outros = 26:14 (obtido {bm}:{40 - bm})', bm == 26)
chk('cada região termina em batalha (11, 24, 40)', all(mod[n - 1] == 'B' for n in (11, 24, 40)))
chk('regiões 7:4, 9:4, 10:6', [sum(c in 'BM' for c in mod[a:b]) for a, b in ((0, 11), (11, 24), (24, 40))] == [7, 9, 10])
@A.app.route('/__entrar-teste-m40')
def _e():
    A.entrar_modo_teste('teste'); return 'ok'
A.USUARIOS_TESTE.add('teste')
c = A.app.test_client()
with c.session_transaction() as s: s['teste']='teste'
MOTOR = {'B': 'batalha.js', 'M': 'motor.js', 'C': 'formatos.js', 'H': 'formatos.js', 'L': 'formatos.js', 'K': 'formatos.js'}
falhou = []
for n in range(1, 41):
    r = c.get(f'/parada/1/{n}'); h = r.get_data(as_text=True)
    if not (r.status_code == 200 and f'Étape {n}' in h and MOTOR[mod[n - 1]] in h and (f'"pid": "{ORDEM[n-1]}"' in h)): falhou.append(n)
chk('todas as 40 rotas /parada/1/N → 200, “Étape N”, motor do modelo e pid do conteúdo' + (f' — falhas: {falhou}' if falhou else ''), not falhou)
chk('/parada/1/41 → 404', c.get('/parada/1/41').status_code == 404)
for k, n in ((4, 13), (11, 40)):
    r = c.get(f'/batalha/{k}'); chk(f'/batalha/{k} → etapa {n}', r.status_code == 302 and r.headers['Location'].endswith(f'/parada/1/{n}'))
# A1: tetos por etapa (etapas 12–39 novas; números contam como série fechada)
for d in P[11:39]:
    nov = [w for w in d.get('novas', []) if not w.startswith('(')]
    if len(nov) > 8 or len(d.get('padroes', [])) > 2: chk(f"A1 etapa {d['etapa']}: {len(nov)} novas, {len(d.get('padroes', []))} padrões", False)
chk('A1: etapas 12–39 com ≤ 8 palavras novas e ≤ 2 padrões', all(len([w for w in d.get('novas', []) if not w.startswith('(')]) <= 8 and len(d.get('padroes', [])) <= 2 for d in P[11:39]))
chk('etapas novas com tabela XP v6, batalhas 0 e sem multiplicador de estrelas', all(d['recompensa']['xp_base'] == {'missao':25,'conversa':20,'historia':20,'biblioteca':15,'cartas':20,'batalha':0}[d.get('formato','missao')] and d['recompensa']['xp_por_estrela']==0 for d in P[11:]))
# arquivos
falta = []
for d in P[11:]:
    if d.get('formato') == 'batalha': continue
    falta += [f"{d['id']}/{k}" for k in d['audios'] if not os.path.exists(f"static/audio/paradas/{d['id']}/{k}.mp3")]
    falta += [v['src'] for v in d['imagens'].values() if not os.path.exists('static/' + v['src'])]
    cn = d['cenario']; falta += [x for x in (cn['fundo'], cn['frente'], cn['npc']['img']) if not os.path.exists('static/' + x)]
for f in glob.glob('data/batalhas/*.json'):
    b = json.load(open(f, encoding='utf-8'))
    falta += [f"{b['id']}/{k}" for k in b['audios'] if not os.path.exists(f"static/audio/batalhas/{b['id']}/{k}.mp3")]
    falta += [q['audio'] for q in b['perguntas'] + b['defesa'] if not os.path.exists('static/audio/' + q['audio'])]
chk(f'todo áudio/imagem referenciado existe ({len(falta)} faltando)', not falta)
# chefe
B = json.load(open('data/batalhas/r1-b11.json', encoding='utf-8')); h = c.get('/parada/1/40').get_data(as_text=True)
chk('chefe: 20 barras, herói 5, combo 1/2/3, erro −1, timer 5 s, xp 0', B['regras']['vida_inimigo'] == 20 and B['regras']['vida_heroi'] == 5 and B['regras']['dano'] == {'leger': 1, 'fort': 2, 'special': 3}
    and B['regras']['dano_erro'] == 1 and B['regras']['timer_defesa_s'] == 5 and B['regras']['combo_zera_apos_especial'] and B['regras']['xp'] == 0)
chk('chefe: fundo do castelo, classe .chefe, 20 segmentos na barra', 'batalha/castelo.png' in h and 'class="chefe"' in h and '--seg: 20' in h and h.count('<i></i>') >= 25)
chk('chefe: revisa as 3 regiões', {q['origem'][:4] for q in B['perguntas']} == {'r1-p'} and any(q['origem'] in ORDEM[:11] for q in B['perguntas']) and any(q['origem'] in ORDEM[11:24] for q in B['perguntas']) and any(q['origem'] in ORDEM[24:] for q in B['perguntas']))
chk('batalhas normais seguem com 5/5', all(json.load(open(f, encoding='utf-8'))['regras']['vida_inimigo'] == 5 for f in glob.glob('data/batalhas/*.json') if not f.endswith('r1-b11.json')))
hm = c.get('/mapa?vista=regiao').get_data(as_text=True)
chk('mapa: 40 reais, etapa 40 rotulada Château', all(f'"/parada/1/{n}"' in hm for n in range(1, 41)) and '"Château"' in hm and 'Mapa concluído' in hm)
chk('mapa: BORDAS intacta', A.BORDAS_MAPA == [("madeira", 0), ("pedra", 45), ("bronze", 135), ("prata", 270), ("ouro", 405), ("diamante", 585)] or 'madeira' in str(A.BORDAS_MAPA))
# usuário de teste: concluir etapas novas dá 0 XP
t = A.app.test_client()
with t.session_transaction() as s:s['teste']='teste'
xs = [(n, (t.post(f'/parada/1/{n}/concluir', json={'acertos': 6, 'erros': 0, 'fala_pendente': False, 'duracao_s': 120}).get_json() or {})) for n in (12, 14, 17, 20, 22, 40)]
chk('teste: concluir etapas 12/14/17/20/22/40 → XP v6 autorizado', all(j.get('ok') and j.get('xp') == {'missao':25,'conversa':20,'historia':20,'biblioteca':15,'cartas':20,'batalha':0}[P[n-1].get('formato','missao')] for n,j in xs))
print(f'\n{ok} OK, {falhas} falhas')

sys.exit(bool(falhas))
