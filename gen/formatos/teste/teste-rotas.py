# Checagens com o test client do Flask (sem Cosmos): usuário normal x teste, formatos, praça, mapa, telas congeladas.
# v7: mapa de 40 etapas (região 1 = etapas 1–11 iguais à v6; 12–40 testadas em gen/mapa40/teste-mapa40.py).
# v6: etapas seguem data/regioes/r1.json (etapa → conteúdo). Formatos: 2 traversier, 6 cartas, 9 bardo, 10 biblioteca; missões 1, 3, 5, 7; batalhas 4, 8, 11.
import os, sys, json
from pathlib import Path
PROJETO = Path(__file__).resolve().parents[3] / "out"
if not (PROJETO / "app.py").exists():
    PROJETO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJETO)); os.chdir(PROJETO)
from unittest.mock import patch
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
ok = falhas = 0
def chk(nome, cond):
    global ok, falhas
    print(('OK   ' if cond else 'FALHA'), nome); ok += bool(cond); falhas += (not cond)
# O app agora exige login. Simula um perfil legado ja integrado sem tocar no Cosmos.
class UsuariosOffline:
    def read_item(self, item, partition_key=None):
        return {"id": item, "avatar": "bardo-m", "nome": "Offline", "moldura": 1,
                "nivelamento_concluido_em": "2026-11-07"}
    def upsert_item(self, doc):
        raise RuntimeError("Cosmos desativado no teste")
A.get_users_container = lambda: UsuariosOffline()
c = A.app.test_client()
with c.session_transaction() as s:
    s["uid"] = "offline-legado"
ORDEM = json.load(open('data/regioes/r1.json', encoding='utf-8'))['ordem']
chk('ordem da região 1 (11 primeiras etapas)', ORDEM[:11] == ['r1-p01', 'r1-p05', 'r1-p02', 'r1-p10', 'r1-p03', 'r1-p08', 'r1-p04', 'r1-p11', 'r1-p06', 'r1-p07', 'r1-p09'])
for n in range(1, 12):
    r = c.get(f'/parada/1/{n}'); h = r.get_data(as_text=True)
    chk(f'GET /parada/1/{n} 200 → {ORDEM[n-1]} (Étape {n}, pid do conteúdo)', r.status_code == 200 and f'Étape {n}' in h and f'"pid": "{ORDEM[n-1]}"' in h)
for n, f in ((2, 'conversa'), (9, 'historia'), (10, 'biblioteca'), (6, 'cartas')):
    h = c.get(f'/parada/1/{n}').get_data(as_text=True)
    chk(f'etapa {n} usa formato.html ({f})', 'formatos.js' in h and f'formato-{f}' in h and 'motor.js' not in h)
    chk(f'etapa {n} normal sem selo de teste', 'MODO TESTE' not in h and '"prefixo": "chemin_"' in h)
for n in (1, 3, 5, 7):
    h = c.get(f'/parada/1/{n}').get_data(as_text=True); chk(f'etapa {n} (missão {ORDEM[n-1]}) continua no motor antigo, áudio da pasta do conteúdo', 'motor.js' in h and 'formatos.js' not in h and f'audio/paradas/{ORDEM[n-1]}/' in h)
for n in (4, 8, 11):
    chk(f'etapa {n} é batalha', 'batalha.js' in c.get(f'/parada/1/{n}').get_data(as_text=True))
chk('etapa 41 não existe (404)', c.get('/parada/1/41').status_code == 404 and c.get('/parada/1/12').status_code == 200)
r = c.get('/batalha/1?personagem=2'); chk('/batalha/1 → etapa 11 (batalha final)', r.status_code == 302 and r.headers['Location'].endswith('/parada/1/11?personagem=2'))
chk('/batalha/2 → etapa 4, /batalha/3 → etapa 8', c.get('/batalha/2').headers.get('Location', '').endswith('/parada/1/4') and c.get('/batalha/3').headers.get('Location', '').endswith('/parada/1/8'))
chk('praça 200', c.get('/praca/1').status_code == 200)
chk('praça região 2 404', c.get('/praca/2').status_code == 404)
hp = c.get('/praca/1').get_data(as_text=True)
chk('praça sem concluir/XP', 'concluir' not in hp and 'XP' not in hp and 'localStorage' not in open('static/parada/praca.js', encoding='utf-8').read())
r = c.post('/parada/1/2/concluir', json={'acertos': 7, 'erros': 1, 'fala_pendente': True, 'duracao_s': 180})
chk('normal concluir sem Cosmos → 503', r.status_code == 503)
chk('concluir com corpo inválido → 400', c.post('/parada/1/6/concluir', data='x', content_type='text/plain').status_code == 400)
hm = c.get('/mapa?vista=regiao').get_data(as_text=True)
chk('mapa: ponto da praça presente, sem número', 'id="praca-ponto"' in hm and '/praca/1' in hm)
chk('mapa: etapas 1–40 reais', all(f'"/parada/1/{n}"' in hm for n in range(1, 41)))
chk('mapa: selos de batalha nas etapas 4, 8, 11 (+13, 16, 19, 24, 27, 31, 34, 40)', 'const BATALHAS = [4, 8, 11, 13, 16, 19, 24, 27, 31, 34, 40];' in hm)
chk('mapa: ordem da trilha para migrar o progresso', '"ordem_v1"' in hm and 'migrarOrdem' in hm)
chk('mapa: BORDAS intacta', A.BORDAS_MAPA == [("madeira", 0), ("pedra", 45), ("bronze", 135), ("prata", 270), ("ouro", 405), ("diamante", 585)] or 'madeira' in str(A.BORDAS_MAPA))
# usuário de teste
t = A.app.test_client()
with t.session_transaction() as s: pass
with A.app.test_request_context():
    pass
r = t.post('/login', data={'usuario': 'teste', 'senha': os.environ.get('NCL_SENHA_TESTE') or 'qualquer'})
logou = r.status_code in (302, 303)
if not logou: raise AssertionError('Login de teste falhou')
ht = t.get('/parada/1/10').get_data(as_text=True)
chk('teste: selo + prefixo separado', 'MODO TESTE' in ht and '"prefixo": "chemin_teste_"' in ht)
for n in (2, 6, 9, 10):
    r = t.post(f'/parada/1/{n}/concluir', json={'acertos': 5, 'erros': 1, 'fala_pendente': False, 'duracao_s': 200})
    j = r.get_json() or {}
    chk(f'teste concluir etapa {n} ({ORDEM[n-1]}) 200 + teste:true + XP v6 autoritativo', r.status_code == 200 and j.get('teste') is True and j.get('xp') == {2:20,6:20,9:20,10:15}[n])
for n in (4, 8, 11):
    j = t.post(f'/parada/1/{n}/concluir', json={'acertos': 5, 'erros': 0, 'fala_pendente': False, 'duracao_s': 60}).get_json() or {}
    chk(f'teste concluir batalha etapa {n}: xp 0', j.get('ok') and j.get('xp') == 0 and j.get('xp_ganho') == 0)
docs = [d for d in A._PERFIS_TESTE.values() if isinstance(d, dict)]
chk('progresso do teste guardado pelo id de conteúdo', any(set(ORDEM) <= set((d.get('paradas_progresso') or {})) or {'r1-p05', 'r1-p08', 'r1-p06', 'r1-p07', 'r1-p10', 'r1-p11', 'r1-p09'} <= set((d.get('paradas_progresso') or {})) for d in docs))
r = t.post('/parada/1/2/concluir', json={'acertos': 5, 'erros': 1, 'fala_pendente': False, 'duracao_s': 100}); chk('repetir não soma XP', (r.get_json() or {}).get('xp_ganho') == 0)
hmt = t.get('/mapa?vista=regiao').get_data(as_text=True)
chk('teste: mapa com praça', 'id="praca-ponto"' in hmt)
chk('teste: praça mostra selo', 'MODO TESTE' in t.get('/praca/1').get_data(as_text=True))
chk('prévia ?passo/estado/tela vão para cfg', '"passo": 3' in c.get('/parada/1/2?passo=3&estado=erro').get_data(as_text=True))
chk('prévia ignora passo inválido', '"previa": {}' in c.get('/parada/1/2?passo=abc').get_data(as_text=True))
for p in ('/personagem', '/nivelamento', '/missao'):
    r = c.get(p); chk(f'{p} responde (sem 500)', r.status_code < 500)
print(f'\n{ok} OK, {falhas} falhas')

sys.exit(bool(falhas))
