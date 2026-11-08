# Balanceamento de XP e cristais — aplicação v7c

## Resumo do que foi aplicado

**XP permanece como aplicado na v6; os ganhos básicos por formato também permanecem.** Na v7c, os bônus de área/chefe/mapa foram ampliados para garantir **1.200 cristais por mapa novo completo**, ou **1.220 com o bônus único de precisão**. Repetições continuam sem créditos de etapa. Os preços aprovados não mudaram: paleta150, partícula250, título90, pet400, cenário300.

O objetivo é poder escolher **um item de cada categoria:400+250+150+90+300=1.190**, sobrando10–30 ao concluir as40 etapas, sem contar moedas de demonstração. A coleção de28 itens pagos continua custando **7.860**; cada mapa novo cobre **15,27%–15,52%** da coleção, não a loja inteira. Pelo menor custo, compra até8 itens pagos distintos (4 títulos +3 paletas +1 partícula =1.060; o nono exigiria1.310), além do Refúgio gratuito e das molduras por LVL. Sem compras prévias, o percurso estimado soma273min (~4h33).

Contas reais começam com0; teste começa com1.000 de demonstração em memória. Para provar o orçamento real, testes zeram esse saldo inicial do teste e também usam CosmosFake:1.200 ganhos, cinco compras/equipamentos por1.190, saldo final10. Valores em data/economia.json; preços/saldo inicial em data/loja.json. **Não há complementação retroativa dos créditos já registrados**; política detalhada abaixo.

## Auditoria histórica v2 (antes da autorização de XP)

Os seis pontos abaixo descrevem o estado anterior; a aplicação v6 está detalhada depois da tabela.

- `app.py`, `parada_concluir()`: `xp_base + xp_por_estrela × estrelas`; credita XP apenas quando não há conclusão anterior para o mesmo ID de conteúdo. Usa os dados de `recompensa` das paradas. **Não foi modificado**.
- `data/paradas/*.json`: nas oito etapas de ensino das primeiras onze posições, XP 10 + 5 por estrela (15–25). Batalhas são zero; etapas 12–40 estão pausadas no servidor, com base/multiplicador zero. Máximo perfeito atual do mapa no servidor: 200 XP.
- `static/parada/motor.js`, `concluir()`/`salvar()`: calcula e exibe XP e grava o registro local, usando `xp_base || 10` e `xp_por_estrela || 5`. **Este arquivo e as missões de blocos estão congelados.** Há uma inconsistência preexistente: valores zero dos JSONs de missões posteriores podem virar os defaults 10/5 no navegador, embora o servidor credite zero. Trocar apenas um config de servidor ou apenas os zeros dos JSONs não elimina isso.
- `static/parada/formatos.js`, `concluir()`/`salvar()`: também calcula e exibe XP local; considera `xp_pausado` e usa `??`, que respeita zero.
- `static/parada/batalha.js`: salva XP zero; `simulados.py`: resultados com XP zero. Permaneceram assim.
- `templates/mapa.html`: reconcilia a ficha/XP do servidor e do aparelho; `BORDAS_MAPA` e seus limites não foram tocados.

### XP aplicado na v6 (somente primeira conclusão)

| Formato | Etapas | XP aplicado na 1ª conclusão | XP em repetição | Cristais na 1ª conclusão (aplicado) |
|---|---:|---:|---:|---:|
| Missão de blocos | 15 | 25 | 0 | 18 |
| Conversa | 4 | 20 | 0 | 20 |
| História | 3 | 20 | 0 | 16 |
| Biblioteca | 3 | 15 | 0 | 16 |
| Cartas | 4 | 20 | 0 | 18 |
| Batalha (inclui chefe) | 11 | 0 | 0 | 12 |
| Simulado | fora das 40 | 0 | 0 | 0 |

A tabela completa soma **640 XP**, alcançando o diamante perto do fim sem mover os limites existentes. Não penaliza quem aprende errando: estrela continua como avaliação visual, não multiplica cristais.

### Para aplicar: quatro passos concluídos na v6

1. `motor.js` respeita `0`, `xp_pausado` e a resposta autoritativa. Não há defaults 10/5. Mostra “Confirmando XP…” antes da confirmação; exibe `xp_ganho`, inclusive zero em repetição; falha mostra “XP pendente”. Prévia não salva. O diff integral está em `docs/diff-motor-xp-v6.patch`; nenhuma lógica de blocos mudou.
2. As 40 `recompensa` e `formatos.js` seguem a tabela; estrelas não multiplicam XP. O servidor usa `xp.py`/`data/xp.json` e grava progresso + XP juntos por ETag/If-Match, repetindo o cálculo com o documento fresco em conflito. Cada ID de conteúdo é creditado só uma vez.
3. Reconciliação somente de conclusões já salvas no servidor: converte a parcela das etapas para a tabela, reconhecendo retroativamente as antigas etapas pausadas. Mantém XP servidor externo/legado legítimo, sem reduzir total legítimo anterior. Campos `xp_regras_versao`, `xp_mapa_contabilizado`, `xp_externo_legado` e `xp_antes_v6` tornam a migração auditável/idempotente. Um perfil novo ganha exatamente 640 pelo mapa; um perfil legado pode terminar acima disso por seu saldo servidor preservado. Nenhum XP de localStorage é importado para a conta.
4. No mapa, o XP servidor prevalece, inclusive zero. O fallback local recalcula por IDs conhecidos e tabela, limitado a 640, sem confiar no campo `xp` local nem em IDs desconhecidos. As expectativas dos testes foram atualizadas; `BORDAS_MAPA` ficou intacta.

Compras/equipamentos nunca consomem XP. Simulados e batalhas/chefe continuam zero. O upsert genérico preserva o ledger de XP/progresso mais recente para não desfazer uma conclusão concorrente; o botão intencional de zerar o teste usa operação atômica própria. Sessão de demonstração que sobreviva a reinício recria apenas o perfil de memória, sem Cosmos.

## Cristais: regra implementada

Crédito de etapa somente uma vez por ID de conteúdo (`r1-pNN`), não por número da posição, dispositivo, sessão ou tentativa. Mudar estrelas, repetir, recarregar, reenviar a mesma requisição ou comprar/equipar não restaura esse crédito.

| Fonte | Valor | Frequência |
|---|---:|---|
| Etapas, conforme tabela | 650 no mapa todo | Uma vez por conteúdo |
| Área 1 (1–11), área 2 (12–24), área 3 (25–40) | 75 cada / 225 total | Uma vez; todas as etapas da área necessárias |
| Chevalier Noir, etapa 40 | 150 | Uma vez, além dos 12 da etapa |
| Mapa 1 completo (40/40) | 175 | Uma vez |
| Não Erra Uma: conclusão aceita com acertos > 0 e erros = 0 | 20 | Uma vez por perfil, não por etapa |
| Repetição da etapa | 0 | Não há farming de conclusão |
| Teimoso / Atrapalhado | 0 | Não incentivar repetir/errar deliberadamente |
| Invicto / Primeira Vez / Falador | 0 | Ainda sem telemetria suficiente |
| Derrota/fuga, praça, prévia, simulado | 0 | Não acionam crédito de conclusão de etapa |

O bônus de precisão pode ser conquistado uma vez numa repetição se ainda não tiver sido ganho. Os demais marcos não são pagos novamente. Etapas somam **650**; os marcos somam **550** (225+150+175), totalizando1.200, mais20 de precisão opcional. A soma das etapas é650, não750: 15×18 + 4×20 + 3×16 + 3×16 + 4×18 + 11×12.

As três áreas são subdivisões do mapa 1 já definidas em `data/regioes/r1.json`, não três mapas novos. Bônus não são moedas compráveis e não dão XP. O ledger de bônus é permanente para impedir recompra de recompensa, independentemente do estado visual derivado dos selos.

## Persistência, concorrência e recuperação

- `economia.py` registra um **after_request** novo sobre a resposta 200/`ok:true` do endpoint de conclusão existente. O hook de cristais não mudou na v6; a conclusão ganhou somente o novo registro atômico de XP/progresso autorizado.
- `cosmeticos.etapas_creditadas` e `cosmeticos.bonus_creditados` ficam no mesmo documento/partição do saldo, junto ao inventário já existente.
- Usa `ContasCosmos.alterar_cosmeticos()` com replace ETag/If-Match. Saldo e marcações são escritos juntos, com releitura/reexecução em conflito; não há incremento cego nem valor de prêmio aceito do cliente. O modo teste usa o lock em memória já existente.
- Cada conclusão aceita é uma autorização de crédito no servidor. O ledger pode registrar dois conteúdos concorrentes mesmo que o snapshot de progresso de outra requisição esteja atrasado. Compras concorrentes preservam saldo/ledger e vice-versa.
- Progresso e cristais são duas gravações distintas. Se o crédito falhar depois de salvar progresso, a resposta inclui `cristais_pendentes:true`; o progresso não é desfeito. Abrir `/heroi` ou `/loja` reconcilia conclusões salvas ainda sem ledger. Repetir a conclusão também tenta creditar.
- **Progresso anterior ao patch:** recebe reconhecimento retroativo uma única vez ao abrir o menu/loja, usando apenas os registros de conclusão do servidor. Não usa localStorage. Isso evita punir quem já jogou e recupera a janela entre gravações, sem criar crédito recorrente por replay.
- Não modifica o modelo antigo de confiança da aprendizagem: o endpoint existente aceita resultados resumidos enviados pelo cliente. Isto não é um sistema antitrapaça de jogo competitivo; não verifica áudio nem cada resposta individual. A v6 resolve a perda por snapshot atrasado de progresso/XP com ETag, mas não adiciona validação competitiva de cada resposta.

## Tempo para comprar — v7c

Estimativas sem compras anteriores; durações já usadas: missão10min, conversa3, história/cartas/batalha5, biblioteca7. Os momentos não são cumulativos depois de gastar. A precisão de20 é considerada ganha cedo na coluna correspondente.

| Item | Preço | Com precisão: etapa / minutos | Sem precisão: etapa / minutos |
|---|---:|---|---|
| Título | 90 | 5 / 38 | 6 / 43 |
| Paleta | 150 | 8 / 58 | 9 / 63 |
| Partícula | 250 | 11 / 75 | 11 / 75 |
| Cenário | 300 | 13 / 90 | 14 / 93 |
| Pet | 400 | 19 / 128 (2h08) | 21 / 143 (2h23) |
| Um de cada categoria | 1.190 | 40 / 273 (4h33), sobram30 | 40 / 273 (4h33), sobram10 |

A média matemática do mapa é264–268 cristais/h, mas os bônus se concentram no fim das áreas e na conclusão. Não é promessa de duração de aprendizagem. O saldo inicial1.000 do teste não entra nessas estimativas nem no orçamento real.

## Aplicação da tarifa v7c e perfis antigos

Mantivemos os valores por formato para preservar o ritmo inicial. O aumento total de20% (1.000→1.200 garantidos) foi concentrado em marcos: área50→75, chefe100→150, mapa100→175. O chefe continua pagando os12 básicos da etapa além de150 do marco; fechar a área3 e o mapa também exige todas as etapas pertinentes.

**Sem retroativo/top-up:** valores e IDs já presentes em etapas_creditadas/bonus_creditados permanecem exatamente como estão. Um mapa antigo totalmente pago continua com1.000–1.020 ganhos históricos, não recebe200 ao abrir o menu ou repetir etapas. Perfis parciais preservam o que receberam; só créditos ainda ausentes no ledger usam os novos valores quando forem pagos, inclusive recuperações pendentes após falha. Por isso um perfil misto pode terminar abaixo de1.200 (ex.: área1 paga antes por50, demais marcos novos:1.175 sem precisão). A garantia1.200 é para o mapa cujos créditos são recebidos integralmente na tarifa v7c. Não se reescreve história nem se cria caminho de farming.

Schema/IDs/versão1 do ledger, ETag/If-Match, idempotência e saldo de compras permanecem. Nenhuma alteração no motor, XP, gameplay ou hooks: somente três valores do JSON de economia. Os testes cobrem ledger antigo completo, mapa novo com/sem precisão, concorrência existente, replay e orçamento real das cinco categorias.

## Ajustes ainda a validar

Valores são uma primeira versão balanceada, a observar em partidas reais: duração efetiva, esforço das conversas, preferências e velocidade de aquisição. Não há compra de cristais, monetização, bônus por perder, diário infinito ou recompensa de simulado. Permanecem pendentes validação de preços/durações em uso real, telemetria das conquistas não rastreáveis e a política de selos visuais permanentes. A autorização de XP já foi atendida na v6.
