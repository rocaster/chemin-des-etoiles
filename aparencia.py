"""Uma apresentação do perfil equipado; não lê créditos nem altera progresso."""
from herois import sheet_heroi
from titulos import titulo_fr

def apresentar(avatar,nome,equipados):
    paleta=equipados.get('personagem',{}).get('paleta')
    nome_arte=avatar+(f'-{paleta}' if paleta else '')
    return dict(avatar=avatar,nome=nome,sprite=sheet_heroi(avatar,paleta),
        retrato=f'loja/mapa/{nome_arte}.png',retrato2=f'loja/mapa/{nome_arte}@2x.png',
        batalha=f'loja/batalha/{nome_arte}.png' if paleta else f'batalha/heroi-{avatar}.png',
        titulo=titulo_fr(equipados.get('titulos'),avatar),pet=equipados.get('pets'),
        efeito=equipados.get('particulas',{}).get('efeito',''))
