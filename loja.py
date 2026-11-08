"""Menus cosméticos separados do onboarding. XP e conteúdo não são moedas."""
import hmac
import json
import secrets
import re
import unicodedata
from pathlib import Path
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from contas_cosmos import ContasIndisponiveis, OperacaoCosmeticaInvalida
from herois import sprite_heroi, pode_piscar, sheet_heroi
from titulos import titulo_fr, titulo_loja

ROOT = Path(__file__).resolve().parent
CATALOGO = json.loads((ROOT / 'data/loja.json').read_text(encoding='utf-8'))
CONQUISTAS = json.loads((ROOT / 'data/conquistas.json').read_text(encoding='utf-8'))
ITENS = {i['id']: i for i in CATALOGO['itens']}
NOMES_PETS = json.loads((ROOT / 'data/pets-nomes.json').read_text(encoding='utf-8'))
CATEGORIAS = {'personagem': 'Personagem', 'particulas': 'Partículas', 'titulos': 'Títulos', 'pets': 'Pets', 'cenarios': 'Cenários'}


def estado_cosmetico(valor, teste=False):
    if valor is None:
        return {'versao': 1, 'cristais': CATALOGO['saldo_inicial']['teste' if teste else 'real'],
                'comprados': [], 'equipados': {}}
    # Corrupção não pode resetar o saldo nem conceder cristais novamente.
    if (not isinstance(valor, dict) or valor.get('versao') != 1
            or type(valor.get('cristais')) is not int or valor['cristais'] < 0
            or not isinstance(valor.get('comprados'), list)
            or not all(isinstance(x, str) for x in valor['comprados'])
            or not isinstance(valor.get('equipados'), dict)):
        raise ContasIndisponiveis()
    nomes = valor.get('nomes_pets', {})
    if not isinstance(nomes, dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in nomes.items()):
        raise ContasIndisponiveis()
    return dict(valor, comprados=list(valor['comprados']), equipados=dict(valor['equipados']))


def operar(valor, acao, item_id='', categoria='', teste=False):
    if categoria == 'molduras' or (isinstance(item_id, str) and item_id.startswith('moldura-')):
        raise OperacaoCosmeticaInvalida('Molduras são conquistadas por nível, nunca compradas com cristais; a maior desbloqueada é usada automaticamente.', 403)
    estado = estado_cosmetico(valor, teste)
    if acao == 'retirar':
        if categoria not in CATEGORIAS:
            raise OperacaoCosmeticaInvalida('Categoria inválida.')
        estado['equipados'].pop(categoria, None)
        return estado
    item = ITENS.get(item_id) if isinstance(item_id, str) else None
    if item is None:
        raise OperacaoCosmeticaInvalida('Item desconhecido.', 404)
    if acao == 'comprar':
        if item.get('padrao'):
            return estado  # Posse intrínseca/gratuita; não cria cobrança ou moeda.
        # Reenvios e cliques duplos não cobram novamente, mesmo após equipar.
        if item_id in estado['comprados']:
            return estado
        if estado['cristais'] < item['preco']:
            raise OperacaoCosmeticaInvalida('Cristais insuficientes.', 409)
        estado['cristais'] -= item['preco']
        estado['comprados'].append(item_id)
    elif acao == 'equipar':
        if item_id not in estado['comprados'] and not item.get('padrao'):
            raise OperacaoCosmeticaInvalida('Compre o item antes de equipar.', 403)
        estado['equipados'][item['categoria']] = item_id
    else:
        raise OperacaoCosmeticaInvalida('Operação inválida.')
    return estado


def item_exibicao(item, estado):
    if item['categoria'] != 'pets':
        return item
    return dict(item, nome_padrao=item['nome'],
                nome=estado.get('nomes_pets', {}).get(item['id'], item['nome']))


def itens_equipados(estado):
    equipados = {cat: item_exibicao(ITENS[iid], estado) for cat, iid in estado['equipados'].items()
                 if isinstance(iid, str) and iid in ITENS
                 and (iid in estado['comprados'] or ITENS[iid].get('padrao'))
                 and ITENS[iid]['categoria'] == cat}
    # O cenário original é sempre possuído/equipado implicitamente quando
    # não há outro selecionado. Nenhuma migração de saldo/inventário necessária.
    equipados.setdefault('cenarios', ITENS['cenario-refugio'])
    return equipados


def renomear_pet(valor, item_id, nome, resetar=False, teste=False):
    estado = estado_cosmetico(valor, teste)
    item = ITENS.get(item_id)
    if not item or item['categoria'] != 'pets':
        raise OperacaoCosmeticaInvalida('Companheiro desconhecido.', 404)
    if item_id not in estado['comprados']:
        raise OperacaoCosmeticaInvalida('Você precisa possuir esse companheiro.', 403)
    nomes = dict(estado.get('nomes_pets', {}))
    if resetar:
        nomes.pop(item_id, None)
    else:
        if not isinstance(nome, str):
            raise OperacaoCosmeticaInvalida('Nome inválido.')
        nome = unicodedata.normalize('NFC', nome.strip())
        if not 1 <= len(nome) <= NOMES_PETS['maximo'] or not any(c.isalnum() for c in nome) or not all(c.isalpha() or c.isdigit() or c in " -'" for c in nome):
            raise OperacaoCosmeticaInvalida('Use de 1 a 16 caracteres: letras, números, espaços, hífen ou apóstrofo.')
        simples = ''.join(c for c in unicodedata.normalize('NFKD', nome.casefold()) if not unicodedata.combining(c))
        simples = simples.translate(str.maketrans('01345789', 'oieastbg'))
        palavras = re.findall('[a-z]+', simples)
        if any(p in NOMES_PETS['bloqueados'] for p in palavras) or ''.join(palavras) in NOMES_PETS['bloqueados']:
            raise OperacaoCosmeticaInvalida('Escolha outro nome para seu companheiro.')
        nomes[item_id] = nome
    estado['nomes_pets'] = nomes
    return estado


def vitrine_molduras(bordas, nivel):
    """Vitrine somente leitura. Fonte única: os limites originais BORDAS_MAPA.
    A moldura ativa continua sendo a maior conquistada pelo XP servidor.
    Não cria itens, preços, posse comprável ou seleção manual no inventário.
    """
    return [dict(id=b['id'], nome=b['nome'], nivel=i+1, xp=b['xp'],
                 sprite=f"mapa/bordas/borda-{b['id']}@2x.png",
                 conquistada=nivel >= i+1, ativa=nivel == i+1)
            for i,b in enumerate(bordas)]


def avaliar_conquistas(perfil, ids_batalha, boss_id):
    """Somente leitura do progresso servidor; localStorage nunca é prova."""
    progresso = (perfil or {}).get('paradas_progresso') or {}
    if not isinstance(progresso, dict):
        progresso = {}
    registros = [v for v in progresso.values() if isinstance(v, dict) and v.get('concluida_em')]
    def numero(reg, chave):
        v = reg.get(chave, 0)
        return v if type(v) is int and v >= 0 else 0
    resultado = []
    for dado in CONQUISTAS['conquistas']:
        criterio = dado['criterio']; desbloqueada = False
        if criterio == 'boss':
            reg = progresso.get(boss_id)
            desbloqueada = isinstance(reg, dict) and bool(reg.get('concluida_em'))
        elif criterio == 'batalha_repetida':
            desbloqueada = any(numero(progresso.get(pid, {}) if isinstance(progresso.get(pid), dict) else {}, 'tentativas') >= dado['minimo'] for pid in ids_batalha)
        elif criterio == 'sem_erros':
            desbloqueada = any(numero(r, 'acertos') > 0 and type(r.get('erros')) is int and r['erros'] == 0 for r in registros)
        elif criterio == 'erros':
            desbloqueada = sum(numero(r, 'erros') for r in registros) >= dado['minimo']
        resultado.append(dict(dado, desbloqueada=desbloqueada))
    return resultado


def registrar_loja(app, contexto):
    bp = Blueprint('loja', __name__)

    def token():
        if not isinstance(session.get('loja_csrf'), str):
            session['loja_csrf'] = secrets.token_urlsafe(32)
        return session['loja_csrf']

    def preparar():
        perfil = contexto['perfil_atual']() or {}
        from xp import reconciliar
        reconciliar(contexto, perfil)
        from economia import reconciliar_perfil
        if perfil:
            reconciliar_perfil(contexto, perfil)
        estado = estado_cosmetico(perfil.get('cosmeticos'), contexto['modo_teste']())
        equipados = itens_equipados(estado)
        avatar = contexto['avatar_mapa'](perfil)
        paleta = equipados.get('personagem', {}).get('paleta')
        sprite = sheet_heroi(avatar,paleta)
        sprite_fechado = sprite
        previews_paletas = {p: sheet_heroi(avatar,p) for p in ('esmeralda','ametista','rubi')}
        batalhas = [contexto['id_parada'](1, n) for n in range(1, 41)
                    if (contexto['carregar_parada'](1, n) or {}).get('formato') == 'batalha']
        xp = contexto['xp_do_perfil'](perfil)
        moldura = contexto['borda_por_xp'](xp)
        return dict(perfil=perfil, estado=estado, equipados=equipados, avatar=avatar, sprite=sprite, sprite_fechado=sprite_fechado,
                    previews_paletas=previews_paletas, heroi_pisca=pode_piscar(avatar,paleta),
                    nome=contexto['_nome_personagem_salvo'](perfil) or contexto['NOMES_PERSONAGEM'][avatar],
                    titulo_equipado=titulo_fr(equipados.get('titulos'),avatar),
                    xp=xp, nivel=moldura+1, moldura=contexto['MOLDURAS'][moldura+1],
                    molduras_nivel=vitrine_molduras(contexto['BORDAS_MAPA'], moldura+1),
                    conquistas=avaliar_conquistas(perfil, batalhas, contexto['id_parada'](1, 40)),
                    csrf=token(), catalogo=CATALOGO, categorias=CATEGORIAS, nota_conquistas=CONQUISTAS['nota'])

    @bp.get('/heroi')
    def heroi():
        return render_template('heroi.html', **preparar())

    @bp.get('/conquistas')
    def conquistas():
        return redirect(url_for('loja.heroi') + '#conquistas')

    @bp.get('/loja')
    def inicio():
        categoria = request.args.get('categoria', 'personagem')
        if categoria not in CATEGORIAS:
            abort(404)
        dados = preparar()
        return render_template('loja.html', categoria=categoria,
                               itens=[titulo_loja(i,dados['avatar']) if categoria=='titulos' else item_exibicao(i,dados['estado']) for i in CATALOGO['itens'] if i['categoria'] == categoria], **dados)

    def gravar(acao):
        corpo = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(corpo, dict) and not hasattr(corpo, 'get'):
            return jsonify(ok=False, erro='Dados inválidos.'), 400
        recebido = request.headers.get('X-CSRF-Token') or corpo.get('csrf', '')
        esperado = session.get('loja_csrf', '')
        if not isinstance(recebido, str) or not esperado or not hmac.compare_digest(recebido.encode("utf-8"), esperado.encode("utf-8")):
            return jsonify(ok=False, erro='Sessão inválida. Atualize a página.'), 403
        iid = corpo.get('item', '')
        categoria = corpo.get('categoria', '')
        if not isinstance(iid, str) or not isinstance(categoria, str):
            return jsonify(ok=False, erro='Dados inválidos.'), 400
        try:
            uid = contexto['id_teste']() if contexto['modo_teste']() else session['uid']
            estado = contexto['usuarios']().alterar_cosmeticos(uid,
                lambda anterior: renomear_pet(anterior, iid, corpo.get('nome'), corpo.get('resetar') is True or (not request.is_json and corpo.get('resetar') == '1'), contexto['modo_teste']())
                if acao == 'renomear' else operar(anterior, acao, iid, categoria, contexto['modo_teste']()))
        except OperacaoCosmeticaInvalida as erro:
            if request.is_json:
                return jsonify(ok=False, erro=str(erro)), erro.status
            return render_template('loja-erro.html', mensagem=str(erro)), erro.status
        except (ContasIndisponiveis, KeyError):
            if request.is_json:
                return jsonify(ok=False, erro='Não foi possível salvar. Tente novamente.'), 503
            return render_template('loja-erro.html', mensagem='Não foi possível salvar. Tente novamente.'), 503
        if request.is_json:
            return jsonify(ok=True, estado=estado)
        if acao == 'renomear':
            flash('Nome do companheiro atualizado!')
            return redirect(url_for('loja.heroi') + '#nome-pet', code=303)
        flash({'comprar': 'Compra guardada no seu inventário!', 'equipar': 'Item equipado!', 'retirar': 'Item retirado.'}[acao])
        cat = ITENS.get(iid, {}).get('categoria', categoria)
        return redirect(url_for('loja.inicio', categoria=cat if cat in CATEGORIAS else 'personagem'), code=303)

    @bp.post('/loja/comprar')
    def comprar():
        return gravar('comprar')

    @bp.post('/loja/equipar')
    def equipar():
        return gravar('equipar')

    @bp.post('/loja/retirar')
    def retirar():
        return gravar('retirar')

    @bp.post('/loja/pet/nome')
    def nome_pet():
        return gravar('renomear')

    @app.context_processor
    def aparencia_do_perfil():
        # Só superfícies ativas do perfil. Fogueira/onboarding ficam intactos.
        if request.endpoint not in ('mapa', 'parada'):
            return {}
        if request.endpoint == 'parada':
            etapa = contexto['carregar_parada'](**request.view_args)
            if not etapa or etapa.get('formato') != 'batalha':
                return {}
        try:
            p = contexto['perfil_atual']() or {}
            e = itens_equipados(estado_cosmetico(p.get('cosmeticos'), contexto['modo_teste']()))
        except ContasIndisponiveis:
            p, e = {}, {}  # Cosmético indisponível nunca impede jogar.
        avatar = contexto['avatar_mapa'](p)
        if request.endpoint == 'parada':
            previa = request.args.get('personagem', '')
            if previa.isdigit() and 1 <= int(previa) <= len(contexto['ORDEM_PERSONAGENS']):
                avatar = contexto['ORDEM_PERSONAGENS'][int(previa)-1]
            elif previa in contexto['AVATAR_IDS']:
                avatar = previa
        from aparencia import apresentar
        visual = apresentar(avatar, contexto['_nome_personagem_salvo'](p) or contexto['NOMES_PERSONAGEM'][avatar], e)
        # v7b: partículas só no cenário /heroi e nas prévias da loja.
        # Suprime apenas a apresentação de mapa/batalha; posse/equipamento
        # permanecem no documento, sem alterar templates/engines congelados.
        visual['efeito'] = ''
        return {'cosmetica': visual, 'efeito_loja_chuva': False}

    app.register_blueprint(bp)
    from economia import registrar_economia
    registrar_economia(app, contexto)
