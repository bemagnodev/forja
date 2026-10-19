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

## Operação, falhas e limites

Os quatro novos lotes consumiram **242/300 tentativas autorizadas**: Gemini A60,
Gemini B62, GPT-OSS 120B A60 e B60. Não houve HTTP429 nesses lotes. Gemini B
teve dois erros de servidor, recuperados sob a mesma configuração. Nenhuma
resposta inválida foi repetida para elevar a qualidade medida.

Histórico preservado do GPT-OSS 20B: A78 chamadas (18 rate limits, um erro
permanente); B86 chamadas (26 rate limits, dois erros permanentes). Nas duas
runs as falhas permanentes continuam na cobertura. As tags inválidas também
continuam contabilizadas: A4 e B6 no 20B, A2/B3 no Gemini e A2/B3 no 120B.

O intervalo de 60s da Groq foi conservador e consumiu aproximadamente uma hora
por prompt. Isso foi espaçamento intencional; não tempo de inferência de uma
hora. As latências medianas de resposta ficaram aproximadamente em 1,2–1,4s
para GPT-OSS e 2,4–2,6s para Gemini. Não comparar velocidade sem considerar
provedor, saída, quotas e diferentes datas de execução. O experimento atual
não é um benchmark controlado de infraestrutura.

Somente os modelos Free Tier autorizados; sem fallback, novos modelos ou
alteração de faturamento. O Prompt C continua pausado e fora destas visões.
O dataset contém questões públicas, com possível exposição no treinamento;
o benchmark é exploratório e restrito à população textual selecionada.

## Entrega local

No seletor da aba Benchmark, após o acabamento aprovado:

1. `Classificação direta — comparação de modelos`.
2. `Classificação com rubrica — comparação de modelos`.
3. `Impacto da rubrica — Gemini Flash-Lite`.

Snapshots sanitizados em `backend/api/ai_lab/published/cf60-prompt-a-models-v1.json`,
`cf60-prompt-b-models-v1.json` e `cf60-best-model-prompts-ab-v1.json`.
Não contêm enunciados, justificativas livres, respostas brutas ou chaves. Após
aprovação explícita, passaram a incluir somente os textos A/B revisados, com
hash e versão. C e exemplos privados continuam excluídos. Pilotos e snapshots
anteriores foram preservados em `api/ai_lab/archive`, fora da vitrine.
Durante a execução dos lotes não houve commit, push, deploy ou migration.
A organização posterior dos commits está em [revisão para publicação](AI_LAB_RELEASE_REVIEW.md).

## Validação da entrega

Na entrega inicial da matriz, 315 testes de backend e 83 de frontend passaram.
Após o acabamento, são 322 backend e 85 frontend aprovados; build e
lint dos dois arquivos React alterados aprovados. TDD reproduziu o rótulo fixo
de Prompt v1 e a ausência de identificação da amostra final antes das correções.
O cabeçalho agora distingue A, B e A/B usando metadados de cada run; arquivos
legados sem versão não recebem uma versão inventada. A amostra por faixa
vem dos resultados, em vez de texto fixo do piloto.

As primeiras tentativas de suíte completa encontraram erros de acesso a arquivos
e recursos do sandbox/Windows. Backend foi coletado explicitamente em `api`,
sem percorrer os diretórios privados de dados/temporários. Frontend completo
passou com uma thread (`--pool=threads --maxWorkers=1`) e diretório temporário
local. Nenhum teste foi removido ou teve suas verificações relaxadas.

As três comparações foram conferidas na página real `http://127.0.0.1:5176/ai-lab`,
incluindo títulos, dados, cobertura, mapa de calor e dispersão. A aba Explorar
permanece a primeira, com ícones Codeforces, AtCoder e CSES preservados.
O acompanhamento recorrente foi pausado após concluir esta matriz; C segue
pausado. Uma próxima execução exigirá novo alinhamento, sem retomada implícita.
