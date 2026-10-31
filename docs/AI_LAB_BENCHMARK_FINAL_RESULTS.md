# Benchmark — fechamento e seleção da página

Vitrine organizada em 31/10/2026. A revisão posterior inclui uma única chamada
de recuperação da 524D no GPT-OSS 20B, com o prompt e parâmetros originais.
Ela retornou rating 1700 (oficial 2100) e tags válidas. A falha HTTP 400 original
foi preservada na proveniência de `cf60-gpt20-a-v1-recovered-524d`.
As três comparações incluem a mesma run de baseline mediana,
`cf60-baseline-grid100-v2`, sem estimativa de tags. Seu MAE é recalculado nos
ratings válidos em comum de cada comparação: 396,7 em Modelos (60 itens),
396,7 em Prompts (60) e 400,0 em Raciocínio (59). As previsões da baseline são
idênticas; os recortes pareados explicam a diferença entre as médias.
Fonte: dataset `cf-rating-v1/final`, 60 problemas textuais revisados e congelados,
800–2400. Os mesmos dados já foram reutilizados em experimentos anteriores;
não constituem avaliação independente após escolha de modelos ou configurações.

## 1. Modelos

Snapshot: `api/ai_lab/published/cf60-models-v1.json`. Reutiliza as runs históricas
do prompt A e a baseline de mediana, com a recuperação registrada do 20B.
Rating nos mesmos 60 itens e F1 nas 60 questões. MAE: Gemini 256,7;
GPT-OSS 120B 375,0; baseline 396,7; GPT-OSS 20B 431,7.
F1: Gemini 0,574; GPT-OSS 120B 0,515; GPT-OSS 20B 0,444.
A escolha do Gemini representa as configurações avaliadas,
não uma conclusão universal sobre os modelos.

## 2. Prompts

Snapshot: `api/ai_lab/published/cf60-gemini-prompts-abc-v1.json`.
Três estratégias no Gemini 3.5 Flash-Lite. Mesmos 60 ratings e F1 micro
nas 60 questões, incluindo previsões de tags fora da taxonomia.

| Estratégia | MAE | Dentro de ±200 | F1 micro de tags | Ratings válidos | Tags válidas |
|---|---:|---:|---:|---:|---:|
| A · Direto | 256,7 | 61,7% | 0,574 | 60/60 | 58/60 |
| B · Rubrica | 268,3 | 60,0% | 0,554 | 60/60 | 57/60 |
| C · Exemplos | 268,3 | 55,0% | 0,563 | 60/60 | 60/60 |

Rubrica e quatro exemplos não reduziram o MAE nesta rodada. C melhorou a
cobertura de tags, sem ganho global de precisão. C foi executado em outra data.
A/B têm textos completos revisados; C tem versão, hash e descrição públicos,
sem o texto efetivo que contém os exemplos privados.

## 3. Raciocínio

Snapshot: `api/ai_lab/published/cf60-gemini-thinking-v1.json`.
Prompt A nos dois níveis, com timeout de 90 segundos. Mesmos 59 ratings e
F1 micro nas 60 questões. Não existem pendências.

| Configuração | MAE | Dentro de ±200 | F1 | Ratings válidos | Tags válidas | Latência mediana |
|---|---:|---:|---:|---:|---:|---:|
| Minimal | 245,8 | 64,4% | 0,562 | 59/60 | 57/60 | 18,1 s |
| High | 235,6 | 66,1% | 0,603 | 60/60 | 60/60 | 26,7 s |

High reduziu o MAE em aproximadamente 4,1%. Nos mesmos 59 ratings comparados,
as respostas salvas registram 70.263 tokens totais em minimal e 392.517 em high:
aproximadamente 5,6 vezes mais, incluindo raciocínio quando informado. Não é
uma estimativa de cobrança nem o consumo completo de tentativas que falharam.
A latência usa as respostas disponíveis por configuração, não necessariamente
a mesma interseção nem apenas o tempo interno do modelo.

High melhorou o erro em 24 questões, piorou em 20 e empatou em 15. Piorou na
faixa 1200–1500 (228,6 para 314,3; 14 itens). O ganho não é uniforme.
Uma rodada não comprova superioridade estatística. O produto mantém seus padrões.

Foram contabilizadas 147 das 160 tentativas autorizadas para esta avaliação.
Minimal preserva uma falha de transporte após três tentativas e duas saídas
inválidas de tags. Retomadas não refizeram as previsões anteriores; hashes foram
conferidos. Relatório privado final:
`backend/var/ai_lab/thinking-90s-final-comparison-continued-2026-10-29.json`.

## Regra de F1 atual

Os três snapshots usam `tag_scoring=full-dataset-v1`. O F1 micro agrega TP, FP
e FN nas 60 questões: `2*TP/(2*TP+FP+FN)`. Tags desconhecidas ou incorretas
contam como falsos positivos; tags oficiais ausentes contam como falsos
negativos. Uma resposta ausente ou sem lista de tags é uma previsão vazia.
Maiúsculas e espaços são normalizados e duplicatas removidas; não há tradução
nem equivalência semântica. Membros não textuais de uma lista contam como extras.
O cálculo usa as tags brutas registradas, inclusive quando a validação estrita
considerou a lista inválida. O contrato do produto e essa validação não mudaram.

A baseline não estima tags, portanto seu F1 permanece não aplicável. Os
contadores de TP/FP/FN e o tamanho da avaliação ficam nos JSONs. A coluna
Cobertura e o subtítulo Tags válidas foram retirados da interface; os dados
operacionais permanecem nos artefatos. Os relatórios anteriores mantêm o F1
histórico da interseção válida; não comparar seus números sem recalcular a
mesma política. A função de métricas preserva essa política legada por padrão
para não reinterpretar operações antigas; os três índices atuais optam
explicitamente pela regra nova.

## Preservação e publicação local

As runs e os manifestos de origem foram conferidos por SHA-256 antes/depois.
Uma run derivada registra apenas a recuperação autorizada, sem editar a origem.
Os snapshots antigos continuam no repositório, fora da seleção principal.
Índices anteriores e hashes ficam no backup privado
`backend/var/ai_lab/publication-backups/pitch-2026-10-31/`.

O índice público seleciona somente os três snapshots novos. Exportação usa
allowlist de campos; não inclui configurações inteiras, respostas brutas,
enunciados, chaves ou exemplos. A API continua somente leitura e funciona sem
acesso à pasta privada. Não houve deploy, commit ou promoção automática de high.

Verificação da entrega revisada: 527 testes do backend (incluindo os 338 do AI Lab),
179 testes frontend, TypeScript, ESLint e build Vite aprovados. Prévia local
conferida nas três comparações, metadados de C e abertura dos diagnósticos.
Na revisão para apresentação, Contests passou a aparecer acima de Fila na sidebar;
sidebar, título e nome acessível da página usam AI Lab. AC confirmado permanece
verde mesmo após erros, preservando o contador e os detalhes de julgamento.
Permanecem avisos de testes sobre `staticfiles` ausente e avisos do build sobre
Browserslist e tamanho do bundle; não bloqueiam esta entrega.
