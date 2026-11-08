# Servidor offline (sem Cosmos) para testes locais na porta 5077. Rodar a partir de /workspace/ncl/out.
import sys, os
sys.path.insert(0, os.getcwd())
from unittest.mock import patch
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
from cosmos_fake import CosmosFake
_cosmos_offline = CosmosFake()
A.get_users_container = lambda: _cosmos_offline
from flask import redirect, request
A.app.config["ONBOARDING_PREVIEW_ENDPOINTS"] = {"_login_teste", "_log"}
@A.app.route("/__login-teste")
def _login_teste():
    A.entrar_modo_teste("teste")
    return redirect(request.args.get("ir", "/mapa?vista=regiao"))
@A.app.route("/__log", methods=["POST"])
def _log():
    with open("/tmp/fmt-result.txt", "a", encoding='utf-8') as f:
        f.write(request.get_data(as_text=True) + "\n")
    return "ok"
A.app.run(host="127.0.0.1", port=int(os.environ.get("CHEMIN_TEST_PORT", "5077")), debug=False)
