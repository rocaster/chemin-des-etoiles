# LEIA-ME — v7: loja, molduras, cenários e nomes de pets

Esta edição cumulativa inclui v7c (títulos franceses e orçamento de cristais), mantendo a restrição de partículas da v7b. A seção mais recente prevalece sobre os registros históricos.

## Instalação local
- Pacote **cumulativo** `patch-xp-loja-v7.zip`: aplicar sobre o projeto + `patch-loja-personagem.zip`. Não exige v2–v6. Inclui v5 (poses articuladas/pets), a correção legada de espada somente no cavaleiro masculino, XP/cristais v6 e o hotfix UTF-8 do proprietário.
- Alternativa **delta** `delta-v7.zip`: aplicar somente se a v6 + hotfix UTF-8 já estiver instalada. Não é um substituto do cumulativo para a base v1.
- Caminhos relativos à raiz do projeto. Não contém .env, ambientes virtuais, cache, instance, node_modules ou credenciais. Nada foi implantado; nenhum Azure/Cosmos real foi acessado.

## Mudanças v7
- TEF/TCF: `templates/mapa.html` mostra as duas placas apenas em `vista-mundo`. Jinja aplica `hidden` na entrada regional, CSS esconde também em transições/obra e a função já existente `modo(m)` sincroniza a visibilidade. Nenhuma mudança nos pontos, trilha, BORDAS_MAPA ou engines.
- Vitrine de molduras em `/heroi` e em todas as abas da `/loja`. Madeira LVL1 (0 XP), Pedra LVL2 (45), Bronze LVL3 (135), Prata LVL4 (270), Ouro LVL5 (405), Diamante LVL6 (585). Fonte única: BORDAS_MAPA original. A maior desbloqueada continua automática; as demais são exibidas como conquistadas/bloqueadas. Sem preço, formulário de compra ou seleção manual. POST de compra/equipamento/retirada de moldura é rejeitado.
- Preços aprovados: paleta150, partícula250, título90, pet400, cenário300. **28 itens pagos =7.860 cristais**; Refúgio padrão grátis fica fora do total. Um mapa rende os mesmos 1.000–1.020, ou 12,72%–12,98% da coleção. Compra até 7 itens pagos baratos distintos, não a loja inteira. Exemplos: pet+partícula+paleta+título890; pet+cenário+paleta+título940; pet+cenário+partícula950; três cenários900. A conta teste tem ainda 1.000 de demonstração, que não são ganhos reais.
- Nova aba **Cenários**: Floresta, Taverna, Céu estrelado, Praia tropical, Mundo dos doces, Jardim japonês com cerejeiras. Seis artes pixel224×192 com o mesmo pedestal/posição de herói e pet. Só alteram o fundo do `/heroi`; a loja mostra prévias. Não há praia da Bretanha/torre do castelo. Refúgio original permanece byte-idêntico e permanentemente possuído/equipado **implicitamente**, sem migração de saldo/inventário; retirar um cenário retorna a ele. Compras/equipamentos usam o mesmo ledger com ETag/If-Match, preço servidor, proteção CSRF e idempotência.
- **Renomear pet gratuitamente** em `/heroi`, quando equipado (qualquer pet possuído pode ser equipado antes). POST `/loja/pet/nome`; trim + normalização NFC;1–16 caracteres; letras, números, espaços, hífen, apóstrofo, com ao menos uma letra/número. Lista básica PT/FR/EN com remoção de acentos e alguns disfarces numéricos; não é moderação universal. Nome por pet em `cosmeticos.nomes_pets`, persistido com ETag e preservado em compras/créditos concorrentes. Restaurar nome original remove só aquele apelido. Templates escapam nomes; saldo e XP não mudam. Nomes aparecem no refúgio, loja e rótulo acessível do companheiro na batalha. O mapa mantém apenas o sprite decorativo, sem nome, como antes.

## Preservado
`load_dotenv()` e hotfix UTF-8 mantidos. Novos/alterados acessos Python a texto usam `encoding='utf-8'`; auditoria em `docs/python-utf8-v7.json`. Motor/formatos, 40 recompensas, regras de XP/cristais, BORDAS, gameplay, telas congeladas, sprites originais/v5 e músicas permanecem byte-idênticos à v6 hotfix. Nenhuma nova mudança em motor.js nesta versão. XP v6: missão25, conversa20, história20, biblioteca15, cartas20; batalha/chefe/simulado0; primeira conclusão apenas, 640 no mapa novo.

## Validação e prévias da v7 original (histórico)
- Pytest: **539 passaram**, tanto normal quanto `PYTHONPATH=/tmp/cp` (cp1252 padrão simulado), usando `/workspace/ncl/.tools-loja/bin/python -m pytest tests -q`. São119 testes novos v7 sobre420 v6.
- Simulados91 Python+29 JS+43 DOM; onboarding124+72 JS; rotas57. Loja55 DOM, XP93 DOM/VM, mapa9 verificações em cada porta5077/5091, mapa40:21, batalha51, missões209 estados DOM, quatro formatos e duas batalhas E2E. Python/DOM principais repetidos com cp1252. HTTP offline46 verificações:40 conclusões, cinco categorias compradas/equipadas, saldo830 após compra1190 a partir de2020, apelido e escopo dos cenários.
- Instalação isolada com apenas v1+v7, cp1252:320 combinações,1.600 páginas200,160 assets200,42 sheets, seis cenários/nomes/molduras e economia completa aprovados.
- Auditoria v7:701 verificações de congelados/UTF-8/artes/BORDAS e diff restrito às placas. Logs/manifestações em `/workspace/ncl/relatorio-xp-loja-v7/`.
- `prints-loja/v7/cenarios-v7-preview.png` e sete `cenario-*-preview.png`: composições de arte PIL, **não screenshots de navegador**. Cópias no ZIP em `docs/pranchas-v7/`. HTMLs HTTP sanitizados de antes/depois e refúgio equipado em `docs/evidencias-v7/`.
- Continua pendente inspeção visual real desktop/mobile e avaliação em uso dos preços/duração. Não há novas regras de ganhos. Conquistas sem telemetria continuam declaradas como não rastreáveis; não se inventou progresso.


## Atualização v7b (histórico) — partículas só no cenário do personagem

- A partícula equipada aparece **somente dentro do diorama do /heroi** e nas **prévias da loja** (visual equipado e amostras de partículas). Não cobre mais o fundo da página, cabeçalho, estatísticas ou baú. A camada é absoluta, recortada no próprio contêiner, sem capturar cliques; `prefers-reduced-motion` a esconde.
- No mapa inteiro, mapas das três áreas, batalhas/chefe e HUD: nenhuma camada cosmética. O contexto visual desses endpoints recebe efeito vazio, sem apagar ou alterar `cosmeticos.equipados`, inventário, moeda, preços ou configurações. Templates/engines do mapa e batalha permanecem byte-idênticos à v7; efeitos próprios de combate, música e congelados não mudaram.
- Comprar, equipar, retirar e voltar ao refúgio continuam funcionando; testes cobrem as cinco partículas em modo teste e CosmosFake, preservando integralmente o perfil após as renderizações. UTF-8 mantido em todos os acessos Python novos/alterados a texto.
- Instalação: já tem v7 (ou v6+hotfix+delta-v7)? Aplique **delta-v7b.zip**. Para a base com patch-loja-personagem.zip, use o **patch-xp-loja-v7.zip atualizado**, que já inclui v7b; não precisa de deltas intermediários. O delta-v7.zip original foi preservado.
- Validação atual: **550 pytest normal +550 cp1252**, simulados91+29JS+43DOM, onboarding124+72JS, rotas57; loja67DOM, XP93DOM/VM, mapa9 por execução, mapa40:21, batalha51, missões209, quatro formatos e duas batalhas E2E. Suites repetidas normal e `PYTHONPATH=/tmp/cp`, com servidor offline também em cp1252. HTTP46 por modo; integridade1.279 por modo. Zero falhas finais.
- Evidências HTTP sanitizadas: /workspace/ncl/prints-loja/v7b/ (normal) e subpasta cp1252/; cópias atuais em docs/evidencias-v7/. Não são screenshots. Manifesto incremental em docs/arquivos-v7b.md; resultados em docs/resultado-xp-loja-v7b.json; logs em /workspace/ncl/relatorio-xp-loja-v7b/.

Instalação isolada v1 + cumulativo atualizado, sob cp1252:320 combinações,1.600 páginas HTTP200,160 assets e42 sheets aprovados, com partículas presentes só em /heroi/prévias da loja; cinco categorias e economia completas preservadas.


## Atualização v7c — títulos franceses e orçamento de1.200 cristais

### Causa e correção dos títulos
O catálogo ativo não tinha nome_fr/nome_fr_f: os quatro títulos possuíam somente nome PT e a mesma descrição genérica. A prévia usava item.nome; /heroi e aparencia.py também liam esse mesmo nome. Portanto não havia tradução anterior sendo ignorada: faltavam dados e um resolvedor de apresentação comum.

Agora titulos.py resolve o francês pelo avatar atual (-m/-f), não pelo nome/sexo da conta. Loja: prévia escura exatamente em FR abaixo do nome; pergaminho com tradução PT e explicação única. Inventário de estilo, /heroi, prévia equipada, mapa e batalha usam FR, inclusive o padrão. IDs e preços90 permanecem. Estado salvo contém os mesmos IDs; trocar avatar recalcula o gênero sem nova compra ou migração.

| ID | Tradução PT (m/f quando muda) | FR masculino | FR feminino |
|---|---|---|---|
| titulo-viajante | Viajante das Estrelas | Voyageur des étoiles | Voyageuse des étoiles |
| titulo-guardiao | Guardião / Guardiã das Palavras | Gardien des mots | Gardienne des mots |
| titulo-voz | Voz do Vilarejo | Voix du village | Voix du village |
| titulo-coroa | Coroa da Teimosia | Couronne de l’entêtement | Couronne de l’entêtement |
| Padrão grátis | Viajante sem título | Voyageur sans titre | Voyageuse sans titre |

Voix e Couronne são expressões nominais invariáveis entre os avatares; não se inventa flexão incorreta. Texto é escapado e mantém UTF-8.

### Cristais aprovados
Etapas mantêm: missão18, conversa20, história16, biblioteca16, cartas18, batalha/chefe12; simulado0. Soma650. Bônus:75 por área (225 total),150 chefe,175 mapa completo =550. **Total garantido1.200; com precisão única+20,1.220.** Replay0, sem mudar XP. Um de cada categoria custa1.190, sobram10–30; loja inteira7.860, cobertura15,27%–15,52%.

**Sem retroativo:** ledger antigo e valores já pagos não mudam. Mapa antigo completamente creditado não recebe diferença ao abrir menu/repetir; perfil parcial recebe a nova tarifa só nos créditos ainda ausentes e pode terminar com total misto inferior ao alvo. A garantia é para um mapa integralmente creditado na tarifa nova. ETag/IDs/schema1 e regras antifarming permanecem; ver balanceamento para tempos de compra/casos antigos.

### Instalação e validação v7c
- Quem tem v7b: aplicar delta-v7c.zip. Base com patch-loja-personagem.zip: aplicar patch-xp-loja-v7.zip atualizado, já cumulativo. **Reinicie o processo Flask após aplicar**, pois catálogo/economia são carregados no import; não é necessária migração de perfil. Nenhum deploy foi feito.
-639 pytest normal +639 cp1252;89 testes novos sobre550. Matriz8 avatares×4 títulos×2 modos, padrão por gênero, troca de avatar sem cobrança, orçamento real1.200 e ledger antigo sem top-up. Suites antigas e E2E repetidas normal/cp1252. Loja82DOM; XP93; simulados91+29JS+43DOM; onboarding124+72JS; rotas57; mapa9; mapa40:21; batalha51; missões209; quatro formatos e duas batalhas E2E; HTTP46 e auditoria1.275 por modo. Zero falhas finais.
- Mock PIL (não screenshot) e HTMLs HTTP sanitizados em prints-loja/v7c/; detalhes em docs/arquivos-v7c.md e docs/resultado-xp-loja-v7c.json. Sem leitura de .env/Azure/deploy; congelados, sprites, música, BORDAS e XP mantidos.

Instalação isolada v1 + cumulativo v7c validada sob cp1252:320 combinações,1.600 páginas HTTP200,160 assets e42 sheets; títulos franceses, partículas restritas,640XP e1.220 cristais do mapa perfeito aprovados.
