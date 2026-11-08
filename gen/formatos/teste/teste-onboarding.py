"""Fluxo completo + concorrencia com CosmosFake: nenhuma rede, e-mail real ou .env."""
import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch

PROJETO = Path(__file__).resolve().parents[3] / "out"
# Permite copiar gen/ para dentro do projeto no patch distribuido.
if not (PROJETO / "app.py").exists():
    PROJETO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJETO))
with patch("dotenv.load_dotenv", return_value=False):
    import app as A
from contas_cosmos import ContasCosmos, ContaDuplicada, ContasIndisponiveis
from cosmos_fake import CosmosFake, erro
from datetime import datetime, timezone
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from werkzeug.security import check_password_hash

ok = 0

def chk(nome, cond):
    global ok
    if not cond:
        raise AssertionError(nome)
    ok += 1
    print("OK  ", nome)


def destino(r, caminho):
    return r.status_code == 302 and urlsplit(r.headers.get("Location", "")).path == caminho


cosmos = CosmosFake()
with patch.object(A, "get_users_container", return_value=cosmos):
    A.app.config.update(TESTING=True)
    A.USUARIOS_TESTE.add("teste")
    A._CADASTROS_IP.clear()
    enviados = []
    def enviar_falso(conta):
        link = A._link_confirmacao(conta)
        enviados.append((conta["usuario"], link))
        return link
    with patch.object(A, "_enviar_confirmacao", side_effect=enviar_falso):
        c = A.app.test_client()
        for rota in ("/", "/personagem", "/nivelamento", "/missao", "/mapa", "/parada/1/1", "/praca/1", "/avatar", "/health"):
            chk("anonimo " + rota + " -> login", destino(c.get(rota), "/login"))
        chk("POST JSON anonimo nao simula sucesso", c.post("/nivelamento", json={}).status_code == 401)
        html = c.get("/login").get_data(as_text=True)
        chk("login preserva marca e subtitulo", "wordmark-chemin-web.png" in html and "Sua jornada rumo ao francês" in html)
        chk("cadastro na mesma tela", "data-modo=\"cadastro\"" in html and "data-cadastro" in html)
        chk("atalho cadastrar abre a mesma tela", destino(c.get("/cadastrar"), "/login"))

        def registrar(usuario="viajante", email="viajante@example.com", senha="ensaio123", confirmacao=None):
            return c.post("/login", data={"acao": "cadastrar", "usuario": usuario, "email": email,
                "senha": senha, "confirmacao": senha if confirmacao is None else confirmacao})
        chk("usuario invalido", registrar(usuario="a!").status_code == 400)
        chk("senha curta", registrar(senha="123").status_code == 400)
        chk("confirmacao diferente", registrar(confirmacao="outrasenha").status_code == 400)
        for email in ("sem-arroba", "a..b@example.com", ".a@example.com", "a@example", "a@-ex.com"):
            chk("email invalido: " + email, registrar(email=email).status_code == 400)
        chk("teste reservado", registrar(usuario="TESTE").status_code == 409)
        r = registrar()
        chk("cadastro pendente na tela de login", r.status_code == 200 and "Enviamos um link para viajante@example.com" in r.get_data(as_text=True))
        chk("link local visivel apenas em teste", "Confirmar e-mail</a>" in r.get_data(as_text=True))
        chk("sem sessao antes de confirmar", destino(c.get("/mapa"), "/login"))
        conta = A.contas().obter("usuario", "VIAJANTE")
        chk("senha armazenada com hash", conta["senha_hash"] != "ensaio123" and check_password_hash(conta["senha_hash"], "ensaio123"))
        chk("conta ainda inativa", conta["confirmado"] == 0)
        r = c.post("/login", data={"usuario": "viajante", "senha": "ensaio123"})
        chk("login nao confirmado bloqueado com reenvio", r.status_code == 403 and "Confirme seu e-mail" in r.get_data(as_text=True) and "Reenviar link" in r.get_data(as_text=True))
        chk("reenvio limitado a 60 s", c.post("/reenviar-confirmacao", data={"usuario": "viajante"}).status_code == 429)
        chk("username unico sem diferenciar caixa", registrar(usuario="VIAJANTE", email="outro@example.com").status_code == 409)
        chk("email unico sem diferenciar caixa", registrar(usuario="outro", email="VIAJANTE@EXAMPLE.COM").status_code == 409)
        chk("link invalido", c.get("/confirmar/nao-e-um-token").status_code == 400)
        with A.app.test_request_context():
            with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=int(time.time()) - 86401):
                token_antigo = A._serializador().dumps({"id": conta["id"], "email": conta["email"], "nonce": conta["nonce"]})
        r = c.get("/confirmar/" + token_antigo)
        chk("link de 24 h expirado", r.status_code == 400 and "expirou" in r.get_data(as_text=True))
        cosmos.alterar(conta["id"], ultimo_envio=0)
        chk("reenvio depois do intervalo", c.post("/reenviar-confirmacao", data={"usuario": "viajante"}).status_code == 200)
        link = urlsplit(enviados[-1][1]).path
        chk("confirmar ativa e leva ao personagem", destino(c.get(link), "/personagem"))
        chk("link nao pode ser reutilizado", A.app.test_client().get(link).status_code == 400)
        chk("personagem renderiza", c.get("/personagem").status_code == 200)
        html_personagem = c.get("/personagem").get_data(as_text=True)
        chk("personagem inclui trilha v2 e volume padrao", 'src="/static/audio/trilha-fundo.js"' in html_personagem and 'data-trilha="/static/audio/trilhas/trilha-personagem.ogg?v=2"' in html_personagem and 'data-volume="0.25"' in html_personagem)
        ogg_personagem = c.get("/static/audio/trilhas/trilha-personagem.ogg?v=2")
        chk("personagem OGG servido e valido", ogg_personagem.status_code == 200 and ogg_personagem.data.startswith(b"OggS") and ogg_personagem.mimetype in ("audio/ogg", "application/ogg"))
        chk("nao pula escolha", destino(c.get("/mapa"), "/personagem"))
        chk("API exige etapa anterior", c.post("/nivelamento", json={}).status_code == 409)
        chk("nao pula pelo avatar legado", destino(c.post("/avatar", data={"avatar": "mago-m", "nome": "Alex"}), "/personagem"))
        chk("nome vazio rejeitado", c.post("/personagem", data={"avatar": "mago-m", "nome": ""}).status_code == 400)
        chk("salva personagem -> nivelamento", destino(c.post("/personagem", data={"avatar": "mago-m", "nome": "Alex"}), "/nivelamento"))
        chk("nivelamento renderiza", c.get("/nivelamento").status_code == 200)
        # Exercita o JavaScript do template, incluindo os tres modelos existentes.
        with tempfile.TemporaryDirectory(prefix="chemin-escrita-") as pasta:
            html = Path(pasta) / "nivelamento.html"
            html.write_text(c.get("/nivelamento?parte=3").get_data(as_text=True), encoding='utf-8')
            js = Path(__file__).with_name("pular-escrita.js")
            resultado_js = subprocess.run(["node", str(js), str(html)], capture_output=True, text=True)
            if resultado_js.returncode:
                print(resultado_js.stderr)
            print(resultado_js.stdout.strip())
            chk("JS pular/continuar preserva validacao e destino", resultado_js.returncode == 0)
        chk("nao pula teste", destino(c.get("/missao"), "/nivelamento"))
        c.get("/sair")
        chk("retoma teste depois de login", destino(c.post("/login", data={"usuario": "viajante", "senha": "ensaio123"}), "/nivelamento"))
        chk("respostas invalidas", c.post("/nivelamento", json=[]).status_code == 400)
        respostas = {"item1": "C", "item2": "B", "item3": "B", "item4": "B", "item5": "C", "item6": "B",
            "item7": {"prenom": "Alex", "age": "25", "ville": "Recife", "nationalite": "brésilien"},
            "item8": "Bonjour, je suis Alex. Je viens du Brésil et je parle un peu français. Je veux apprendre chaque jour avec mes amis et découvrir la ville.",
            "fala": {"estado": "pulado"}, "modelo": 1}
        for n in (0, 24, 41):
            r_invalido = c.post("/nivelamento", json=dict(respostas, item8=" ".join(["bonjour"] * n)))
            chk(f"API escrita nao pulada rejeita {n} palavras", r_invalido.status_code == 400)
        chk("API nao aceita string como flag de pular", c.post("/nivelamento", json=dict(respostas, item8="", escrita_pulada="true")).status_code == 400)
        r = c.post("/nivelamento", json=respostas)
        chk("teste concluido -> pergaminho", r.status_code == 200 and r.get_json().get("proximo") == "/missao")
        perfil = A.contas().read_item(conta["id"])
        chk("respostas e conclusao persistidas", perfil.get("nivelamento_concluido_em") and perfil["nivelamento_respostas"]["item1"] == "C")
        chk("nenhuma regua ou pontuacao inventada", "nivelamento_pontos" not in perfil and "nivelamento_pontos_detalhe" not in perfil)
        chk("envio normal nao exclui escrita", perfil["nivelamento_respostas"]["escrita_pulada"] is False and perfil["nivelamento_respostas"]["escrita_itens_excluidos"] == [])
        chk("nao pula pergaminho pelo mapa", destino(c.get("/mapa"), "/missao"))
        chk("nao pula pergaminho pela home", destino(c.get("/"), "/missao"))
        c.get("/sair")
        chk("retoma pergaminho depois de login", destino(c.post("/login", data={"usuario": "viajante", "senha": "ensaio123"}), "/missao"))
        r = c.get("/missao")
        chk("pergaminho de boas-vindas renderiza", r.status_code == 200 and "Bienvenue" in r.get_data(as_text=True))
        chk("botao existente do pergaminho -> home -> mapa", destino(c.get("/"), "/mapa"))
        chk("mapa renderiza com musica v2", c.get("/mapa").status_code == 200 and "?v=2" in c.get("/mapa").get_data(as_text=True))
        chk("onboarding marcado como concluido", A.contas().read_item(conta["id"]).get("onboarding_concluido_em"))
        chk("logout limpa sessao", destino(c.get("/sair"), "/login") and destino(c.get("/mapa"), "/login"))
        chk("senha incorreta", c.post("/login", data={"usuario": "viajante", "senha": "errada"}).status_code == 401)
        chk("login recorrente -> mapa direto", destino(c.post("/login", data={"usuario": "VIAJANTE", "senha": "ensaio123"}), "/mapa"))
        chk("perfil Cosmos em nova instancia", ContasCosmos(lambda: cosmos).read_item(conta["id"])["nome_personagem"] == "Alex")
        chk("logout legado limpa conta normal tambem", destino(c.get("/teste/sair"), "/login") and destino(c.get("/mapa"), "/login"))
        with patch.dict(os.environ, {"NCL_SENHA_TESTE": ""}):
            chk("login teste preservado", destino(c.post("/login", data={"usuario": "teste", "senha": "qualquer"}), "/mapa"))
        chk("teste continua livre", all(c.get(p).status_code == 200 for p in ("/personagem", "/nivelamento", "/missao", "/mapa", "/praca/1")))
        c.get("/sair")
        # Sem modo teste, nao vaza link de ativacao na tela.
        A.app.config["TESTING"] = False
        with patch.dict(os.environ, {"NCL_MODO_TESTE": "0"}):
            r = registrar(usuario="segunda", email="segunda@example.com")
            chk("link oculto fora de teste", r.status_code == 200 and "Confirmar e-mail</a>" not in r.get_data(as_text=True))
        A.app.config["TESTING"] = True

    # Exercita a composicao SMTP, mas o transporte e apenas um mock.
    conta = A.contas().obter("usuario", "segunda")
    with A.app.test_request_context(), patch.dict(os.environ, {"MAIL_SERVER": "smtp.example.com", "MAIL_FROM": "jogo@example.com", "MAIL_USERNAME": "", "MAIL_USE_TLS": "true", "MAIL_PORT": "587"}), patch.object(A.smtplib, "SMTP") as smtp:
        A._enviar_confirmacao(conta)
        mensagem = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        chk("SMTP texto + HTML e nome da marca", mensagem.is_multipart() and "Chemin des Étoiles" in mensagem["From"])
        chk("SMTP inicia TLS", smtp.return_value.__enter__.return_value.starttls.called)
    with A.app.test_request_context(), patch.dict(os.environ, {"MAIL_SERVER": ""}), patch.object(A.app.logger, "warning") as logger:
        link = A._enviar_confirmacao(conta)
        chk("sem SMTP retorna link local e registra no terminal", "/confirmar/" in link and logger.called)
    # Um novo jogador pula a parte 3 inteira e conclui o mesmo fluxo, sem nota zero.
    uid_pular = "qa-pular-escrita"
    perfil_pular = {"id": uid_pular, "avatar": "mago-m", "nome_personagem": "Alex", "nome": "Alex",
                    "moldura": 1, "onboarding_versao": 1, "xp": 0,
                    "nivelamento_pontos": 7, "nivelamento_pontos_detalhe": {"total": 7}}
    A.contas().criar(uid_pular, "qa_pular", "hash-fake", "qa_pular@example.com", perfil_pular, "nonce-pular", time.time())
    A.contas().confirmar(uid_pular, "nonce-pular")
    cp = A.app.test_client()
    with cp.session_transaction() as sessao:
        sessao["uid"] = uid_pular
    dados_pulados = dict(respostas, escrita_pulada=True, item7={}, item8="")
    r = cp.post("/nivelamento", json=dados_pulados)
    chk("API aceita escrita pulada vazia e mantem pergaminho", r.status_code == 200 and r.get_json()["proximo"] == "/missao")
    p = A.contas().read_item(uid_pular)
    salvas = p["nivelamento_respostas"]
    chk("escrita persistida explicitamente pulada", salvas["escrita_pulada"] is True)
    chk("ficha e mensagem excluidas da avaliacao", salvas["escrita_itens_excluidos"] == ["item7", "item8"])
    chk("pular nao grava zero nem conserva nota antiga", p.get("nivelamento_pontos") is None and p.get("nivelamento_pontos_detalhe") is None)
    avaliacao = A.pontuar_nivelamento(salvas, "m")
    chk("helper legado nao trata escrita pulada como zero", avaliacao["item7"] is None and avaliacao["item8"] is None and avaliacao["total"] is None)
    chk("helper legado identifica itens excluidos", avaliacao["itens_excluidos"] == ["item7", "item8"])
    chk("escrita pulada conclui nivelamento", bool(p.get("nivelamento_concluido_em")))
    chk("pular nao pula o pergaminho", destino(cp.get("/mapa"), "/missao"))
    chk("pergaminho apos pular renderiza", cp.get("/missao").status_code == 200)
    chk("botao do pergaminho apos pular -> mapa", destino(cp.get("/"), "/mapa") and cp.get("/mapa").status_code == 200)
    # Limites inclusivos permanecem aceitos no envio normal, sem criar classificacao.
    for n in (25, 40):
        r = cp.post("/nivelamento", json=dict(respostas, item8=" ".join(["bonjour"] * n), escrita_pulada=False))
        chk(f"API escrita normal aceita {n} palavras", r.status_code == 200)
    p = A.contas().read_item(uid_pular)
    chk("resposta normal posterior nao fica marcada pulada", p["nivelamento_respostas"]["escrita_pulada"] is False and p["nivelamento_respostas"]["escrita_itens_excluidos"] == [])

    # Conta e reservas no mesmo users, perfil sem aninhamento e sem segredos na renderizacao.
    ativo = A.contas().obter("usuario", "viajante")
    chk("conta conserva perfil no mesmo documento", ativo["tipo"] == "conta" and ativo["nome_personagem"] == "Alex" and "perfil" not in ativo)
    chk("point read do perfil nao expoe credenciais", "senha_hash" not in A.contas().read_item(ativo["id"]))
    chk("confirmacao nao foi desfeita por salvar perfil", ativo["confirmado"] is True and ativo["nonce"] is None)
    pendente = A.contas().obter("usuario", "segunda")
    expirado = datetime.fromtimestamp(time.time() - 86401, timezone.utc).isoformat()
    cosmos.alterar(pendente["id"], criado_em=expirado)
    A.contas().limpar_pendentes(time.time(), forcar=True)
    chk("limpa somente pendentes antigas", A.contas().obter("usuario", "segunda") is None and A.contas().obter("usuario", "viajante") is not None)
    chk("limpeza libera usuario e email", all(ContasCosmos.reserva_id(campo, valor) not in cosmos.docs for campo, valor in (("usuario", "segunda"), ("email", "segunda@example.com"))))
    consultas = cosmos.calls["query_items"]
    A.contas().limpar_pendentes(time.time())
    chk("varredura limitada a uma por 20 min", cosmos.calls["query_items"] == consultas)
    antes = cosmos.calls["query_items"]
    A.contas().obter("usuario", "viajante")
    A.contas().obter("email", "VIAJANTE@EXAMPLE.COM")
    chk("lookup usa reservas e point reads, sem query", cosmos.calls["query_items"] == antes)

    legado = {"id": "legado", "avatar": "bardo-m", "nome": "Legado", "xp": 75, "moldura": 1, "personalizado": "preservar"}
    cosmos.create_item(legado)
    p = A.contas().read_item("legado")
    p["nome"] = "Outro nome"
    A.contas().upsert_item(p)
    l = cosmos.read_item("legado", "legado")
    chk("perfil legado preservado sem campos novos", l["personalizado"] == "preservar" and l["xp"] == 75 and "tipo" not in l and "confirmado" not in l)
    with c.session_transaction() as sessao:
        sessao.clear(); sessao["uid"] = "legado"
    chk("sessao legada continua lendo personagem", c.get("/nivelamento").status_code == 200)
    c.get("/sair")

    cosmos.down = True
    r = c.post("/login", data={"usuario": "viajante", "senha": "ensaio123"})
    chk("Cosmos fora: login tem erro amigavel sem 500", r.status_code == 503 and "Não foi possível acessar as contas" in r.get_data(as_text=True))
    r = c.post("/login", data={"acao": "cadastrar", "usuario": "terceira", "email": "terceira@example.com", "senha": "ensaio123", "confirmacao": "ensaio123"})
    chk("Cosmos fora: cadastro tem erro amigavel", r.status_code == 503 and "Não foi possível acessar as contas" in r.get_data(as_text=True))
    chk("Cosmos fora: reenvio amigavel", c.post("/reenviar-confirmacao", data={"usuario": "viajante"}).status_code == 503)
    chamadas = sum(cosmos.calls.values())
    with patch.dict(os.environ, {"NCL_SENHA_TESTE": ""}):
        r = c.post("/login", data={"usuario": "teste", "senha": "qualquer"})
    chk("teste entra mesmo com Cosmos fora", destino(r, "/mapa") and c.get("/mapa").status_code == 200)
    chk("teste nunca toca Cosmos", sum(cosmos.calls.values()) == chamadas)
    c.get("/sair")
    cosmos.down = False
    with c.session_transaction() as sessao:
        sessao["uid"] = ativo["id"]
    cosmos.down = True
    chk("sessao existente tambem mostra erro amigavel", c.get("/mapa").status_code == 503)
    cosmos.down = False
    c.get("/sair")
    A._CADASTROS_IP["127.0.0.1"] = [time.time()] * 5
    r = c.post("/login", data={"acao": "cadastrar", "usuario": "limite", "email": "limite@example.com", "senha": "ensaio123", "confirmacao": "ensaio123"})
    chk("limite de cadastro por IP preservado", r.status_code == 429)


def nova_conta(store, uid, usuario, email, agora=None):
    return store.criar(uid, usuario, "hash-simulado", email,
        {"id": uid, "xp": 0, "moldura": 1, "onboarding_versao": 1}, "nonce-" + uid,
        time.time() if agora is None else agora)


# Dois processos logicos competem pelas mesmas reservas, sem lock de unicidade no app.
for campo in ("usuario", "email"):
    fake = CosmosFake()
    store = ContasCosmos(lambda: fake)
    barreira = Barrier(2)
    def antes_criar(doc):
        if doc.get("tipo") == "reserva-" + campo:
            barreira.wait(timeout=5)
    fake.before_create = antes_criar
    def competidor(n):
        try:
            usuario = "disputa" if campo == "usuario" else "disputa" + str(n)
            email = "disputa@example.com" if campo == "email" else f"disputa{n}@example.com"
            nova_conta(store, "corrida" + str(n), usuario, email)
            return True
        except ContaDuplicada:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(competidor, (1, 2)))
    fake.before_create = None
    chk("unicidade concorrente por " + campo, resultados.count(True) == 1 and resultados.count(False) == 1)
    chk("rollback nao deixa reserva do perdedor: " + campo, len(fake.docs) == 3 and sum(d.get("tipo") == "conta" for d in fake.docs.values()) == 1)

# Falha antes/depois de criar a conta: inclui resposta perdida apos escrita bem-sucedida.
for apos in (False, True):
    fake = CosmosFake(); store = ContasCosmos(lambda: fake)
    def falhar(doc):
        if doc.get("tipo") == "conta":
            raise erro(503)
    if apos: fake.after_create = falhar
    else: fake.before_create = falhar
    try:
        nova_conta(store, "falhou", "falhou", "falhou@example.com")
        raise AssertionError("Era para falhar")
    except ContasIndisponiveis:
        pass
    chk("rollback completo " + ("depois" if apos else "antes") + " da escrita da conta", not fake.docs)

fake = CosmosFake(); store = ContasCosmos(lambda: fake)
def falhar_email(doc):
    if doc.get("tipo") == "reserva-email": raise erro(503)
fake.before_create = falhar_email
try:
    nova_conta(store, "parcial", "parcial", "parcial@example.com")
except ContasIndisponiveis:
    pass
chk("rollback quando apenas username estava reservado", not fake.docs)
fake.before_create = None

# Reserva expirada e encontrada durante novo cadastro, mesmo sem a varredura.
nova_conta(store, "velha", "reusar", "reusar@example.com", time.time() - 86401)
nova_conta(store, "nova", "REUSAR", "REUSAR@EXAMPLE.COM")
chk("cadastro recupera reservas de conta expirada", store.obter("usuario", "reusar")["id"] == "nova" and "velha" not in fake.docs)
# Reserva sem conta por falha de processo: nao e roubada enquanto pode estar em criacao.
rid = store.reserva_id("usuario", "orfa")
fake.create_item({"id": rid, "uid": "inacabada", "tipo": "reserva-usuario", "criado_em": datetime.now(timezone.utc).isoformat()})
try:
    nova_conta(store, "outra", "orfa", "outra@example.com")
    raise AssertionError("Reserva recente nao pode ser roubada")
except ContaDuplicada:
    pass
chk("reserva orfa recente bloqueia nova tentativa", fake.docs[rid]["uid"] == "inacabada")
fake.alterar(rid, criado_em=datetime.fromtimestamp(time.time() - 86401, timezone.utc).isoformat())
nova_conta(store, "recuperada", "orfa", "outra@example.com")
chk("reserva orfa antiga e recuperada", store.obter("usuario", "orfa")["id"] == "recuperada")

# Confirmacao e reenvio simultaneos: etag/412 permitem so um vencedor.
for operacao in ("confirmar", "reservar_envio"):
    fake = CosmosFake(); store = ContasCosmos(lambda: fake)
    nova_conta(store, "concorrente", "concorrente", "concorrente@example.com")
    barreira = Barrier(2)
    def antes_replace(uid, body):
        if uid == "concorrente": barreira.wait(timeout=5)
    fake.before_replace = antes_replace
    def tentativa(_):
        if operacao == "confirmar": return store.confirmar("concorrente", "nonce-concorrente")
        return store.reservar_envio("concorrente", time.time())
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(tentativa, (1, 2)))
    fake.before_replace = None
    chk(operacao + " simultaneo tem um unico vencedor", resultados.count(True) == 1 and resultados.count(False) == 1)

# Limpeza com snapshot antigo nao apaga conta confirmada por outro escritor.
fake = CosmosFake(); store = ContasCosmos(lambda: fake)
nova_conta(store, "ativada", "ativada", "ativada@example.com", time.time() - 86401)
def ativar_na_hora(uid):
    if uid == "ativada":
        fake.before_delete = None
        fake.alterar(uid, confirmado=True, nonce=None)
fake.before_delete = ativar_na_hora
store.limpar_pendentes(time.time(), forcar=True)
chk("cleanup respeita etag e nao apaga ativacao concorrente", len(fake.docs) == 3 and fake.docs["ativada"]["confirmado"] is True)

# Uma exclusao ja feita por outro processo (404) e idempotente e libera as reservas.
fake = CosmosFake(); store = ContasCosmos(lambda: fake)
nova_conta(store, "sumiu", "sumiu", "sumiu@example.com", time.time() - 86401)
def apagar_na_hora(uid):
    if uid == "sumiu":
        fake.before_delete = None
        with fake.lock: del fake.docs[uid]
fake.before_delete = apagar_na_hora
store.limpar_pendentes(time.time(), forcar=True)
chk("cleanup suporta corrida 404", not fake.docs)

# Save de perfil usa a conta atual, nao restaura hash/nonce antigos.
fake = CosmosFake(); store = ContasCosmos(lambda: fake)
nova_conta(store, "perfil", "perfil", "perfil@example.com")
p = store.read_item("perfil"); p["nome_personagem"] = "Alex"
store.confirmar("perfil", "nonce-perfil")
store.upsert_item(p)
chk("salvar perfil preserva credenciais e confirmacao atuais", fake.docs["perfil"]["confirmado"] is True and fake.docs["perfil"]["nonce"] is None and fake.docs["perfil"]["senha_hash"] == "hash-simulado")
# Forca um 412 apenas na primeira tentativa de salvar; depois deve repetir sem perder auth.
def mudar_etag(uid, body):
    fake.before_replace = None
    fake.alterar(uid, ultimo_envio=123)
fake.before_replace = mudar_etag
p["nome_personagem"] = "Outro"
store.upsert_item(p)
chk("save repete apos 412 e preserva campo de login concorrente", fake.docs["perfil"]["ultimo_envio"] == 123 and fake.docs["perfil"]["nome_personagem"] == "Outro")
# IDs Cosmos validos tambem para caracteres especiais permitidos em e-mail.
fake = CosmosFake(); store = ContasCosmos(lambda: fake)
nova_conta(store, "especial", "especial", "a/b?c#d@example.com")
chk("email com caracteres especiais tem reserva codificada", store.obter("email", "a/b?c#d@example.com")["id"] == "especial" and all(not any(c in uid for c in "/?#") for uid in fake.docs))
# Se ate o rollback perde conectividade, a reserva nao e roubada: recupera apos 24 h.
fake = CosmosFake(); store = ContasCosmos(lambda: fake)
def perder_conexao(doc):
    if doc.get("tipo") == "reserva-usuario":
        fake.down = True
        raise erro(503)
fake.after_create = perder_conexao
try:
    nova_conta(store, "interrompida", "interrompida", "interrompida@example.com")
except ContasIndisponiveis:
    pass
fake.down = False; fake.after_create = None
rid = store.reserva_id("usuario", "interrompida")
chk("queda durante rollback mantem reserva sem roubar outra conta", fake.docs[rid]["uid"] == "interrompida" and len(fake.docs) == 1)
fake.alterar(rid, criado_em=datetime.fromtimestamp(time.time() - 86401, timezone.utc).isoformat())
nova_conta(store, "retomada", "interrompida", "interrompida@example.com")
chk("reserva de rollback interrompido recuperada apos 24 h", store.obter("usuario", "interrompida")["id"] == "retomada")
chk("nenhum cliente Cosmos real foi inicializado", A._client is None)
print(f"\n{ok} OK, 0 falhas — Cosmos fake; nenhum e-mail real ou acesso a .env")
