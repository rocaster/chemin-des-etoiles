"""Diagnostico offline, sem abrir .env nem chamar Azure."""
import sys
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
import contas_cosmos as C

SEGREDO = "AccountEndpoint=https://fake-secret-account.documents.azure.com/;AccountKey=fake-secret-key-123==;"


def test_metadados_sem_segredos(capsys):
    erro = RuntimeError(SEGREDO)
    erro.status_code = 401
    erro.headers = {"x-ms-substatus": "1001", "authorization": SEGREDO}
    erro.error = SimpleNamespace(code="Unauthorized", message=SEGREDO)
    C.registrar_falha_contas("criar", erro)
    texto = capsys.readouterr().err
    assert texto == "operacao=criar excecao=RuntimeError status_code=401 sub_status=1001 code=Unauthorized\n"
    for parte in (SEGREDO, "AccountEndpoint", "fake-secret-account", "fake-secret-key-123", "AccountKey"):
        assert parte not in texto


def test_campos_maliciosos_e_keyerror_nao_env(capsys):
    erro = RuntimeError(SEGREDO)
    erro.status_code = SEGREDO
    erro.sub_status = SEGREDO
    erro.code = SEGREDO
    C.registrar_falha_contas("obter", erro)
    C.registrar_falha_contas("obter", KeyError(SEGREDO))
    assert capsys.readouterr().err == "operacao=obter excecao=RuntimeError\noperacao=obter excecao=KeyError\n"


def test_env_ausente(monkeypatch, capsys):
    monkeypatch.setattr(A, "_client", None)
    monkeypatch.delenv("COSMOS_CONNECTION", raising=False)
    with pytest.raises(C.ContasIndisponiveis):
        A.get_db()
    assert capsys.readouterr().err == "operacao=get_db_config excecao=KeyError variavel_ausente=COSMOS_CONNECTION\n"


def test_client_failure(monkeypatch, capsys):
    monkeypatch.setattr(A, "_client", None)
    monkeypatch.setenv("COSMOS_CONNECTION", SEGREDO)
    def falhar(*args):
        raise ValueError(SEGREDO)
    monkeypatch.setattr(A, "CosmosClient", SimpleNamespace(from_connection_string=falhar))
    with pytest.raises(C.ContasIndisponiveis):
        C.ContasCosmos(A.get_users_container).obter("usuario", "teste")
    texto = capsys.readouterr().err
    assert "operacao=get_db excecao=ValueError" in texto
    assert SEGREDO not in texto
    assert "AccountKey" not in texto


def test_wrapper_e_fornecedor(capsys):
    def falhar():
        raise RuntimeError(SEGREDO)
    with pytest.raises(C.ContasIndisponiveis):
        C.ContasCosmos(falhar).conectar()
    @C._proteger
    def operacao():
        raise RuntimeError(SEGREDO)
    with pytest.raises(C.ContasIndisponiveis):
        operacao()
    texto = capsys.readouterr().err
    assert "operacao=conectar excecao=RuntimeError" in texto
    assert "operacao=operacao excecao=RuntimeError" in texto
    assert SEGREDO not in texto


def test_fallback_logger_desabilitado(monkeypatch, capsys):
    monkeypatch.setattr(C._logger, "disabled", True)
    C.registrar_falha_contas("conectar", ValueError(SEGREDO))
    assert capsys.readouterr().err == "operacao=conectar excecao=ValueError\n"


def test_http_response_error(capsys):
    from azure.core.exceptions import HttpResponseError
    erro = HttpResponseError(message=SEGREDO)
    erro.status_code = 404
    erro.error = SimpleNamespace(code="NotFound")
    erro.sub_status_code = 1003
    C.registrar_falha_contas("obter", erro)
    assert capsys.readouterr().err == "operacao=obter excecao=HttpResponseError status_code=404 sub_status=1003 code=NotFound\n"
