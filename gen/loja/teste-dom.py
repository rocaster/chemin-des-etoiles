"""Renderiza Flask offline e executa contratos DOM com jsdom (npm install em gen/loja)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
with patch('dotenv.load_dotenv', return_value=False):import app as A
from loja import operar
A.app.config['TESTING']=True
A.USUARIOS_TESTE.add('teste')
A.get_users_container=lambda:(_ for _ in ()).throw(AssertionError('Cosmos real proibido'))
A._PERFIS_TESTE['teste:teste']={'id':'teste:teste','teste':True,'avatar':'cavaleiro-f','nome_personagem':'Luna','xp':135}
c=A.app.test_client()
with c.session_transaction() as s:s['teste']='teste'
with tempfile.TemporaryDirectory(prefix='loja-dom-') as pasta:
    def save(nome,url):Path(pasta,nome+'.html').write_text(c.get(url).text,encoding='utf-8')
    save('heroi','/heroi')
    for cat in ('personagem','particulas','titulos','pets','cenarios'):save(cat,'/loja?categoria='+cat)
    A._PERFIS_TESTE['teste:teste']['avatar']='mago-m'
    save('titulos-m','/loja?categoria=titulos');save('heroi-m','/heroi')
    A._PERFIS_TESTE['teste:teste']['avatar']='cavaleiro-f'
    v=None
    for iid in ('pet-dragao','titulo-voz','paleta-rubi'):
        v=operar(v,'comprar',iid,teste=True);v=operar(v,'equipar',iid,teste=True)
    A._PERFIS_TESTE['teste:teste']['cosmeticos']=v
    save('equipado','/heroi');save('loja-equipado','/loja?categoria=pets')
    v=operar(v,'comprar','efeito-chuva',teste=True);v=operar(v,'equipar','efeito-chuva',teste=True)
    A._PERFIS_TESTE['teste:teste']['cosmeticos']=v
    for nome,url in [('heroi-particula','/heroi'),('loja-particula','/loja'),('loja-particulas','/loja?categoria=particulas'),('mapa-mundo-particula','/mapa?vista=mundo'),('mapa-regiao-particula','/mapa?vista=regiao'),('batalha-particula','/parada/1/4'),('chefe-particula','/parada/1/40')]:save(nome,url)
    v['equipados'].pop('pets')
    save('comprado','/loja?categoria=pets')
    v['cristais']=0
    save('sem-saldo','/loja?categoria=particulas')
    subprocess.run(['node',str(Path(__file__).with_suffix('.js')),pasta],check=True)
