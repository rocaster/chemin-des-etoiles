import hmac
import json
import os
import re
import uuid
import time
import smtplib
from email.message import EmailMessage
from threading import RLock
from html import escape
from urllib.parse import urlsplit
from datetime import datetime, timezone

from azure.cosmos import CosmosClient
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from contas_cosmos import ContasCosmos, ContaDuplicada, ContasIndisponiveis, registrar_falha_contas
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

# Configuracao via variaveis de ambiente; o .env local (se existir) e carregado como antes.
load_dotenv()

app = Flask(__name__)
# Assina o cookie de sessao. Em producao vira um segredo do Key Vault.
app.secret_key = os.environ.get("SECRET_KEY", "dev-somente-local-troque-depois")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DB_NAME = "ncl-exam-db"

CLASSES = {
    "cavaleiro": "Cavaleiro",
    "arqueiro": "Arqueiro",
    "mago": "Mago",
    "bardo": "Bardo",
}
GENEROS = {"m": "masculino", "f": "feminino"}
# Os 8 avatares: "cavaleiro-m", "cavaleiro-f", ...
AVATARES = [
    {"id": f"{c}-{g}", "classe": nome, "genero": GENEROS[g]}
    for c, nome in CLASSES.items()
    for g in ("m", "f")
]
AVATAR_IDS = {a["id"] for a in AVATARES}
NOMES_PERSONAGEM = {
    "arqueiro-f": "Arqueira",
    "arqueiro-m": "Arqueiro",
    "bardo-f": "Barda",
    "bardo-m": "Bardo",
    "cavaleiro-f": "Cavaleira",
    "cavaleiro-m": "Cavaleiro",
    "mago-f": "Maga",
    "mago-m": "Mago",
}


# Molduras por regiao do mapa (1 a 6)
MOLDURAS = {
    1: "moldura-1-madeira.png",
    2: "moldura-2-pedra.png",
    3: "moldura-3-bronze.png",
    4: "moldura-4-prata.png",
    5: "moldura-5-ouro.png",
    6: "moldura-6-diamante.png",
}

_client = None


def get_db():
    global _client
    try:
        if _client is None:
            try:
                conexao = os.environ["COSMOS_CONNECTION"]
            except KeyError as erro:
                registrar_falha_contas("get_db_config", erro, "COSMOS_CONNECTION")
                raise ContasIndisponiveis() from None
            _client = CosmosClient.from_connection_string(conexao)
        return _client.get_database_client(DB_NAME)
    except ContasIndisponiveis:
        raise
    except Exception as erro:
        registrar_falha_contas("get_db", erro)
        raise ContasIndisponiveis() from None


def get_container():
    return get_db().get_container_client("questions")


def get_users_container():
    return get_db().get_container_client("users")


# ===== Usuario de teste (tudo liberado no mapa; nada vai para o Cosmos) =====
# Quem entra pelo /login com um destes nomes ganha o "modo teste". Lista configuravel por variavel de
# ambiente (lida so via os.environ); vazia desliga o modo. Senha: se NCL_SENHA_TESTE estiver definida,
# precisa bater; se nao, qualquer senha nao vazia serve (o modo teste nao le nem grava dados reais).
USUARIOS_TESTE = {u.strip().lower() for u in os.environ.get("NCL_USUARIOS_TESTE", "teste").split(",") if u.strip()}
_LOCK_COSMETICOS_TESTE = RLock()
_PERFIS_TESTE = {}   # perfis de teste em memoria do processo (somem ao reiniciar o servidor)


def modo_teste():
    return session.get("teste") in USUARIOS_TESTE


def id_teste():
    return "teste:" + session.get("teste", "")


class _UsuariosTeste:
    """Mesmo jeito de usar do container 'users', mas em memoria e marcado como teste."""

    def read_item(self, item, partition_key=None):
        doc = _PERFIS_TESTE.get(item)
        if doc is None and modo_teste() and item == id_teste():
            # Sessão de teste pode sobreviver a um reinício; dados são só memória.
            with _LOCK_COSMETICOS_TESTE:
                entrar_modo_teste(session['teste'])
                doc = _PERFIS_TESTE.get(item)
        if doc is None:
            raise KeyError(item)
        return json.loads(json.dumps(doc))

    def upsert_item(self, doc):
        doc = json.loads(json.dumps(doc))
        doc["teste"] = True
        with _LOCK_COSMETICOS_TESTE:
            atual = _PERFIS_TESTE.get(doc["id"], {})
            if atual.get("xp_regras_versao") == 6:
                for campo in ("xp", "paradas_progresso", "xp_regras_versao", "xp_mapa_contabilizado", "xp_externo_legado", "borda_mapa"):
                    if campo in atual:
                        doc[campo] = atual[campo]
            if "cosmeticos" in atual:
                doc["cosmeticos"] = atual["cosmeticos"]
            _PERFIS_TESTE[doc["id"]] = doc
        return doc

    def alterar_perfil(self, uid, transformar):
        with _LOCK_COSMETICOS_TESTE:
            doc = transformar(self.read_item(uid))
            _PERFIS_TESTE[uid] = json.loads(json.dumps(doc))
            return doc

    def alterar_cosmeticos(self, uid, transformar):
        with _LOCK_COSMETICOS_TESTE:
            doc = self.read_item(uid)
            estado = transformar(doc.get("cosmeticos"))
            doc["cosmeticos"] = estado
            _PERFIS_TESTE[uid] = doc
            return json.loads(json.dumps(estado))


def usuarios():
    """Contas/perfis no Cosmos existente; teste continua somente em memoria."""
    if modo_teste():
        return _UsuariosTeste()
    return contas()


def perfil_atual():
    """Le o perfil da pessoa pelo id guardado na sessao. Retorna None se nao existe."""
    uid = id_teste() if modo_teste() else session.get("uid")
    if not uid:
        return None
    try:
        return usuarios().read_item(item=uid, partition_key=uid)
    except ContasIndisponiveis:
        raise
    except Exception:
        return None


def contas():
    return ContasCosmos(get_users_container)


def proxima_etapa(perfil):
    perfil = perfil or {}
    # Perfis anteriores que ja jogaram/fizeram o teste nao repetem a introducao.
    if not perfil.get("onboarding_versao") and (perfil.get("paradas_progresso") or perfil.get("nivelamento_concluido_em")):
        return "mapa"
    if perfil.get("avatar") not in AVATAR_IDS or not (perfil.get("nome_personagem") or perfil.get("nome")):
        return "personagem"
    if not perfil.get("nivelamento_concluido_em"):
        return "nivelamento"
    return "mapa" if perfil.get("onboarding_concluido_em") else "missao"


@app.before_request
def proteger_jornada():
    publicos = {"static", "login", "cadastrar", "confirmar_email", "reenviar_confirmacao", "logout", "teste_sair"}
    publicos.update(app.config.get("ONBOARDING_PREVIEW_ENDPOINTS", ()))
    if request.endpoint in publicos:
        return None
    if not modo_teste() and not session.get("uid"):
        if request.is_json and request.method == "POST":
            return jsonify(ok=False, erro="Entre novamente para continuar.", login=url_for("login")), 401
        return redirect(url_for("login"))
    if modo_teste():
        return None  # Mantem o teste livre para todas as telas/previas.
    perfil = perfil_atual()
    if perfil is None:
        session.clear()
        return redirect(url_for("login"))
    etapa = proxima_etapa(perfil)
    if etapa != "mapa" and request.endpoint != etapa:
        # O botao do pergaminho aponta para home; so ele encerra o onboarding.
        if etapa == "missao" and request.endpoint == "home" and session.get("boas_vindas_vistas") == session.get("uid"):
            return None
        if request.is_json and request.method == "POST":
            return jsonify(ok=False, erro="Conclua a etapa anterior.", proximo=url_for(etapa)), 409
        return redirect(url_for(etapa))


@app.route("/")
def home():
    perfil = perfil_atual()
    if not modo_teste() and proxima_etapa(perfil) == "missao":
        perfil["onboarding_concluido_em"] = datetime.now(timezone.utc).isoformat()
        try:
            usuarios().upsert_item(perfil)
            session.pop("boas_vindas_vistas", None)
        except Exception:
            return "Não foi possível salvar. Volte ao pergaminho e tente novamente.", 503
    return redirect(url_for("mapa"))


@app.route("/avatar", methods=["GET", "POST"])
def avatar():
    return redirect(url_for("personagem"))



def _nome_personagem_salvo(perfil):
    if not perfil:
        return ""
    valor = perfil.get("nome_personagem")
    if not isinstance(valor, str):
        return ""
    return valor.strip()[:20]


def _pagina_personagem(selecionado, erro, nome_personagem, status=200):
    if selecionado not in AVATAR_IDS:
        selecionado = "cavaleiro-f"
    html = render_template(
        "personagem.html",
        selecionado=selecionado,
        erro=erro,
        nome_personagem=nome_personagem or "",
    )
    if status != 200:
        return html, status
    return html


@app.route("/personagem", methods=["GET", "POST"])
def personagem():
    selecionado = request.values.get("sel") or request.form.get("avatar") or "cavaleiro-f"
    if selecionado not in AVATAR_IDS:
        selecionado = "cavaleiro-f"

    if request.method == "POST":
        escolha = request.form.get("avatar", "")
        nome_bruto = request.form.get("nome", "")
        if not isinstance(nome_bruto, str):
            nome_bruto = ""
        nome = nome_bruto.strip()

        if escolha not in AVATAR_IDS:
            return _pagina_personagem(
                "cavaleiro-f",
                "Escolha um personagem.",
                nome[:20],
                400,
            )

        if not nome or len(nome) > 20:
            erro = (
                "Dê um nome ao seu personagem."
                if not nome
                else "O nome pode ter no máximo 20 caracteres."
            )
            return _pagina_personagem(escolha, erro, nome[:20], 400)

        perfil = perfil_atual()
        classe, genero = escolha.split("-")
        uid = session.setdefault("uid", uuid.uuid4().hex)
        # Se a pessoa ja tem perfil, troca so o personagem e mantem o progresso.
        doc = perfil or {
            "id": uid,
            "xp": 0,
            "regiao": "vilarejo",
            "moldura": 1,
            "sequencia_dias": 0,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        doc.update({
            "nome_personagem": nome,
            "nome": nome,
            "avatar": escolha,
            "classe": classe,
            "genero": genero,
        })
        try:
            usuarios().upsert_item(doc)
        except Exception:
            return _pagina_personagem(
                escolha,
                "Não foi possível salvar agora. Tente de novo.",
                nome,
                503,
            )
        return redirect(url_for("mapa" if proxima_etapa(doc) == "mapa" else "nivelamento"))

    return _pagina_personagem(selecionado, None, _nome_personagem_salvo(perfil_atual()))


NIVELAMENTO_GABARITO = {"item1": "C", "item2": "B", "item3": "B", "item4": "B", "item5": "C", "item6": "B"}
NACIONALIDADES_F = {"brésilienne", "canadienne", "française"}
NACIONALIDADES_M = {"brésilien", "canadien", "français"}
_SO_LETRAS = re.compile(r"^[^\W\d_]+(?:[ '’-][^\W\d_]+)*$")
_NUMEROS_FR = r"(?:\d{1,3}|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|dix-sept|dix-huit|dix-neuf|vingt|trente|quarante|cinquante|soixante)(?:[- ](?:et[- ])?\w+)*"


def pontuar_nivelamento(respostas, genero=""):
    """Pontos brutos 0-12 do esquema do rascunho. Sem nivel CEFR/NCLC: a regua esta pendente."""
    r = respostas or {}
    leitura_escuta = sum(1 for k, v in NIVELAMENTO_GABARITO.items() if r.get(k) == v)

    ficha = r.get("item7") or {}
    item7 = 0
    prenom, ville = (ficha.get("prenom") or "").strip(), (ficha.get("ville") or "").strip()
    if _SO_LETRAS.match(prenom) and _SO_LETRAS.match(ville):
        item7 += 1
    idade = (ficha.get("age") or "").strip()
    nac = ficha.get("nationalite") or ""
    if idade.isdigit() and 1 <= int(idade) <= 120 and nac:
        # Concordancia de genero so quando o avatar tem genero e a pessoa nao escolheu "autre".
        if nac == "autre" or genero not in {"f", "m"}:
            item7 += 1
        elif (genero == "f" and nac in NACIONALIDADES_F) or (genero == "m" and nac in NACIONALIDADES_M):
            item7 += 1

    texto = (r.get("item8") or "").lower().replace("’", "'")
    marcas = [
        bool(re.search(r"\bje m'appelle\s+\w|\bje suis\s+[a-zà-ÿ]", texto)),
        bool(re.search(r"\bj'ai\s+" + _NUMEROS_FR + r"\s+ans\b", texto)),
        bool(re.search(r"\bj'habite\s+(?:à|a|au|aux|en|dans)\b|\bje suis d(?:e|u|es|')", texto)),
        bool(re.search(r"\bj'aime\b|\bj'adore\b|\bje fais\b", texto)),
        len(re.findall(r"[^\W_]+(?:['-][^\W_]+)*", texto)) >= 25,
    ]
    n = sum(marcas)
    item8 = 0 if n <= 1 else 1 if n <= 3 else 2

    # Provisorio: sem transcricao, gravou = 1 ponto, pulou = 0.
    fala = 1 if (r.get("fala") or {}).get("estado") == "gravado" else 0

    escrita_pulada = r.get("escrita_pulada") is True
    total = None if escrita_pulada else leitura_escuta + item7 + item8 + fala
    resultado = {
        "total": total,
        "leitura_escuta": leitura_escuta,
        "item7": None if escrita_pulada else item7,
        "item8": None if escrita_pulada else item8,
        "fala": fala,
        "fala_provisoria": True,
    }
    if escrita_pulada:
        # Sem converter ausencia em zero, nem inventar uma regua alternativa.
        resultado.update(escrita_pulada=True, itens_excluidos=["item7", "item8"])
    return resultado


def faixa_missao(pontos):
    if pontos is None or pontos <= 4:
        return "a"
    return "b" if pontos <= 8 else "c"


MENSAGENS_MISSAO = {
    "a": {
        "saudacao": "Bienvenue, {viajante} !",
        "abertura": "os sinos do vilarejo tocam para anunciar a sua chegada.",
        "linhas": [
            "Toda grande jornada começa pelos primeiros passos — e os seus começam hoje.",
            "Cada palavra aprendida será uma pedra firme no seu caminho.",
            "Os guias do Chemin des Étoiles caminharão ao seu lado desde a primeira trilha.",
        ],
        "despedida": "Bon courage, et en route !",
    },
    "b": {
        "saudacao": "Bravo, {viajante} !",
        "abertura": "os batedores contam que você já reconhece os primeiros sinais da estrada.",
        "linhas": [
            "Placas, recados e saudações já não lhe são estranhos.",
            "Agora é hora de transformar esses sinais em passos seguros.",
            "A próxima etapa da jornada espera por você além da ponte do vilarejo.",
        ],
        "despedida": "Courage, l'aventure continue !",
    },
    "c": {
        "saudacao": "Magnifique, {viajante} !",
        "abertura": "você chega ao acampamento com uma base sólida como as muralhas da cidadela.",
        "linhas": [
            "Já lê, escuta e escreve com a firmeza de quem conhece o caminho.",
            "Os mestres reservaram desafios à altura da sua coragem.",
            "Que as estrelas guiem a sua pena e a sua voz.",
        ],
        "despedida": "En avant, et que la quête commence !",
    },
}


NIVELAMENTO_OPCOES = {"A", "B", "C"}
NIVELAMENTO_MODELOS = {1, 2, 3}
NIVELAMENTO_NACIONALIDADES = {
    "brésilienne", "brésilien", "canadienne", "canadien",
    "française", "français", "autre",
}


def _texto_curto(valor, limite):
    if not isinstance(valor, str):
        return ""
    return valor.strip()[:limite]


def _limpar_respostas_nivelamento(dados):
    """Guarda as respostas cruas do teste. Nao calcula nivel: a regua esta pendente."""
    if not isinstance(dados, dict):
        return None
    respostas = {}
    for n in range(1, 7):
        valor = dados.get(f"item{n}")
        respostas[f"item{n}"] = valor if valor in NIVELAMENTO_OPCOES else None
    ficha = dados.get("item7") if isinstance(dados.get("item7"), dict) else {}
    nacionalidade = _texto_curto(ficha.get("nationalite"), 20)
    respostas["item7"] = {
        "prenom": _texto_curto(ficha.get("prenom"), 40),
        "age": _texto_curto(str(ficha.get("age", "")), 3),
        "ville": _texto_curto(ficha.get("ville"), 60),
        "nationalite": nacionalidade if nacionalidade in NIVELAMENTO_NACIONALIDADES else "",
    }
    respostas["item8"] = _texto_curto(dados.get("item8"), 600)
    respostas["escrita_pulada"] = dados.get("escrita_pulada") is True
    respostas["escrita_itens_excluidos"] = ["item7", "item8"] if respostas["escrita_pulada"] else []
    fala = dados.get("fala") if isinstance(dados.get("fala"), dict) else {}
    estado = fala.get("estado")
    duracao = fala.get("duracao_s")
    respostas["fala"] = {
        # O audio nao e enviado; so registramos se houve gravacao ou se foi pulada.
        "estado": estado if estado in {"gravado", "pulado"} else "pulado",
        "duracao_s": round(float(duracao), 1) if isinstance(duracao, (int, float)) and 0 <= duracao <= 31 else None,
    }
    escutas = dados.get("escutas") if isinstance(dados.get("escutas"), dict) else {}
    respostas["escutas"] = {
        k: int(escutas[k]) for k in ("item4", "item5", "item6")
        if isinstance(escutas.get(k), int) and 0 <= escutas[k] <= 2
    }
    return respostas


@app.route("/nivelamento", methods=["GET", "POST"])
def nivelamento():
    if request.method == "POST":
        respostas = _limpar_respostas_nivelamento(request.get_json(silent=True))
        if respostas is None:
            return jsonify(ok=False, erro="Respostas inválidas."), 400
        texto_escrito = (request.get_json(silent=True) or {}).get("item8", "")
        if not respostas["escrita_pulada"] and (not isinstance(texto_escrito, str) or not 25 <= len(re.findall(r"(?:[^\W_]|['’-])+", texto_escrito)) <= 40):
            return jsonify(ok=False, erro="Escreva entre 25 e 40 palavras ou pule esta parte."), 400
        uid = session.setdefault("uid", uuid.uuid4().hex)
        doc = perfil_atual() or {
            "id": uid,
            "xp": 0,
            "regiao": "vilarejo",
            "moldura": 1,
            "sequencia_dias": 0,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        modelo = (request.get_json(silent=True) or {}).get("modelo")
        if respostas["escrita_pulada"]:
            doc["nivelamento_pontos"] = None
            doc["nivelamento_pontos_detalhe"] = None
        doc.update({
            "nivelamento_modelo": modelo if isinstance(modelo, int) and not isinstance(modelo, bool) and modelo in NIVELAMENTO_MODELOS else None,
            "nivelamento_respostas": respostas,
            "nivelamento_concluido_em": datetime.now(timezone.utc).isoformat(),
        })
        try:
            usuarios().upsert_item(doc)
        except Exception:
            return jsonify(ok=False, erro="Não foi possível salvar agora. Tente de novo."), 503
        return jsonify(ok=True, proximo=url_for("missao"))

    try:
        parte = int(request.args.get("parte", "1"))
    except ValueError:
        parte = 1
    parte = min(max(parte, 1), 5)
    perfil = perfil_atual() or {}
    return render_template("nivelamento.html", parte=parte, genero=perfil.get("genero", ""))


@app.route("/missao")
def missao():
    perfil = perfil_atual() or {}
    faixa = request.args.get("faixa", "").lower()
    if faixa not in MENSAGENS_MISSAO:
        respostas = perfil.get("nivelamento_respostas")
        if not respostas:
            if modo_teste():   # usuario de teste: abre a missao com a faixa inicial em vez de exigir o nivelamento
                respostas = None
                faixa = "a"
            else:
                return redirect(url_for("nivelamento"))
        # Sem calcular pontuacao/nivel novos: a regua continua pendente.
        # Preserva apenas a mensagem ja escolhida por dados antigos, quando houver.
        pontos = perfil.get("nivelamento_pontos")
        faixa = faixa_missao(pontos) if isinstance(pontos, int) else "a"
    estado = request.args.get("estado", "fechado")
    if estado not in {"fechado", "abrindo", "aberto"}:
        estado = "fechado"
    nome = perfil.get("nome_personagem") or ""
    genero = perfil.get("genero", "")
    base = MENSAGENS_MISSAO[faixa]
    msg = {
        "saudacao": base["saudacao"].format(viajante="voyageuse" if genero == "f" else "voyageur"),
        "abertura": f"{nome}, {base['abertura']}" if nome else base["abertura"][0].upper() + base["abertura"][1:],
        "linhas": base["linhas"],
        "despedida": base["despedida"],
    }
    session["boas_vindas_vistas"] = session.get("uid")
    return render_template("missao.html", erro=False, faixa=faixa, msg=msg, nome=nome, estado=estado)


MAPA_REGIOES = [
    {"n": 1, "nome": "Hameau des Érables", "x": 57.5, "y": 63.0},
    {"n": 2, "nome": "Forêt Rousse", "x": 51.0, "y": 77.0},
    {"n": 3, "nome": "Bourg du Carrefour", "x": 67.0, "y": 47.5},
    {"n": 4, "nome": "Lac d'Argent", "x": 45.5, "y": 41.0},
    {"n": 5, "nome": "Château Royal", "x": 48.5, "y": 27.0},
    {"n": 6, "nome": "Citadelle de l'Ouest", "x": 21.0, "y": 28.5},
    {"n": 7, "nome": "Monts Givrés", "x": 25.0, "y": 9.5},
    {"n": 8, "nome": "Pics du Nord", "x": 59.0, "y": 8.5},
    {"n": 9, "nome": "Abbaye des Brumes", "x": 71.5, "y": 28.5},
    {"n": 10, "nome": "Tours de l'Aube", "x": 80.5, "y": 42.0},
    {"n": 11, "nome": "Phare du Ponant", "x": 78.0, "y": 79.0},
    {"n": 12, "nome": "Port des Voiles", "x": 34.0, "y": 88.0},
]
MAPA_PARADAS = 40


@app.route("/mapa")
def mapa():
    # Prototipo visual da jornada: progresso so de demonstracao no navegador (localStorage).
    vista = request.args.get("vista", "mundo")
    if vista not in {"mundo", "regiao"}:
        vista = "mundo"
    try:
        parada = int(request.args.get("parada", "0"))
    except ValueError:
        parada = 0
    parada = parada if 1 <= parada <= MAPA_PARADAS + 1 else 0
    try:
        de = int(request.args.get("de", "0"))
    except ValueError:
        de = 0
    de = de if 1 <= de <= MAPA_PARADAS else 0
    # Paradas que ja tem licao de verdade (JSON em data/paradas); as outras seguem no modo demo.
    perfil = perfil_do_mapa()
    from xp import reconciliar
    reconciliar(globals(), perfil)
    reais, titulos, batalhas = {}, {}, []
    for n in range(1, MAPA_PARADAS + 1):
        d = carregar_parada(1, n)
        if d:
            reais[n] = url_for("parada", regiao=1, n=n)
            titulos[n] = d.get("titulo", "")
            if d.get("formato") == "batalha":
                batalhas.append(n)
    ordem = ordem_regiao(1) or {}
    trilha = {"versao": ordem.get("versao", 1), "ordem": ordem.get("ordem", []), "ordem_v1": ordem.get("ordem_v1", [])}
    return render_template("mapa.html", regioes=MAPA_REGIOES, total=MAPA_PARADAS, vista=vista, parada=parada,
                           de=de, paradas_reais=reais, paradas_titulos=titulos, paradas_batalha=batalhas, trilha=trilha,
                           teste=modo_teste(), prefixo=prefixo_local(), avatar=avatar_mapa(perfil),
                           bordas=BORDAS_MAPA, xp_servidor=xp_do_perfil(perfil) if perfil else None,
                           xp_por_id=__import__('xp').XP_POR_ID)


# ---- Paradas (licoes) ----
# Cada parada e um JSON em data/paradas/r<regiao>-p<NN>.json; o motor (static/parada/motor.js) le os blocos e itens.
PARADAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "paradas")


AVATAR_PADRAO = "cavaleiro-m"

# Bordas da ficha do jogador no mapa, liberadas pelo XP total ganho concluindo paradas.
# Cada parada da 1a vez da 10 + 5 por estrela (15 a 25 XP). Os limites seguem o pior caso (15 XP/parada):
# quem conclui as 39 paradas chega ao diamante no fim (585); com media de 20 XP/parada, por volta da parada 30.
BORDAS_MAPA = [
    {"id": "madeira", "nome": "Madeira", "xp": 0},
    {"id": "pedra", "nome": "Pedra", "xp": 45},       # ~3 paradas
    {"id": "bronze", "nome": "Bronze", "xp": 135},    # ~9
    {"id": "prata", "nome": "Prata", "xp": 270},      # ~18
    {"id": "ouro", "nome": "Ouro", "xp": 405},        # ~27
    {"id": "diamante", "nome": "Diamante", "xp": 585},  # ~39
]


def borda_por_xp(xp):
    """Indice (0..5) da maior borda liberada para esse XP."""
    nivel = 0
    for i, b in enumerate(BORDAS_MAPA):
        if (xp or 0) >= b["xp"]:
            nivel = i
    return nivel


def xp_do_perfil(perfil):
    try:
        return max(0, int((perfil or {}).get("xp") or 0))
    except (TypeError, ValueError):
        return 0


def avatar_mapa(perfil=None):
    """Personagem escolhido (para a ficha no mapa); sem escolha, o padrao."""
    av = (perfil or {}).get("avatar")
    return av if av in AVATAR_IDS else AVATAR_PADRAO


def perfil_do_mapa():
    return perfil_atual() if (session.get("uid") or modo_teste()) else None


def prefixo_local():
    """Prefixo das chaves de progresso no localStorage: o teste nao mistura com o de verdade."""
    return "chemin_teste_" if modo_teste() else "chemin_"


# Ordem da trilha por região (data/regioes/r<N>.json): ordem[k-1] = id do conteúdo da etapa k (/parada/<N>/<k>).
# O progresso (servidor e localStorage) fica guardado pelo id de conteúdo; só a etapa atual do mapa é por número.
REGIOES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "regioes")


def ordem_regiao(regiao):
    caminho = os.path.join(REGIOES_DIR, f"r{regiao}.json")
    if not os.path.isfile(caminho):
        return None
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def id_parada(regiao, n):
    """Id do conteúdo da etapa n (ex.: etapa 2 da região 1 → r1-p05). Sem arquivo de ordem: r<regiao>-p<NN>."""
    ordem = (ordem_regiao(regiao) or {}).get("ordem")
    if ordem is None:
        return f"r{regiao}-p{n:02d}"
    return ordem[n - 1] if 1 <= n <= len(ordem) else None


def carregar_parada(regiao, n):
    if not (1 <= regiao <= len(MAPA_REGIOES) and 1 <= n <= MAPA_PARADAS):
        return None
    pid = id_parada(regiao, n)
    if not pid or not re.fullmatch(r"r\d+-p\d{2}", pid):
        return None   # etapa ainda sem conteúdo (demo no mapa)
    caminho = os.path.join(PARADAS_DIR, pid + ".json")
    if not os.path.isfile(caminho):
        return None
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def estrelas_parada(dados, erros):
    for faixa in (dados.get("recompensa") or {}).get("estrelas", []):
        if faixa.get("min_erros", 0) <= erros <= faixa.get("max_erros", 10 ** 6):
            return int(faixa.get("estrelas", 1))
    return 1


def _inteiro(valor, maximo):
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= maximo:
        return None
    return valor


@app.route("/parada/<int:regiao>/<int:n>")
def parada(regiao, n):
    dados = carregar_parada(regiao, n)
    if dados is None:
        abort(404)
    if dados.get("formato") == "batalha":
        return tela_batalha(regiao, n, dados)
    if dados.get("formato") in FORMATOS_PARADA:
        # Templates data-driven (conversa, historia, biblioteca, cartas). Previa: ?passo=N, ?estado=erro|digitar|aberta, ?tela=recompensa|forja
        previa = {}
        try:
            passo = int(request.args.get("passo", "0"))
        except ValueError:
            passo = 0
        if 1 <= passo <= 60:
            previa["passo"] = passo
        if request.args.get("estado") in {"erro", "digitar", "aberta"}:
            previa["estado"] = request.args["estado"]
        if request.args.get("tela") in {"recompensa", "forja"}:
            previa["tela"] = request.args["tela"]
        return render_template("formato.html", dados=dados, regiao=regiao, n=n, previa=previa,
                               pid=id_parada(regiao, n), total=MAPA_PARADAS,
                               teste=modo_teste(), prefixo=prefixo_local())
    # Parametros de previa (nao salvam nada): ?bloco=N, ?item=K, ?estado=erro|gravando|dialogo, ?tela=recompensa
    previa = {}
    for chave, maximo in (("bloco", len(dados["blocos"])), ("item", 50)):
        try:
            v = int(request.args.get(chave, "0"))
        except ValueError:
            v = 0
        if 1 <= v <= maximo:
            previa[chave] = v
    if request.args.get("estado") in {"erro", "gravando", "dialogo"}:
        previa["estado"] = request.args["estado"]
    if request.args.get("tela") == "recompensa":
        previa["tela"] = "recompensa"
    return render_template("parada.html", dados=dados, regiao=regiao, n=n, previa=previa,
                           pid=id_parada(regiao, n), total=MAPA_PARADAS,
                           teste=modo_teste(), prefixo=prefixo_local())


# ===== Batalha: parada de progressão (formato "batalha"). Vitória conclui a parada pela rota normal; XP 0 (pausado) =====
PASTA_BATALHAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "batalhas")
ORDEM_PERSONAGENS = [a["id"] for a in AVATARES]   # ?personagem=1..8 nesta ordem


def carregar_batalha(bid):
    if not re.fullmatch(r"r\d+-b\d{2}", str(bid or "")):
        return None
    caminho = os.path.join(PASTA_BATALHAS, f"{bid}.json")
    if not os.path.isfile(caminho):
        return None
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def tela_batalha(regiao, n, parada_dados):
    """Parada de batalha (ex.: etapa 11 = r1-p09 → data/batalhas/r1-b01.json). Debug: ?personagem=1..8, ?inimigo=, ?tela=vitoria|derrota."""
    dados = carregar_batalha(parada_dados.get("batalha"))
    if dados is None:
        abort(404)
    perfil = perfil_do_mapa()
    heroi = avatar_mapa(perfil)
    escolha = request.args.get("personagem", "")
    if escolha.isdigit() and 1 <= int(escolha) <= len(ORDEM_PERSONAGENS):
        heroi = ORDEM_PERSONAGENS[int(escolha) - 1]
    elif escolha in AVATAR_IDS:
        heroi = escolha
    if heroi != avatar_mapa(perfil) or escolha:   # ?personagem= de depuração: mostra o nome do personagem escolhido
        nome = NOMES_PERSONAGEM.get(heroi, "Héros")
    else:
        nome = _nome_personagem_salvo(perfil) or NOMES_PERSONAGEM.get(heroi, "Héros")
    inimigo = request.args.get("inimigo", "")
    if inimigo not in dados["inimigos"]:
        inimigo = ""   # vazio: o JS sorteia um inimigo da floresta
    tela = request.args.get("tela") if request.args.get("tela") in {"vitoria", "derrota"} else ""
    return render_template("batalha.html", dados=dados, parada=parada_dados, regiao=regiao, n=n, pid=id_parada(regiao, n),
                           heroi=heroi, nome=nome, inimigo=inimigo, tela=tela, teste=modo_teste(), prefixo=prefixo_local())


@app.route("/batalha/<int:n>")
def batalha(n):
    """Atalho antigo: /batalha/1 → a etapa que usa essa batalha (r1-b01 = batalha final, etapa 11), mantendo os parâmetros."""
    bid = f"r1-b{n:02d}"
    for k in range(1, MAPA_PARADAS + 1):
        d = carregar_parada(1, k)
        if d and d.get("formato") == "batalha" and d.get("batalha") == bid:
            return redirect(url_for("parada", regiao=1, n=k, **request.args.to_dict()))
    abort(404)


FORMATOS_PARADA = {"conversa", "historia", "biblioteca", "cartas"}
PASTA_PRACA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "praca")


@app.route("/praca/<int:regiao>")
def praca(regiao):
    """Praça de imersão: fora da trilha, sem progresso, sem XP, nada é salvo."""
    caminho = os.path.join(PASTA_PRACA, f"r{regiao}.json")
    if not os.path.isfile(caminho):
        abort(404)
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    return render_template("praca.html", dados=dados, regiao=regiao, teste=modo_teste(),
                           transcricao=request.args.get("transcricao") == "1",
                           pessoa=request.args.get("pessoa", "")[:20])


@app.route("/parada/<int:regiao>/<int:n>/concluir", methods=["POST"])
def parada_concluir(regiao, n):
    dados = carregar_parada(regiao, n)
    if dados is None:
        abort(404)
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        return jsonify(ok=False, erro="Dados inválidos."), 400
    acertos = _inteiro(corpo.get("acertos"), 1000)
    erros = _inteiro(corpo.get("erros"), 1000)
    duracao = _inteiro(corpo.get("duracao_s", 0), 86400)
    fala_pendente = corpo.get("fala_pendente")
    if acertos is None or erros is None or duracao is None or not isinstance(fala_pendente, bool):
        return jsonify(ok=False, erro="Dados inválidos."), 400
    pid = id_parada(regiao, n)
    uid = id_teste() if modo_teste() else session.setdefault("uid", uuid.uuid4().hex)
    doc = perfil_atual() or {
        "id": uid,
        "xp": 0,
        "regiao": "vilarejo",
        "moldura": 1,
        "sequencia_dias": 0,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }
    from xp import concluir
    estrelas = estrelas_parada(dados, erros)
    agora = datetime.now(timezone.utc).isoformat()
    resultado = {}
    entrada = dict(acertos=acertos, erros=erros, duracao_s=duracao, fala_pendente=fala_pendente)
    def transformar(atual):
        atualizado, meta = concluir(atual, pid, dados, entrada, agora, estrelas, borda_por_xp, BORDAS_MAPA)
        resultado.clear(); resultado.update(meta)
        return atualizado
    try:
        usuarios().alterar_perfil(uid, transformar)
    except Exception:
        return jsonify(ok=False, erro="Não foi possível salvar agora. O progresso ficou neste aparelho."), 503
    extra = {"teste": True} if modo_teste() else {}
    return jsonify(ok=True, **resultado, **extra)


@app.errorhandler(ContasIndisponiveis)
def erro_contas_indisponiveis(erro):
    mensagem = "Não foi possível acessar as contas agora. Tente novamente em instantes."
    if request.is_json and request.method == "POST":
        return jsonify(ok=False, erro=mensagem), 503
    return _tela_login(mensagem, 503)


def _tela_login(erro=None, status=200, **dados):
    return render_template("login.html", erro=erro, **dados), status


def _email_valido(email):
    if len(email) > 254 or email.count("@") != 1:
        return False
    local, dominio = email.split("@")
    if not 1 <= len(local) <= 64 or local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
        return False
    partes = dominio.split(".")
    return len(partes) >= 2 and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in partes)


def _serializador():
    return URLSafeTimedSerializer(app.secret_key, salt="chemin-confirmar-email-v1")


def _link_confirmacao(conta):
    base = os.environ.get("APP_BASE_URL", "http://localhost:5000").rstrip("/")
    partes = urlsplit(base)
    if partes.scheme not in {"http", "https"} or not partes.netloc or partes.query or partes.fragment:
        raise ValueError("APP_BASE_URL invalida")
    token = _serializador().dumps({"id": conta["id"], "email": conta["email"], "nonce": conta["nonce"]})
    return base + url_for("confirmar_email", token=token)


def _enviar_confirmacao(conta):
    link = _link_confirmacao(conta)
    servidor = os.environ.get("MAIL_SERVER")
    if not servidor:
        app.logger.warning("Confirmacao local (sem SMTP): %s", link)
        return link
    msg = EmailMessage()
    remetente = os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME")
    if not remetente:
        raise ValueError("Configure MAIL_FROM")
    msg["From"] = "Chemin des Étoiles <" + remetente + ">"
    msg["To"] = conta["email"]
    msg["Subject"] = "Confirme seu e-mail — Chemin des Étoiles"
    msg.set_content("Bienvenue!\n\nPara ativar sua conta, clique no link abaixo:\n" + link +
                    "\n\nO link vale por 24 horas. Se você não pediu esta conta, ignore esta mensagem.")
    msg.add_alternative('<p>Bienvenue!</p><p>Para ativar sua conta, <a href="' + escape(link, quote=True) +
                        '">confirme seu e-mail</a>.</p><p>O link vale por 24 horas. Se você não pediu esta conta, ignore esta mensagem.</p>', subtype="html")
    with smtplib.SMTP(servidor, int(os.environ.get("MAIL_PORT", "587")), timeout=15) as smtp:
        if os.environ.get("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}:
            smtp.starttls()
        usuario = os.environ.get("MAIL_USERNAME")
        if usuario:
            smtp.login(usuario, os.environ.get("MAIL_PASSWORD", ""))
        smtp.send_message(msg)
    return None


def _despachar_confirmacao(conta):
    if not contas().reservar_envio(conta["id"], time.time()):
        return _tela_login("Aguarde 60 segundos antes de pedir outro link.", 429, reenviar=conta["usuario"])
    try:
        link = _enviar_confirmacao(conta)
    except Exception:
        # Nao registra erro de SMTP: pode conter dados privados do provedor.
        return _tela_login("Não foi possível enviar o e-mail agora. Tente reenviar o link em 60 segundos.",
                           503, reenviar=conta["usuario"])
    mostrar = app.testing or os.environ.get("NCL_MODO_TESTE") == "1"
    aviso = "Enviamos um link para " + conta["email"]
    if not os.environ.get("MAIL_SERVER"):
        aviso += ". Modo local sem SMTP: use o link no terminal do servidor; nenhum e-mail foi enviado."
    return _tela_login(aviso=aviso, reenviar=conta["usuario"], link_confirmacao=link if mostrar else None)


def _entrar_conta(conta):
    session.clear()
    session["uid"] = conta["id"]
    session["conta_cosmos"] = True


_CADASTROS_IP = {}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if modo_teste():
            return redirect(url_for("mapa", vista="mundo"))
        if session.get("uid") and perfil_atual():
            return redirect(url_for(proxima_etapa(perfil_atual())))
        return _tela_login(modo="cadastro" if request.args.get("modo") == "cadastro" else "entrar")
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "")
    cadastro = request.form.get("acao") == "cadastrar"
    if cadastro:
        email = request.form.get("email", "").strip().lower()
        campos = dict(modo="cadastro", usuario=usuario, email=email)
        if not re.fullmatch(r"[a-z0-9_][a-z0-9_.-]{2,29}", usuario):
            return _tela_login("Use de 3 a 30 caracteres: letras sem acento, números, ponto, traço ou sublinhado.", 400, **campos)
        if not _email_valido(email):
            return _tela_login("Informe um e-mail válido.", 400, **campos)
        if not 6 <= len(senha) <= 128:
            return _tela_login("A senha deve ter de 6 a 128 caracteres.", 400, **campos)
        if senha != request.form.get("confirmacao", ""):
            return _tela_login("As senhas não coincidem.", 400, **campos)
        contas().limpar_pendentes(time.time())
        if usuario in USUARIOS_TESTE or contas().obter("usuario", usuario):
            return _tela_login("Este usuário já está em uso. Escolha outro.", 409, **campos)
        if contas().obter("email", email):
            return _tela_login("Este e-mail já está em uso.", 409, **campos)
        agora = time.time()
        # Limite simples por processo; nao confia em X-Forwarded-For recebido do cliente.
        for ip in list(_CADASTROS_IP):
            _CADASTROS_IP[ip] = [t for t in _CADASTROS_IP[ip] if t > agora - 3600]
            if not _CADASTROS_IP[ip]:
                del _CADASTROS_IP[ip]
        tentativas = _CADASTROS_IP.setdefault(request.remote_addr or "local", [])
        if len(tentativas) >= 5:
            return _tela_login("Muitas contas criadas por aqui. Tente novamente em uma hora.", 429, **campos)
        uid = uuid.uuid4().hex
        perfil = {"id": uid, "xp": 0, "regiao": "vilarejo", "moldura": 1,
                  "sequencia_dias": 0, "criado_em": datetime.now(timezone.utc).isoformat(), "onboarding_versao": 1}
        try:
            conta = contas().criar(uid, usuario, generate_password_hash(senha), email, perfil, uuid.uuid4().hex, agora)
        except ContaDuplicada:
            return _tela_login("Usuário ou e-mail já está em uso.", 409, **campos)
        tentativas.append(agora)
        session.clear()
        return _despachar_confirmacao(conta)
    if usuario in USUARIOS_TESTE and senha:
        exigida = os.environ.get("NCL_SENHA_TESTE")
        if exigida and not hmac.compare_digest(senha.encode(), exigida.encode()):
            return _tela_login("Senha do usuário de teste incorreta.", 401)
        session.clear()
        entrar_modo_teste(usuario)
        return redirect(url_for("mapa", vista="mundo"))
    contas().limpar_pendentes(time.time())
    conta = contas().obter("usuario", usuario)
    if not conta or not check_password_hash(conta["senha_hash"], senha):
        return _tela_login("Usuário ou senha incorretos.", 401, usuario=usuario)
    if not conta["confirmado"]:
        return _tela_login("Confirme seu e-mail para entrar.", 403, reenviar=usuario)
    _entrar_conta(conta)
    return redirect(url_for(proxima_etapa(perfil_atual())))


@app.route("/confirmar/<token>")
def confirmar_email(token):
    try:
        dados = _serializador().loads(token, max_age=86400)
    except SignatureExpired:
        return _tela_login("Este link expirou. Entre com usuário e senha para reenviar o link.", 400)
    except BadSignature:
        return _tela_login("Link de confirmação inválido.", 400)
    if not isinstance(dados, dict):
        return _tela_login("Link de confirmação inválido.", 400)
    conta = contas().obter("id", dados.get("id", ""))
    if not conta or conta["email"] != dados.get("email") or not contas().confirmar(conta["id"], dados.get("nonce")):
        return _tela_login("Este link já foi usado ou não é válido. Entre na sua conta.", 400)
    _entrar_conta(conta)
    return redirect(url_for(proxima_etapa(perfil_atual())))


@app.route("/reenviar-confirmacao", methods=["POST"])
def reenviar_confirmacao():
    usuario = request.form.get("usuario", "").strip().lower()
    conta = contas().obter("usuario", usuario)
    if not conta or conta["confirmado"]:
        return _tela_login(aviso="Se a conta estiver aguardando confirmação, enviaremos um novo link.")
    return _despachar_confirmacao(conta)


@app.route("/sair")
def logout():
    session.clear()
    return redirect(url_for("login"))


def entrar_modo_teste(usuario):
    session["teste"] = usuario
    pid = id_teste()
    if pid not in _PERFIS_TESTE:
        avatar = sorted(AVATAR_IDS)[0]
        classe, genero = avatar.split("-")
        _UsuariosTeste().upsert_item({
            "id": pid, "nome": "Teste", "nome_personagem": "Teste", "avatar": avatar, "classe": classe,
            "genero": genero, "xp": 0, "regiao": "vilarejo", "moldura": 1, "sequencia_dias": 0,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        })


@app.route("/teste/zerar", methods=["POST"])
def teste_zerar():
    # Zera so o progresso do usuario de teste (perfil em memoria); o navegador limpa as chaves chemin_teste_*.
    if not modo_teste():
        abort(404)
    def limpar(doc):
        for k in ("paradas_progresso", "nivelamento_respostas", "nivelamento_pontos", "nivelamento_pontos_detalhe",
                  "nivelamento_modelo", "nivelamento_concluido_em"):
            doc.pop(k, None)
        doc.update(xp=0, xp_regras_versao=6, xp_mapa_contabilizado=0, xp_externo_legado=0,
                   borda_mapa=BORDAS_MAPA[0]['id'])
        return doc
    _UsuariosTeste().alterar_perfil(id_teste(), limpar)
    return jsonify(ok=True)


@app.route("/teste/sair")
def teste_sair():
    return logout()


@app.route("/cadastrar")
def cadastrar():
    return redirect(url_for("login", modo="cadastro"))


@app.route("/health")
def health():
    try:
        get_container().read()
        get_users_container().read()
        return jsonify(status="ok", cosmos="conectado")
    except Exception as e:
        return jsonify(status="erro", detalhe=str(e)), 500


from simulados import registrar_simulados
registrar_simulados(app, usuarios, perfil_atual)


# Menus cosméticos novos; nenhuma alteração nas rotas congeladas.
from loja import registrar_loja
registrar_loja(app, globals())


if __name__ == "__main__":
    app.run(debug=True)
