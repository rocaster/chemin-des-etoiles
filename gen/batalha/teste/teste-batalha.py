# v7: alvo = etapa 11 (batalha final da vila, r1-p09 → r1-b01); as outras 10 batalhas estão em gen/mapa40/teste/.
# Checagens da batalha com o test client do Flask: rotas, parâmetros de depuração, marcador no mapa, nenhum XP.
import os, sys, json, re
sys.path.insert(0, '/workspace/ncl/out'); os.chdir('/workspace/ncl/out')
from unittest.mock import patch
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
A.USUARIOS_TESTE.add('teste')
c = A.app.test_client(); ok = falhas = 0
with c.session_transaction() as s: s['teste']='teste'
def chk(n, cond):
    global ok, falhas; print(('OK   ' if cond else 'FALHA'), n); ok += bool(cond); falhas += (not cond)
r = c.get('/parada/1/11'); chk('/parada/1/11 (batalha) 200', r.status_code == 200)
r = c.get('/batalha/1?personagem=3&tela=vitoria'); chk('/batalha/1 → redireciona para /parada/1/11 com os parâmetros', r.status_code == 302 and r.headers['Location'].endswith('/parada/1/11?personagem=3&tela=vitoria'))
chk('v7: /batalha/2 → etapa 4 e /batalha/12 404', c.get('/batalha/2').status_code == 302 and c.get('/batalha/12').status_code == 404)
for i, a in enumerate(A.ORDEM_PERSONAGENS, 1):
    h = c.get(f'/parada/1/11?personagem={i}').get_data(as_text=True)
    chk(f'personagem={i} -> heroi-{a}.png + nome {A.NOMES_PERSONAGEM[a]}', f'batalha/heroi-{a}.png' in h and f'id="nome-heroi">{A.NOMES_PERSONAGEM[a]}<' in h
        and os.path.isfile(f'static/batalha/heroi-{a}.png'))
for e in ['renard', 'oie', 'rat']:
    h = c.get(f'/parada/1/11?inimigo={e}').get_data(as_text=True); chk(f'inimigo={e}', f'"inimigo": "{e}"' in h or f'"inimigo":"{e}"' in h)
h = c.get('/parada/1/11?inimigo=dragao').get_data(as_text=True); chk('inimigo inválido -> sorteio', '"inimigo": ""' in h or '"inimigo":""' in h)
for t in ['vitoria', 'derrota']:
    h = c.get(f'/parada/1/11?tela={t}').get_data(as_text=True); chk(f'tela={t}', f'"tela": "{t}"' in h or f'"tela":"{t}"' in h)
D = json.load(open('data/batalhas/r1-b01.json', encoding='utf-8'))
chk('regras v2: vida 5/5, dano 1/2/3, erro 1, xp 0', D['regras']['vida_heroi'] == 5 and D['regras']['vida_inimigo'] == 5 and D['regras']['xp'] == 0
    and D['regras']['dano'] == {'leger': 1, 'fort': 2, 'special': 3} and D['regras']['dano_erro'] == 1)
pior = (D['regras']['vida_inimigo'] * 1) + (D['regras']['vida_heroi'] - 1)   # caso mais longo: acerto/erro alternados
chk('v3: Spécial reutilizável, combo zera depois dele', D['regras'].get('combo_zera_apos_especial') is True and 'especial_por_batalha' not in D['regras'])
js3 = open('static/parada/batalha.js', encoding='utf-8').read()
chk('v3: sem lógica de uso único/ocultar Spécial no JS', 'especialGasto' not in js3 and 'gastarEspecial' not in js3 and "E.combo = 0; mostrarCombo(); comboZerado();   /* depois do Spécial o combo zera */" in js3)
h3 = c.get('/parada/1/11').get_data(as_text=True)
chk('v3: entrada Spécial sempre no painel', 'data-tipo="special"' in h3)
chk(f'perguntas suficientes sem repetir no caso mais longo ({pior} respostas; banco {len(D["perguntas"])})', len({p["fr"] for p in D['perguntas']}) >= pior)
for cl in ['cavaleiro', 'arqueiro', 'mago', 'bardo']:
    e = D['especiais'][cl]
    chk(f'Spécial {cl}: {e["nome"]} (imagem 10 quadros + som)', os.path.isfile('static/' + e['img']) and os.path.isfile('static/' + e['som'])
        and __import__('struct').unpack('>II', open('static/' + e['img'], 'rb').read()[16:24]) == (4000, 225))
for i, a in enumerate(A.ORDEM_PERSONAGENS, 1):
    h = c.get(f'/parada/1/11?personagem={i}').get_data(as_text=True)
    chk(f'personagem={i}: 5+5 segmentos e Spécial da classe {a.split("-")[0]}', f'especial-{a.split("-")[0]}.png' in h
        and len(re.findall(r'<i></i>', h.split('id="barra-heroi"')[1].split('</div>')[0])) == 5
        and len(re.findall(r'<i></i>', h.split('id="barra-inimigo"')[1].split('</div>')[0])) == 5)
chk('todos os áudios existem', all(os.path.isfile('static/audio/' + p['audio']) for p in D['perguntas'])
    and all(os.path.isfile(f'static/audio/batalhas/r1-b01/{k}.mp3') for k in [v['intro'] for v in D['inimigos'].values()] + ['vitoria', 'derrota']))
chk('sprites dos inimigos/efeitos/sons existem', all(os.path.isfile('static/' + v['img']) for v in D['inimigos'].values())
    and all(os.path.isfile(f'static/batalha/{f}') for f in ['floresta.png', 'efeito-corte.png', 'efeito-golpe.png', 'efeito-estrela.png', 'efeito-dano.png'] + [f'som-{s}.wav' for s in ['leger', 'fort', 'special', 'dano', 'vitoria', 'derrota']]))
js = open('static/parada/batalha.js', encoding='utf-8').read()
chk('v5: JS só grava na vitória (salvarVitoria) — sessionStorage/XHR/beacon não usados', js.count('fetch(') == 1 and 'function salvarVitoria' in js and not re.search(r'sessionStorage|XMLHttpRequest|sendBeacon', js))
with c.session_transaction() as s: pass
c2 = A.app.test_client(); c2.get('/__login-teste?ir=/mapa') if '/__login-teste' in [r.rule for r in A.app.url_map.iter_rules()] else None
m = c.get('/mapa?vista=regiao').get_data(as_text=True)
chk('mapa v5: sem ponto solto de batalha; praça intacta; etapa 11 marcada como batalha (v7: 11 batalhas)', 'id="batalha-ponto"' not in m and 'class="batalha-ponto"' not in m
    and 'id="praca-ponto"' in m and '"/parada/1/11"' in m and re.search(r'const BATALHAS = \[4, 8, 11, 13, 16, 19, 24, 27, 31, 34, 40\];', m) is not None)
# ---- v4: contra-ataque com defesa
import struct
dim = lambda f: struct.unpack('>II', open('static/' + f, 'rb').read()[16:24])
R = D['regras']; dfs = D['defesa']
chk('v4: regras do contra-ataque (dano 1, também depois de erro de ataque)', R.get('contra_ataque') is True and R.get('dano_defesa') == 1 and R.get('contra_apos_erro') is True)
nums = [x for x in dfs if x['tipo'] == 'numero']; pals = [x for x in dfs if x['tipo'] == 'palavra']
chk(f'v6/v7: banco de defesa da batalha final da vila = números 1–20 ({len(nums)}) + palavras curtas da região 1 ({len(pals)})', [x['pt'] for x in nums] == [str(n) for n in range(1, 21)]
    and all(x['origem'] in ('r1-p01', 'r1-p02', 'r1-p03', 'r1-p04', 'r1-p05', 'r1-p06', 'r1-p07', 'r1-p08') for x in pals) and len(pals) >= 10)
chk('v4: todo item de defesa tem áudio fr-CA e 2 parecidos/opções', all(os.path.isfile('static/audio/' + x['audio']) for x in dfs)
    and all(len(x['parecidos']) == 2 for x in nums) and os.path.isfile('static/audio/batalhas/r1-b01/bloque.mp3'))
max_ataques = R['vida_inimigo'] + (R['vida_heroi'] - 1)   # ≤5 acertos (cada um tira ≥1) + ≤4 erros sem morrer
max_defesas = max_ataques - 1                              # sem contra-ataque depois do golpe final
chk(f'v4: caso mais longo = {max_ataques} ataques + {max_defesas} defesas; bancos {len(D["perguntas"])} / {len(dfs)} sem repetir',
    len({p['fr'] for p in D['perguntas']}) >= max_ataques and len({x['fr'] for x in dfs}) >= max_defesas)
chk('v4: inimigos com 7 quadros (idle, dor, queda, preparo, golpe)', all(dim(v['img']) == (672 * 4, 64 * 4) for v in D['inimigos'].values()))
chk('v4: escudo, ícone e sons de bloqueio/preparo', all(os.path.isfile('static/batalha/' + f) for f in ['efeito-escudo.png', 'escudo-icone.png', 'som-bloqueio.wav', 'som-preparo.wav']))
h4 = c.get('/parada/1/11').get_data(as_text=True)
chk('v4: página carrega voz.js antes do batalha.js e tem escudo/"Bloqué"', h4.find('parada/voz.js') < h4.find('parada/batalha.js') and h4.find('parada/voz.js') > 0 and 'id="efeito-bloqueio"' in h4 and 'id="bloqueado"' in h4)
js4 = open('static/parada/batalha.js', encoding='utf-8').read()
chk('v4: defesa sem autoavaliação ("Falei em voz alta"/"Falei certo") e sem mexer no combo', 'Falei' not in js4 and 'auto-certo' not in js4
    and 'E.combo' not in js4[js4.index('async function turnoInimigo'):js4.index('async function bloqueio')])
# ---- v5: parada 9 de progressão + timer
P9 = json.load(open('data/paradas/r1-p09.json', encoding='utf-8'))
chk('v5: r1-p09 = formato batalha → r1-b01, XP 0 (pausado)', P9['formato'] == 'batalha' and P9['batalha'] == 'r1-b01'
    and P9['recompensa']['xp_base'] == 0 and P9['recompensa']['xp_por_estrela'] == 0)
chk('v5: timer da defesa 5 s com tolerância 0,7 s nos dados', R.get('timer_defesa_s') == 5 and abs(R.get('timer_graca_s', 0) - 0.7) < 1e-9)
h5 = c.get('/parada/1/11').get_data(as_text=True)
chk('v5: tela da parada 9 aponta para a rota de conclusão e volta ao mapa a partir da 9', '"/parada/1/11/concluir"' in h5 and 'de=11' in h5)
js5 = open('static/parada/batalha.js', encoding='utf-8').read()
chk('v5: JS conclui pela rota normal e guarda no localStorage do prefixo (libera a próxima)', 'CFG.concluir' in js5 and '_atual`' in js5 and 'xp: 0' in js5)
chk('v5: timer pausa com a aba escondida, ?timer=N/0, tolerância da voz', 'document.hidden' in js5 and 'visibilitychange' in js5 and '"timer"' in js5 and 'GRACA_MS' in js5)
print(f'\n{ok} OK, {falhas} falhas')

sys.exit(bool(falhas))
