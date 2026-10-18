# AI Lab — comparação de modelos e demonstração

> Histórico da primeira entrega. Para os próximos passos, prevalece o
> [plano geral de revisão](2026-10-17-ai-lab-revisao-geral-plan.md), com o design
> aprovado, publicação por snapshot, revisão da CLI e recuperação de falhas.

Data: 2026-10-17. Estado: implementação das entregas A/B aprovada e concluída localmente; novas inferências dependem de autorização explícita de orçamento. Sem commit ou push.

Andamento: adaptador Groq para os dois modelos, catálogo/dispatcher, comando ampliado, API autenticada de leitura e aba Benchmark implementados com ciclos TDD. O índice privado seleciona Gemini e baseline já salvos. Nenhum lote Groq foi executado; os 60 finais ainda não foram coletados/revisados. Integração da exploração individual (E) permanece posterior à primeira comparação (C), conforme a prioridade definida abaixo.

Verificação desta entrega: backend 231 testes aprovados (95 legados preservados), frontend 69 testes aprovados, build Vite, lint dos arquivos novos, checks Django e ausência de alterações de schema aprovados. Ciclos RED/GREEN observados para adaptador, despacho/orçamento, leitura/API, componentes e abas. Conferência visual local com os dados reais, incluindo seleção do problema 1849E pelo gráfico. Erros intermitentes de permissão/leitura de dependências no isolamento Windows exigiram repetir as suítes fora dele; Vitest concluiu com um worker em threads. A checagem global TypeScript ainda aponta erros em código preexistente; os componentes novos não geraram diagnósticos. Nenhum modelo chamado ou artefato real sobrescrito; adicionado apenas o índice privado da demonstração.

Complementa o [desenho original](2026-10-17-ai-benchmark-design.md). A mudança proposta é antecipar uma visualização local dos resultados salvos e comparar modelos com o prompt v1 antes de experimentar prompts. A persistência Django continua no escopo original do Marco 2; seu adiamento abaixo é uma proposta explícita para reduzir o caminho até a demonstração, não uma decisão já aprovada.

## 1. Objetivo e ponto de partida

Responder: qual configuração estima melhor o rating de problemas de 800 a 2400, com que cobertura e tempo de resposta? Tags são uma avaliação secundária. O resultado apresentado na entrevista deve permitir explicar os dados, a referência, o baseline, as falhas e os limites da conclusão.

Já temos o núcleo local, prompt v1, 12 problemas de desenvolvimento revisados e congelados, baseline e piloto Gemini concluído. Nos 12 itens, Gemini 3.5 Flash-Lite teve MAE 383,3, contra 466,7 do baseline; 6/12 previsões ficaram a até 200 pontos, contra 4/12. Isso é evidência exploratória de desenvolvimento. O resultado consolidado tem 12 respostas válidas, mas houve duas falhas históricas de autorização: preservá-las na informação operacional.

A página AILab.tsx ainda usa o classificador antigo de services/ai_classifier.py. Sua lista de modelos, prompt e cache de platform_metadata não são os do benchmark. A latência medida no navegador inclui etapas adicionais. Não misturar essas previsões com as execuções controladas.

## 2. Modelos propostos e alternativas

Revisão após esclarecimento do usuário: três provedores deixaram de ser um requisito. Estrutura de testes e frontend aprovada; Gemini/GPT-OSS/Qwen são a seleção aprovada para preparar a integração. OpenRouter/Nemotron passa a ser alternativa, não dependência da entrega. Há somente um novo adaptador, Groq, testado separadamente para cada modelo suportado, e 12 tentativas propostas para cada um dos dois novos modelos. Não criar openrouter.py nem seus testes antes de sua inclusão efetiva.

| Provedor | ID exato | Papel |
| --- | --- | --- |
| Google | gemini-3.5-flash-lite | Reutilizar os 12 resultados existentes; referência atual |
| Groq | openai/gpt-oss-120b | Próximo modelo recomendado; outra família, modelo de produção e oferta de plano gratuito |
| Groq | qwen/qwen3.8-27b | Terceira família com o mesmo adaptador Groq; modelo preview, sujeito a descontinuação |

Alternativas verificadas: GPT-OSS 20B na Groq para uma comparação posterior de tamanho/latência; Gemini 3.8 Flash para uma comparação dentro do mesmo provedor; nvidia/nemotron-3-super-120b-a12b:free pelo OpenRouter se preferirmos essa família e aceitarmos outro adaptador e execução em mais de um dia. Nenhuma delas entra automaticamente na execução.

Escolher GPT-OSS 120B primeiro por diversificar a comparação e aproveitar o contrato de saída estruturada. Não pressupor que será mais preciso. Nemotron é uma hipótese útil de comparação, não uma promessa de superioridade. Não usar openrouter/free, pois escolhe modelos dinamicamente. Registrar também o provedor efetivo retornado pelo OpenRouter quando disponível.

Não há evidência de que quaisquer desses modelos sejam os três mais precisos para esta tarefa. A recomendação otimiza diversidade de famílias, gratuidade, quota e trabalho de integração. Qwen está listado como preview na Groq; GPT-OSS 20B é alternativa de produção, mas reduz diversidade por compartilhar a família GPT-OSS. Fixar o ID e preservar os resultados salva a demonstração caso a disponibilidade mude.

### Cotas públicas verificadas em 2026-10-17

| Modelo/rota | Requisições por dia | Outros limites públicos relevantes |
| --- | --- | --- |
| Groq GPT-OSS 120B | 1.000 | 30/min; 8.000 tokens/min; 200.000 tokens/dia |
| Groq Qwen 3.8 27B | 1.000 | 30/min; 8.000 tokens/min; 200.000 tokens/dia |
| Groq GPT-OSS 20B, alternativa | 1.000 | 30/min; 8.000 tokens/min; 200.000 tokens/dia |
| OpenRouter gratuito sem compra de créditos | 50, compartilhadas entre modelos gratuitos | 20/min; falhas consomem cota; 60 itens exigem pelo menos dois dias |
| Gemini 3.5 Flash-Lite | 500, confirmadas pelo print do projeto Forja | 15/min; 250.000 tokens/min; painel mostrava 12/500 utilizadas |

O print confirma especificamente Flash-Lite 3.5; não extrapolar esses limites para Gemini 3.8 Flash ou Live. Modelos Live foram discutidos como possibilidade futura de tutor por voz e não entram no benchmark.

Fontes adicionais: [preços OpenRouter, FAQ de limites](https://openrouter.ai/pricing), [limites Google](https://ai.google.dev/gemini-api/docs/rate-limits) e [catálogo Groq](https://console.groq.com/docs/models). Limites Groq são por organização; confirmar valores efetivos no painel. Não somar quotas por modelo como garantia de independência dos pools. Para 72 itens por modelo (12 dev + 60 finais), 200.000 tokens/dia comportariam média de aproximadamente 2.777 tokens por item, antes de margem para falhas/raciocínio e outros usos. Com média de 4.000, seriam 288.000 tokens: distribuir em dois ou mais dias. Isso é dimensionamento, não medição de consumo futuro.

Os 60 finais do Gemini cabem na cota diária mostrada, respeitando os limites por minuto e outros usos do projeto. Não usar inferência para descobrir quotas. Os limites não autorizam chamadas; cada lote ainda depende da permissão explícita do usuário.

Gratuidade é condição de execução: confirmar plano da conta e rota antes de chamar; nunca migrar automaticamente para plano, rota, modelo ou ferramenta pagos. Catálogo público não comprova acesso da chave específica. Quotas e disponibilidade devem ser verificadas novamente no momento da autorização; não prometer um limite universal. As quotas por tokens também podem limitar a execução mesmo com requisições disponíveis.

Fontes oficiais consultadas nesta revisão:

- [Google: preços e free tier](https://ai.google.dev/gemini-api/docs/pricing).
- [Groq: modelos](https://console.groq.com/docs/models) e [limites do plano gratuito](https://console.groq.com/docs/rate-limits).
- [OpenRouter: rota Nemotron gratuita](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free) e [limites](https://openrouter.ai/docs/api_reference/limits).

## 3. Protocolo fixo antes de executar

- Mesmo snapshot dos 12 itens, mesmos hashes, prompt efetivo v1 e taxonomia oficial. Nenhum rating, tag oficial, título, ID, URL ou total de resoluções entra no payload. Nenhuma ferramenta de navegação/pesquisa é habilitada. Isso evita vazamento direto, mas não elimina possível memorização dos problemas públicos no treinamento.
- Uma previsão por item/modelo; sem escolher a melhor de várias tentativas. Manter instrução e entrada semanticamente iguais; apenas o envelope exigido por cada API muda. Registrar parâmetros de geração, limite de saída e opções de raciocínio; não prometer equivalência de temperatura ou determinismo entre provedores. Definir esses parâmetros antes do lote e não ajustá-los após olhar os acertos.
- O adaptador converte para rating, tags e justificativa. Validação comum: rating inteiro múltiplo de 100 entre 800 e 2400, sem truncamento; tags oficiais com espaços/capitalização normalizados e duplicatas removidas, sem sinônimos. JSON inválido, truncamento e valores fora do domínio ficam visíveis como falhas de validação, não são corrigidos por outra IA.
- Baseline da mediana definido no desenvolvimento; no conjunto final usar esse valor sem recalculá-lo nas referências finais. Baseline não disputa métricas de tags.
- MAE é a métrica principal; proporção com erro até 200 pontos e F1 micro de tags são complementares. Mostrar também viés médio e erros por faixa se calculáveis com as informações já salvas, sem transformar isso em dependência da primeira tela.
- Comparação pareada na interseção válida por tarefa, acompanhada de N comparado, válidos/total, respondidos, pendentes, falhas e taxa de falha. Com interseção vazia, apresentar indisponível, não zero. Não favorecer um modelo que responde menos.
- Separar falha por item de histórico de tentativas: uma resposta posterior válida não apaga uma tentativa anterior malsucedida. Latência da chamada e tokens são indicadores operacionais, não prova isolada de qualidade; reutilização do Gemini ocorreu em outro horário.

## 4. Entregas, TDD e critérios de aceite

### Entrega A — ampliar o núcleo, sem chamar modelos

Criar catálogo pequeno com provedor e IDs explícitos e um ponto comum de classificação no módulo existente. Adicionar somente groq.py, com testes separados para GPT-OSS e Qwen. Estender o comando run_ai_benchmark existente, sem criar mais comandos para executar ou comparar. Reutilizar validação, métricas, limites e salvamento atuais; não criar uma arquitetura de plugins.

TDD de cada adaptador, em ciclos separados: RED com cliente HTTP/SDK simulado para o payload esperado e uma resposta válida; GREEN com a menor implementação; RED/GREEN para autenticação, quota, timeout, JSON inválido, resposta incompleta e ausência de uso de ferramentas. Só então refatorar duplicações reais. Testar explicitamente rota gratuita, rejeição de modelo não autorizado e ausência de fallback pago. Retry de SDK desabilitado para não escapar do contador.

Testar o despacho, identidade da execução e orçamento antes de ampliá-los. Não mudar o prompt v1 ou reexecutar o Gemini como efeito colateral. Aceite: os dois adaptadores (Gemini e Groq) seguem o mesmo contrato, com os dois modelos Groq testados separadamente; testes não usam a rede nem chaves reais. Suíte completa do backend ao fechar a entrega.

### Entrega B — mostrar os resultados que já existem

Adicionar API autenticada somente de leitura para listar execuções conhecidas e retornar uma comparação saneada. Ela lê os artefatos locais; nenhum GET executa IA, coleta enunciados ou inicia lote. IDs de execução resolvidos dentro da raiz configurada, sem aceitar caminhos arbitrários. Retornar somente campos necessários para a tela, nunca chaves, snapshots completos ou logs HTTP brutos.

Na página atual, acrescentar uma aba Benchmark e preservar Explorar. Construir com Gemini e baseline já salvos: tabela, gráfico de MAE e dispersão previsto versus oficial com diagonal ideal. Mostrar dataset, quantidade de itens, prompt e natureza desenvolvimento/final. Detalhe por problema: referência e previsão de rating/tags, erro e justificativa salva. Não é necessário exibir enunciados completos.

TDD da API: RED para acesso não autorizado, comparação conhecida, artefato ausente/incompleto, caminho inválido e garantia de nenhuma chamada de IA; GREEN mínimo. TDD da interface com dados sintéticos: valores da tabela, cobertura junto à qualidade, troca de modelo/dataset, ponto ligado ao detalhe, vazio e falha de carregamento. Verificar manualmente legibilidade dos gráficos e layout. Usar SVG simples e componentes existentes; só adicionar biblioteca se a implementação real justificar.

Aceite: demonstração local navegável sem novas chamadas; filtros não misturam prompts/datasets incompatíveis; testes, build e verificações pertinentes passam. Nesta proposta a leitura inicial usa arquivos privados locais; publicação remota exige escolher e configurar armazenamento persistente, não basta fazer deploy do frontend. Persistência Django permanece alternativa do plano original, com models em api/models.py e migração em uma entrega independente. Não aplicar migration em produção.

### Entrega C — piloto comparativo com os dois modelos adicionais

Pedir autorização nominando os dois IDs e um teto de 12 tentativas de geração por modelo: até 24 novas tentativas. A primeira chamada bem-sucedida já conta como um dos 12 itens; não há chamada extra de smoke test. Falhas também gastam teto, portanto 12 tentativas não garantem 12 respostas válidas. Metadados e tentativas adicionais só com orçamento explícito.

Executar sequencialmente, persistir cada resultado e interromper cedo se houver erro estrutural de autenticação, acesso ou rota. Respeitar quota e Retry-After. Começar sem retry automático; qualquer retry posterior deve ser limitado e consumir o mesmo teto autorizado. Não reprocessar automaticamente falhas já registradas nem substituir o modelo. Retomar apenas itens pendentes preservando a identidade científica da execução.

TDD anterior à operação: simular interrupção/retomada, falha antes de gravar resposta, exaustão de orçamento, rejeição de mudança de prompt/modelo e reuso sem nova chamada. A operação real é um experimento autorizado, não um teste automatizado da suíte. Aceite: três modelos visíveis na mesma tela, qualidade e cobertura pareadas, orçamento auditável e falhas preservadas. Fechar com suíte completa.

### Entrega D — congelar os 60 finais e executar o benchmark

Separar esta etapa do piloto. Usar seleção reproduzível já existente sobre snapshot público do Codeforces, seed registrada, 15 problemas em cada faixa: 800–1100, 1200–1500, 1600–1900, 2000–2400. Não selecionar a partir de preferências ou resultados do modelo. Evitar contests do desenvolvimento e limitar concentração por contest conforme a regra atual. Referências de rating/tags vêm do catálogo oficial; o enunciado vem do scraper. Guardar snapshot/data para que mudanças futuras do catálogo não mudem silenciosamente a referência.

Gerar revisão legível, conferir preparação de entrada e aprovar os 60 antes de congelar. Itens quebrados ou sem suporte podem ser substituídos antes de executar por critérios documentados e reservas determinísticas; não excluir depois porque um modelo errou. Nenhuma chamada dos modelos finais ocorre antes da validação e congelamento do conjunto.

TDD: testes de separação por contest, quotas, determinismo, invalidação por mudança de conteúdo e bloqueio de execução sem congelamento; ampliar apenas onde faltar cobertura. Executar suíte completa antes da operação. Autorizar depois até 60 tentativas/modelo, 180 no total, com falhas dentro do teto e sem reaproveitar os 12 dev como teste final. Agendar em mais de um dia se o plano gratuito exigir. O orçamento não é autorização antecipada.

Aceite: tela distingue piloto e benchmark final, apresenta resultados salvos e tamanho efetivo das comparações. Não inventar significância estatística para uma amostra pequena e estratificada. A demonstração permanece útil mesmo se uma rota gratuita ficar indisponível: mostrar o resultado parcial honestamente, sem substituição silenciosa. Suíte completa ao encerrar o marco.

### Entrega E — integrar a engine de exploração e preparar a entrevista

O dispatcher comum deve ser aproveitado na exploração individual, evitando duas implementações de provedor. Fazer a ponte do contrato rating/tags/justification para o formato atual da API; preservar consumidores existentes. Atualizar o catálogo de modelos da tela a partir do backend, sem listas divergentes.

Antes de reutilizar previsão antiga, exigir identidade compatível de modelo/prompt; se não houver identidade registrada, tratar como legado e não como resultado do benchmark. Não criar cache genérico. Se integrar essa mudança atrasar a demonstração, entregar a aba Benchmark primeiro e deixar a unificação individual para logo depois, claramente separada.

TDD: teste de regressão do contrato público, seleção do adaptador correto, bloqueio de modelo não permitido e previsão legada incapaz de se passar por resultado novo. Manter os testes legados e executar a suíte completa. Preparar um roteiro de cinco minutos: problema do usuário, protocolo, baseline, comparação, dois erros reais e decisão de produto. Usar dados salvos durante a apresentação, sem depender de uma inferência ao vivo.

## 5. Estrutura mínima proposta

```text
backend/api/ai_lab/
  classification.py          # ponto comum e baseline; ampliar o existente
  contracts.py               # validação/taxonomia existentes
  dataset.py                 # seleção e entrada existentes
  metrics.py                 # comparações existentes
  runner.py                  # orçamento/retomada existentes
  review.py                  # revisão existente
  catalog.py                 # somente os modelos realmente integrados
  results.py                 # leitura saneada para a API, quando necessária
  prompts/classification_v1.txt
  providers/gemini.py
  providers/groq.py
backend/api/tests/ai_lab/
  conftest.py                 # fixtures específicas; preservar os arquivos atuais
  test_dataset.py
  test_classification.py
  test_metrics.py
  test_commands.py
  test_groq.py                # adicionar quando o adaptador existir
  test_results_api.py         # adicionar na entrega da API
frontend/src/pages/AILab.tsx
frontend/src/components/ai-lab/
  BenchmarkResults.tsx        # tabela, estado e seleção
  PredictionChart.tsx         # dispersão; separar outras partes só se necessário
backend/var/ai_lab/           # privado e ignorado; datasets e execuções reais
```

Não criar diretórios vazios, interfaces para ML, filas de execução, painel de edição de prompt ou sistema genérico de experimentos. Fixtures pequenas, sintéticas/revisadas, no Git; catálogos, enunciados completos e respostas reais permanecem privados. Testes são estritamente aditivos; não mover nem renomear legados. Preservar a contagem anterior; quedas inesperadas precisam ser investigadas, não compensadas por novos testes.

## 6. Ordem prática, segurança e reversibilidade

Prioridade: A e B, depois C; D é a expansão necessária para o benchmark final. E aproveita o núcleo sem bloquear a primeira visualização. Buscar primeiro uma demonstração funcional com o que já existe. Não atrelar a apresentação à disponibilidade imediata das três APIs. Estimar prazo em cada entrega após inspecionar seus testes; revisão humana dos 60 e quotas são parte do prazo, não apenas codificação.

Seguir docs/TESTING.md: RED relevante observado, GREEN mínimo, REFACTOR com testes verdes. Todo teste automatizado usa serviços simulados e ambiente de testes isolado. Comandos reais usam configuração local explícita de AI Lab, nunca settings_test nem conexão acidental ao Supabase. Preservar os artefatos existentes e não ler/expor valores das chaves em relatórios.

Quando houver autorização de commits, separar comportamentos reversíveis: catálogo/dispatcher, Groq, OpenRouter, leitura/API, interface, integração individual e documentação. Não juntar refatoração ampla com provedores. Dados reais não acompanham commits. Reverter UI/API não elimina resultados privados; reverter adaptador não invalida históricos salvos. Este planejamento não autoriza commit, push, chamada de modelo ou migration.

Prompt v2, dicas por estatísticas de acerto, exemplos adicionais e algoritmos ML ficam para depois dessa comparação. Alterações futuras geram nova versão e passam primeiro pelo desenvolvimento; se os 60 finais orientarem a alteração, deixam de ser um teste final intocado para essa nova versão.
