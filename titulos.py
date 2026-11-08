"""Apresentação dos títulos: francês por avatar, tradução PT só na loja.
Não altera catálogo, estado equipado, preço, inventário, XP ou créditos.
"""

def titulo_fr(item, avatar):
    feminino = isinstance(avatar,str) and avatar.endswith('-f')
    padrao = 'Voyageuse sans titre' if feminino else 'Voyageur sans titre'
    if not item:
        return padrao
    return item.get('nome_fr_f' if feminino else 'nome_fr') or item.get('nome_fr') or padrao


def titulo_loja(item, avatar):
    feminino = isinstance(avatar,str) and avatar.endswith('-f')
    return dict(item, nome_fr_exibicao=titulo_fr(item,avatar),
                nome_pt_exibicao=item.get('nome_pt_f',item['nome']) if feminino else item['nome'])
