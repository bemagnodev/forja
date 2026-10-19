# AI Lab — revisão antes de commit e push

> Registro da revisão anterior. O contrato de produto, imagens, limpeza e runner
> foram posteriormente revisados conforme `2026-10-19-ai-lab-product-finalization.md`.
> Para o estado final, consultar `../AI_LAB_FINAL_REVIEW.md` e
> `../AI_LAB_TYPESCRIPT_DEBT.md`.

Data: 19/10/2026. Estado revisado: `main`, HEAD `9b1d82b`, mais a árvore de
trabalho atual. Não houve commit, push, deploy ou chamada real de IA nesta revisão.

## Conclusão

Não identifiquei falha P0/P1 no escopo examinado. Foram corrigidos problemas de
proveniência do cache, atualização entre telas, HTML inválido e extração do
AtCoder. Backend, testes frontend, build e lint dos arquivos revisados passam.
**A checagem de tipos do frontend ainda falha** e deve ser tratada explicitamente
antes de considerar a entrega integralmente validada. Build do Vite não substitui
TypeScript.

Os fluxos ativos usam `gemini-3.5-flash-lite` com `classification_v1` como padrão.
Fila e Contests só geram/salvam a previsão desse modelo; Explorar mantém os três
modelos selecionáveis e não grava classificação global. Essa escolha é sustentada
pelo benchmark de 60 problemas textuais do Codeforces, não por uma avaliação
equivalente de AtCoder/CSES ou por superioridade estatística demonstrada.

## Escopo real do histórico

HEAD e a referência **local** `origin/main` apontam para `9b1d82b`. Portanto, não
há commits locais posteriores a essa referência: as mudanças recentes ainda são
arquivos modificados/novos. Não fiz fetch para afirmar o estado remoto atual.

O repositório tem 87 commits. A revisão detalhada cobriu o conjunto do AI Lab
abaixo, as origens das integrações (`332c4cb`, `bb5ab99`, `9e28021`) e as mudanças
atuais relevantes de API, classificação, runners, scrapers, sincronização,
persistência, resultados, frontend e testes. Não representa auditoria linha a
linha de todos os 87 commits históricos ou certificação de segurança do produto.

| Commit | Responsabilidade examinada | Resultado |
| --- | --- | --- |
| `bc6bac5` | Desenho aprovado do benchmark | Implementação atual evoluiu para três modelos/dois provedores e três visões A/B, conforme decisões posteriores documentadas. |
| `14d8913` | Dataset, contratos, baseline, adaptadores, execução e API de resultados | Revistos separação de referências/entrada, congelamento, limites, retomada, validação e métricas pareadas. Ver limitações operacionais abaixo. |
| `4846fe3` | Comparações no frontend | Curadoria, nomes das técnicas, prompts, coberturas, escala fixa, dispersão e mapa de calor verificados no estado atual. |
| `1edb0d8` | Estado de tags inválidas | Contrato estrito do benchmark preservado; filtragem de tags no Explorar é apresentação experimental separada. |
| `cc0562d` | Snapshots sanitizados do piloto | Publicação atual usa três snapshots finais; pilotos arquivados e versão original do piloto preservada adicionalmente. |
| `9b1d82b` | Documentação do protocolo/resultados | Completada por documentação das execuções A/B, curadoria e este relatório. |

## Falhas corrigidas nesta revisão

### 1. Cache do produto sem identidade suficiente

**Antes:** uma previsão com rating/tags/justificativa podia ser aceita sem
comprovar que veio do modelo escolhido e do Prompt 1. Alterar o padrão do
classificador não garantia que a fila e os contests usariam esse padrão.

**Agora:** `api/api.py` exige o modelo padrão, o hash exato do prompt atual e
rating/tags válidos para reutilizar a previsão. A classificação registra
`ai_model`, `ai_prompt_version` e `ai_prompt_hash` no JSON de metadados existente.
O hash é capturado do texto efetivamente enviado pelo bridge em `ai_lab/explore.py`.
Não foi adicionada tabela ou migration.

Isso não limpa dados em massa nem chama IA ao abrir a página. Ao clicar para
classificar, uma previsão sem essa proveniência deixa de ser cache válido.
Shift+clique continua forçando recálculo. Em falha/resposta parcial, a previsão
anterior permanece preservada. Modelo/prompt não equivalem a um hash do enunciado:
mudanças na preparação ainda podem exigir recálculo explícito.

**TDD:** nove casos falharam antes da correção, cobrindo cache desconhecido/outro
modelo/outro prompt e seis combinações de plataforma/rota. A integração verifica
o bridge real até o adaptador simulado, prompt exato, modelo, persistência e
segundo acesso: produto reutiliza cache; Explorar chama novamente sem escrever.
Fixtures antigas de cache foram atualizadas para representar cache compatível.

### 2. Fila e Contests deixavam a outra tela com dados antigos

**Antes:** cada componente invalidava somente a própria consulta após classificar.
**Agora:** ambos invalidam `queue` e `contest-problems`. O resultado oficial
continua distinto da previsão de IA; os metadados oficiais não são sobrescritos.

**TDD:** testes novos reproduziram as duas invalidações ausentes. Também verificam
uma chamada por clique, nenhuma chamada no render e Shift+clique nas duas telas.

### 3. Botão da fila invisível sem hover e botões aninhados

Removido o `opacity-0` do contêiner do botão de IA. Ele tem texto, fundo e borda
roxos permanentemente; hover apenas reforça o destaque. Não foi criada coluna.
Adicionado nome acessível ao botão nas duas telas.

O seletor de prioridade da linha usava `asChild` de outro sistema de componentes
e criava `<button>` dentro de `<button>`. Foi removida essa composição no seletor.
O teste de regressão falhou com a estrutura anterior e passa com a estrutura
atual. Isso não resolve os outros usos antigos de `asChild` no projeto.

O tipo frontend `QueueItem` recebeu `linked_problem_id`, já presente na resposta
do backend e usado pelo botão.

### 4. Exemplos do AtCoder sobrescreviam formatos de entrada/saída

As condições por substring aceitavam tanto `Input` quanto `Sample Input 2`.
Reprodução local devolveu o exemplo `4 5` como formato de entrada.

Corrigido com correspondência às seções `input`/`input format` e
`output`/`output format`. O teste novo usa dois exemplos e confirma que as
especificações originais permanecem. RED observado antes da correção; nenhuma
página externa foi acessada. Essa correção não adiciona coleta de exemplos ou
processamento visual completo ao scraper do AtCoder.

### 5. Histórico dos snapshots esclarecido

O piloto arquivado da árvore de trabalho já continha GPT-OSS 20B, diferentemente
do piloto existente em HEAD. As interseções e os MAEs, portanto, também diferem.
Não deve ser descrito como byte a byte igual ao último commit.

Foi preservada adicionalmente a cópia exata de HEAD em
`api/ai_lab/archive/9b1d82b/cf-rating-v1-development.json`, com igualdade dos bytes
e hash do envelope verificados. O README diferencia as duas versões. O Qwen
arquivado também coincide byte a byte com o snapshot de HEAD. Nada foi incluído
na vitrine ou recalculado por inferência.

## Pendências e limitações, por prioridade

| Prioridade | Achado | Consequência / ação recomendada |
| --- | --- | --- |
| P2 | `tsc --noEmit -p tsconfig.app.json` falha com 24 diagnósticos. Inclui props `asChild`, `type`/`collapsible`, imports de tipo e código não utilizado. Há problemas já presentes em HEAD, inclusive o Accordion de Explorar. | Não afirmar que frontend está totalmente validado. Corrigir compatibilidade com Base UI nas telas atingidas e resolver os demais diagnósticos em alteração delimitada, sem desligar regras. |
| P2 | Produto detecta `visual_status=unprocessed` depois da inferência (`api/api.py`). | Preserva o banco corretamente, mas pode gastar uma chamada em uma entrada que será recusada. Avaliar recusa antecipada no produto; manter avaliação parcial explícita em Explorar. Não mudar o protocolo do benchmark textual. |
| P3 | `services/ai_classifier.py` permanece como implementação antiga sem import no fluxo ativo, além dos próprios testes. Usa modelos, taxonomia, contrato e retry diferentes. | Redundância real e risco de reutilização errada no futuro. Remover/depreciar em refatoração independente e ajustar documentação/testes; não encaminhar o runtime de volta para ela. |
| P3 | Exceção inesperada no runner gerenciado pode deixar `stop_reason=running` mesmo com lock removido. `KeyboardInterrupt` tem tratamento próprio. | Estado operacional enganoso, embora tentativa reservada evite repetição silenciosa. Adicionar teste e estado de interrupção/falha inesperada antes de novos lotes. Não editar runs concluídas para corrigir a apresentação. |
| P3 | Toast de fila/Contests diz “predição gerada” mesmo ao reutilizar cache. | Usar o campo `cached` para distinguir resultado salvo de chamada nova. Não interfere nas métricas, mas melhora a compreensão do consumo. |

Os limites e a proveniência das continuações atuais foram conferidos. O CLI limita
chamadas por arquivo de run; o orçamento somado entre ancestrais depende dos
helpers privados usados nas continuações. Isso é uma limitação de operação para
futuros experimentos, não uma autorização para mais chamadas ou alteração dos
históricos atuais. Não é necessário introduzir agora um orquestrador genérico.

## Testes ausentes ou alcance limitado

- Contratos de requisição/resposta são testados com mocks. Não há nesta revisão
  teste real de chave, cota, disponibilidade ou latência dos provedores.
- API testada em SQLite isolado. Os testes de interleaving protegem o merge de
  metadados, mas não provam locks/concorrência real de PostgreSQL. Não conectei
  a banco externo para preencher essa lacuna.
- A suíte do scraper do AtCoder não continha exemplos após Input/Output; a nova
  regressão cobre esse caso. Cobertura equivalente de imagens, amostras e layouts
  variados de AtCoder/CSES ainda é menor que a de Codeforces.
- A conferência no navegador usou um problema sintético local. Não substitui
  E2E automatizado, teste em produção ou revisão responsiva completa.
- Falta teste para o estado de erro inesperado do runner e para a recusa visual
  antes de consumir uma chamada no produto.
- Testes legados do classificador antigo não devem ser contabilizados como prova
  de funcionamento do bridge ativo. Os testes novos exercitam o caminho atual.

## Integridade e protocolo do benchmark

- Dataset final permanece congelado: 60 problemas, hash
  `7ea7ea0585d6a6c74877fe2f9c96ac6f70a521589bb4c395f84bb0a3f1315400`.
- Três comparações públicas, com envelopes e identidades validados. A leitura
  privada correspondente valida proveniência, hashes dos ancestrais e 60 itens.
- Classificação direta e com rubrica comparam os três modelos nas interseções
  válidas de cada tarefa, exibindo também cobertura e falhas.
- A terceira visão usa as previsões A/B existentes do Gemini nos mesmos itens;
  não mistura MAEs individuais de amostras diferentes.
- Baseline segue a grade de 100 pontos; resultados fora do domínio não são
  truncados. Tags do benchmark continuam estritas, sem sinônimos automáticos.
- Não foram alterados prompts A/B, parâmetros, previsões, dataset ou resultados
  científicos. Prompt C e novas inferências permanecem parados.
- Snapshots públicos examinados não contêm enunciados, inputs, catálogos,
  respostas brutas ou configurações completas. Prompts A/B são a exceção
  explicitamente aprovada, com hash/texto revisados. Exemplos de C são privados.
- Varredura local dos 62 candidatos textuais anteriores a este relatório não
  encontrou padrões das chaves examinadas nem `.env`, bancos ou `var/ai_lab`
  entre candidatos ao Git. Isso é verificação por padrões, não prova universal
  de ausência de qualquer segredo.

## Evidências de execução

| Verificação | Resultado |
| --- | --- |
| Backend completo: `python -m pytest api -q` | **332 passaram**, versus 322 antes desta revisão. Sem testes movidos/excluídos. |
| Frontend completo: Vitest, um worker | **90 passaram**, versus 85 antes desta revisão. |
| Build de produção local, Vite | Passou; alerta de bundle de aproximadamente 819 kB e Browserslist desatualizado. |
| ESLint dos arquivos frontend revisados | Passou. Não equivale a lint integral do repositório. |
| Django check, settings isolados de teste | Sem problemas. |
| `git diff --check` | Sem problemas. |
| TypeScript explícito | **Falhou**, conforme pendência P2; não ocultado pelo build verde. |
| Navegador: fila → Contests → Explorar | Sucesso com scraper e adaptador simulados; zero chamadas externas. |

Na conferência visual, o botão da fila tinha cor `rgb(232, 121, 249)`, fundo roxo
translúcido e opacidade do contêiner 1 sem hover. A fila salvou 1200/math no SQLite
de QA; Contests exibiu e reutilizou a previsão sem segunda geração simulada;
Explorar gerou uma resposta separada, identificada como experimental. O mock
exigiu modelo e texto exatos de `classification_v1`.

As fixtures sintéticas foram removidas após a conferência e o servidor local
original de QA foi restaurado. Logs e screenshot ficam privados em `var/ai_lab`.
Não houve migration operacional; migrations internas da suíte ocorreram somente
no SQLite de teste, conforme a política do projeto. Nenhum banco de produção
foi consultado/alterado.

## Sequência recomendada antes do push

1. Revisar este relatório e fechar a pendência de TypeScript com escopo limitado.
2. Decidir se a recusa visual antecipada entra nesta entrega ou fica registrada.
3. Conferir o diff final e separar commits por comportamento: preparação e merge
   de metadados; execução/prompts; curadoria/snapshots; apresentação; correções
   de integração desta revisão. Não usar `git add .` indiscriminadamente.
4. Confirmar somente arquivos sanitizados/documentação/fixtures revisadas nos
   commits. Manter dados de trabalho e ferramentas privadas fora do Git.
5. Somente depois realizar commit/push autorizado. Este relatório não os executa.

Não é necessário reexecutar os benchmarks para corrigir a interface, os tipos,
o cache do produto ou a extração do AtCoder.
