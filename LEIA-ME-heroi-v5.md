# V5 — pets novos do zero e poses articuladas dos oito heróis

**Aplicar `patch-heroi-v5.zip` após `patch-loja-personagem.zip`. Não requer v2/v3/v4.** Extraia na raiz do app, com backup, reinicie Flask e atualize a página. Não há deploy, alteração Azure, leitura/arquivo `.env` ou mudança de dependência de produção.

## Arte inteiramente nova

- Dez pets criados **individualmente com GenerateImage, sem qualquer imagem de referência**, usando exclusivamente a descrição de estilo do Alex. Nenhum contorno, sprite, mapa de pixels ou forma de gerador anterior foi usado. A antiga função de desenho foi substituída por um pipeline novo baseado nas novas fontes.
- Oito heróis também redesenhados com corpo/gesto/pose novos. As referências anteriores foram somente de identidade/cor/equipamento, não bases de pixels/recortes de pose. A arqueira final foi criada sem imagem de referência para evitar repetir a posição de tiro.
- JPEGs originais novos, PNGs limpos, proveniência SHA-256, máscaras, pivôs e **peças RGBA separadas** estão em `gen/loja/fontes-v5/`. Nada depende de chamadas de imagem durante execução do jogo.
- Remoção de fundo por chroma conectado (preserva brilhos internos), paleta limitada, recorte transparente, encaixe na grade. Pets trabalham em 96×96; quadro final 48×48. Outline marrom quente, olhos brilhantes, cabeças grandes, volumes em tons e silhuetas próprias. Não foi desenhado cachorro.

## Pose e movimentos

| Herói | Nova pose / animação |
|---|---|
| Cavaleiro | Cabelo castanho, aço/azul/dourado; espada erguida à esquerda e mão livre acolhedora. Inclina/lateraliza cabeça, levanta/abaixa espada e abre/fecha braço livre; respiração com pés fixos. |
| Cavaleira | Rabo de cavalo ruivo, armadura azul/prateada; própria espada ao lado e mão livre baixa. Cabeça, braço da espada e mão livre independentes. |
| Arqueiro | Cabelo castanho-claro, couro e capa verde; arco baixo e outra mão levantada em saudação. Cabeça, arco/antebraço e mão de cumprimento móveis. |
| Arqueira | Cabelo escuro trançado, couro/capa verde; arco em repouso horizontal abaixo da cintura e palma aberta. Inclina cabeça, ajusta arco e abre mão livre; não está mirando. |
| Mago | Chapéu/capa roxos, cabelo grisalho; livro aberto oferecido ao lado e mão explicativa levantada. Cabeça/chapéu, braço/livro e mão livre articulados. |
| Maga | Cabelo lavanda, chapéu/vestido roxos; palma mágica afastada do tronco e outra mão diante do corpo. Cabeça/chapéu, braço com estrelas e braço livre articulados. |
| Bardo | Cabelo preto, vermelho/pena branca; alaúde diagonal mais baixo e joelhos relaxados. Cabeça, braço/instrumento e antebraço de dedilhado independentes. |
| Barda | Cabelo loiro, vermelho/pena branca; um pé à frente e alaúde diagonal baixo. Cabeça, apoio do instrumento e braço de dedilhado articulados. |

| Pet | Novo desenho / movimentos |
|---|---|
| Dragão bebê | Verde de olhos âmbar e barriga marfim, chifres, asas turquesa e cauda em lança. Cabeça inclinável, asa abre/fecha e cauda balança. |
| Lobo | Prateado/cinza, orelhas pontudas, peito claro, pelo em tufos e cauda espessa. Cabeça, orelha e cauda independentes. |
| Raposa | Ruiva de olhos grandes e cauda muito volumosa com ponta marfim. Cabeça curiosa, orelha mexe e cauda abana. |
| Tigre | Laranja, listras marrons, bochechas creme e patas grossas. Cabeça inclinável, orelha redonda e cauda listrada móveis. |
| Corvo místico | Violeta de bico grande, olhos luminosos e penas em camadas. Cabeça, asa e leque da cauda móveis. |
| Fênix | Dourada, crista e longas penas flamejantes. Cabeça, asa e cauda articuladas. |
| Gato das sombras | Roxo de olhos dourados, peito lilás e cauda com fumaça. Cabeça, orelha e cauda independentes. |
| Cervo dourado | Cervato dourado sentado, pintas, cascos e pequenos chifres. Inclina cabeça e mexe orelha/cauda. |
| Coruja sábia | Marrom de discos creme e óculos de latão. Cabeça/óculos, tufo e asa móveis. |
| Coelho cristal | Branco-azulado, uma orelha cristalina dobrada, olhos castanhos e cauda de algodão. Cabeça, orelha e cauda independentes. |

Animação é um rig 2D simples por peças com pivôs, sobreposições e underpainting do tronco sob itens/braços. Não é só mover/piscar a imagem inteira, nem uma rotação 3D completa da cabeça. Pets têm paleta fixa entre quadros para evitar mudança de tons. Oito quadros/2,8 s; pés ancorados. CSS `steps(8,end)` sem scripts novos/dependências externas; `prefers-reduced-motion` fixa o primeiro quadro.

## Onde aparece / compatibilidade

- Somente `/heroi` e prévias da loja usam as poses novas. **Os previews de heróis E pets agora animam na loja**, conforme o pedido adicional; efeitos de partículas não mudaram.
- A solicitação posterior de **6–8 quadros** substituiu o contrato anterior de quatro: são **8**. Mantido quadro de pet **48×48** e renderização CSS de mesmo tamanho; a sheet nos mesmos caminhos passa de **192×48 para 384×48**. Heróis novos: **96×128 por quadro**, sheets **768×128**, em `static/loja/herois/poses-v5/`, oito personagens × quatro cores = 32 sheets.
- IDs, nomes, preços (pets 240), equipamento salvo, temas e paletas existentes continuam iguais. Novas paletas mudam apenas máscaras de tecido, preservando rosto/cabelo/pele/itens. Originais antigos de paleta permanecem byte a byte intactos.
- Só cavaleiro/cavaleira seguram espada. A antiga troca lenha→espada continua exclusiva dos oito arquivos legados de `cavaleiro-m`, sem alteração. Cavaleira tem sua própria espada na pose nova; outros usam arco/livro/magia/alaúde, jamais espada. Isso **não** altera o acervo original nem a fogueira.
- `/personagem`, mapa/molduras/bordas, missões/motores, nivelamento, XP/trilhas, economia de cristais, refúgio/almofada, painel direito e baú preservados. O rig novo substitui a antiga oscilação CSS da dupla, não o cenário/layout. Conta e compras não precisam de migração.
- Se instalou v2 anteriormente, extração não remove derivados antigos: `python gen/loja/limpar_derivados_obsoletos.py` apaga somente a lista de 56 nomes obsoletos, sem tocar originais ou os oito legados masculinos.

## Arquivos e reprodução

```sh
python gen/loja/gerar_poses_v5.py
python -m pytest tests/test_loja.py tests/test_heroi_v2.py tests/test_heroi_v3.py tests/test_heroi_v4.py tests/test_heroi_v5.py -q
python gen/loja/teste-dom.py
```

Para limpar novamente as fontes brutas: `python gen/loja/animacao_v5.py`, depois o gerador de poses. Não precisa gerar nada para usar o ZIP. Não execute o gerador geral de paletas para esta atualização. O resolvedor/gerador legado v3 continua apenas para o acervo antigo; os menus usam `sheet_heroi()`.

## Resultados e entregas

- **299 pytest** (202 anteriores, com contratos de pose/quadros atualizados, +97 novos); **47 DOM** da loja.
- Simulados **91 Python +29 JS +43 DOM**; onboarding **124 Python +72 JS**; rotas **57**; mapa 40 etapas/praça/cliques/arrasto correto em 5077 e na v5 isolada em 5089. Zero falhas finais.
- **508 verificações de integridade**, incluindo originais pré-v2, congelados, economia, preços, painel e baú. Auditor usa snapshots locais externos, não é requisito de produção.
- Instalação limpa com **somente v1 + v5**, sem v2/v3/v4: **320 combinações** herói/paleta/pet, **960 páginas**, **53 assets únicos** e **42 sheets novos** responderam HTTP 200.
- **20 GIFs** conferidos: oito quadros diferentes cada, 350 ms, loop infinito.
- `prints-loja/arte-pets-preview.png`: **2400×1180**, matriz grande + oito quadros finais por pet.
- `prints-loja/poses-herois-preview.png`: **1920×1340**, oito heróis grandes.
- `prints-loja/anim/<id>.gif`: 18 individuais; `todos-herois.gif` e `todos-pets.gif` coletivos. Pets 384×384, heróis 384×512 nos GIFs individuais.
- Cópias de todos esses PNGs/GIFs incluídas no ZIP em **`docs/pranchas-v5/`**, com fontes/rigs editáveis. GIFs usam fundo neutro para revisão; sprites/fontes PNG têm transparência.

São pranchas de arte/GIFs, **não screenshots do navegador**. Inspecionados desenhos e quadros-chave; aprovação estética e inspeção real de CSS/layout desktop/mobile continuam pendentes. Testes usam CosmosFake e mock de dotenv, sem Cosmos/SMTP reais ou leitura de `.env`; `load_dotenv()` continua no app.
