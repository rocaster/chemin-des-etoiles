"""Contas locais persistentes: SQLite, sem acesso ao Cosmos nem leitura de .env."""
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager


class ContasLocais:
    def __init__(self, caminho):
        self.caminho = caminho

    @contextmanager
    def conectar(self):
        Path(self.caminho).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.caminho, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("""CREATE TABLE IF NOT EXISTS contas (
            id TEXT PRIMARY KEY, usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
            senha_hash TEXT NOT NULL, perfil TEXT NOT NULL,
            email TEXT UNIQUE COLLATE NOCASE, confirmado INTEGER NOT NULL DEFAULT 1,
            nonce TEXT, criado_em REAL NOT NULL DEFAULT 0, ultimo_envio REAL NOT NULL DEFAULT 0
        )""")
        # Compatibilidade com a primeira versao local: contas existentes ja estao confirmadas.
        colunas = {r[1] for r in con.execute("PRAGMA table_info(contas)")}
        for nome, tipo in (("email", "TEXT"), ("confirmado", "INTEGER NOT NULL DEFAULT 1"),
                           ("nonce", "TEXT"), ("criado_em", "REAL NOT NULL DEFAULT 0"),
                           ("ultimo_envio", "REAL NOT NULL DEFAULT 0")):
            if nome not in colunas:
                con.execute(f"ALTER TABLE contas ADD COLUMN {nome} {tipo}")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS contas_usuario ON contas(usuario COLLATE NOCASE)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS contas_email ON contas(email COLLATE NOCASE)")
        con.commit()
        try:
            with con:
                yield con
        finally:
            con.close()

    def obter(self, campo, valor):
        if campo not in {"id", "usuario", "email"}:
            raise ValueError("Campo invalido")
        with self.conectar() as con:
            r = con.execute(f"SELECT * FROM contas WHERE {campo} = ? COLLATE NOCASE", (valor,)).fetchone()
            return dict(r) if r else None

    def limpar_pendentes(self, agora):
        with self.conectar() as con:
            con.execute("DELETE FROM contas WHERE confirmado = 0 AND criado_em < ?", (agora - 86400,))

    def criar(self, uid, usuario, senha_hash, email, perfil, nonce, agora):
        with self.conectar() as con:
            con.execute("DELETE FROM contas WHERE confirmado = 0 AND criado_em < ?", (agora - 86400,))
            con.execute("""INSERT INTO contas
                (id,usuario,senha_hash,email,perfil,confirmado,nonce,criado_em)
                VALUES (?,?,?,?,?,0,?,?)""",
                (uid,usuario,senha_hash,email,json.dumps(perfil, ensure_ascii=False),nonce,agora))

    def reservar_envio(self, uid, agora):
        with self.conectar() as con:
            return con.execute("""UPDATE contas SET ultimo_envio = ?
                WHERE id = ? AND confirmado = 0 AND ultimo_envio <= ?""",
                (agora, uid, agora - 60)).rowcount == 1

    def confirmar(self, uid, nonce):
        with self.conectar() as con:
            return con.execute("""UPDATE contas SET confirmado = 1, nonce = NULL
                WHERE id = ? AND nonce = ? AND confirmado = 0""", (uid,nonce)).rowcount == 1

    def read_item(self, item, partition_key=None):
        conta = self.obter("id", item)
        if not conta:
            raise KeyError(item)
        return json.loads(conta["perfil"])

    def upsert_item(self, doc):
        with self.conectar() as con:
            n = con.execute("UPDATE contas SET perfil = ? WHERE id = ?",
                            (json.dumps(doc, ensure_ascii=False), doc["id"])).rowcount
            if not n:
                raise KeyError(doc["id"])
        return doc
