"""Fixtures Flask offline para o teste DOM/VM. Não abre navegador nem .env."""
import os,sys,json,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
with patch('dotenv.load_dotenv',return_value=False):import app as A
A.USUARIOS_TESTE.add('teste');A._PERFIS_TESTE['teste:teste']={'id':'teste:teste','teste':True,'avatar':'cavaleiro-m','xp':0}
c=A.app.test_client()
with c.session_transaction() as s:s['teste']='teste'
r=c.get('/mapa');assert r.status_code==200
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'mapa.json';p.write_text(json.dumps({'mapa':r.text}), encoding='utf-8')
 env=dict(os.environ);env['NODE_PATH']=str(ROOT.parent/'gen/formatos/teste/node_modules')
 sys.exit(subprocess.run(['node',str(ROOT/'gen/loja/xp-v6-dom.js'),str(ROOT),str(p)],env=env).returncode)
