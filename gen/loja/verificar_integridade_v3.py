"""Snapshot local da v2 + originais anteriores à v2. Não lê arquivos .env."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
BK=ROOT.parent/'backup-heroi-v3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={p:sha(ROOT/p)==valor for p,valor in json.loads((BK/'protegidos.json').read_text()).items()}
pre_v2=json.loads((ROOT.parent/'backup-heroi-espada/protegidos.json').read_text())
for p,valor in pre_v2.items():
    if p.startswith(('static/fogueira/','static/avatars/','static/loja/paletas/')):
        checks['original_pre_v2:'+p]=sha(ROOT/p)==valor
arquivos=list((ROOT/'static/loja/herois/espada').glob('*.png'))
checks['somente_oito_derivados_cavaleiro_m']=len(arquivos)==8 and all(p.name.startswith('cavaleiro-m') for p in arquivos)
for p in arquivos:checks['cavaleiro_m_igual_v2:'+p.name]=sha(p)==sha(BK/'espada-v2'/p.name)
for trecho,marker in [('painel_direito','<div class="pergaminho ficha">'),('bau','<section id="conquistas"')]:
    antes=(BK/'templates/heroi.html').read_text().split(marker)[1]
    depois=(ROOT/'templates/heroi.html').read_text().split(marker)[1]
    checks[trecho+'_inalterado']=antes==depois
assert all(checks.values()),[k for k,v in checks.items() if not v]
out=ROOT.parent/'relatorio-heroi-v3';out.mkdir(exist_ok=True)
(out/'integridade.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(len(checks),'verificações de integridade v3 OK; originais intactos, só cavaleiro-m derivado.')
