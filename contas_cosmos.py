"""Contas/perfis no container users existente; nenhuma alteracao de infraestrutura.

Requer partition key /id, como os point reads de perfis ja existentes.
Reservas sao atomicas por id; as tres particoes NAO formam uma transacao.
Falhas normais sao compensadas; indisponibilidade durante rollback pode deixar
pendencias recuperadas depois. Reservas orfas so sao liberadas apos 24 horas.
"""
from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from threading import Lock
from urllib.parse import quote
import time
import logging
import re
import sys

from azure.core import MatchConditions


class OperacaoCosmeticaInvalida(ValueError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


class ContaDuplicada(Exception):
    pass


class ContasIndisponiveis(Exception):
    pass


class _StderrContas(logging.Handler):
    def emit(self, record):
        print(self.format(record), file=sys.stderr, flush=True)


_logger = logging.getLogger("ncl.contas.diagnostico")
_logger.setLevel(logging.ERROR)
_logger.propagate = False
if not _logger.handlers:
    _logger.addHandler(_StderrContas())

# Campos textuais do SDK nao sao confiaveis: nunca registrar texto livre.
_CODIGOS_SEGUROS = frozenset({
    "Unauthorized", "Forbidden", "NotFound", "BadRequest", "Conflict",
    "PreconditionFailed", "RequestTimeout", "TooManyRequests",
    "InternalServerError", "ServiceUnavailable", "RequestEntityTooLarge",
    "MethodNotAllowed", "Gone", "RetryWith", "PartitionKeyMismatch",
})


def registrar_falha_contas(operacao, erro, variavel_ausente=None):
    """Somente metadados permitidos; nunca mensagem, traceback ou resposta HTTP."""
    campos = ["operacao=" + operacao, "excecao=" + type(erro).__name__]
    headers = getattr(erro, "headers", None)
    if not isinstance(headers, dict):
        headers = {}
    for nome, valor in (
        ("status_code", getattr(erro, "status_code", None)),
        ("sub_status", getattr(erro, "sub_status", None) or getattr(erro, "sub_status_code", None) or headers.get("x-ms-substatus")),
    ):
        if type(valor) is int or (type(valor) is str and re.fullmatch(r"[0-9]{1,8}", valor)):
            campos.append(nome + "=" + str(valor))
    codigo = getattr(erro, "code", None)
    if codigo is None:
        codigo = getattr(getattr(erro, "error", None), "code", None)
    if type(codigo) is str and codigo in _CODIGOS_SEGUROS:
        campos.append("code=" + codigo)
    if isinstance(erro, KeyError) and variavel_ausente == "COSMOS_CONNECTION":
        campos.append("variavel_ausente=" + variavel_ausente)
    texto = " ".join(campos)
    if _logger.isEnabledFor(logging.ERROR) and not _logger.disabled:
        _logger.error(texto)
    else:
        print(texto, file=sys.stderr, flush=True)


def _proteger(funcao):
    @wraps(funcao)
    def executar(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except (ContaDuplicada, KeyError, OperacaoCosmeticaInvalida):
            raise
        except ContasIndisponiveis as erro:
            registrar_falha_contas(funcao.__name__, erro)
            raise
        except Exception as erro:
            registrar_falha_contas(funcao.__name__, erro)
            raise ContasIndisponiveis() from None
    return executar


def _status(erro):
    return getattr(erro, "status_code", None)


def _iso(epoca):
    return datetime.fromtimestamp(epoca, timezone.utc).isoformat()


def _epoca(valor):
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError):
        return float("inf")  # Documento desconhecido nao e apagado.


class ContasCosmos:
    INTERVALO_LIMPEZA = 20 * 60
    _ultima_limpeza = {}
    _lock_limpeza = Lock()
    CAMPOS_LOGIN = {"tipo", "usuario", "usuario_lower", "email", "email_lower",
                    "senha_hash", "confirmado", "nonce", "ultimo_envio"}

    def __init__(self, fornecedor):
        self.fornecedor = fornecedor

    def conectar(self):
        try:
            return self.fornecedor()
        except ContasIndisponiveis:
            raise
        except Exception as erro:
            registrar_falha_contas("conectar", erro)
            raise ContasIndisponiveis() from None

    @staticmethod
    def reserva_id(campo, valor):
        # /, ?, # sao proibidos em IDs Cosmos, mas podem aparecer no e-mail.
        # Codificacao sem ambiguidade; usernames/e-mails usuais ficam legiveis.
        return "reserva-" + campo + ":" + quote(valor.strip().lower(), safe="@._-+")

    def _ler(self, uid):
        try:
            return self.conectar().read_item(item=uid, partition_key=uid)
        except Exception as erro:
            if _status(erro) == 404:
                return None
            raise

    def _substituir(self, atual, novo):
        return self.conectar().replace_item(item=atual["id"], body=novo,
            etag=atual["_etag"], match_condition=MatchConditions.IfNotModified)

    def _apagar(self, doc):
        try:
            self.conectar().delete_item(item=doc["id"], partition_key=doc["id"],
                etag=doc["_etag"], match_condition=MatchConditions.IfNotModified)
            return True
        except Exception as erro:
            if _status(erro) == 404:
                return True
            if _status(erro) == 412:
                return False
            raise

    @staticmethod
    def _expirada(doc, agora):
        return (doc.get("tipo") == "conta" and doc.get("confirmado") is False
                and _epoca(doc.get("criado_em")) < agora - 86400)

    def _liberar_reserva(self, rid, uid):
        atual = self._ler(rid)
        if atual and atual.get("uid") == uid and atual.get("tipo") in {"reserva-usuario", "reserva-email"}:
            return self._apagar(atual)
        return False

    def _apagar_expirada(self, uid, agora):
        conta = self._ler(uid)  # Rele: query/reserva podem ter uma versao antiga.
        if not conta or not self._expirada(conta, agora):
            return False
        # Apaga conta ANTES das reservas. Confirmacao concorrente muda o etag:
        # 412 impede apagar tanto a conta ativada quanto as reservas dela.
        if not self._apagar(conta):
            return False
        for campo, valor in (("usuario", conta["usuario_lower"]), ("email", conta["email_lower"])):
            self._liberar_reserva(self.reserva_id(campo, valor), uid)
        return True

    def _liberar_se_expirada(self, reserva, agora):
        uid = reserva.get("uid")
        if reserva.get("tipo") not in {"reserva-usuario", "reserva-email"} or not uid:
            return False
        conta = self._ler(uid)
        if conta:
            return self._apagar_expirada(uid, agora) if self._expirada(conta, agora) else False
        # Nao rouba uma reserva cujo cadastro ainda esta criando a conta.
        if _epoca(reserva.get("criado_em")) < agora - 86400:
            return self._liberar_reserva(reserva["id"], uid)
        return False

    @_proteger
    def obter(self, campo, valor):
        if campo == "id":
            doc = self._ler(valor)
            return doc if doc and doc.get("tipo") == "conta" else None
        if campo not in {"usuario", "email"}:
            raise ValueError("Campo invalido")
        rid = self.reserva_id(campo, valor)
        reserva = self._ler(rid)
        if not reserva:
            return None
        doc = self._ler(reserva.get("uid", ""))
        if doc and self._expirada(doc, time.time()):
            self._apagar_expirada(doc["id"], time.time())
            doc = self._ler(doc["id"])
        elif not doc:
            self._liberar_se_expirada(reserva, time.time())
        return doc if doc and doc.get("tipo") == "conta" else None

    def _reservar(self, campo, valor, uid, agora):
        rid = self.reserva_id(campo, valor)
        doc = {"id": rid, "tipo": "reserva-" + campo, "uid": uid, "criado_em": _iso(agora)}
        for _ in range(3):
            try:
                return self.conectar().create_item(body=doc)
            except Exception as erro:
                if _status(erro) != 409:
                    raise
                atual = self._ler(rid)
                if atual is None:
                    continue
                if self._liberar_se_expirada(atual, agora):
                    continue
                raise ContaDuplicada() from None
        raise ContaDuplicada()

    @_proteger
    def criar(self, uid, usuario, senha_hash, email, perfil, nonce, agora):
        usuario, email = usuario.strip().lower(), email.strip().lower()
        ids = [self.reserva_id("usuario", usuario), self.reserva_id("email", email)]
        doc = {k: v for k, v in perfil.items() if not k.startswith("_")}
        doc.update({"id": uid, "tipo": "conta", "usuario": usuario, "usuario_lower": usuario,
                    "email": email, "email_lower": email, "senha_hash": senha_hash,
                    "confirmado": False, "criado_em": _iso(agora), "nonce": nonce, "ultimo_envio": 0})
        try:
            self._reservar("usuario", usuario, uid, agora)
            self._reservar("email", email, uid, agora)
            return self.conectar().create_item(body=doc)
        except Exception as erro_original:
            if not isinstance(erro_original, (ContaDuplicada, ContasIndisponiveis)):
                registrar_falha_contas("criar", erro_original)
            # Compensacao por propriedade + etag, inclusive se create aplicou e
            # a resposta se perdeu. Nunca apaga reservas de outra tentativa.
            # Sem conectividade, nao existe rollback atomico entre particoes.
            try:
                possivel = self._ler(uid)
                if possivel and possivel.get("tipo") == "conta" and possivel.get("nonce") == nonce:
                    if not self._apagar(possivel):
                        raise ContasIndisponiveis()
                for rid in reversed(ids):
                    self._liberar_reserva(rid, uid)
            except Exception as erro:
                registrar_falha_contas("criar_rollback", erro)
                raise ContasIndisponiveis() from None
            raise

    @_proteger
    def limpar_pendentes(self, agora, forcar=False):
        with self._lock_limpeza:
            anterior = self._ultima_limpeza.get(self.fornecedor, float("-inf"))
            if not forcar and agora - anterior < self.INTERVALO_LIMPEZA:
                return 0
            self._ultima_limpeza[self.fornecedor] = agora
        consulta = ("SELECT * FROM c WHERE c.tipo = @tipo AND c.confirmado = @confirmado "
                    "AND c.criado_em < @limite")
        removidas = 0
        for doc in self.conectar().query_items(query=consulta,
                parameters=[{"name": "@tipo", "value": "conta"},
                            {"name": "@confirmado", "value": False},
                            {"name": "@limite", "value": _iso(agora - 86400)}],
                enable_cross_partition_query=True):
            removidas += self._apagar_expirada(doc["id"], agora)
        return removidas

    @_proteger
    def reservar_envio(self, uid, agora):
        for _ in range(4):
            doc = self._ler(uid)
            if not doc or doc.get("tipo") != "conta" or doc.get("confirmado") or self._expirada(doc, agora):
                return False
            if doc.get("ultimo_envio", 0) > agora - 60:
                return False
            novo = dict(doc, ultimo_envio=agora)
            try:
                self._substituir(doc, novo)
                return True
            except Exception as erro:
                if _status(erro) == 404:
                    return False
                if _status(erro) != 412:
                    raise
        return False

    @_proteger
    def confirmar(self, uid, nonce):
        for _ in range(4):
            doc = self._ler(uid)
            if (not doc or doc.get("tipo") != "conta" or doc.get("confirmado")
                    or not nonce or doc.get("nonce") != nonce or self._expirada(doc, time.time())):
                return False
            novo = dict(doc, confirmado=True, nonce=None)
            try:
                self._substituir(doc, novo)
                return True
            except Exception as erro:
                if _status(erro) == 404:
                    return False
                if _status(erro) != 412:
                    raise
        return False

    @_proteger
    def read_item(self, item, partition_key=None):
        doc = self._ler(item)
        if doc is None:
            raise KeyError(item)
        if doc.get("tipo") != "conta":
            return doc  # Perfil legado intacto, sem campos de login inventados.
        return {k: v for k, v in doc.items() if k not in self.CAMPOS_LOGIN and not k.startswith("_")}

    @_proteger
    def upsert_item(self, doc):
        for _ in range(4):
            atual = self._ler(doc["id"])
            if atual is None:
                raise KeyError(doc["id"])
            if atual.get("tipo") != "conta":
                # O comportamento antigo do container continua para perfis legados.
                novo = dict(doc)
                if atual.get("xp_regras_versao") == 6:
                    for campo in ("xp", "paradas_progresso", "xp_regras_versao", "xp_mapa_contabilizado", "xp_externo_legado", "borda_mapa"):
                        if campo in atual:
                            novo[campo] = atual[campo]
                if "cosmeticos" in atual:
                    novo["cosmeticos"] = atual["cosmeticos"]
                try:
                    self._substituir(atual, novo)
                    return doc
                except Exception as erro:
                    if _status(erro) == 412:
                        continue
                    raise
            novos_campos = {k: v for k, v in doc.items() if k not in self.CAMPOS_LOGIN
                            and not k.startswith("_") and k not in {"id", "cosmeticos"}}
            novo = dict(atual, **novos_campos)
            if atual.get("xp_regras_versao") == 6:
                for campo in ("xp", "paradas_progresso", "xp_regras_versao", "xp_mapa_contabilizado", "xp_externo_legado", "borda_mapa"):
                    if campo in atual:
                        novo[campo] = atual[campo]
            try:
                self._substituir(atual, novo)
                return doc
            except Exception as erro:
                if _status(erro) == 404:
                    raise KeyError(doc["id"]) from None
                if _status(erro) != 412:
                    raise
        raise ContasIndisponiveis()

    @_proteger
    def alterar_perfil(self, uid, transformar):
        """Progresso/XP derivados da versão atual, nunca de snapshot atrasado."""
        for _ in range(12):
            atual = self._ler(uid)
            if atual is None:
                raise KeyError(uid)
            novo = transformar(deepcopy(atual))
            if novo == atual:
                return novo
            try:
                self._substituir(atual, novo)
                return novo
            except Exception as erro:
                if _status(erro) != 412:
                    raise
        raise ContasIndisponiveis()

    @_proteger
    def alterar_cosmeticos(self, uid, transformar):
        """Compra/equipamento na mesma partição; callback puro reexecutado no 412.

        Só este caminho escreve cosmeticos. Progresso e credenciais vêm sempre
        da versão mais recente; não há upsert cego nem crédito vindo do cliente.
        """
        for _ in range(8):
            atual = self._ler(uid)
            if atual is None:
                raise KeyError(uid)
            estado = transformar(deepcopy(atual.get("cosmeticos")))
            if estado == atual.get("cosmeticos"):
                return estado
            novo = dict(atual, cosmeticos=estado)
            try:
                self._substituir(atual, novo)
                return estado
            except Exception as erro:
                if _status(erro) == 404:
                    raise KeyError(uid) from None
                if _status(erro) != 412:
                    raise
        raise ContasIndisponiveis()
