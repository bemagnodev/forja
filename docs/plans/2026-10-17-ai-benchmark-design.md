# Benchmark de classificacao de problemas

Data: 2026-10-17
Estado: desenho aprovado em conversa; implementacao ainda nao iniciada.

## Objetivo

Evoluir o AI Playground da Forja para comparar classificadores de problemas de
programacao competitiva, priorizando rating e avaliando tags como objetivo
secundario. Produzir resultados reproduziveis e inspecionaveis para orientar o
produto e apoiar o AI Showcase da entrevista do Nubank.

## Decisoes aprovadas

- Primeira fonte: Codeforces oficial, com rating e tags oficiais como referencia.
- Desenvolvimento: 12 problemas, separados dos problemas de avaliacao por contest.
- Avaliacao: 60 problemas, 15 em cada faixa: 800-1100, 1200-1500,
  1600-1900 e 2000-2400, inclusive.
- Selecao reproduzivel com semente fixa, diversidade de assuntos e controle de
  concentracao por contest. Registrar criterios, elegiveis e exclusoes.
- Primeiro prompt fixo e claro, sem exemplos classificados, estatisticas de
  resolucao ou chamadas em multiplas etapas.
- Modelos gratuitos; validar acesso e limites na conta antes dos lotes.
- Executar e retomar lotes por comando; visualizar resultados no Playground.
- Manter teste individual na interface.
- Preparar extensao para novos provedores, prompts e classificadores de ML.
- Contest Review e experimentos com dados adicionais ficam para depois.

## Preparacao dos dados

Congelar uma versao do conjunto com enunciados, referencias, origem, data de
coleta, divisao desenvolvimento/avaliacao e versao da preparacao. Identificadores
e respostas de referencia nunca entram implicitamente na entrada do modelo.

Entrada permitida: descricao, formatos de entrada e saida, limites, exemplos e
notas necessarias. Excluir titulo, indice, URL, nome do contest, rating, tags,
editoriais e estatisticas. Preservar formulas e informacoes essenciais.

Excluir inicialmente problemas interativos, output-only e enunciados sem
representacao confiavel. Registrar falhas de coleta; substituir segundo regras
de selecao, antes de observar previsoes. Nao escolher casos por resultado.

Inspecionar especialmente a conversao de LaTeX do scraper existente. Remover
identificadores reduz pistas, mas nao elimina memorizacao de textos publicos.
As chamadas nao recebem ferramentas de busca, navegacao ou execucao.

## Arquitetura

Fluxo: conjunto versionado -> execucao configurada -> classificador -> previsoes
persistidas -> avaliacao deterministica -> API de consulta -> Playground.

Separar conjunto, item do conjunto, execucao e previsao em registros Django.
Cada execucao referencia uma versao congelada do conjunto e uma configuracao
imutavel do classificador. Registrar provedor, modelo/algoritmo, prompt quando
aplicavel, parametros, versao de codigo e configuracao de entrada.

Uma interface comum recebe dados preparados e retorna rating, tags e
justificativa opcional. Adaptadores Gemini e Groq encapsulam detalhes externos.
Um futuro algoritmo de ML usa a mesma interface sem depender de prompt.

Catalogo de classificadores fornecido pelo backend evita listas duplicadas.
Validacao local verifica rating inteiro no dominio definido, tags na taxonomia
e campos obrigatorios. Saida estruturada do provedor nao substitui validacao.

Resultados experimentais nao sobrescrevem previsoes de produto. Identidade de
cache considera entrada, classificador e configuracao. Chamadas de benchmark
nao reutilizam silenciosamente o cache legado do endpoint de produto.

## Execucao e falhas

Execucao por comando com progresso e retomada sem duplicar resultados
concluidos. Persistir por item, com estados pendente, sucesso e falha.
Guardar categoria de falha, tentativas e duracoes, sem credenciais em logs.
Politica de retry limitada para erros recuperaveis, respeitando limites do
provedor. Nao trocar automaticamente para modelos pagos ou outro modelo.

Medir chamada e processamento no backend; distinguir espera por retry e cache.
Registrar tokens quando fornecidos pelo provedor e configuracao efetiva.
Falhas nao entram como previsoes numericas nem desaparecem dos relatorios.

## Avaliacao

- Principal: MAE de rating, em pontos.
- Complementar: percentual dentro de +/-200 pontos e erro por faixa.
- Tags: F1 com agregacao explicitamente definida antes da primeira comparacao.
- Operacao: latencia mediana, quantidade valida e taxa de falha.
- Baseline sem LLM: mediana de rating calculada somente no desenvolvimento.

Comparacoes pareadas usam a intersecao de problemas respondidos validamente,
mostrando cobertura e falhas de cada metodo. Identificar esse subconjunto na UI.
Congelar o prompt apos o piloto. Alteracoes posteriores recebem nova versao;
nao ajustar o prompt no conjunto final e apresenta-lo como teste independente.

## Playground

Explorar: fluxo individual existente, entrada efetiva e resposta, com label
Justificativa da classificacao em lugar de Chain of Thought.

Experimentos: selecionar conjunto e execucoes, tabela de metricas, barras de
MAE por metodo, erro por faixa e dispersao previsto versus oficial. Lista por
problema ordenavel por erro, com detalhe de entrada, referencia e previsao.

Conjuntos de dados: versao, composicao, distribuicao, origem e detalhes dos itens.
Nao iniciar lotes pelo navegador nesta entrega. Endpoints seguem autenticacao
existente; credenciais de provedores permanecem exclusivamente no backend.

## Verificacao e criterio de pronto

Testar separacao referencia/entrada, selecao deterministica, validacao de
respostas, metricas com casos calculados manualmente e retomada idempotente.
Usar mocks para testes automatizados; chamadas reais sao piloto identificado.

Primeira entrega pronta quando os tres candidatos gratuitos forem validados,
o conjunto estiver congelado, o lote puder ser retomado, os resultados forem
visiveis nos graficos e os erros individuais puderem ser inspecionados.
Manter resultados salvos para demonstracao sem dependencia de API ao vivo.

## Limites e pontos a conferir na implementacao

O conjunto e exploratorio: nao demonstra superioridade universal nem ausencia
de contaminacao. Tags oficiais sao referencia incompleta. Generalizacao para
Gyms/CSES exige avaliacao separada. Uma execucao por configuracao nao mede
variabilidade entre repeticoes.

Candidatos discutidos: Gemini Flash-Lite, Gemini Flash e GPT-OSS via Groq;
IDs e acesso gratuito devem ser confirmados no momento do piloto.
Detalhar agregacao de F1, parametros da selecao e contrato dos comandos antes
de implementar essas partes, sem acrescentar infraestrutura de tarefas agora.
