"""FR por gênero nas superfícies de jogo; tradução/explicação PT na loja."""
import copy,re
from html import unescape
import pytest
from test_loja import ctx,A,post,ROOT,abastecer
from loja import ITENS
from herois import AVATARES
from titulos import titulo_fr

TABELA={
 'titulo-viajante':('Voyageur des étoiles','Voyageuse des étoiles'),
 'titulo-guardiao':('Gardien des mots','Gardienne des mots'),
 'titulo-voz':('Voix du village','Voix du village'),
 'titulo-coroa':('Couronne de l’entêtement','Couronne de l’entêtement')}

def perfil(fake,teste):return A._PERFIS_TESTE['teste:teste'] if teste else fake.docs['real']
def avatar_atual(fake,teste,avatar):
    if teste:perfil(fake,teste)['avatar']=avatar
    else:fake.alterar('real',avatar=avatar)

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('avatar',sorted(AVATARES))
@pytest.mark.parametrize('iid',TABELA)
def test_titulo_fr_em_todo_perfil_e_preview_pt_no_pergaminho(ctx,teste,avatar,iid):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste);avatar_atual(fake,teste,avatar)
    feminino=avatar.endswith('-f');fr=TABELA[iid][feminino];item=ITENS[iid]
    loja=c.get('/loja?categoria=titulos').text
    cards=dict(re.findall(r'<article[^>]+data-item="([^"]+)"[^>]*>(.*?)</article>',loja,re.S))
    for chave,card in cards.items():
        meta=ITENS[chave];esperado=TABELA[chave][feminino]
        nome,previa=re.search(r'<span class="preview-titulo"><small>(.*?)</small><span lang="fr">(.*?)</span>',card,re.S).groups()
        assert unescape(nome)=='Luna' and unescape(previa)==esperado
        pt=meta.get('nome_pt_f',meta['nome']) if feminino else meta['nome']
        assert unescape(re.search(r'<h3>(.*?)</h3>',card,re.S)[1])==pt
        assert 'Tradução de' in card and meta['descricao'] in unescape(card)
    for _ in range(2):assert post(c,t,item=iid).json['estado']['cristais']==910
    assert post(c,t,'/loja/equipar',item=iid).json['estado']['equipados']['titulos']==iid
    antes=copy.deepcopy(perfil(fake,teste));c2,_=f(teste)
    for path in ['/heroi','/loja?categoria=personagem','/mapa?vista=mundo','/mapa?vista=regiao','/parada/1/4','/parada/1/40']:
        h=unescape(c2.get(path).text);assert fr in h and item['nome'] not in h,path
        if feminino and TABELA[iid][0]!=fr:assert TABELA[iid][0] not in h
    assert perfil(fake,teste)==antes

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('avatar',sorted(AVATARES))
def test_padrao_sem_titulo_tambem_frances_por_avatar(ctx,teste,avatar):
    fake,f=ctx;c,_=f(teste);avatar_atual(fake,teste,avatar)
    esperado='Voyageuse sans titre' if avatar.endswith('-f') else 'Voyageur sans titre'
    for path in ['/heroi','/loja','/mapa?vista=mundo','/mapa?vista=regiao','/parada/1/4']:
        h=c.get(path).text;assert esperado in h and 'Viajante sem título' not in h

@pytest.mark.parametrize('teste',[True,False])
def test_troca_de_avatar_recalcula_genero_sem_migrar_ou_cobrar(ctx,teste):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste);post(c,t,item='titulo-guardiao');post(c,t,'/loja/equipar',item='titulo-guardiao')
    estado=copy.deepcopy(perfil(fake,teste)['cosmeticos'])
    for avatar,fr in [('mago-m','Gardien des mots'),('arqueiro-f','Gardienne des mots'),('bardo-m','Gardien des mots')]:
        avatar_atual(fake,teste,avatar);assert fr in c.get('/heroi').text
        assert perfil(fake,teste)['cosmeticos']==estado

def test_catalogo_titulos_traducoes_precos_e_descricao_unica():
    itens=[ITENS[i] for i in TABELA]
    assert all(i['preco']==90 for i in itens)
    assert len({i['descricao'] for i in itens})==4
    assert all('Um título para exibir' not in i['descricao'] for i in itens)
    assert titulo_fr({'nome':'Antigo português'},'cavaleiro-f')=='Voyageuse sans titre'
