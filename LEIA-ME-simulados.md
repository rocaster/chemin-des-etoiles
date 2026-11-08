# Simulados TEF Canada / TCF Canada — Chemin des Étoiles

## Instalar
Pare o Flask (Ctrl+C), faça backup da pasta e extraia `patch-simulados-ui.zip` na raiz do aplicativo (a pasta com `app.py`), substituindo os arquivos. **Este patch contém só a revisão visual e pressupõe o `patch-simulados.zip` já aplicado**, depois dos patches de onboarding/Cosmos e pular escrita. Não reaplique a versão visual antiga por cima desta. Reinicie `python app.py` e atualize com Ctrl+F5. CSS/JS têm versão `ui2` para invalidar cache. Não há deploy, dependência web nova nem mudança de configuração Azure.

Duas placas de madeira no canto inferior esquerdo do mapa levam a TEF Canada e TCF Canada. Em telas estreitas ficam acima da faixa inferior de controles; não alteram mini-mapa, regiões em construção, XP ou bordas. A verificação visual real ainda está pendente.

## Rotas
- `/simulados/tef` e `/simulados/tcf`: escolha CO, CE, EE, EO ou prova completa; retomar/descartar tentativa e histórico.
- `/simulados/<examen>/prova`: mesa de exame compartilhada, mas diferente do cenário do nivelamento.
- `/simulados/<examen>/iniciar` (POST), `/estado` (GET), `/entregar` (POST): estado, início e entrega das partes.
- `/simulados/resultados/<id>`: resultado privado da tentativa, acessível apenas ao dono do perfil.

## Interface v2 — escrivaninha ilustrada
- Sai a barra escura. O nome do exame fica numa placa de madeira suspensa; o retorno é um ícone de pergaminho enrolado com `aria-label="Voltar ao mapa"`, reutilizando `missao/rolo.png`.
- A mesa agora é **ilustração original gerada com GenerateImage**, tendo `nivelamento/mesa-fundo.png` como referência. Vela, tinteiro, pena, livros e mapa fazem parte da pintura, com sombras e luz quente; não são objetos flutuantes feitos em CSS. O pergaminho central recebe a folha HTML/textura existente, discretamente inclinada e com sombra.
- A finalização segue `gen/formatos/arte_formatos.py`: grade nativa 400×225, paleta de 64 cores, ampliação NEAREST ×4. `static/simulados/escrivaninha-v2.webp`: **1600×900, 31.252 bytes**, lossless. Fonte gerada, script portátil e proveniência: `gen/simulados/escrivaninha-v2-raw.jpg`, `otimizar_arte_ui.py`, `arte-ui-v2.json`. Para reexportar (Pillow instalado): `python gen/simulados/otimizar_arte_ui.py`. Não chama serviços, não lê `.env` e não modifica nenhuma arte antiga.
- Ampulheta SVG original de interface, com os números HTML gravados numa pequena placa de latão. HUD fixa e compacta no celular; preservados IDs, contagem da parte/competência, avisos 5/1 min, envio automático e retomada. Não é um relógio desenhado dentro da imagem de fundo.
- Papel mais enxuto: título de época com a pilha de fontes display já usada no login (Cinzel/Trajan/Georgia, sem download de fontes), cinco fitas com tempos, prova completa dourada como ação principal. As quatro competências permanecem independentes. Tentativa ativa é informada por texto e opção de retomar; não torna a prova completa falsamente desabilitada. Substituição e descarte continuam com confirmação.
- Caderno de tentativas recolhido por padrão. Descarte vira link discreto no rodapé. Aviso curto de não afiliação fica no rodapé, expansível com detalhes e informação sobre reconhecimento de voz. A ressalva editorial das faixas TCF saiu das telas de início, escrita e resultado e continua **neste documento**; intervalos solicitados e contadores permanecem nas tarefas.
- Botões estáticos/dinâmicos usam `.botao`, textura `nivelamento/papel-textura.png`, cores e bordas do jogo. Não há framework de UI novo. Cenário compartilhado por início/prova/resultados. O examinador continua sendo Anselme.
- **Não foram alterados** app/backend, Cosmos, regras, bancos, áudios, voz, XP, música, placas/lógica do mapa, telas congeladas ou `motor.js`.

## Fórmulas e relógio
TEF: CO 40 QCM/40 min; CE 40/60 min; EE A 25 min (mín. 80 palavras) + B 35 min (mín. 200); EO A 5 min + B 10. Completo: 2 h 55.
TCF: CO 39/35 min; CE 39/60; EE 3 tarefas/60; EO entrevista 2 min, preparação 2 min, interação 3:30 e ponto de vista 4:30. Completo: 2 h 47.

O contador da parte e o total restante da competência (CO/CE/EE/EO) começam no servidor ao iniciar, ficam fixos na ampulheta, visíveis também no mobile, áudio e oral; avisa nos últimos 5 min/1 min. Guarda timestamps e deadline no perfil: recarregar não zera o relógio. No zero envia automaticamente e segue à próxima parte; se a página foi fechada, ao reabrir envia a parte vencida e conserva o prazo encadeado, sem ganhar tempo extra. Sem conexão, mostra erro e tenta salvar de novo. Rascunhos ficam no navegador até a entrega; não são sincronizados entre aparelhos. Sem localStorage, há aviso para manter a página aberta.

EE TCF usa 60–120 / 120–150 / 120–180 palavras, **a confirmar no PDF oficial**, conforme o relatório de pesquisa. TEF A é continuação de fait divers e B opinião argumentativa. Escrita não é corrigida: contador, indicação da faixa e checklist de autoavaliação; texto curto é salvo mesmo assim, especialmente no envio automático.

## Questões e áudio
Há 80 itens editoriais originais (40 CO e 40 CE), sem copiar questões reais. Cada prova tem banco completo materializado: TEF 40+40 e TCF 39+39, totalizando 158 posições. **Os dois modelos compartilham parte do banco**; não são 158 questões diferentes. Dificuldade A1→C2 é uma classificação editorial, não calibração. Um modelo fixo por exame, sem aleatorização.

CO: 40 MP3 franceses canadenses gerados com o edge-tts já usado no projeto (vozes Sylvie/Antoine, alternadas). Os 39 primeiros também atendem ao TCF. Duração dos clipes: aproximadamente 9,5–22,7 s; os textos e documentos ainda precisam de revisão pedagógica e de comparação com a extensão/distribuição de estímulos de uma prova real. Áudio técnico decodificado com ffprobe, não avaliado de ouvido por um humano nesta execução.

Sem replay: o botão desativa após começar; TEF tenta início após 5 s de leitura. Se o navegador bloquear autoplay antes de haver áudio, solicita um clique para autorizar a primeira escuta. Recarregar não libera uma gravação já consumida neste navegador; uma escuta interrompida não é repetida. TCF mostra a pergunta depois do áudio (a pergunta também é lida no MP3). CO é sequencial, sem voltar; CE permite navegar entre questões (também no TCF neste treino; confirmar a interface oficial específica do centro para essa regra). Quatro alternativas e uma correta por item; erro/branco não desconta pontos.

Geradores: `gen/simulados/gerar_banco.py` e `gerar_audio.py` (este usa o executável edge-tts do box em `/workspace/ncl/.tts/bin/edge-tts`; caminho a adaptar se quiser regenerar no Windows). Não carregam `.env` nem usam chave. Os áudios prontos estão no patch, não é preciso gerar no PC.

## Examinador oral
Role-play por intenções/palavras-chave, não uma pessoa nem IA generativa. TEF A/TCF interação respondem a perguntas de preço, horários, local, material e inscrição sobre o anúncio; TEF B apresenta objeções; TCF entrevista pergunta sobre o cotidiano, e a defesa de opinião recebe pedidos de esclarecimento. A preparação TCF é separada, sem diálogo, com dois minutos de relógio.

Usa a infraestrutura Web Speech já existente (`ChemVoz` para disponibilidade/idioma) e reconhecimento contínuo no motor novo; o navegador pode reiniciar a sessão de reconhecimento depois de pausas. Pare a intervenção para enviar ao examinador. Suas respostas aparecem no diálogo, e o NPC pode ser ouvido por speechSynthesis. Precisa de permissão, navegador compatível e HTTPS (ou localhost). O serviço de reconhecimento do navegador pode transmitir voz ao provedor. Há alternativa digitada, explicitamente marcada como texto. Reconhecimento/vozes/ruído/acento variam; precisa de teste com microfone real, especialmente em telefone.

Transcrição salva com limites: últimas 40 intervenções e até 5.000 caracteres por parte oral; o resultado avisa quando truncado, e métricas se referem ao trecho salvo. Feedback conta palavras, intervenções, perguntas e tempo: **não avalia pronúncia, qualidade, fluência, persuasão ou proficiência**. O NPC pode interpretar mal perguntas fora do roteiro. Não substitui um examinador humano.

## Pontuação e dados
CO/CE: acertos brutos + **estimativa não oficial** linear na escala, com faixa NCLC baseada nos limites do relatório/IRCC. TEF mostra /699 e equivalência antiga estimada CO/360 ou CE/300; TCF /699. **Não existe conversão oficial de proporção de acertos**: provas reais usam itens calibrados/IRT. A estimativa não prevê sua nota real e não serve para imigração. EE/EO ficam sem nota ou NCLC.

Aviso de não afiliação a CCI Paris, France Éducation international e IRCC aparece em todas as telas. XP sempre zero; nenhuma regra do mapa ou batalha foi alterada.

Uma tentativa ativa e as últimas cinco concluídas ficam no perfil: `simulados_ativo` / `simulados_historico`. Novas contas usam o adaptador Cosmos existente (mesmo `users`), perfis legados continuam funcionando e `teste` continua só em memória. Nenhuma configuração, índice, container ou TTL foi alterado. Início/entrega escrevem no perfil; navegar/responder/consumir áudio usa rascunho local. Dados escritos e transcrições são privados ao usuário, mas não entram em um serviço de correção.

## Testes e pendências
- `python gen/formatos/teste/teste-simulados.py`: 91 verificações Flask/regras, 29 verificações JavaScript e 43 verificações adicionais de UI/DOM com o HTML real do Flask (timer, reload, autoplay único, navegação, TCF pergunta após áudio, autosubmit, voz contínua simulada e preparação), offline.
- Onboarding: 122 OK, mais seus 72 checks JS; rotas: 57 OK; `node mapa.js`: 40 etapas, praça, cliques e arrasto preservados. Os avisos de HTMLMediaElement.play do jsdom são esperados; jsdom não comprova reprodução real.
- MP3: 40 arquivos decodificados, 4.148.352 bytes no total, aproximadamente 691 s.
- **Não foram produzidas screenshots reais da v2.** Não há executor de navegador/desktop disponível nesta sessão, e a regra da ferramenta proíbe dirigir navegador por Shell/Playwright; não foi contornada. As 43 verificações UI usam jsdom, que não renderiza layout e não comprova qualidade visual, sobreposição ou responsividade. Foi inspecionada a arte gerada, não as telas em um navegador. Ainda faltam as capturas reais 1280×800 e 390×844 (início, CO com timer, EO e resultados), sua inspeção e a iteração visual. Diretório reservado: `/workspace/ncl/prints-simulados/`; nenhum PNG desta revisão foi criado. A referência anexada no pedido não existia no caminho informado; foram estudadas as artes e estilos reais do projeto. Nada foi apresentado como screenshot ou teste real de microfone/áudio.
- Faltam confirmar faixas TCF no PDF, validar interface de navegação CE TCF, ampliar os modelos independentes/estímulos longos, revisão pedagógica/calibração, qualidade sonora e teste do NPC com fala real.
- Nenhum `.env` foi aberto. Testes usam fake Cosmos, bloqueiam dotenv e não enviam e-mails. O app normal preserva seu `load_dotenv()` habitual.

Backup inicial: `/tmp/bk-simulados/`; **backup anterior à UI v2: `/tmp/bk-simulados-ui/`**, com caminhos de `out/`, `gen/` e `docs/`. Logs dos testes e hashes de integridade também estão no backup da v2. O ZIP usa caminhos relativos à raiz do aplicativo (`templates/`, `static/`, `gen/`, `docs/`, sem prefixo `out/`), não contém `.env`, ambientes, caches, bancos, backups ou capturas falsas.

Prévia offline já disponível no box: `http://localhost:5077/__login-teste?ir=/simulados/tcf` (somente servidor offline com perfil de teste). Para capturar futuramente, usar `teste`, nunca contas reais/Cosmos real. Confirmar enquadramento do papel/fitas, nome na placa, retorno por rolo, cronômetro fixo nas larguras indicadas, áudio único, alternativa digitada e rodapé do resultado. A inspeção e os PNGs **ainda estão pendentes**, portanto a aprovação visual não está concluída.
