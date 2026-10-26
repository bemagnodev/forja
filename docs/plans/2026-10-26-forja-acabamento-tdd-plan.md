# Forja — plano de acabamento com TDD

Status: aprovado pelo usuário em 26/10/2026; implementação e validação concluídas, aguardando revisão antes de commit/push.

Fonte: `docs/reviews/2026-10-25-forja-audit.md`, pontos 1–8, considerando as decisões já editadas nesse documento. Objetivo: melhorar os fluxos existentes e a apresentação para a entrevista. O ponto 7 está explicitamente adiado no documento atual; não será implementado nesta rodada. O ponto 9 foi transferido ao backlog pós-entrevista.

## Abordagem proposta

Recomendo correções pequenas por comportamento, reutilizando Django, React Query, componentes e testes existentes. Alternativas: uma reforma geral do frontend exigiria validar muita coisa sem relação direta com os problemas; apenas mudar textos e CSS deixaria falhas de persistência e navegação abertas. A rodada incremental cobre os defeitos sem criar uma arquitetura nova.

Ordem: **1 → 3 → 4 → 5 → 2 → 6 → 8**. Cada etapa passa por teste vermelho, correção mínima, teste verde e refatoração pequena. O ponto 7 é uma decisão de escopo, sem código. Para layout, o teste automatizado cobre estrutura, conteúdo e calendário; a qualidade visual exige navegador real.

Sem alterações de datasets, prompts, resultados ou métricas do benchmark; sem chamadas reais de IA, sincronizações externas ou migrations de produção. O redesign de Contests documentado separadamente não será incorporado automaticamente a esta rodada.

## 1. Fila: confirmação honesta e recuperação de falhas

Arquivos principais: `pages/Queue.tsx`, `components/queue/AddItemDialog.tsx`, edição de descrição e controles de prioridade quando necessário.

**Decisão proposta:** concluir, criar e editar somente confirmam sucesso após resposta do servidor. Durante a operação, impedir o reenvio conflitante e mostrar estado pendente discreto. Preservar o Desfazer após conclusão confirmada. Reordenação pode continuar otimista para manter o arraste fluido, mas com rollback e uma operação de reordenação em voo; sem mecanismo genérico novo de mutations.

**RED:** ampliar `pages/Queue.test.tsx` e criar `components/queue/AddItemDialog.test.tsx` se necessário. Promises controladas simulam pendência, sucesso, timeout e 500. Cobrir:

- sem toast de sucesso nem remoção definitiva antes da confirmação;
- falha de conclusão mantém o item; falha do Desfazer preserva o estado confirmado;
- criação falha mantém formulário aberto e valores; sucesso fecha e limpa;
- clique repetido não cria duas requisições;
- prioridade/descrição não anunciam valor persistido quando o salvamento falha;
- arraste falho restaura a ordem e informa erro; refetch não é sobrescrito por rollback antigo.

**GREEN:** ajustar callbacks e estados locais/React Query; usar erro acessível e toast já existente. Definir snapshot da reordenação com cancelamento de query antes da alteração e invalidação ao finalizar. Não apagar conteúdo do formulário no erro.

**Aceite:** nenhum falso sucesso; nova tentativa funciona; regressões existentes de inclusão, filtros, IA e toast continuam passando. Não adicionar visualização de concluídos ou novos recursos da fila nesta etapa.

## 2. Fila: prioridade visível no desktop

**Decisão proposta:** prioridade antes das informações secundárias, com espaço reservado; título e rating preservados. Tags mostram uma amostra e expansão acessível para o restante; descrição mantém edição e uma prévia curta. Contest pode virar segunda linha da identificação quando necessário. Preservar agrupamento, arraste, ícones de plataforma e classificação com IA.

**RED:** testes de interação para abrir tags completas, acessar prioridade, editar descrição e classificar usando IA simulada. Evitar testes que apenas fixam nomes de classes CSS.

**GREEN:** ajustar somente os componentes da tabela/linha necessários, sem nova biblioteca ou framework de tabela.

**Aceite visual obrigatório:** 1280, 1366 e 1600 px, com títulos longos, muitas tags e agrupamento ativo/inativo. Prioridade e ações essenciais não dependem de rolagem horizontal em 1280/1366. Tooltip/expansão funcionam por teclado. Registrar capturas locais; não usar dados privados em screenshots do README.

## 3. Contest: metadados independentes da navegação

Arquivos: `backend/api/api.py`, tipos de Contests, `pages/ContestDetail.tsx`, `ProblemStatusSelect.tsx` e chamadas de navegação pertinentes.

**Decisão proposta:** endpoint de detalhe `/contests/{id}` com nome, plataforma, URL e resumo de participação/progresso do usuário autenticado. Reutilizar as regras de resumo existentes da listagem, extraindo somente a lógica realmente compartilhada. Não duplicar cálculos nem buscar todos os contests para localizar um ID no frontend. `location.state` poderá antecipar conteúdo, mas a resposta será a fonte atualizada.

**RED backend:** acrescentar casos em teste de Contests existente, ou `test_contests.py` se a responsabilidade justificar: usuário com participação; ID inexistente; acesso sem autenticação; ausência de participação sem expor progresso de outro usuário; resumo atualizado após mudança de revisão. Definir 404 para detalhe de participação inexistente e não disparar importação externa.

**RED frontend:** novo `pages/ContestDetail.test.tsx`: entrada direta sem state, entrada pelo Dashboard, state antigo substituído pelo servidor, loading/erro/404 e atualização de resumo após mutation simulada. A página deve mostrar nome e URL corretos em todos os caminhos.

**GREEN:** integrar query de detalhe e invalidar detalhe, problemas, lista, Dashboard e fila somente nos fluxos em que os dados sejam afetados. Testar também falha de mudança de status, sem fingir sucesso. Preservar as regras existentes de DONE/UPSOLVED.

**Aceite:** link direto funciona; nome e cabeçalho não ficam presos ao snapshot da navegação. Sem redesign da página ou implementação do modo virtual AtCoder nesta etapa.

## 4. Dashboard: períodos, nomes e fuso consistentes

Arquivos: `backend/api/services/dashboard_service.py`, `backend/api/tests/test_dashboard.py`, contrato `api-dashboard.ts` e componentes do Dashboard.

**Decisões propostas para aprovação:**

- manter o cálculo móvel de 30 dias e mudar o rótulo para “Últimos 30 dias”;
- calendário anual e resumo semanal representam dias civis em `America/Sao_Paulo`, incluindo hoje; último ano = hoje e 364 dias anteriores;
- sete dias = hoje e seis dias anteriores, com limites de consulta coerentes;
- calendário conta submissões aceitas, sem deduplicá-las silenciosamente; tooltip explica a unidade;
- manter “Questões recentes”, conforme o Markdown atual, com eventos AC no feed; não introduzir deduplicação sem decisão adicional;
- sequência máxima explicitamente “no último ano”; sequência atual admite hoje ainda sem AC, como a regra anterior;
- “Resolvidos por tópico” e “15 mais frequentes”, sem afirmar domínio;
- manter rating/tags de referência e mostrar cobertura de problemas classificados; não preencher lacunas usando IA nesta rodada;
- manter a regra de conclusão manual e seu efeito no total, sem alterar a FSM.

**RED:** relógio fixo, virada de mês, instantes que cruzam UTC/São Paulo, bordas inclusiva/exclusiva do intervalo anual/semanal, ano bissexto, ausência de AC, duas AC no mesmo dia/problema, tópico acima do limite de 15 e problema sem rating. Testar que o cálculo não passa a usar previsões de IA. Testes frontend verificam rótulos, cobertura e ausência de métricas inventadas.

**GREEN:** usar conversão explícita de timezone e limites locais. Incluir na resposta a data de referência/fuso necessária ao calendário; frontend não deve recalcular “hoje” em um fuso diferente do backend. Preservar consumidores atuais de campos quando possível; não exigir migration.

**Aceite:** API e calendário atribuem uma AC ao mesmo dia; todos os textos descrevem a unidade e janela real. Dados antigos não são regravados. Inconsistências dos importadores CSES/AtCoder permanecem tarefas separadas, sem prometer que serão resolvidas por esta correção de apresentação.

## 5. Calendário anual: alinhamento e composição

Depende do contrato de datas do ponto 4. Arquivos: `ActivityHeatmap.tsx`, seu teste, `Last7DaysWidget.tsx`, layout do Dashboard e respectivos testes.

**Decisão proposta:** semanas de domingo a sábado, com células de preenchimento não contadas fora dos 365 dias. Rótulos discretos de meses e dias; legenda proporcional. Altura natural e alinhamento ao topo, retirando o vazio causado pelo alongamento/ancoragem inferior. Ajustar a composição com o resumo semanal sem encolher mais os pontos. Acrescentar dias ao resumo semanal.

**RED:** cobrir datas inicial/final, alinhamento de domingo e sábado, preenchimentos, meses, ano bissexto, contagem de dias ativos dentro do recorte e associação entre data e tooltip. Dados vazios produzem calendário válido. Não usar screenshots como único teste de datas.

**GREEN:** composição mínima com CSS e componentes existentes; helper puro de calendário apenas se necessário para separar cálculo de apresentação. Preservar cores da Forja e escalas de intensidade.

**Aceite visual:** revisão em 1280/1366/1600, com dados vazios e densos, sem rolagem horizontal nem cartão alto com grade encostada no rodapé. Rótulos legíveis em compartilhamento de tela. Ajuste visual será apresentado antes de publicação.

## 6. Telas futuras acessíveis e saída da conta

**Decisão já registrada:** manter Notes, Settings, Profile e Teams acessíveis. Sinalizar “Em breve” nos atalhos e explicar brevemente a finalidade prevista em cada tela, sem prometer prazo ou funcionalidade pronta.

**RED:** ampliar `Sidebar.test.tsx` para links e indicação de disponibilidade; verificar conteúdo das quatro páginas sem implementar seus módulos. Testar saída via interface e retorno ao login.

Adicionar logout visível exige cobrir a transição de sessão: em `AuthContext.test.tsx` e teste de integração com React Query, confirmar remoção de tokens/cabeçalho, cancelamento das queries da sessão e limpeza de dados em cache. Uma resposta antiga atrasada não pode preencher a próxima sessão. Usar APIs e interceptadores atuais, sem reescrever autenticação.

**GREEN:** saída em área de conta, ação acessível por teclado, navegação protegida mantida. Limpeza de sessão mínima necessária para tornar essa saída confiável; não ampliar para convite, refresh ou política de senha.

**Aceite:** nenhuma tela é removida; “Em breve” claro; logout não deixa os dados da conta anterior visíveis ao novo login simulado.

## 7. Proteção da demo: adiada

Não implementar bloqueio específico ou alterar permissões da demo nesta rodada, conforme o Markdown atual. Preservar o risco documentado. Não classificar esta pendência como concluída.

## 8. README alinhado à entrega

**Mudança:** descrever classificação direta versus rubrica, três modelos, conjunto de 60 problemas e três comparações públicas. Usar números do relatório publicado com seus denominadores, decisão do Gemini e limitações. Remover a promessa de algo já entregue no roadmap; manter futuras estratégias como futuras.

**Validação:** documentação não pede teste artificial que espelha o texto. Conferir números contra `AI_LAB_BENCHMARK_AB_RESULTS.md` e snapshots, links e renderização Markdown. Screenshot nova somente se sanitizada e útil; preferir dados públicos do benchmark, sem nome/conta real.

**Aceite:** não afirmar superioridade estatística, custo/tokens não medidos, validação de 2500–3500, ou comparação controlada de latência. Não publicar enunciados, respostas livres, exemplos privados ou credenciais adicionais.

## Organização de testes e validação final

Seguir `docs/TESTING.md`: AAA, testes isolados, Django com `core.settings_test` e SQLite em memória. Reutilizar arquivos de testes existentes; novos somente por responsabilidade. Não mover ou renomear testes nem reduzir a suíte. Chamadas de fonte, IA e serviços externos substituídas por mocks.

Em cada etapa: executar primeiro a regressão nova e registrar falha esperada; fazer correção, executar o arquivo e testes relacionados. Ao fechar a rodada:

```powershell
# Dentro de backend, usando a venv existente:
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe manage.py check --settings core.settings_test

# Dentro de frontend:
npm test
npx tsc --noEmit -p tsconfig.app.json
npx tsc --noEmit -p tsconfig.node.json
npm run build
# ESLint deve receber explicitamente a lista dos arquivos TS/TSX alterados.

# Na raiz do repositório:
git diff --check
```

Registrar diagnósticos históricos separadamente e resolver os que forem tocados/introduzidos pela rodada; não chamar de verde um typecheck que permanece falhando. A revisão final deve incluir navegação real com API/IA simuladas em ambiente local seguro e conferência visual. Não rodar um backend de demonstração com credenciais ou banco de produção por conveniência.

## Unidades de entrega futuras

Sugestão de commits pequenos após autorização específica: fila/persistência; detalhe/API de contest; semântica e datas do Dashboard; calendário; layout da fila; telas futuras/logout; README. Testes acompanham cada comportamento. Refatorações independentes não entram nesses commits. Não há commit, push ou deploy autorizado por este plano.

## Notion atualizado nesta rodada

- Ponto 9 registrado como risco técnico alto, Sprint Futuro, pós-entrevista: https://app.notion.com/p/4056091e553681faa539f4f91a6bfa14
- Encerradas nas vistas de pendências: restauração do Gemini, conjunto de avaliação e comparação de modelos. Histórico preservado com evidências.
- Classificação em lote do acervo mantida aberta: runner de benchmark não equivale à feature do produto.
- Validações gerais de autenticação, smoke AtCoder e auditoria de dados não foram encerradas sem evidência suficiente.

## Aprovação registrada

Usuário aprovou a execução deste plano. Ponto 7 e problema dos IDs permanecem adiados. Commit, push e deploy ainda dependem de autorização posterior.


## Registro de execução

- Testes vermelhos confirmados antes das correções: persistência/criação/reordenação da fila; detalhe de contest inexistente; calendário e janelas UTC/São Paulo; tags expansíveis; limpeza de sessão e refresh antigo; calendário sem data de referência.
- Ponto 1: confirmações após resposta; rascunhos preservados; arraste otimista com rollback sem sobrescrever refetch mais recente.
- Ponto 3: detalhe autenticado por ID; resumo compartilhado com listagem, incluindo problemas de catálogo sem tracking; invalidação dos resumos após revisão manual.
- Pontos 4/5: referência de data do backend, datas locais, sete dias civis, rótulos e cobertura; semanas alinhadas e calendário com altura natural.
- Ponto 2, primeira iteração (substituída na revisão visual): seis colunas, prioridade antes das informações secundárias, contest abaixo do título e tags expansíveis. Conferência local em 1280/1366/1600: sem rolagem horizontal na tabela.
- Ponto 6: páginas futuras acessíveis com “Em breve”; saída visível; cache e requests antigos isolados na transição de sessão. Hook separado de AuthProvider para cumprir o lint de Fast Refresh.
- Ponto 8: README atualizado com resultados, recortes e limites da avaliação.
- Proteção adicional de compatibilidade: durante versões desencontradas de frontend/backend, ausência da nova data de referência exibe indisponibilidade do calendário, sem derrubar a página ou inventar data local.
- Prévia visual usa somente dados sintéticos e middleware local descartável em `frontend/node_modules/.cache`; não usa Django, banco ou IA. Scripts/capturas privados não fazem parte da entrega Git.
- Nenhuma alteração nos IDs de submissão, sincronizadores, modelos Django, dataset congelado, prompts ou snapshots do benchmark.


### Validação da entrega

- Frontend: 139 testes aprovados em 25 arquivos na execução completa sequencial. Rodada concorrente anterior excedeu 5 segundos em dois testes; os 22 testes dos dois arquivos passaram isoladamente, e a rodada completa sequencial passou sem alterar timeouts.
- TypeScript app/node, ESLint dos arquivos alterados, build Vite, Django check com settings_test e git diff --check aprovados. Nenhuma regra foi desativada.
- Backend final: **461 testes aprovados**, com SQLite em memória e rede externa bloqueada. A execução final usou uma pasta temporária nova do sistema, fora do repositório. Rodadas anteriores no diretório monitorado do projeto encontraram PermissionError intermitente em dois testes existentes de escrita atômica do runner; ambos passaram isoladamente. Nenhum teste ou regra foi modificado para contornar essas falhas. O resultado final completo está em `backend/var/test-temp/acabamento-pytest-system-temp.log` (privado e ignorado pelo Git).
- Warnings históricos: staticfiles ausente em settings de testes, retorno de tuplas depreciado em endpoints antigos, base Browserslist antiga e bundle maior que 500 kB. Não são novos erros ocultados.
- Conferência visual local: fila sem overflow horizontal em 1280 (969/969 px), 1366 (1055/1055 px) e 1600 (1289/1289 px), incluindo tags abertas e agrupamento. Calendário sem overflow nas três larguras; cartão em 1366 com aproximadamente 239 px, em vez dos 294 px anteriores.
- Pelo navegador, nome/link do contest carregaram vindo do Dashboard; falha simulada de edição preservou o rascunho; logout retornou à tela de login. Nenhuma requisição foi enviada ao backend publicado.
- As mudanças preexistentes em `docs/plans/2026-10-25-contests-redesign-design.md` não foram produzidas ou alteradas por esta rodada; não incluí-las automaticamente nos futuros commits.
- Não houve commit, push, deploy, migration ou nova inferência de IA. Os pontos 7 e 9 permanecem adiados.

- Revisão do diff: `api.py` já possui CRLF no objeto Git antigo. `git -c core.autocrlf=false diff -- backend/api/api.py` ou `git diff --ignore-space-at-eol` evidencia as alterações localizadas de schema, endpoint e resumo compartilhado; não houve reescrita arquitetural do arquivo. Nenhuma configuração Git global foi alterada.


### Revisão visual e autorização de publicação

Usuário autorizou corrigir o visual, conferir, fazer commit e push. Os badges de tags e o tooltip anteriores foram restaurados, com indicação acessível; o contest voltou à coluna própria. A prioridade continua visível. Logo da plataforma, título e botão de IA usam uma linha de alinhamento comum e espaço fixo para a ação.

Os dias e as células do calendário agora pertencem à mesma grade. Medição no navegador em 1280/1366/1600: diferença de centros inferior a 0,01 px para Dom/Ter/Qui/Sáb e para os ícones de plataforma/IA. Sem overflow horizontal na fila ou calendário. Capturas ficam fora do Git.

TDD: os dois testes de regressão falharam antes da correção; os testes focados passaram após corrigir a grade e restaurar badges/tooltip. A suíte frontend completa passou novamente: 139 testes. Nenhum timeout ou regra foi alterado.

Alterações concorrentes de resultados de contests, modelos, sincronizador, migration e tipos frontend não pertencem a esta entrega. O snapshot selecionado exclui esses trechos, inclusive no arquivo compartilhado api.py; a cópia de validação é privada em backend/var/release-check. A edição pendente do documento de redesign também fica fora. O commit de documentação 23d5082 já existente na branch é preservado na publicação normal.
