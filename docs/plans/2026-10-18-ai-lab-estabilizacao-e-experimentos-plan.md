# AI Lab: estabilização, entendimento e experimentos

## Escopo e estado

Plano solicitado em 2026-10-18 e posteriormente aprovado pelo usuário com o pedido explícito de implementação do passo 1. A separação sem cache do Explorar está aprovada. Sem chamadas reais de IA, migrations de produção, commit ou push nesta fase. As mudanças locais anteriores são preservadas, exceto comportamentos explicitamente substituídos por este plano.

Sequência acordada: (1) corrigir problemas definidos; (2) explicar e discutir a estrutura; (3) executar experimentos de prompts em escala somente após revisão e autorização próprias.

Decisões recebidas: três usuários e um usuário ativo não justificam throttle/permissões adicionais agora; classificação da fila/contests é importante e deve continuar persistida no banco; testes do Explorar não devem alterar essas previsões; melhorar diagnóstico e aproveitar validade parcial sem mudar o protocolo do benchmark.

Atualização após as últimas anotações: o cache no navegador deixou de ser a proposta. O usuário apresentou duas alternativas e depois aprovou implementar a separação sem cache. A sequência de três passos permanece; passos 2 e 3 não fazem parte desta implementação.

### Escolha recomendada e alternativa

- Recomendação: produto persistente, Explorar sem persistência/cache, benchmark em artefatos próprios. Reutilizar funções/adaptadores, não o efeito de gravar no banco. Cada interface tem uma finalidade explícita.
- Alternativa válida: reaproveitar a rota persistente em Explorar. Poupa uma rota, mas exige decidir quando um experimento substitui a previsão global, como identificar modelo/configuração e como evitar atualizações indesejadas. Isso traz decisões de produto desnecessárias para comparar modelos agora.
- Não adotar simultaneamente um terceiro sistema de cache no navegador. Não criar colunas/migrations apenas para separar o Playground: os dados atuais de classificação estão no JSONField platform_metadata, não em colunas individuais de rating/tags/reasoning. Uma eventual normalização em colunas/modelos próprios será avaliada como refatoração independente, com critérios claros, sem apagar o que já está persistido.

## Passo 1 — correções e simplificação

### 1.1 Preservar a classificação persistente da fila/contests

Hoje AILab, fila e contests compartilham POST /problems/{id}/predict. A rota atual grava campos globais e cache por modelo em platform_metadata. Remover todas as gravações dessa rota quebraria o efeito esperado dos botões da fila/contests.

Preservar POST /problems/{id}/predict como operação de produto: consulta a previsão persistida e, quando necessário ou explicitamente forçada, classifica e salva o resultado usado pela fila e contests. Manter o recálculo manual já disponível nesses componentes. Não apagar ai_rating/ai_tags/ai_reasoning ou caches existentes. A seleção experimental do Playground não deve determinar qual resultado global será usado.

Revisar o caminho de gravação do produto e os escritores relevantes: a chamada externa não deve ocorrer com bloqueio de banco aberto; a gravação posterior precisa preservar metadados oficiais e outras atualizações. Uma transação/merge apenas no classificador não garante proteção se outro escritor continuar salvando uma cópia antiga do JSON inteiro. Corrigir os cenários necessários de maneira delimitada, com testes, sem refatoração geral das sincronizações ou migração de schema. Não considerar que separar Explorar elimina o risco remanescente do produto.

TDD: reproduzir perda de atualização e proteger merge de metadados/caches; acerto no cache persistido evita chamada; recálculo solicitado salva atualização; dados oficiais permanecem; fila/contests mantêm contrato e efeitos existentes. Testes SQLite não comprovam semântica de bloqueios PostgreSQL: explicitar esse limite e não alegar teste real de concorrência nesse banco sem evidência.

### 1.2 Explorar independente, sem cache nem escrita no banco — aprovado

Propor uma rota específica de classificação do AI Lab, autenticada e sem persistência/cache, reutilizando api/ai_lab/explore.py e os adaptadores existentes. Consultar o problema é permitido; salvar/atualizar Problem ou ler uma previsão antiga como resposta ao pedido experimental não. Não copiar a engine nem os scrapers. O benchmark e seu executor continuam independentes.

Cada clique explícito em Categorizar solicita uma nova classificação no modelo escolhido. Selecionar modelo/problema, abrir a página ou trocar de aba não executa IA. Uma tentativa por clique, sem retry/fallback oculto. Resultado fica apenas no estado da tela para ser lido; trocar modelo/problema limpa a exibição. Não usar localStorage, sessionStorage, cache persistido no backend ou arquivos para reusar previsões do Explorar. Cache de buscas de problemas não é cache de classificação e pode permanecer.

Ctrl/Shift não precisa ter função especial no Explorar, pois qualquer clique já gera novamente. Preservar os atalhos de recálculo na fila/contests, onde há cache persistente. Identificar modelo e validade na UI experimental e bloquear duplicidade de clique enquanto houver requisição, sem infraestrutura de throttle adicional nesta fase.

Texto visível abaixo do botão: “Cada classificação faz uma nova chamada ao modelo. O resultado não é salvo nem altera a fila ou os contests.” Não prometer resultado sempre válido ou ausência de contabilização de falhas pelo provedor.

Decisão confirmada pelo pedido de implementação: separação sem cache no Explorar, mantendo persistência/recálculo no fluxo do produto e resultados científicos no benchmark.

TDD: duas classificações explícitas do mesmo problema/modelo fazem duas chamadas simuladas; nenhuma gravação no banco; nenhum cache legado, por modelo ou navegador impede a nova chamada; a exploração não altera o resultado retornado pela fila/contests; modelo desconhecido rejeitado antes de rede; nenhuma inferência em GET/seleção; bloqueio de clique durante requisição; ajuda visível, ícones e primeira aba preservados. Fixtures sintéticas, sem chave real.

### 1.3 Diagnóstico seguro

Adicionar status HTTP opcional e categoria à falha estruturada e ao histórico privado de novas tentativas. Preservar Retry-After quando disponível. Não salvar corpo HTTP, credenciais ou URL autenticada. Manter a distinção entre ausência de previsão utilizável e causa específica, com rótulos compreensíveis.

Não inventar status HTTP para falhas históricas: a última falha do GPT-OSS 20B segue com causa específica desconhecida. Não reexecutar para reconstruir diagnóstico sem autorização.

TDD: respostas HTTP simuladas por adaptador; status/categoria preservados; corpo privado omitido; ausência de status em timeout/legado aceita. Verificar leitores de arquivos antigos e contagem de tentativas.

### 1.4 Resultado parcial sem alterar protocolo do benchmark

Decisão explicitamente aprovada pelo usuário: rating, tags e justificativa têm estados próprios. Em Explorar, mostrar rating válido mesmo com tags inválidas e exibir as tags que pertencem à taxonomia oficial, acompanhadas de aviso e quantidade descartada. Isso é apresentação parcial, não conversão da resposta original em tags válidas. Não corrigir sinônimos. Não persistir essa apresentação filtrada como classificação global do produto.

Preservar validação estrita e métricas dos benchmarks existentes. Qualquer tag desconhecida continua invalidando a tarefa de tags no protocolo atual; rating é avaliado separadamente. Não reexportar snapshots antigos sob outra regra. Se futuramente avaliarmos tags filtradas, definir outra versão de protocolo e aplicar a mesma regra a todas as configurações, preservando a saída original e a taxa de respostas inválidas.

TDD: rating válido com tags mistas, rating inválido com tags válidas, todas as tags inválidas e resposta totalmente válida; aviso explícito; nenhuma mudança no F1/validação estrita dos artefatos anteriores; parcial não provoca retry automático.

### 1.5 Fechamento

Poucos commits futuros por comportamento, somente após autorização apropriada. RED observado, GREEN mínimo e refatoração; testes específicos em backend/api/tests/ai_lab, fixtures no conftest.py específico, sem mover/renomear legados. Suítes completas backend/frontend, build, lint dos arquivos alterados, nenhuma nova regressão TypeScript e conferência local sem inferência. Nenhuma migration de produção.

Fora deste passo: throttle, acesso staff, Redis, cache genérico, agendamento, múltiplos prompts novos e experimentos reais. Política de recuperação limitada do executor será fechada no passo 2, antes dos lotes do passo 3; não mudar política de runs antigos.

## Passo 2 — entender e discutir a estrutura atual

Sessão guiada antes de implementar mudanças do executor. Explicar e abrir os arquivos relevantes com o usuário:

- Prompt: api/ai_lab/prompts/classification_v1.txt; {taxonomy} recebe a lista oficial. Enunciado preparado entra como conteúdo separado no adaptador. Prompt atual pede rating 800–2400, tags oficiais e justificativa curta; não usa taxa de acerto.
- Dataset: backend/var/ai_lab/datasets/cf-rating-v1/development/manifest.json. São 12 entradas revisadas/congeladas, referências oficiais separadas e hash para detectar alterações.
- Execução: backend/var/ai_lab/runs/<run-id>/run.json. Um modelo, um prompt, uma configuração e um dataset por execução; previsões, tentativas e erros salvos progressivamente. Retomada preserva identidade e não refaz sucessos.
- Comparação: índice privado showcase.json seleciona explicitamente runs existentes; não executa modelos. Hoje exige mesmo dataset e mesmo prompt.
- Vitrine: api/ai_lab/published/<comparacao>.json é uma cópia derivada sanitizada e versionada. A página lê essa cópia; não incorpora resultados do Explorar nem chama IA.

Explicar também a separação proposta: fila/contests usam classificação persistida do produto; Explorar é uma chamada experimental sem gravação; Benchmark lê experimentos identificados e salvos. Reutilizar adaptadores não deve unificar os efeitos dessas três operações.

Os três itens atuais do seletor não são três datasets ou três estratégias: (a) principal, Flash-Lite/120B/20B/baseline nos mesmos 12 selecionados, interseção rating 11 e tags 9; (b) Qwen parcial anterior, rating comum 2/tags 1; (c) Gemini 3.8 interrompido, sem previsões válidas. Todos usam o desenvolvimento v1 e o mesmo prompt. Não misturar denominadores ao comparar números desses itens.

Conferir preocupações reais de contaminação: identificação/referência fora da entrada; não escolher questões pelo desempenho; não compartilhar cache entre configurações; não sobrescrever runs ao trocar prompt; não otimizar no conjunto final e descrevê-lo como teste intocado. Questões públicas podem ter aparecido no treinamento; anonimização não prova ausência de memorização.

Decisões desta sessão: duas ou três variantes; arquivos/versionamento de prompts; identidade da configuração; retry/timeout/cadência por provedor; teto total e reserva de recuperação; apresentação clara de comparações; comandos e explicação de iniciar/parar/retomar. Alterações mínimas, preservando artefatos existentes.

## Passo 3 — experimentos em massa, posteriormente

### Unificação do scraper aprovada antes do congelamento

O usuário aprovou preservar BaseScraper e scrapers por plataforma, concentrar a
extração CF em CodeforcesScraper.parse_html e montar o payload em preparation.py.
Dataset mantém só wrapper de compatibilidade e políticas de revisão/elegibilidade;
não tem parser HTML próprio. Extração preserva LaTeX, todos os blocos e exemplos.
Imagens img são preservadas com URL/alt/posição e marcador, sem download ou envio
multimodal. Explorar identifica avaliação visual parcial na resposta/justificativa;
produto não a salva como previsão completa. SVG e conteúdo incorporado não
suportado geram erro explícito. Protocolo do benchmark continua textual.

Reprocessamento offline dos mesmos 60 HTMLs concluído: zero payloads alterados,
mesma seleção, desenvolvimento de 12 preservado byte a byte. Revisão regenerada,
backup e relatório privados, todos os 60 ainda collected/sem revisão. Sem nova
coleta, IA, congelamento ou publicação. O teste legado de scraper teve somente
expectativas de LaTeX atualizadas para o comportamento aprovado, sem mover ou
remover testes. Testes novos de equivalência, matemática, múltiplos blocos,
imagens/validade parcial e proteção da previsão global ficam em ai_lab.

### Atualização operacional do passo 2

O usuário aprovou implementar seleção de prompt/identidade, recuperação automática
limitada e roteiro de operação antes de selecionar/congelar os 60. Novas runs usam
política `managed-v1`: até três tentativas por item, orçamento acumulado explícito,
cadência configurável, backoff/jitter e respeito a Retry-After. Sucessos e respostas
inválidas não são refeitos; resultados desconhecidos de interrupções também não.
Falhas estruturais interrompem; espera longa/rate limit persistente pausa o provedor.
Não se presume que todo 429 é cota diária. Pilotos antigos conservam sua identidade
e política, inclusive a recuperação manual legada. Sem chamadas reais nesta entrega.

Prompt é selecionado por nome de arquivo em `api/ai_lab/prompts`; só v1 existe.
O usuário ficará responsável pelos exemplos do segundo prompt, com revisão conjunta.
Comparação entre prompts distintos exige opção explícita no índice privado,
mantendo o mesmo dataset e identificando o prompt por linha. Não reexportar
snapshots históricos. Consulta `--status` não executa modelos nem exige chaves.
Roteiro em `docs/AI_LAB_EXPERIMENTS.md`, incluindo limites, comandos futuros,
interrupção, retomada e reserva de chamadas. Coleta/congelamento dos 60, prompt v2
e lotes reais continuam pendentes e exigem revisão/autorização próprias.

Validação desta implementação: RED observado para seleção de prompt e comparação
explícita de prompts; novos cenários simulam recuperação, teto acumulado,
interrupção, identidade imutável e consulta sem chaves/inferência. Backend completo
final: 293 aprovados (antes: 283); frontend: 78 aprovados. Houve falhas ambientais
de acesso a temporários/rename no Windows em rodadas intermediárias; frontend
passou usando temporários locais e a repetição completa final do backend passou.
Avisos legados permanecem. `git diff --check` aprovado; testes legados fora de
ai_lab preservados. Nenhuma chamada real, coleta dos 60, migration, commit ou
push. HEAD continua 9b1d82b. O roteiro novo não autoriza os comandos de consumo
que apresenta como exemplos futuros.

Revisar/coletar/congelar as 60 questões com critério reprodutível antes de qualquer lote. Depurar variantes nas 12 de desenvolvimento. Recomendar começar com dois prompts nos três modelos de maior cota: 6 runs, 360 tentativas iniciais; terceiro prompt elevaria para 9 runs e 540 tentativas iniciais. Recuperações requerem reserva explicitamente autorizada, sem orçamento ilimitado.

Executar automaticamente lotes locais com progresso persistido, cadência por provedor e retomada. Repetir somente falhas transitórias sob política definida; não repetir classificações ruins/invalidas para melhorar artificialmente a métrica. Quota diária encerra com progresso salvo. Nenhum fallback pago ou troca automática de modelo.

Uma mudança de estratégia exige novo run; reaproveitar o mesmo conjunto congelado não mistura respostas. Se as 60 forem usadas iterativamente para orientar mudanças, descrevê-las como conjunto de avaliação usado no desenvolvimento, não teste final intocado.

O usuário deve aprender a executar um lote, interromper, retomar e interpretar resultados. Comparar modelos/prompts com coortes explícitas, cobertura, falhas e consumo. Só publicar derivados revisados. Este plano não autoriza novas chamadas, a coleta dos 60 ou o lote final.

## Registro da implementação do passo 1 — 2026-10-18

- Criada POST /api/ai-lab/problems/{id}/classify: autenticada, sem cache de classificação e sem escrita no banco. Explorar passou a usar essa rota, com uma nova chamada por clique explícito e ajuda visível. Ícones, modelos e primeira aba preservados. Removido o atalho force apenas de Explorar, onde deixou de ter significado.
- POST /api/problems/{id}/predict preserva cache e recálculo da fila/contests. Novas classificações usam o modelo padrão já configurado no código (Flash-Lite); seleção experimental é rejeitada nessa rota. Previsões antigas sem proveniência não recebem atribuição inventada. Campos/cache anteriores não foram apagados.
- Criado services/problem_metadata.py, usado pela predição e pelos escritores de catálogo CF, Gym, AtCoder e CSES. O merge relê a linha com select_for_update dentro de transação curta, sem chamadas externas sob o bloqueio; grava somente campos explicitamente atualizados. Payload sem rating/tags oficiais não apaga valores já conhecidos. Escritores que alteram somente título já usam update_fields e foram preservados.
- Testes reproduziram deterministicamente uma atualização de sincronização concluída durante a inferência e perda de campos de IA após atualização de rating AtCoder. Verificam preservação de título, dados oficiais, caches e campos alheios em ordens distintas de atualização. Isso não é um teste real de bloqueios concorrentes em PostgreSQL; nenhum banco remoto foi acessado.
- Explorar devolve rating e tags com validade independente; apresenta tags oficiais aproveitáveis e quantidade descartada. Não corrige sinônimos, não trunca rating nem mostra delta fictício para rating inválido. Resposta parcial não dispara retry. O produto preserva previsão salva se a nova resposta for parcial. O validador estrito do benchmark não foi alterado.
- ProviderFailure recebeu http_status opcional; adaptadores preservam status conhecido e o runner grava esse dado no histórico privado de novas falhas. A API apresenta status/categoria seguros na mensagem, quando disponíveis. Sem corpo HTTP/credenciais, sem reconstrução inventada de falhas antigas e sem alteração de políticas de retry/timeout.
- TDD RED observado antes das correções. Um teste legado detectou alteração na ordem de tags persistidas; a implementação foi corrigida sem modificar o teste legado. Nenhum teste fora de api/tests/ai_lab foi movido, renomeado ou alterado.
- Conferência visual com servidor temporário de resposta simulada, scraper simulado e SQLite local existente: resultado parcial, aviso de tag descartada, identificação do modelo e ajuda visível confirmados. Captura identificada como simulação. Servidor simulado encerrado, backend local normal restaurado e página recarregada sem dados simulados. Nenhuma inferência real.
- Dados científicos, snapshots e prompts existentes não foram reexecutados ou recalculados nesta fase. A auditoria dos hashes originais passou. O diff acumulado ainda inclui alterações de rodadas anteriores, inclusive snapshots do piloto, não novas chamadas desta implementação.
- Passos 2 e 3 permanecem pendentes. Sem throttle, novos prompts, migrações de schema, operações de produção, commit ou push.
- Validação final: backend completo 283 testes aprovados; frontend completo 78 e três testes da página reexecutados após o ajuste visual do aviso; build refeito aprovado, lint aprovado, comparação TypeScript com HEAD sem diagnósticos introduzidos. Check Django, makemigrations --check --dry-run em settings_test, auditoria de credenciais/artefatos e git diff --check aprovados. Avisos legados de staticfiles/deprecações/Browserslist/bundle e erros TypeScript anteriores permanecem. HEAD continua 9b1d82b.
