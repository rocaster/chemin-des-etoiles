"""Prévia local em 5088, sem Cosmos, SMTP ou .env. Use somente no box local."""
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SUPORTE = ROOT / 'gen/formatos/teste'
if not (SUPORTE / 'cosmos_fake.py').exists():
    SUPORTE = ROOT.parent / 'gen/formatos/teste'
sys.path.insert(0, str(SUPORTE))
with patch('dotenv.load_dotenv', return_value=False):
    import app as A
from cosmos_fake import CosmosFake
from flask import redirect
fake = CosmosFake()
A.get_users_container = lambda: fake
A.app.config['ONBOARDING_PREVIEW_ENDPOINTS'] = {'_loja_preview'}
@A.app.get('/__loja-preview')
def _loja_preview():
    A.entrar_modo_teste('teste')
    return redirect('/heroi')
if __name__ == '__main__':
    A.app.run(host='127.0.0.1', port=5088, debug=False)
