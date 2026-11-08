"""Gera somente poses novas/rigs/previews, nunca originais ou paletas antigas."""
try:
    from .animacao_v5 import gerar_pets,gerar_herois,exportar_partes
except ImportError:
    from animacao_v5 import gerar_pets,gerar_herois,exportar_partes
if __name__=='__main__':
    exportar_partes();gerar_pets();gerar_herois()
    print('V5: 18 rigs, 8 quadros, 42 sheets, 18 GIFs + 2 coletivos, pranchas geradas.')
