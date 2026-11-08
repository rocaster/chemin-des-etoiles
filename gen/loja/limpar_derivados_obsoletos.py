"""Remove exclusivamente os 56 derivados não-cavaleiro-m da v2.

Opcional ao aplicar v3 sobre v2. A v3 fresca sobre patch-loja-personagem
não os contém. Nunca toca fogueira/, avatars/ ou paletas/ originais.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DESTINO=ROOT/'static/loja/herois/espada'
AVATARES=('cavaleiro-f','arqueiro-m','arqueiro-f','mago-m','mago-f','bardo-m','bardo-f')
OBSOLETOS=tuple(avatar+paleta+quadro+'.png' for avatar in AVATARES
               for paleta in ('','-esmeralda','-ametista','-rubi') for quadro in ('','-fechado'))

def limpar(destino=DESTINO):
    removidos=[]
    for nome in OBSOLETOS:
        p=Path(destino)/nome
        if p.is_file():
            p.unlink();removidos.append(nome)
    return removidos

if __name__=='__main__':
    removidos=limpar()
    print(f'{len(removidos)} derivados v2 obsoletos removidos. Originais não alterados.')
