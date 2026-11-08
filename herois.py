"""Resolvedor legado v3 + poses novas v5 de menu/prévias.

Para os demais: fonte original aberta/fechada na cor padrão; paletas já
existentes, sem novo desenho. Não existia quadro fechado dessas paletas:
usa o mesmo PNG estático, sem inventar/recolorir outro quadro.
"""
AVATARES=frozenset(f'{c}-{g}' for c in ('cavaleiro','arqueiro','mago','bardo') for g in ('m','f'))
PALETAS=(None,'esmeralda','ametista','rubi')


def sprite_heroi(avatar,paleta=None,fechado=False):
    if avatar not in AVATARES or paleta not in PALETAS:
        raise ValueError('Avatar/paleta inválidos.')
    if avatar=='cavaleiro-m':
        return f'loja/herois/espada/{avatar}'+(f'-{paleta}' if paleta else '')+('-fechado' if fechado else '')+'.png'
    if paleta:
        return f'loja/paletas/{avatar}-{paleta}.png'
    return f'fogueira/sprite-{avatar}-'+('fechado' if fechado else 'aberto')+'.png'


def pode_piscar(avatar,paleta=None):
    return avatar=='cavaleiro-m' or paleta is None


def sheet_heroi(avatar,paleta=None):
    """Pose nova v5, somente menu/loja; itens específicos da classe."""
    if avatar not in AVATARES or paleta not in PALETAS:
        raise ValueError('Avatar/paleta inválidos.')
    return 'loja/herois/poses-v5/'+avatar+(f'-{paleta}' if paleta else '')+'.png'
