# Benchmark de classificação — três modelos, prompts A/B

Concluído em 19/10/2026. Mesmos 60 problemas textuais revisados e congelados,
800–2400, 15 por faixa. Não houve alteração dos enunciados, prompts ou previsões
durante os lotes. As runs anteriores do GPT-OSS 20B foram reutilizadas com
verificação SHA-256 da proveniência; os arquivos-fonte permaneceram idênticos.

## Experimento 1 — Prompt A nos três modelos

Rating: interseção válida de **59/60**. Tags: **52/60**. Todas as linhas usam
o mesmo conjunto válido para a respectiva métrica, incluindo a baseline.

| Modelo | MAE ↓ | Dentro de ±200 ↑ | F1 micro tags ↑ | Ratings válidos /60 | Tags válidas /60 | Respondidas /60 | Chamadas históricas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.5 Flash-Lite | 255,9 | 62,7% | 57,4% | 60 | 58 | 60 | 60 |
| GPT-OSS 120B | 371,2 | 45,8% | 52,0% | 60 | 58 | 60 | 60 |
| Baseline mediana | 394,9 | 33,9% | — | 60 | — | 60 | 0 |
| GPT-OSS 20B | 432,2 | 37,3% | 45,8% | 59 | 55 | 59 | 78 |

Gemini foi escolhido pelo menor MAE em A e cobertura de pelo menos 95%,
conforme o protocolo registrado antes da comparação final. Todos os três
modelos atenderam à cobertura mínima. Isso identifica o melhor neste conjunto,
não um vencedor universal nem uma estimativa independente após seleção.

## Experimento 2 — Prompt B nos mesmos três modelos

Rating: interseção válida de **58/60**. Tags: **48/60**.

| Modelo | MAE ↓ | Dentro de ±200 ↑ | F1 micro tags ↑ | Ratings válidos /60 | Tags válidas /60 | Respondidas /60 | Chamadas históricas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.5 Flash-Lite | 263,8 | 60,3% | 56,8% | 60 | 57 | 60 | 62 |
| GPT-OSS 120B | 365,5 | 41,4% | 53,4% | 60 | 57 | 60 | 60 |
| Baseline mediana | 387,9 | 34,5% | — | 60 | — | 60 | 0 |
| GPT-OSS 20B | 431,0 | 39,7% | 48,0% | 58 | 52 | 58 | 86 |

Não subtrair diretamente as médias dos experimentos 1 e 2 para afirmar o efeito
do prompt: eles usam interseções diferentes. A previsão da baseline é fixa;
sua média muda porque a população válida comparada mudou, não porque foi treinada
novamente. A comparação pareada abaixo resolve isso para o modelo selecionado.

## Experimento 3 — Gemini, Prompt A versus B

Nenhuma chamada extra. Rating nos mesmos **60/60** problemas; tags nos mesmos
**57/60** com tags válidas em A e B.

| Estratégia | MAE ↓ | Dentro de ±200 ↑ | F1 micro tags ↑ | Cobertura rating | Cobertura tags |
|---|---:|---:|---:|---:|---:|
| A — original | 256,7 | 61,7% | 56,7% | 60/60 | 58/60 |
| B — rubrica | 268,3 | 60,0% | 55,1% | 60/60 | 57/60 |
| Baseline mediana | 396,7 | 33,3% | — | 60/60 | — |

B reduziu o erro absoluto em 14 problemas, aumentou em 18 e empatou em 28.
O MAE aumentou 11,7 pontos. Nesta rodada, a rubrica não trouxe melhoria para
o Gemini. Não foi realizado teste de significância, repetição com várias seeds
ou holdout adicional; não concluir que a rubrica sempre piora resultados.

## Limitações e artefatos

A amostra é textual e balanceada: não representa toda a distribuição do
Codeforces. Problemas públicos podem ter sido vistos no treinamento. A escolha
do vencedor usa este mesmo conjunto; não equivale a uma avaliação independente.
A qualidade entre 2500 e 3500 não foi avaliada.

As tentativas históricas incluem falhas e ancestrais das runs. Respostas inválidas
não foram repetidas para melhorar as métricas. Datas, quotas e intervalos entre
chamadas diferem; os tempos não constituem comparação controlada de infraestrutura.

As três comparações sanitizadas estão em `backend/api/ai_lab/published`,
selecionadas por `index.json`. Incluem prompts A/B revisados, versão e hash;
não incluem enunciados, justificativas livres, respostas brutas ou chaves.
Pilotos, Qwen, Gemini 3.8 e a comparação isolada do GPT-OSS 20B estão em
`archive`, fora da vitrine. O Prompt C permanece pausado.

Funcionamento e publicação: [AI Lab](AI_LAB.md).
Comandos e retomada: [operação dos experimentos](AI_LAB_EXPERIMENTS.md).
