# AI Lab — plano geral de revisão e conclusão

Data: 2026-10-17.
Estado: entregas técnicas 1–5 verificadas, piloto GPT-OSS concluído e Qwen preservado como teste parcial. Snapshots sanitizados preparados para versionamento. O registro atual está na seção 15; as seções 13–14 descrevem os checkpoints anteriores.

## 1. Objetivo e precedência

Entregar na própria Forja uma comparação de classificação compreensível, reproduzível e publicável para a entrevista, sem dependência do preview temporário. Rating é o objetivo principal; tags são secundárias. Este documento passa a ser a referência para a próxima execução e substitui os trechos conflitantes dos planos anteriores sobre frontend, três provedores, publicação e retomada. Os documentos anteriores permanecem como histórico.

Escopo: corrigir a base existente, não recomeçar o laboratório. Não introduzir banco, migrations, disco pago, filas, cache genérico, infraestrutura de ML ou novo framework de experimentos para esta entrega. A persistência Django prevista anteriormente fica adiada; a vitrine usará snapshots derivados revisados.

Decisões consolidadas:

- Três modelos em dois provedores: Gemini 3.5 Flash-Lite/Google, GPT-OSS 120B/Groq e Qwen 3.8 27B/Groq. OpenRouter é alternativa futura, não requisito. Comparar configurações de modelos; latência entre modelos diferentes não isola desempenho do provedor.
- Prompt v1 e dataset de desenvolvimento congelados preservados. Nenhum prompt novo ou dica adicional no meio da comparação.
- Baseline v2: mediana do desenvolvimento arredondada ao múltiplo de 100 mais próximo, empate para cima, saída inteira entre 800 e 2400; nova execução identificada sem sobrescrever a versão contínua anterior.
- Piloto: 12 problemas já revisados. Final: 60 problemas diferentes, selecionados e revisados separadamente, entre 800 e 2400. Nenhuma chamada final antes de congelar o conjunto.
- Dados privados em backend/var/ai_lab. Vitrine publicada recebe apenas um snapshot explicitamente exportado e revisado.
- Nenhuma inferência, compra, troca de modelo, commit, push ou deploy é autorizada pela criação deste plano.

## 2. Ponto de partida e cuidados

Já existem adaptadores Gemini/Groq, execução local com orçamento/retomada, métricas, API autenticada de leitura, tabela e gráficos. Gemini e baseline têm resultados reais para os 12 problemas; Groq ainda não foi chamado. A aba Explorar mantém a engine antiga e não participa automaticamente do benchmark.

Última verificação registrada: backend 231 testes, dos quais 95 legados; frontend 69 testes. Recontar antes de começar e preservar todos. Build passou; TypeScript global tem diagnósticos preexistentes. Guardar o baseline de diagnósticos para distinguir regressões, sem esconder falhas ou incluir refatoração geral no escopo.

O preview em localhost:5175 é apenas ferramenta auxiliar ignorada pelo Git. A validação de aceite deve ocorrer em /ai-lab com frontend e backend reais, login normal e ambiente local isolado. Não substituir a API autenticada por um servidor de demonstração no produto.

Referências de trabalho: docs/TESTING.md, docs/AI_LAB.md, .agents/skills/test-driven-development/SKILL.md e .agents/skills/frontend-design/SKILL.md. Usar o design aprovado abaixo e os tokens efetivos da aplicação; não instalar fontes ou redesenhar outras páginas para cumprir exemplos desatualizados da skill.

## 3. Entrega 1 — convenção dos comandos e consistência documental

Arquivos: backend/api/ai_lab/runner.py; os três comandos prepare_ai_dataset.py, validate_ai_dataset.py e run_ai_benchmark.py; backend/api/tests/ai_lab/test_commands.py; docs/AI_LAB.md.

1. TDD: escrever e observar falhar testes de parsing para --dataset-version, seleção da versão correta e --version padrão do Django sem I/O de dataset/rede. Depois substituir a sobrescrita interna do argumento do Django pela opção explícita.
2. Atualizar chamadas internas e os testes específicos do AI Lab afetados, preservando os cenários e testes legados externos. Não manter alias --version ambíguo. Documentar a incompatibilidade deliberada da CLI; nenhum arquivo de dados será renomeado.
3. Alinhar o runbook a três modelos/dois provedores e à separação de execução privada/publicação. Manter IDs históricos e resultados existentes.

Aceite: comandos e --help coerentes, --version volta ao comportamento do framework, datasets/run-ids existentes continuam legíveis. Rodar testes direcionados e suíte completa do backend. Unidade de commit futuro: correção da CLI e documentação diretamente correspondente.

## 4. Entrega 2 — recuperação limitada de falhas transitórias

Arquivos: backend/api/ai_lab/runner.py; run_ai_benchmark.py; test_classification.py e test_commands.py. Ampliar apenas o registro necessário; não criar serviço genérico de jobs.

1. Definir uma política igual para os modelos: uma tentativa inicial e no máximo uma recuperação por item, solicitada explicitamente com --retry-failures. Retomada normal continua executando somente pendentes. Flag de recuperação seleciona somente falhas transitórias registradas, sem iniciar outros itens como efeito surpresa.
2. Recuperáveis: timeout/erro de transporte transitório, HTTP 429 e erros transitórios de servidor. Não recuperar automaticamente autenticação, HTTP 400, JSON inválido, truncamento, tags inválidas, rating fora do domínio ou previsões válidas com erro alto.
3. Cada chamada, inclusive recuperação, consome o mesmo teto total autorizado. Flag não amplia teto, não zera request_count e não muda modelo, entrada, prompt ou parâmetros. Com teto esgotado, encerrar antes de chamar; ampliação exige autorização.
4. Respeitar Retry-After e quota diária. Se a espera ultrapassar a janela de execução, registrar quando retomar em vez de chamar cedo ou repetir em loop. Pausar lote em falha estrutural de acesso/cota.
5. Preservar resultado e histórico de cada tentativa, duração, categoria e consumo. A resposta válida posterior pode ser o resultado efetivo do item, mas não apaga sua falha inicial. A vitrine distingue falhas finais, histórico operacional e precisão.
6. Manter leitura dos arquivos antigos sem conversão automática destrutiva. Definir a adaptação de registros antigos ao histórico antes de implementar; os originais/proveniências do piloto concluído devem permanecer preservados. Não mudar silenciosamente a identidade científica para retomar.

TDD: RED/GREEN para seleção exclusiva de transitórios, ausência de repetição de sucesso/saída inválida, limite por item, orçamento global, crash após reservar chamada, respeito à espera, lock, retomada idempotente e leitura legada. Testes sem rede, com relógio/espera simulados.

Aceite: falha simulada seguida de sucesso deixa histórico verificável e contagem correta; nenhum cenário excede autorização. Suíte completa do backend verde. Unidade de commit futuro: recuperação e testes, independente do frontend.

## 5. Entrega 3 — métricas por faixa e contrato da apresentação

Arquivos: backend/api/ai_lab/metrics.py e results.py; backend/api/tests/ai_lab/test_metrics.py e test_results_api.py.

1. Reutilizar a comparação existente para calcular MAE por faixa oficial: 800–1100, 1200–1500, 1600–1900 e 2000–2400. Rating oficial define a faixa, nunca o previsto.
2. Por faixa, usar os mesmos itens válidos entre os modelos comparados para rating, incluindo o baseline quando listado; retornar N comparado, total da faixa e MAE de cada configuração. Ausência de interseção produz null, não zero. Não comparar médias calculadas sobre conjuntos diferentes sem informar.
3. Manter MAE, dentro de ±200, F1 micro de tags com sua interseção própria, cobertura, falhas e pendências. Baseline não estima tags. Definir claramente denominadores nos dados e na interface.
4. Acrescentar identificação de apresentação independente dos IDs científicos: nome "Experimento Codeforces 1", contagem e estágio (desenvolvimento/final). Usar um único contrato de leitura para API local e snapshot publicado.
5. O snapshot contém números necessários para tabela/mapa, pontos da dispersão e detalhes aprovados, sem permitir cálculo diferente ou mistura de modelos/datasets/prompts por engano. A seleção do modelo na dispersão não altera silenciosamente a coorte da tabela/mapa.

TDD: exemplos sintéticos com resultados matemáticos conhecidos; limites de faixa; falhas assimétricas; interseção vazia; erro zero real; baseline sem tags; precisão não favorecida por menos respostas. API cobre autenticação e rejeição de artefatos incompatíveis.

Aceite: métricas esperadas verificadas manualmente numa fixture pequena, contratos local/exportado equivalentes, nenhuma inferência necessária. Suíte completa do backend verde.

## 6. Entrega 4 — página visual aprovada na Forja

Arquivos: frontend/src/pages/AILab.tsx; componentes em frontend/src/components/ai-lab; testes específicos de página/componentes. Reutilizar Tooltip, Drawer/Sheet ou equivalente existente após verificar disponibilidade e acessibilidade. Não adicionar biblioteca de gráficos por antecipação.

### Composição, nesta ordem

1. Cabeçalho: "Experimento Codeforces 1"; badge vermelha discreta "12 problemas"; seletor de experimento quando necessário; linha secundária "Desenvolvimento · Prompt v1". Metodologia/hashes/seed em "Sobre o experimento", fechado inicialmente.
2. Tabela compacta: Modelo, Erro médio, Até ±200, Cobertura e F1 de tags. Ordenar MAE crescente, com indisponíveis no fim e desempate estável. Barras pequenas integradas ao MAE; remover o card separado de barras. Informar N pareado e que menor MAE é melhor. Falhas/pendências explícitas junto da cobertura; não chamar pendência de falha.
3. Ajuda em cada métrica: texto curto com unidade, denominador/sentido e exemplo quando útil. Acessível por mouse, foco e toque, sem depender de hover ou somente do atributo title.
4. Mapa de calor: modelos nas linhas, faixas nas colunas; número de MAE em cada célula; uma escala de intensidade compartilhada, legenda e quantidade comparada acessível. Distinguir zero de sem dados. No piloto, informar que há apenas três problemas selecionados por faixa e que o resultado é exploratório. Se houver falhas, N válido pode ser menor.
5. Dispersão ampla: um modelo por vez; X "Rating oficial", Y "Rating estimado", ambos 800–2400; diagonal "Estimativa correta"; pontos menores e discretos; sem códigos permanentes; seleção destacada. Agrupar coordenadas coincidentes sem deslocar ratings ou somar métricas. Mostrar quantidade no grupo e permitir escolher seus problemas. Tooltip: oficial, estimado, diferença com sinal/sentido. Não truncar nem plotar como válidos valores fora do domínio.
6. Detalhe fechado inicialmente: clique/foco/teclado num ponto abre painel lateral no desktop e seção abaixo do gráfico no celular. Mostrar rating, erro, tags e justificativa curta salva do modelo selecionado; grupo permite seleção do problema. Identificador aparece somente no detalhe. Não exibir dois cards permanentes de comparação. Sem IA para produzir/resumir justificativas nesta etapa.
7. "Detalhes da avaliação" recolhido ao final: latência observada, respostas, pendências, falhas atuais e histórico. Histórico não é removido, apenas deixa a visão inicial.

### Linguagem visual e navegação

- Superfícies zinc escuras, bordas discretas, tokens primary/forja para vermelho e baseline em cinza. Intensidade de erro não deve parecer automaticamente "melhor" por ser a cor de destaque. Legendas/valores garantem leitura sem depender de cor.
- Tipografia, espaçamento, foco e controles coerentes com páginas atuais. Animações curtas e respeito a preferência de movimento reduzido. Não acrescentar gradientes ou fontes estranhas ao projeto.
- Explorar deve ser a primeira aba na ordem visual e abrir por padrão, preservando os ícones Codeforces, AtCoder e CSES na classificação, conforme confirmação do usuário. Manter aba Benchmark visível e estado vazio útil. Não mudar depois o padrão sem decisão explícita.
- Loading, vazio, erro de leitura e comparação parcial não bloqueiam Explorar. Leitura nunca dispara inferência. Layout móvel com tabela rolável, controles legíveis e gráficos sem rótulos sobrepostos.

TDD: testes de ordenação/indisponíveis, informações de cobertura/falhas/pendência, tooltips por foco, células do mapa e sem dados, agrupamento de coordenadas, troca de modelo, detalhe inicialmente fechado, abertura/fechamento e seleção de grupo. Preservar testes existentes; atualizar testes novos do AI Lab quando a expectativa de design tiver mudado, sem simplesmente apagá-los.

Aceite: suíte frontend completa, build, lint dos arquivos alterados e ausência de novos diagnósticos TypeScript. Conferência na rota real /ai-lab, desktop e celular, com teclado e login local, usando resultados existentes. Mostrar a página ao usuário antes de avançar para operações reais. Retirar o preview temporário do fluxo de revisão; arquivos auxiliares não entram no Git.

## 7. Entrega 5 — snapshot publicável e independente do disco de execução

Arquivos mínimos: função de exportação em results.py enquanto couber nessa responsabilidade; export.py apenas se justificar separação. Reutilizar run_ai_benchmark com modo explícito de exportação somente de leitura, sem inferência, ou função existente de preparação da vitrine. Evitar novo comando se uma opção clara resolver. Snapshot final em backend/api/ai_lab/published/<experimento>.json, diretório criado apenas junto do primeiro artefato aprovado. Novo teste de exportação pode ficar em test_results_api.py até justificar arquivo próprio.

1. Definir schema_version e campos permitidos: identidade de apresentação, estágio, dataset/modelos/versão ou hash do prompt, contagens/coortes, métricas gerais e por faixa, referências/previsões necessárias aos gráficos, e detalhe estritamente selecionado. Nome de modelo não é evidência de free tier da conta.
2. Excluir por allowlist: enunciados, catálogo, prompt completo, respostas brutas, campos privados arbitrários, logs HTTP, caminhos locais, chaves e dados de usuários. Justificativa humana legível só entra como campo revisado do detalhe; pode ser omitida se não aprovada para publicação. Os originais permanecem privados e intactos.
3. Exportação explícita e determinística a partir de execuções compatíveis; registrar versão/hashes de origem e impedir sobrescrita silenciosa de snapshot congelado. Sem inferência ou coleta durante exportação, build ou startup.
4. API continua autenticada. Produção lê snapshots versionados incluídos no artefato de deploy, sem precisar de var/ai_lab, nem enviar dados privados ao servidor. Leitura privada para trabalho local só com configuração local explícita; não usar fallback silencioso em produção. Não copiar o preview auxiliar para produção.
5. Revisar o JSON gerado e o diff antes de qualquer commit/publicação. Esta é a exceção documentada à regra anterior de nenhum resultado no Git: somente o material derivado aprovado; nunca todos os arquivos de runs.

TDD: inserir sentinelas privadas em fixtures e comprovar exclusão pela allowlist; verificar conteúdo matemático, schema, determinismo, compatibilidade de versões, snapshot ausente/inválido, proteção de origem e equivalência com API. Simular ambiente sem diretório privado: listagem e comparação publicada devem continuar funcionando. Conferir inclusão no pacote/build de deploy.

Aceite: Forja local iniciada com apenas o snapshot publicado e sem fonte privada consegue mostrar a mesma avaliação. Nenhum serviço pago ou migration necessário. Suítes completas backend/frontend e build aprovados. Deploy real depende de autorização posterior; a aprovação do desenho não autoriza publicação do JSON.

## 8. Entrega 6 — verificar contrato real e concluir piloto comparativo

Pré-requisitos: entregas técnicas e visuais aceitas; plano gratuito da conta confirmado; chaves privadas configuradas; IDs, parâmetros e teto explicitamente autorizados. Não listar/testar modelos com a chave como efeito colateral de abrir a página.

1. Proposta de orçamento, ainda não liberada: até 12 tentativas de geração para openai/gpt-oss-120b e 12 para qwen/qwen3.8-27b, ambos pela Groq; falhas e recuperações entram no teto. Não repetir Gemini.
2. A primeira tentativa de cada modelo é a verificação real do contrato. Usar um dos itens congelados com a mesma configuração do lote; se válida, reutilizar como resultado daquele item. Sem chamada extra de smoke test.
3. Em HTTP 400, acesso negado, modelo indisponível ou parâmetros incompatíveis, interromper e explicar. Corrigir contrato antes de continuar. Mudança de parâmetros/prompt exige identidade nova de execução; não misturar resultados. Falha consome autorização mesmo sem resultado válido.
4. Executar restante sequencialmente, respeitando tokens/minuto/dia e Retry-After. Se o teto produzir menos de 12 respostas válidas, mostrar parcial e discutir recuperação/orçamento, sem criar permissão automática para completar.
5. Conferir comparação conjunta dos três modelos e baseline. Exportar novo snapshot somente após revisão de conteúdo e métricas. Preparar exemplos de erros sem alterar o prompt v1.

Testes anteriores à rede: payload dos dois modelos, parsing, categorias de erro, nenhuma ferramenta/fallback/retry oculto, orçamento e configuração persistidos. A chamada real é experimento autorizado separado, não parte da suíte automatizada.

Aceite: evidência de aceitação real de cada contrato, ledger correto e resultados comparáveis ou falha explicada; todos os dados apresentados identificados como desenvolvimento. Suítes completas no fechamento.

## 9. Entrega 7 — conjunto final, showcase e integração posterior

1. Selecionar 60 problemas reproduzivelmente do snapshot oficial, 15 por faixa, seed registrada, contests distintos do desenvolvimento e limite de concentração existente. Referências oficiais separadas da entrada. Não escolher exemplos favoráveis a um modelo.
2. Revisar HTML/enunciados e payloads, substituir antes da execução somente por critérios documentados e reservas reproduzíveis; congelar após aprovação dos 60. Não excluir depois por erro do modelo. Baseline fixado no desenvolvimento.
3. Solicitar autorização para o lote final de até 60 tentativas/modelo, 180 totais, com a política de recuperação explicitada. Não incluir os 12 dev como teste final. Cotas podem exigir mais de um dia; autorizações anteriores não são reaproveitadas para novos lotes.
4. Revisar métricas e snapshot final; distinguir piloto/final no seletor. Preparar narrativa da entrevista: problema do estudante, protocolo, baseline, trade-offs, falhas, resultados e limites da conclusão. Não depender de inferência ao vivo.
5. Após aceite e autorização, publicar snapshot/código com possibilidade de reversão. Verificar /ai-lab na aplicação publicada e recuperação após novo deploy sem depender de uploads ao disco temporário.
6. Unificar depois a exploração individual com a engine comum, em mudança independente: preservar contrato da API e garantir que cache legado não se passe por previsão do modelo/prompt selecionado. Essa refatoração não bloqueia o benchmark salvo e requer seu próprio plano/testes antes de alterar o comportamento existente.

Aceite: demonstração confiável com dados salvos, sem extrapolar precisão universal ou causalidade por provedor. Os 60 não voltam a ser teste intocado se seus erros forem usados para otimizar prompt; novas versões começam no desenvolvimento.

## 10. Estrutura mínima pretendida

```text
backend/api/ai_lab/
  catalog.py, classification.py, contracts.py  # existentes
  dataset.py, review.py                       # existentes
  runner.py                                  # CLI e recuperação limitada
  metrics.py                                 # geral e por faixa
  results.py                                 # leitura e snapshot saneado
  prompts/classification_v1.txt               # preservado
  providers/gemini.py, providers/groq.py       # existentes
  published/<experimento>.json                # só artefato derivado revisado
backend/api/tests/ai_lab/
  conftest.py, fixtures/                      # específicos, pequenos e revisados
  test_dataset.py, test_classification.py, test_metrics.py
  test_commands.py, test_groq.py, test_results_api.py
backend/var/ai_lab/                           # privado e ignorado
frontend/src/pages/AILab.tsx
frontend/src/components/ai-lab/
  BenchmarkResults.tsx                        # composição/estado e tabela
  PredictionChart.tsx                         # dispersão agrupada
  RatingHeatmap.tsx                           # quando implementado
  ProblemDetail.tsx                           # painel, se justificar separação
  *.test.tsx
```

Sem novos arquivos/diretórios apenas para uso futuro. Preferir extrações motivadas por responsabilidade real, não por uma estrutura idealizada.

## 11. Sequência, TDD e checkpoints

Ordem: 1 → 2 → 3 → 4 → revisão visual na Forja → 5 → revisão do snapshot → autorização → 6 → revisão dos 60 → autorização → 7. A página pode ser avaliada com Gemini/baseline, sem aguardar Groq.

Para cada comportamento: teste RED observado pela ausência do comportamento, implementação GREEN mínima e refatoração com testes verdes. Suítes completas ao fechar cada entrega, sem mover/renomear testes legados ou aceitar redução inexplicada de contagem. Testes automatizados usam simulações e settings_test/SQLite isolado; comandos reais usam configuração local explícita, nunca settings_test ou Supabase por acidente. Uma falha de ambiente deve ser distinguida de regressão e a suíte reexecutada com segurança, sem ignorar erros.

Commits futuros pequenos e reversíveis por comportamento: CLI; recuperação/histórico; métricas/contrato; tabela/cabeçalho; mapa; dispersão/painel; exportação/leitura publicada; documentação/artefato revisado. Não misturar refatoração geral, dados privados ou mudanças da engine antiga. Criar commits/push somente quando autorizado.

Rollback: alterações visuais não mudam experimentos; recuperação não elimina tentativas anteriores; exportação não altera a fonte; snapshot anterior permanece recuperável por versão. Reverter vitrine não deve exigir migration nem apagar datasets. Não remover modificações preexistentes do usuário.

## 12. Fora desta execução

Prompt v2, dicas por estatística de acerto, ML clássico, Contest Review/solving detalhado, Live API/tutor por voz, OpenRouter, execução de lotes pelo navegador, cache genérico, migrations de produção e correções gerais de TypeScript. Nada disso será incluído para fechar um detalhe de interface ou uma falha transitória do provedor.

## 13. Registro de execução local — 2026-10-17

- Entregas 1–3: CLI usa --dataset-version, --version padrão preservado; recuperação explícita de transitórios com histórico, teto e espera persistidos; métricas pareadas por faixa. Novas execuções têm uma tentativa inicial por item em ambos os provedores. Arquivos do piloto Gemini concluído e sua proveniência foram preservados.
- Entrega 4: tabela crescente por MAE, ajuda nas cinco colunas, identidade do experimento/badge, mapa de calor e dispersão agrupada com detalhe sob demanda. Explorar é primeira e selecionada inicialmente; os três ícones existentes permanecem. Teste da ordem foi observado falhar antes da correção e ficou verde depois dela.
- Entrega 5: exportação determinística por allowlist, sem sobrescrita; API normal lê somente snapshots publicados, e configuração local explícita permite arquivos privados. Teste de API confirma leitura publicada sem dataset privado. A pasta publicada ainda não foi criada: falta revisão/aprovação do conteúdo real antes da cópia.
- Candidato privado gerado pelo comando real: backend/var/ai_lab/exports/cf-rating-v1-development.json. Integridade conferida pelo leitor de snapshots: 12 problemas, Gemini e baseline, somente hash do prompt, sem justificativas. Arquivo ignorado pelo Git. Sem nova inferência.
- Validação: backend completo 248 testes; frontend completo 72 testes em 13 arquivos; build frontend, lint dos componentes novos e teste da página, check do Django, verificação de ausência de novas migrations e git diff --check aprovados. Permanecem avisos existentes de dependências/build e diagnósticos TypeScript globais preexistentes, sem novos diagnósticos nos componentes adicionados.
- Conferência visual na rota real /ai-lab, com login normal, frontend e backend locais e SQLite exclusivo de revisão. Foram conferidos tabela, mapa, tooltips, troca de modelo, grupo de pontos e abertura/fechamento do detalhe com Escape/devolução de foco. Foram aplicadas apenas migrations já existentes a esse banco local novo de revisão, sem criar migrations ou acessar produção.
- Limitação móvel identificada: a Sidebar global fixa de 224 px reduz excessivamente a área útil em telas estreitas. Os componentes novos têm rolagem/empilhamento, mas o aceite completo de uso no celular depende de uma correção separada da navegação global; ela não foi alterada nesta entrega.
- A revisão visual pelo usuário e a aprovação do snapshot permanecem pendentes. As entregas 6–7 não foram executadas. Nenhum modelo Groq foi chamado; nenhuma migration em produção, publicação, commit ou push foi realizado.

## 14. Revisão antes do push — 2026-10-17

Correções com RED observado, GREEN e regressão:

- Baseline contínuo divergente do contrato dos modelos: versão `development-median-grid100-half-up-v2`, com testes de empate, extremos e tipo inteiro. O comando persiste a identidade nova. A mediana real do piloto era 1600 e continua 1600, com MAE 466,7; não houve vantagem numérica nesse piloto.
- Contrato Groq: Qwen usa `reasoning_format=hidden` no JSON; GPT-OSS omite esse campo não suportado. Payload e configuração persistida compartilham os mesmos parâmetros. Testes HTTP separados para cada modelo; documentação oficial pública conferida, sem usar chaves.
- Interrupção após reserva: o item fica registrado como `interrupted` antes da requisição, além do consumo do orçamento. Retomada não duplica silenciosamente uma chamada de resultado desconhecido. Recuperação automática desse estado permanece proibida.
- Histórico: duas falhas registradas com a mesma categoria contam duas tentativas falhas, em vez de serem deduplicadas. Registros legados sem eventos individuais não são extrapolados.
- TypeScript: a revisão encontrou a opção `exact` inválida em `getByRole` no teste dos ícones. Removida sem retirar as verificações dos três ícones. Comparação com fontes do HEAD: 30 diagnósticos anteriores, 30 atuais, nenhum introduzido.

Dados locais: novo run-id `baseline-dev-grid100-v2`, índice privado atualizado, backup do índice anterior e snapshot candidato em `backend/var/ai_lab/exports/grid100-v2/cf-rating-v1-development.json`. Conferidos por leitura: previsões baseline inteiras, métricas iguais às anteriores, resultado Gemini intacto e hashes dos artefatos científicos originais preservados. Tudo continua ignorado pelo Git; a pasta publicada não foi criada.

Auditoria dos arquivos modificados/novos: nenhum artefato privado ou arquivo .env candidato ao Git; nenhuma chave nos padrões de credenciais examinados; nenhum arquivo maior que 1 MiB. Testes legados não movidos, renomeados ou alterados. Backend completo: 257 aprovados (95 legados preservados). Check Django e makemigrations --check --dry-run com settings_test aprovados, sem gerar/aplicar migrations.

Frontend completo revalidado: 72 testes em 13 arquivos aprovados com um worker em threads. Houve tentativas anteriores inválidas por EPERM no temporário do sandbox e falta de memória/paginação do Windows; elas não foram consideradas sucesso. A reexecução integral passou após liberar os servidores locais de revisão e executar fora do isolamento. O aviso legado `asChild` de Queue permanece. TypeScript foi comparado com HEAD sem alterar fontes legadas no disco.

Build de produção frontend, lint dos componentes novos/teste da página e git diff --check revalidados e aprovados. Os avisos de Browserslist desatualizado e bundle grande permanecem. Servidores locais auxiliares de revisão foram desligados durante essa verificação para liberar recursos; não houve deploy.

Pendências antes da demonstração publicada: revisão visual pelo usuário; aprovar/copiar somente o snapshot sanitizado para a pasta publicada; organizar commits coerentes e autorizar push/deploy. Sem snapshot publicado, Benchmark ficará vazio no deploy; Explorar continua acessível como primeira aba. A Sidebar móvel e os diagnósticos TypeScript anteriores são trabalhos separados.

Próximas operações de IA: confirmar free tier e limites reais da conta; obter autorização dos IDs exatos e até 12 tentativas por modelo Groq (24 totais, incluindo falhas). Primeira chamada de cada modelo valida o contrato real e é reutilizada no piloto. Iniciar com teto operacional 1, dentro da autorização total, conferir a resposta e ampliar gradualmente até o teto autorizado, espaçando chamadas conforme a quota de tokens para evitar desperdiçar orçamento em 429. Não repetir Gemini, não mudar prompt nem iniciar os 60 finais nesta etapa. Depois revisar a comparação, publicar snapshot aprovado e selecionar/revisar/congelar os 60 separados antes de nova autorização.

Nenhuma chamada de IA, migration de produção, commit, push ou publicação foi realizada nesta revisão.

## 15. Continuação autorizada — 2026-10-17

O usuário pediu prosseguimento, confirmou a conta Groq gratuita e autorizou até 12 tentativas de `openai/gpt-oss-120b` e 12 de `qwen/qwen3.8-27b`, 24 totais incluindo falhas e recuperações. A revisão automática bloqueou a primeira tentativa antes da execução por exigir autorização explícita do payload. O usuário confirmou o envio dos enunciados públicos preparados (descrição, formatos de entrada/saída, amostras, limites e notas), sem dados de estudantes, identificação ou rating/tags oficiais. Só depois dessa confirmação a chamada foi executada. Gemini não foi chamado novamente.

Os primeiros sucessos reais validaram ambos os contratos e foram aproveitados nos próprios itens. A condução usa o comando existente, um novo teto operacional por chamada dentro da autorização total e pelo menos 65 segundos entre requisições. Somente metadados seguros de resposta/cotas foram registrados adicionalmente; payload, prompt v1 e parâmetros de geração foram preservados.

Qwen: execução `qwen38-27b-dev-v1` parada com 6 tentativas, 2 respostas válidas, 1 item com falha após recuperação e 9 pendentes. Histórico preserva 4 respostas HTTP 429. Uma das respostas de erro informou `Request too large`, tokens de saída, limite 1000 e solicitado 1155; cabeçalhos informavam 8000 tokens/minuto e 1000 requisições/dia. Não tratar isso como simples espera por janela de minuto nem prometer que o teto nominal garante viabilidade. Novo perfil com menos tokens exige nova identidade e decisão explícita; as 6 tentativas restantes não serão consumidas automaticamente. Até essa decisão, preparar ensaio parcial separado da comparação principal, distinguindo limitação operacional de qualidade do modelo.

GPT-OSS: execução `gpt-oss-120b-dev-v1` concluída em 12 tentativas, 12 ratings válidos, 11 saídas de tags válidas e nenhuma falha de requisição. Uma resposta usou `sorting`, fora da taxonomia oficial que contém `sortings`, e permaneceu inválida só para tags. Nenhum sinônimo foi mapeado. Consumo novo total: 18 tentativas (12 GPT-OSS + 6 Qwen), dentro das 24 autorizadas; as 6 restantes do Qwen não foram usadas.

Comparação principal `cf-rating-v1-development`: as execuções operacionalmente completas de Gemini e GPT-OSS, mais baseline, nos mesmos 12 itens válidos de rating. MAE: GPT-OSS 333,3; Gemini 383,3; baseline 466,7. Até ±200: 50%, 50% e 33,3%, respectivamente. F1 micro nas mesmas 11 questões de tags: GPT-OSS 0,638 e Gemini 0,687. A alteração do F1 exibido para Gemini decorre da nova interseção de tags, não de nova inferência ou edição de sua previsão. Continua sendo desenvolvimento exploratório, sem conclusão universal de superioridade.

Comparação `cf-rating-v1-qwen-partial`: preserva os quatro conjuntos de previsões, com interseção de rating de 2 itens e de tags de 1 item. Rótulo explícito de teste parcial por limite de saída. Não comparar o MAE desse subconjunto diretamente ao MAE de 12 itens da comparação principal. A separação foi motivada pelo bloqueio operacional e pelas pendências, sem escolher exemplos segundo acerto/erro; todos os itens e falhas originais permanecem disponíveis.

Exportados e recalculados os snapshots por allowlist; os únicos artefatos derivados destinados ao Git ficam em `backend/api/ai_lab/published/cf-rating-v1-development.json` e `cf-rating-v1-qwen-partial.json`. Sem enunciados, catálogo, prompt completo, justificativas, respostas brutas ou dados de usuários. A conferência adicional inicialmente contou os placeholders pendentes do snapshot parcial como linhas processadas; o script auxiliar foi corrigido para distinguir pendentes antes da recomputação. As métricas do runner/API e os arquivos científicos não precisaram de correção. Hashes dos resultados originais preservados.

A observação real revelou um rótulo incorreto no detalhe: tags inválidas apareciam como não aplicáveis. Teste RED reproduziu o problema; GREEN distingue válida, inválida, pendente e não aplicável. Frontend completo: 73 testes aprovados; build e lint aprovados; TypeScript com os mesmos 30 diagnósticos anteriores, nenhum novo. Backend completo reexecutado: 257 aprovados. Commits locais separados de backend, frontend e correção do detalhe foram criados. Dados privados e auxiliares de condução continuam ignorados pelo Git.

Preparação independente dos 60 finais: seleção provisória privada em `backend/var/ai_lab/reviews/final-selection-preview.json`, a partir do catálogo/hash do desenvolvimento, seed 42, 15 por faixa de 800–2400, no máximo dois problemas por contest e nenhum contest do desenvolvimento. Nenhum enunciado final foi coletado e o conjunto não está revisado/congelado. Nenhuma chamada final está autorizada.

Aceite local dos snapshots reais: API autenticada conferida em SQLite de teste em memória, com fonte privada apontando para caminho inexistente e leitura exclusivamente publicada. A página real também foi conferida com backend/SQLite local, leitura publicada, tabela principal de 12 itens, seletor para o ensaio parcial e cobertura/falhas/pendências correspondentes. Explorar abre primeiro e mantém os três ícones; o detalhe real de 1690E mostra rating correto e tags inválidas. Painel lateral validado no breakpoint desktop e viewport restaurado ao padrão. Nenhuma IA é chamada ao consultar a vitrine. A limitação móvel da Sidebar global continua fora desta entrega.
