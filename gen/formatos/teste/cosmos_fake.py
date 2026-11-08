"""Fake em memoria do SDK publico usado pelas contas. Nunca abre rede/.env."""
from collections import Counter
from copy import deepcopy
from threading import RLock

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosHttpResponseError


def erro(status):
    return CosmosHttpResponseError(status_code=status, message="Erro simulado")


class CosmosFake:
    def __init__(self):
        self.docs = {}
        self.lock = RLock()
        self.versao = 0
        self.calls = Counter()
        self.down = False
        self.before_create = None
        self.after_create = None
        self.before_replace = None
        self.before_delete = None

    def _chamar(self, metodo):
        with self.lock:
            self.calls[metodo] += 1
        if self.down:
            raise erro(503)

    def _gravar(self, doc):
        novo = deepcopy(doc)
        self.versao += 1
        novo["_etag"] = str(self.versao)
        self.docs[novo["id"]] = novo
        return deepcopy(novo)

    def create_item(self, body, **kwargs):
        self._chamar("create_item")
        if self.before_create:
            self.before_create(deepcopy(body))
        with self.lock:
            if body["id"] in self.docs:
                raise erro(409)
            salvo = self._gravar(body)
        if self.after_create:
            self.after_create(deepcopy(salvo))
        return salvo

    def read_item(self, item, partition_key, **kwargs):
        self._chamar("read_item")
        if partition_key != item:
            raise erro(400)
        with self.lock:
            if item not in self.docs:
                raise erro(404)
            return deepcopy(self.docs[item])

    def upsert_item(self, body, **kwargs):
        self._chamar("upsert_item")
        with self.lock:
            return self._gravar(body)

    def replace_item(self, item, body, etag=None, match_condition=None, **kwargs):
        self._chamar("replace_item")
        if self.before_replace:
            self.before_replace(item, deepcopy(body))
        with self.lock:
            if item not in self.docs:
                raise erro(404)
            if match_condition == MatchConditions.IfNotModified and etag != self.docs[item]["_etag"]:
                raise erro(412)
            if body["id"] != item:
                raise erro(400)
            return self._gravar(body)

    def delete_item(self, item, partition_key, etag=None, match_condition=None, **kwargs):
        self._chamar("delete_item")
        if self.before_delete:
            self.before_delete(item)
        if partition_key != item:
            raise erro(400)
        with self.lock:
            if item not in self.docs:
                raise erro(404)
            if match_condition == MatchConditions.IfNotModified and etag != self.docs[item]["_etag"]:
                raise erro(412)
            del self.docs[item]

    def query_items(self, query, parameters, enable_cross_partition_query=False, **kwargs):
        self._chamar("query_items")
        assert enable_cross_partition_query
        params = {p["name"]: p["value"] for p in parameters}
        assert params["@tipo"] == "conta" and params["@confirmado"] is False
        with self.lock:
            return [deepcopy(d) for d in self.docs.values()
                    if d.get("tipo") == params["@tipo"] and d.get("confirmado") is False
                    and d.get("criado_em", "z") < params["@limite"]]

    def alterar(self, uid, **campos):
        """Simula uma escrita concorrente externa, gerando outro etag."""
        with self.lock:
            return self._gravar(dict(self.docs[uid], **campos))
