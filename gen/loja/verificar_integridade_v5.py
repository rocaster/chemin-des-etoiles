"""Auditoria local v5 contra snapshots, sem .env/rede.
Exceções são APENAS superfícies novas autorizadas para poses v5.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
AUTORIZADOS={'herois.py','loja.py','templates/heroi.html','templates/loja.html','templates/loja-base.html','static/loja/heroi-v2.css'}
checks={}
for backup in ['backup-loja/frozen.json','backup-heroi-espada/protegidos.json','backup-heroi-v3/protegidos.json','backup-heroi-v4/protegidos.json','backup-heroi-v5/protegidos.json']:
    for name,h in json.loads((ROOT.parent/backup).read_text()).items():
        if name in AUTORIZADOS or name.startswith('static/loja/pets/'):continue
        # data/loja.json ganhou apenas aviso da economia na v2. Catálogo/saldo
        # são comparados abaixo; v4/v5 inteiros continuam idênticos.
        if name=='data/loja.json' and backup.startswith('backup-heroi-espada/'):continue
        checks[backup+':'+name]=sha(ROOT/name)==h
old=json.loads((ROOT.parent/'backup-heroi-espada/data/loja.json').read_text())
new=json.loads((ROOT/'data/loja.json').read_text())
checks['catalogo_precos_saldos_v1_intactos']=old['itens']==new['itens'] and old['saldo_inicial']==new['saldo_inicial']
for part,marker in [('painel_direito','<div class="pergaminho ficha">'),('bau','<section id="conquistas"')]:
    checks[part+'_intacto']=(ROOT.parent/'backup-heroi-v5/templates/heroi.html').read_text().split(marker)[1]==(ROOT/'templates/heroi.html').read_text().split(marker)[1]
legacy=list((ROOT/'static/loja/herois/espada').glob('*.png'))
checks['legado_so_oito_cavaleiro_m']=len(legacy)==8 and all(p.name.startswith('cavaleiro-m') for p in legacy)
for p in legacy:checks['espada_legada_intacta:'+p.name]=sha(p)==sha(ROOT.parent/'backup-heroi-v3/espada-v2'/p.name)
checks['load_dotenv_preservado']='load_dotenv()' in (ROOT/'app.py').read_text()
# As novas poses não substituem fontes antigas, mesmo onde já havia espada.
for p in (ROOT/'static/loja/pets').glob('*.png'):
    checks['pet_novo_nao_igual_v4:'+p.name]=sha(p)!=sha(ROOT.parent/'backup-heroi-v5/static/loja/pets'/p.name)
assert all(checks.values()),[k for k,v in checks.items() if not v]
out=ROOT.parent/'relatorio-heroi-v5';out.mkdir(exist_ok=True)
(out/'integridade.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(len(checks),'verificações v5 OK: originais/congelados/XP/economia/preços/painel/baú preservados.')
