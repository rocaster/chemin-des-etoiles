# XP e loja v6 — Chemin des Étoiles

Patch **cumulativo após `patch-loja-personagem.zip`**: não é necessário instalar v2/v3/v4/v5. Inclui as poses, fontes/rigs, dez pets, pranchas/GIFs da v5 e os oito derivados legados de espada **somente do cavaleiro masculino**. Nenhum original de fogueira foi substituído.

## Aplicação local

Faça backup, extraia `patch-xp-loja-v6.zip` na raiz do projeto, reinicie o Flask e atualize a página sem cache. Não há deploy, comando Azure, migração de infraestrutura ou acesso a segredos. `load_dotenv()` permanece no app; os testes o simulam sem abrir `.env`. Não execute geradores antigos do mapa que ainda documentam a pausa histórica de XP.

## XP final

| Formato | Etapas | Primeira conclusão | Repetição | Total do mapa |
|---|---:|---:|---:|---:|
| Missão de blocos | 15 | 25 | 0 | 375 |
| Conversa | 4 | 20 | 0 | 80 |
| História | 3 | 20 | 0 | 60 |
| Biblioteca | 3 | 15 | 0 | 45 |
| Cartas | 4 | 20 | 0 | 80 |
| Batalha/chefe | 11 | 0 | 0 | 0 |
| Simulado | fora do mapa | 0 | 0 | 0 |
| **Mapa novo completo** | **40** | | | **640** |

Estrelas continuam avaliação, sem multiplicar XP. `data/xp.json` documenta a tabela ativa; as quarenta `recompensa` estão alinhadas. O bloco `xp_proposta_nao_aplicada` de `data/economia.json` é metadado histórico v2, não fonte de XP ativa.

### Mudança exata em `motor.js`

**Três hunks, 23 linhas adicionadas e 5 removidas**, exclusivamente dentro da seção de conclusão/XP (antigas linhas 581–618). Diff completo: `docs/diff-motor-xp-v6.patch`.

1. O POST lê/valida o JSON autoritativo em vez de retornar só `r.ok`; salva `xp_creditado_etapa`, `xp_ganho`, versão e confirmação no registro local.
2. `|| 10` / `|| 5` viraram `?? 0`, respeitando `xp_pausado` e zero. Antes da resposta aparece “Confirmando XP…”, não um prêmio inventado.
3. A recompensa mostra `xp_ganho` confirmado: repetição mostra `+0 XP`; falha mostra “XP pendente”. Prévia não salva. Mensagem do modo teste esclarece persistência em memória, não no Cosmos.

Todo o motor antes da seção de recompensa e depois dela está byte-idêntico. Blocos, respostas, missão, fluxo, XP de batalha/simulado, música, `/nivelamento`, `/missao` e limites de `BORDAS_MAPA` não mudaram.

### Persistência e legado

`ContasCosmos.alterar_perfil()` usa ETag/If-Match para gravar progresso + XP de uma versão fresca. Reenvios e duas primeiras conclusões concorrentes só creditam uma vez. Salvamento genérico atrasado não desfaz XP/progresso/compras atuais. O teste usa RLock/memória.

A migração reconhece **somente conclusões salvas no servidor**, recalculando a parcela do mapa (inclusive etapas antes pausadas), preservando XP legítimo servidor externo/legado e sem reduzir o total anterior. É versionada/idempotente. Perfis novos têm 640 pelo mapa; um legado pode somar XP servidor preservado. Nunca importa valores alegados pelo localStorage. A borda usa XP servidor, inclusive zero; o fallback local recalcula apenas IDs conhecidos, no máximo 640.

## Cristais e loja

Regra e preços aprovados da v5 foram mantidos. Primeira conclusão: missão 18; conversa 20; história/biblioteca 16; cartas 18; batalha 12; simulado 0. Área completa 50 ×3; chefe 100; mapa 100; primeira conclusão sem erros 20 uma vez por perfil. **1.000–1.020 por mapa** (~4h30); repetições não repagam etapas. Se ainda não ganho, o bônus de precisão pode sair numa repetição, só uma vez.

Saldos iniciais: conta real 0; demonstração 1.000 em memória. Paleta 120; partícula 160; título 90; pet 240. Comprar guarda no inventário; **Equipar** aplica; **Restaurar padrão** retira sem devolver cristais. XP não é gasto. POSTs mantêm sessão/CSRF, preços/posse/saldo validados no servidor e compra idempotente.

O ledger de cristais já funcionava; a v6 corrige a janela em que duas conclusões podiam sobrescrever progresso/XP e comprometer sua recuperação. Progresso e crédito continuam duas gravações: se o crédito falhar, a resposta sinaliza pendência; visitar `/heroi` ou `/loja` recupera uma vez. Nenhum crédito vem do navegador. Sessão de teste que sobreviva ao reinício volta a ter perfil de memória utilizável; zerar o teste usa o caminho atômico intencional, sem desfazer inventário/ledger.

### O visual equipado agora aparece

- `/heroi`: cena e poses articuladas v5, paleta/título/pet/partícula; almofada sem pet.
- `/loja`: amostras do catálogo + resumo explícito do visual realmente equipado.
- `/mapa`: retrato recortado da pose v5 na **mesma moldura de XP**, título compacto, pet pequeno dentro da área da ficha e partícula local. Trilha/câmera/arrasto/placas permanecem intactos.
- Batalhas: retrato articulado v5 no HUD, título/pet/partícula decorativos. Para não quebrar os 12 quadros de ataque/dano, o ator de combate conserva sua geometria original e recebe **somente recoloração do tecido**; não se força a tira idle v5 sobre o motor de combate. Cabeças/cabelos/itens continuam originais; nos magos, apenas o trecho livre do manto abaixo dos cabelos/magia é recolorido, pois estes compartilham roxos com o tecido. HUD/música/regras não mudam.
- Chuva visível nos perfis sem clarão; clarão suave apenas na batalha. Nenhum som extra. Movimento reduzido desliga efeitos/loops.
- `/personagem` mantém os originais e está congelado. Telas de lições/nivelamento/simulados não possuem retrato do jogador a substituir. Templates antigos `home.html`/`avatar.html` estão sem uso: as rotas redirecionam para mapa/seleção.

## Arquivos principais alterados ou novos na v6

| Arquivo(s) | Mudança |
|---|---|
| `app.py` | Conclusão atômica/XP; reconciliação no mapa; adaptador em memória; recuperação/reset do teste. Rotas congeladas intactas. |
| `contas_cosmos.py` | Novo callback ETag para perfil; upsert genérico não retrocede o ledger v6. |
| `xp.py`, `data/xp.json`, `data/paradas/*.json` (40) | Tabela, migração, crédito único; só campos de recompensa XP nos conteúdos. |
| `static/parada/motor.js`, `formatos.js` | Exibição/registro autoritativos, zero/replay/pendência. |
| `aparencia.py`, `loja.py` | Resolver único do perfil equipado; integração nas superfícies ativas. |
| `templates/mapa.html`, `batalha.html` | Camadas cosméticas; mapa prefere XP servidor. |
| `templates/heroi.html`, `loja.html`, `loja-base.html`, `perfil-resumo.html` | Visibilidade coerente, resumo equipado e notas atualizadas. |
| `static/loja/perfil-v6.css` | Dimensões/efeitos decorativos responsivos, sem capturar toque. |
| `static/loja/mapa/` (64 PNGs), `static/loja/batalha/` (24 PNGs) | Retratos v5 1×/2×; paletas de tecido com alfa/12 quadros preservados. |
| `gen/loja/gerar_aparencia_v6.py` | Gerador reproduzível, sem sobrescrever originais. |
| `tests/test_xp_loja_v6.py`, `tests/test_loja.py` | 121 novos casos + contratos de visibilidade atualizados. |
| `gen/loja/teste-xp-v6-dom.py`, `xp-v6-dom.js`, `teste-http-v6.py`, `verificar_integridade_v6.py` | Regressão, evidência HTTP e auditoria do escopo autorizado. |
| `gen/formatos/teste/`, `gen/mapa40/teste/`, `gen/batalha/teste/` | Cópias executáveis dos testes locais; expectativas XP/autenticação fake; porta alternativa opcional. |
| `docs/balanceamento-xp-cristais.md`, `docs/diff-motor-xp-v6.patch`, `docs/resultado-xp-loja-v6.json`, changelog item 19 | Decisões, diff e resultados. |

## Testes finais

- **420 pytest** (299 anteriores +121 novos), **47 DOM loja**, **93 DOM/VM XP**, **30 verificações HTTP reais locais**.
- Simulados: **91 Python +29 JS +43 DOM**. Onboarding: **124 Python +72 JS**. Rotas: **57**.
- Mapa: **9 verificações em 5077 e mais 9 em 5090**, com 40 etapas, praça/cliques/arrasto e ausência de erros JS.
- Extras: **21** mapa-40 Python, **51** batalha Python, **209** itens/recompensas de missões no DOM; quatro formatos concluídos ponta a ponta, vitória normal e chefe com XP zero.
- **758 verificações de integridade**; conteúdo/estrelas/artes v5/congelados/trilhas/bordas preservados. Instalação limpa somente v1+v6: **320 combinações, 1.600 páginas HTTP 200, 153 assets HTTP 200**, 42 sheets, mapa de 640 XP/1.020 cristais e compra/equipamento nas quatro categorias validados.
- Sem falhas finais. Sem Cosmos/SMTP reais. Os testes fazem mock de dotenv.

Comandos base:
```sh
python -m pytest tests -q
python gen/loja/teste-dom.py
python gen/loja/teste-xp-v6-dom.py
python gen/formatos/teste/teste-simulados.py
python gen/formatos/teste/teste-onboarding.py
python gen/formatos/teste/teste-rotas.py
# em outro terminal, a partir da raiz, sem carregar .env:
python gen/formatos/teste/flask-offline.py
node gen/formatos/teste/mapa.js
```
No box, foi usado `/workspace/ncl/.tools-loja/bin/python` e `NODE_PATH=/workspace/ncl/gen/formatos/teste/node_modules`. Node requer jsdom. O auditor de integridade usa snapshots externos locais de desenvolvimento, não é requisito de produção. Os READMEs/resultados v5 são históricos; este documento e o auditor v6 são a referência atual.

## Evidência visual: limitação explícita

**Não há screenshots PNG v6.** Nenhuma ferramenta de captura de navegador autorizada está disponível; a política desta execução impede contornar isso com Playwright/Puppeteer/CDP por Shell. Não foi produzida imagem falsa como se fosse captura.

Foram salvas respostas HTTP (CSRF removido) em `/workspace/ncl/prints-loja/v6/`: `loja-antes.html`, `loja-depois-compra.html`, `loja-equipada.html`, `heroi-equipado.html`, `mapa-equipado.html`, `batalha-equipada.html`, `resultado-http.json`. Elas comprovam conteúdo/endpoints, **não CSS/layout real**. As pranchas/GIFs v5 continuam disponíveis, não são screenshots.

Pendências: captura e inspeção visual desktop/mobile em navegador real; monitorar duração/preços em uso real; telemetria dos três selos ainda não rastreáveis (Invicto, Primeira Vez, Falador). XP e ganho de cristais não estão pendentes.
