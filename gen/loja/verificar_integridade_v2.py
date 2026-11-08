"""Auditoria local contra o snapshot anterior à v2; nunca lê .env.
O snapshot fica fora do app e do pacote, em backup-heroi-espada/protegidos.json.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
BK=ROOT.parent/'backup-heroi-espada'
permitidos={'templates/heroi.html','templates/loja-base.html','data/loja.json'}
hashes=json.loads((BK/'protegidos.json').read_text())
resultado={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in hashes.items()
           if p not in permitidos and not p.startswith('static/loja/pets/')}
a=json.loads((BK/'data/loja.json').read_text());b=json.loads((ROOT/'data/loja.json').read_text())
resultado['precos_itens_paletas_iniciais_identicos']=a['itens']==b['itens'] and a['saldo_inicial']==b['saldo_inicial']
old=(BK/'templates/heroi.html').read_text();new=(ROOT/'templates/heroi.html').read_text()
resultado['painel_direito_identico']=old.split('<div class="pergaminho ficha">')[1].split('</section>')[0]==new.split('<div class="pergaminho ficha">')[1].split('</section>')[0]
resultado['bau_conquistas_identico']=old.split('<section id="conquistas"')[1]==new.split('<section id="conquistas"')[1]
resultado['load_dotenv_preservado']='load_dotenv()' in (ROOT/'app.py').read_text()
assert all(resultado.values()),{p:v for p,v in resultado.items() if not v}
out=ROOT.parent/'relatorio-heroi-espada/integridade.json'
out.write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
print(len(resultado),'verificações de integridade OK: originais/paletas/mapa/funções/músicas preservados.')
