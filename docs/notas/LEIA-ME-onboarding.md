# Onboarding — Chemin des Étoiles

## Instalar no teste local
1. Pare o Flask com Ctrl+C e faça uma cópia da pasta do projeto.
2. Extraia `patch-onboarding.zip` diretamente em `ncl-simulado`, substituindo os arquivos indicados. Não há pasta `out/` dentro do zip.
3. Execute `python app.py` e abra `http://localhost:5000`. Atualize com Ctrl+F5.
4. O login `teste` continua livre como antes. Para validar o cadastro completo, saia e use outro usuário.

## Fluxo
Cadastro na própria tela de login (usuário, e-mail, senha e confirmação) → link de confirmação → personagem e nome → nivelamento → pergaminho de boas-vindas → mapa.
O botão “Começar a missão” da última folha do nivelamento abre o pergaminho. O botão existente do pergaminho termina a introdução e abre o mapa. Depois, entrar novamente leva direto ao mapa. A etapa pendente é retomada após sair/entrar.

## Desenvolvimento sem enviar e-mail
Sem `MAIL_SERVER`, o link de confirmação aparece no terminal que executa Flask; nenhum e-mail é enviado. Copie o link para o navegador. Para exibir também um botão na tela, inicie em modo de teste local no PowerShell:

```powershell
$env:NCL_MODO_TESTE="1"
python app.py
```

Use esse modo apenas localmente. O link expira em 24 horas; pode ser usado uma vez. Reenvio limitado a uma vez a cada 60 segundos. Sem confirmação, a conta não entra. Contas pendentes com mais de 24 h são removidas pelo jogo; a varredura roda no máximo uma vez a cada 20 minutos, acionada por cadastro/login comum. Um cadastro que encontra suas reservas expiradas também pode liberá-las imediatamente.

## Envio real (configurar depois; nenhum servidor foi alterado)
As configurações vêm das variáveis de ambiente; o `.env` local continua sendo carregado como antes (python-dotenv), então dá para colocá-las lá:

- `SECRET_KEY`: segredo forte, estável e privado para assinar sessão e links. Configure antes de usar publicamente; a chave de desenvolvimento não é segura para produção. Mudar essa chave invalida sessões e links antigos.
- `MAIL_SERVER`: host SMTP.
- `MAIL_PORT`: normalmente `587`.
- `MAIL_USERNAME`, `MAIL_PASSWORD`: autenticação SMTP; mantenha em segredo.
- `MAIL_FROM`: apenas o endereço do remetente; o nome exibido é “Chemin des Étoiles”.
- `MAIL_USE_TLS`: `true` por padrão, usa STARTTLS. Esta implementação é para SMTP/STARTTLS, não SSL implícito da porta 465.
- `APP_BASE_URL`: endereço onde o navegador acessa o app, sem barra final; padrão `http://localhost:5000`. Em uso público, configure a URL HTTPS correta antes de gerar links.
- `NCL_MODO_TESTE`: deixe desligado fora do teste local.

Exemplo de provedor: Gmail com `smtp.gmail.com`, porta 587 e TLS; habilite verificação em duas etapas e use uma senha de app no SMTP, não a senha normal. Não compartilhe a senha de app no chat. Entrega real de e-mail ainda precisa ser validada pelo Alex; os testes usaram SMTP simulado.

## Dados e preservação
**Novas contas e perfis ficam agora no Cosmos existente**, banco `ncl-exam-db`, container `users`, por `get_users_container()`. Não é necessário credencial nova: usa `COSMOS_CONNECTION` já configurada no seu computador. O carregamento habitual via `load_dotenv()` foi mantido no app; o agente não abriu nenhum `.env`. Os testes offline desabilitam esse carregamento e substituem Cosmos/SMTP por simulações.

Não cria nem muda containers, índices, TTL, políticas de chave única ou configuração Azure. O código pressupõe partition key `/id`, conforme os point reads antigos (`partition_key=uid`); isso ainda precisa ser conferido com o container real no PC do Alex. O login `teste` continua em memória e não lê/grava Cosmos, mesmo se o serviço estiver indisponível.

Cada cadastro normal cria três documentos: conta com `id=uid`, reserva `reserva-usuario:<usuario normalizado>` e reserva `reserva-email:<email normalizado>`, ambas apontando para `uid`. Caracteres incompatíveis com IDs Cosmos são codificados. As duas reservas são criadas antes da conta usando `create_item`; um 409 impede duplicatas, inclusive em cadastros simultâneos. A conta conserva o perfil no mesmo documento e acrescenta campos de autenticação, sem senha em texto puro. Consultas por usuário/e-mail usam point reads das reservas, sem query entre partições.

Falhas normais fazem rollback dos documentos pertencentes à tentativa, com ETag. **Não existe transação atômica entre as três partições:** se a rede cair também durante o rollback, pode sobrar uma reserva. A retomada é conservadora: uma reserva órfã recente não é roubada; depois de 24 h, um novo cadastro com aquele identificador pode recuperá-la. Limpeza, confirmação e reenvio usam ETag/If-Match para não apagar uma conta ativada nem enviar/confirmar duas vezes numa corrida. A limpeza apaga somente `tipo='conta'`, `confirmado=false` e criação anterior a 24 h; remove depois as reservas que ainda pertencem ao mesmo UID. Perfis legados não são transformados nem entram nessa limpeza.

**SQLite foi desativado, sem fallback.** `instance/usuarios.sqlite3`, se existir, não é lido, migrado, alterado nem incluído no patch. Contas criadas só no SQLite precisam ser recadastradas no Cosmos; Alex informou não ter usado contas reais ali. O antigo `contas_locais.py` foi guardado em `/tmp/bk-onboarding-cosmos/out/contas_locais.py` no box e removido do projeto no box. Se esse arquivo sobrar no seu Windows após extrair o patch, fica inativo, sem importação pelo app; pode arquivá-lo depois. Não há necessidade de apagar nenhum banco para instalar.

Senhas são guardadas somente como hash Werkzeug. Respostas do nivelamento são salvas sem pontuar/classificar: a régua continua pendente.
Templates de personagem, nivelamento e missão, motor, conteúdo de etapas, bordas e regras de XP permaneceram intactos. Músicas e cache `v=2` preservados. Regiões 2–12 continuam sem clique. O mapa ganhou só o link “Sair” para contas normais.

## Como testar no PC do Alex (Cosmos real)
1. Pare o Flask com Ctrl+C, extraia o patch e execute `python app.py` na mesma pasta/venv de antes. A conexão Cosmos existente continua suficiente; não envie credenciais pelo chat.
2. Entre como `teste` para conferir mapa e músicas sem gravar no Cosmos. Saia para testar cadastro real.
3. Crie um usuário claramente identificável de QA, por exemplo com prefixo `qa_20261107_`, e um e-mail seu que possa receber a confirmação. Se SMTP não estiver configurado, use o link do terminal ou `NCL_MODO_TESTE=1` localmente.
4. Confirme, escolha personagem/nome, conclua o nivelamento, abra o pergaminho e entre no mapa. Saia e entre novamente: deve cair direto no mapa. Tente repetir usuário/e-mail para conferir os conflitos.
5. Esse teste normal grava de verdade os três documentos no `users` existente. A validação real no Cosmos e a entrega real SMTP ainda precisam acontecer no seu computador; aqui só foram usados fakes.

## Como limpar as contas de teste
Contas não confirmadas expiram após 24 h e são limpas pelo jogo, com suas reservas, em um cadastro/login comum posterior (varredura limitada a 20 min). Contas confirmadas **não** são apagadas automaticamente.
Para remover uma conta QA confirmada no Data Explorer do Azure, pare seu Flask, identifique o UID e confira que a conta é realmente sua conta de teste; apague primeiro o documento da conta, depois as duas reservas **apenas se `uid` nelas ainda apontar para aquela conta**. Não apague perfis legados nem outros documentos. Não foi executada nenhuma limpeza no Cosmos real durante este trabalho.

## Isolamento futuro e custo (somente sugestões, não implementadas)
- Separar cadastros QA dos reais seria mais seguro: futuramente pode existir `COSMOS_USERS_CONTAINER` apontando para um container separado `users-teste`, ou uma estratégia completa de prefixos de teste. **Essa variável/seleção não foi implementada** e nenhum container foi criado. Hoje cadastro normal usa `users`; só o usuário especial `teste` e os testes automatizados ficam isolados em memória.
- Custo ilustrativo de cadastro pequeno: três creates + um replace para reservar envio, além de alguns point reads, aproximadamente **25–50 RU**, fora varredura, confirmação, conflitos e retries. Não é uma medição do seu banco: tamanho dos documentos, indexação, consistência e número de partições mudam o custo. Um point read de 1 KB costuma custar ~1 RU e uma escrita pequena ~5 RU como referência.
- TTL no Azure poderia simplificar expiração no futuro, mas exige planejar também as reservas para não expirar nomes de contas confirmadas. Não basta ligar TTL indiscriminadamente. **Nenhum TTL foi configurado aqui.**

## Verificação offline realizada
- `python gen/formatos/teste/teste-onboarding.py`: **103 OK**, Cosmos fake thread-safe, SMTP simulado; inclui corridas de usuário/e-mail, 404/409/412, rollback antes/depois de uma escrita cuja resposta se perdeu, recuperação de reserva órfã, limpeza, reenvio, confirmação única e erros amigáveis com Cosmos fora.
- `python gen/formatos/teste/teste-rotas.py`: **57 OK**, offline; perfis legados e `teste` preservados.
- `node mapa.js` em `gen/formatos/teste/`, com `flask-offline.py` na porta 5077: 40 etapas, praça, cliques e arrasto corretos. jsdom avisa que não implementa `HTMLMediaElement.play`; não é teste de áudio real.
- Testes e servidor offline substituem `load_dotenv` antes de importar o app, sem abrir `.env`, e nunca inicializam o cliente Cosmos real. O app normal mantém `load_dotenv()`.
- Nenhum screenshot novo nesta execução; visual e reprodução real ainda dependem de navegador. Nenhuma tela congelada foi alterada nesta troca de armazenamento.

Backups no box: `/tmp/bk-onboarding/` (versão inicial) e `/tmp/bk-onboarding-cosmos/` (antes desta troca). Nenhuma conexão ou mudança remota foi feita durante a implementação. Ao extrair este patch, você aplica as mudanças apenas no seu teste local.
