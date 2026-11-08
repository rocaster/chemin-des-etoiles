# Personagem, loja e baú — patch local (sem deploy)

> **Histórico da v1.** O pacote atual cumulativo é `patch-heroi-v5.zip`, aplicado depois desta v1, sem precisar da v2/v3/v4. Consulte `LEIA-ME-heroi-v5.md` para as novas poses articuladas dos oito heróis e dez pets. Fogueira/originais intactos; só cavaleiros têm espada e só o acervo legado masculino tem a antiga troca lenha→espada. Ganhos de cristais estão ativos conforme `docs/balanceamento-xp-cristais.md`.

Extraia `patch-loja-personagem.zip` **na raiz do projeto**, sobre a versão atual dos patches de onboarding/Cosmos e simulados. Faça backup dos arquivos substituídos e reinicie o Flask. Não muda configuração Azure, dependências de produção ou infraestrutura. Nenhum `.env` faz parte do pacote; `load_dotenv()` continua no aplicativo.

## Abrir
- `/heroi`: personagem inteiro com a moldura existente, XP, nível visual, cristais, título, pet equipado e baú.
- `/loja`: abas Personagem, Partículas, Títulos e Pets.
- `/conquistas`: atalho para `/heroi#conquistas`.
- No mapa-múndi, três placas de madeira empilhadas **à direita**, espelhando os simulados à esquerda. No mapa de etapas as novas placas ficam ocultas para não cobrir a trilha; no mobile são compactas. Câmera, geometria, XP e bordas não mudam.

O nível exibido é **visual (1–6)**: acompanha as molduras/limiares de XP já existentes. Não inventa outra fórmula de XP ou mede proficiência em francês.

## Compras e dados
- `data/loja.json` concentra preços provisórios e saldo inicial: **teste 1.000, conta real 0**. Não há regra de ganhar cristais, gancho de recompensa ou botão de crédito.
- Conta real: `cosmeticos` no mesmo documento `users`, com `versao`, `cristais`, `comprados` e `equipados`. Compra/equipamento usam leitura + replace com ETag/If-Match e até oito tentativas em conflito; não fazem upsert cego.
- `teste`: apenas memória, com lock; saldo/inventário somem ao reiniciar. Nenhuma chamada Cosmos.
- POST `/loja/comprar`, `/loja/equipar`, `/loja/retirar`: sessão existente + CSRF vinculado à sessão; preço/saldo/propriedade decididos no servidor. Repetir compra não cobra duas vezes. Não há estorno, transferência ou venda.
- Salvamentos antigos de perfil preservam o namespace cosmético atual, inclusive em conflitos. XP, credenciais e progresso não são escritos pela compra.

## Arte e efeitos
- 10 pets originais procedurais, 48×48 por quadro, quatro quadros por pet (PNG 192×48). Piscar, pequeno deslocamento de cabeça/olhar e movimento leve; animação CSS apenas no menu do personagem. Loja mostra um quadro parado. Sem pets em mapa ou batalhas.
- 3 paletas × 8 avatares, sobre os sprites existentes: recoloração dos tons de tecido, sem roupa nova. Os originais não são sobrescritos.
- Verão, inverno, outono e névoa: só nos novos menus. Chuva + clarão suave: só nas batalhas; não acrescenta som nem altera música/combate. Tudo respeita `prefers-reduced-motion`.
- Gerador reproduzível: `python gen/loja/gerar_arte.py` (Pillow, só desenvolvimento).

## Baú e pendências
Critérios **provisórios** em `data/conquistas.json`, calculados apenas do progresso salvo no servidor:
- Chevalier? Já foi!: conclusão da etapa 40.
- Teimoso: três conclusões da mesma batalha (**não** três derrotas).
- Não Erra Uma: uma conclusão atualmente salva com acertos e zero erros.
- Atrapalhado: dez erros somados nas últimas conclusões salvas.
- Nem um Arranhão (mapa invicto), Primeira Vez e Falador: **ainda não rastreáveis**. Derrotas/primeira resposta/voz real não têm histórico confiável no perfil existente. Não foram criados contadores nos motores congelados.

Selos refletem o retrato atual, não um histórico imutável: os dois critérios baseados nas últimas conclusões podem voltar a bloquear após repetições. Confirmar preços, critérios definitivos e se os selos devem virar desbloqueios permanentes antes de produção. Definir obtenção de cristais ainda é necessário; contas reais ficam sem poder comprar enquanto isso não for decidido.

## Testes offline
Não execute o app contra contas reais para testar. Os scripts abaixo mockam `load_dotenv` e usam CosmosFake; não enviam e-mail.

```sh
pip install pytest pillow
python -m pytest tests/test_loja.py -q
# Para DOM (Node):
cd gen/loja && npm install && cd ../..
python gen/loja/teste-dom.py
```

Os testes usam o `cosmos_fake.py` dos testes de onboarding já existentes em `gen/formatos/teste/` (no box também aceitam o diretório irmão de `out`). Para prévia offline isolada: `python gen/loja/servidor_offline.py`; abrir `http://127.0.0.1:5088/__loja-preview`. O helper é só local, não faz parte das rotas do app em produção.

Resultado no box: loja **51 pytest + 44 DOM**, simulados **91 Python + 29 JS + 43 DOM**, onboarding **124 Python + 72 JS**, rotas **57**, mapa **40 etapas/praça/cliques/arrasto OK** em 5077 e também contra a versão atual isolada em 5088. As contagens de JS/DOM dos simulados/onboarding são executadas pelos respectivos scripts Python; não representam testes de navegador. Os avisos do jsdom sobre `HTMLMediaElement.play` são conhecidos.

**Sem screenshots de navegador nesta execução:** a interface deste executor não disponibiliza automação de navegador permitida; não se usou Playwright/CDP via Shell para contornar isso. Os PNGs em `/workspace/ncl/prints-loja/arte-pets-preview.png` e `arte-paletas-preview.png` são pranchas de arte, **não capturas de tela**. Layout desktop/mobile, encaixe das placas, moldura/pet e efeitos ainda precisam de inspeção visual em navegador real. Estrutura DOM e CSS responsivo foram testados, não o layout renderizado.

Superfícies congeladas conferidas: funções de personagem/nivelamento/missão/parada/conclusão/batalha/XP, `BORDAS_MAPA`, templates congelados, motor e áudios batalha/chefe intactos. Em `batalha.html`, somente a camada visual de chuva condicional foi acrescentada; código de combate e música preservados. Nada foi implantado remotamente.
