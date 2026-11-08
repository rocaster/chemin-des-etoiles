# Herói v3 — só o cavaleiro masculino troca lenha por espada

**Aplicar `patch-heroi-v3.zip` depois de `patch-loja-personagem.zip`. A v2 NÃO é necessária.** O pacote v3 é cumulativo: mantém o refúgio, pets distintos, animações leves, economia de cristais e todos os testes da v2, corrigindo a arte dos personagens.

Extraia na raiz do projeto e reinicie Flask. Faça backup dos arquivos substituídos. Nenhum deploy, configuração Azure, arquivo `.env` ou credencial foi tocado.

## Arte, personagem por personagem

| Personagem | Estado v3 | Fonte usada |
|---|---|---|
| Cavaleiro | ÚNICO alterado: lenha → espada, mesma pose | `static/loja/herois/espada/cavaleiro-m*.png` (8 arquivos: 4 cores × aberto/fechado) |
| Cavaleira | Original intacto, já tinha espada; nenhum derivado | `static/fogueira/sprite-cavaleiro-f-{aberto,fechado}.png`; paletas existentes |
| Arqueiro | Espada acrescentada na v2 removida; pose original | `static/fogueira/sprite-arqueiro-m-{aberto,fechado}.png`; paletas existentes |
| Arqueira | Arco e pose originais restaurados | `static/fogueira/sprite-arqueiro-f-{aberto,fechado}.png`; paletas existentes |
| Mago | Livro/pose originais restaurados | `static/fogueira/sprite-mago-m-{aberto,fechado}.png`; paletas existentes |
| Maga | Magia/palma/pose originais restauradas | `static/fogueira/sprite-mago-f-{aberto,fechado}.png`; paletas existentes |
| Bardo | Alaúde/pose originais restaurados | `static/fogueira/sprite-bardo-m-{aberto,fechado}.png`; paletas existentes |
| Barda | Arte/pose originais restauradas, sem espada nova | `static/fogueira/sprite-bardo-f-{aberto,fechado}.png`; paletas existentes |

“Paletas existentes” = `static/loja/paletas/<avatar>-{esmeralda,ametista,rubi}.png`, anteriores à v2, sem nenhuma alteração de bytes. A fonte única `herois.py` é usada tanto em `/heroi` quanto nas prévias da loja e na prancha de revisão. Nenhum personagem mudou no mapa, batalha ou fogueira `/personagem`.

Para os sete não alterados, a cor padrão pisca usando os arquivos abertos/fechados originais. **Antes da v2 não existiam quadros fechados das paletas compradas:** não foram inventados nem recoloridos. Nessas paletas, a imagem fica sem piscada para não trocar brevemente a cor da roupa; respiração/movimento compartilhado e pet continuam. Cavaleiro masculino conserva seus oito derivados e piscada em todas as cores. Movimento reduzido continua respeitado.

O gerador de espadas agora recusa qualquer avatar diferente de `cavaleiro-m`. As 56 imagens derivadas obsoletas dos outros sete foram removidas do box e não estão neste ZIP.

### Se a v2 já foi instalada

A v3 também pode ser aplicada por cima dela, mas extrair ZIP não apaga arquivos antigos. Depois da extração execute:

```sh
python gen/loja/limpar_derivados_obsoletos.py
```

O script remove somente uma lista exata de 56 nomes em `static/loja/herois/espada/`. Nunca toca `fogueira/`, `avatars/`, `paletas/` ou os oito arquivos de `cavaleiro-m`. Nenhuma exclusão ocorre automaticamente ao iniciar o aplicativo.

## Recursos cumulativos mantidos

- Refúgio pixel-art/estrado e almofada para pet ausente em `/heroi`; sem moldura redonda no menu, com a moldura do mapa preservada.
- Painel de XP/nível/cristais, loja, compras/equipar, conquistas e dez pets de silhuetas distintas iguais à v2.
- Cristais por primeira conclusão: missão 18, conversa 20, história/biblioteca 16, cartas 18, batalha 12; simulado 0. Repetições não pagam etapa. Bônus únicos: áreas 50 cada, chefe 100, mapa 100, precisão 20. Total 1.000–1.020 por mapa; preços mantidos.
- Ledger com ETag/If-Match e reconciliação de créditos pendentes/legados. Conta nova 0; teste 1.000 em memória. Consulte `docs/balanceamento-xp-cristais.md`.
- XP não foi modificado: a proposta continua documentada, condicionada à autorização dos motores congelados. Fontes/conteúdo/XP/bordas/músicas permanecem como antes.

## Gerar e testar

```sh
python gen/loja/gerar_herois_espada.py
python -m pytest tests/test_loja.py tests/test_heroi_v2.py tests/test_heroi_v3.py -q
python gen/loja/teste-dom.py
```

Pillow/pytest/jsdom são ferramentas de desenvolvimento. O gerador só escreve os oito arquivos masculinos e limpa os nomes derivados obsoletos; lê os demais originais apenas para a prancha.

Prancha atualizada dos oito personagens × quatro cores:
`/workspace/ncl/prints-loja/heroi-espada-preview.png`.

Resultado final: **166 pytest + 47 DOM**, simulados **91 Python + 29 JS + 43 DOM**, onboarding **124 Python + 72 JS**, rotas **57**, mapa em 5077/5088 correto e **152 verificações de integridade**; zero falhas.

Instalação cumulativa também testada do zero com **somente v1 + v3, sem v2**: 64 páginas e 416 imagens responderam HTTP 200.

As pranchas são arte, não screenshots de navegador. Inspeção visual real desktop/mobile do CSS continua pendente. Resultados finais estão em `docs/resultado-heroi-v3.json`; auditoria compara hashes com snapshots locais e testa cada classe/paleta/quadro original.
