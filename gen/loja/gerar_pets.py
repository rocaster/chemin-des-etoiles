"""Entrada compatível; v5 NOVA, sem polígonos/geradores de pets anteriores.
Fontes de desenho independentes e rigs editáveis em fontes-v5/.
O pedido posterior de animação substitui 4 quadros por 8, mantendo base 48 px.
"""
from pathlib import Path
try:
    from .animacao_v5 import PETS,NOMES_PETS as NOMES,DISTINTOS,STYLE,quadro_pet,gerar_pets
except ImportError:
    from animacao_v5 import PETS,NOMES_PETS as NOMES,DISTINTOS,STYLE,quadro_pet,gerar_pets
ROOT=Path(__file__).resolve().parents[2]
def gerar():gerar_pets(ROOT)
if __name__=='__main__':gerar()
