# Plano de encerramento dos experimentos do benchmark

Data: 29/10/2026. Proposta para discussão; nenhuma nova chamada autorizada por este documento.

## Objetivo e escopo

Encerrar a investigação atual com uma última hipótese pequena: aumentar o esforço de raciocínio melhora a classificação do Gemini 3.5 Flash-Lite? Preservar JSONs, comandos e execução em segundo plano existentes. Não construir workers, interface de configuração ou matriz de vários modelos.

O few-shot C terminou com 60 ratings e 60 saídas de tags válidos. Na comparação com A, MAE 268,3 versus 256,7; F1 pareado nas mesmas 58 questões 0,558 versus 0,571. Consumo de entrada aproximadamente 3,6 vezes maior. Encerrar C nesta rodada, preservando os resultados. Isso não demonstra que few-shot seja ineficaz em outros modelos ou com outros exemplos.

## Etapa 1 — Preparação técnica mínima

1. Em `backend/api/management/commands/run_ai_benchmark.py`, aceitar um nível de raciocínio explícito e validado para a experiência Gemini.
2. Em `backend/api/ai_lab/providers/gemini.py` e no encaminhamento do gerador, enviar a configuração efetiva à API. Preservar os padrões dos chamadores existentes e do produto.
3. Registrar nível explícito na configuração imutável do run; uma retomada com outro nível deve ser rejeitada. Registrar tokens de raciocínio e motivo de término quando disponíveis, além das medidas existentes.
4. Testar com respostas simuladas: configuração salva corresponde à enviada, valores inválidos são rejeitados, retomadas incompatíveis falham e usos atuais sem parâmetros continuam funcionando.

Dependências: nenhuma chamada real nesta etapa. Seguir as skills do projeto de brainstorming/TDD antes da implementação. Aceitação: testes focados aprovados, sem alterar os artefatos históricos.

## Etapa 2 — Piloto e decisão

Usar as 12 questões do desenvolvimento original, já revisadas e congeladas. Como o prompt é A, não há exemplos few-shot no payload. Não criar outro subconjunto dos 60 finais.

Executar duas runs novas de `gemini-3.5-flash-lite`, com `classification_v1`: `minimal` e `high`. Cada uma recebe as mesmas 12 questões. Manter timeout, política de retries, schema e demais parâmetros iguais. Intercalar blocos das configurações, se operacionalmente simples, para reduzir diferenças temporais; não requer infraestrutura de fila.

São 24 chamadas iniciais, mais retries dentro de um teto a autorizar. Fazer uma verificação inicial integrada à própria run. Não presumir que o saldo da autorização do few-shot autoriza esta experiência.

Antes das chamadas, fixar a regra de decisão. Proposta conservadora: considerar ampliação somente com redução de MAE de pelo menos 10%, cobertura sem queda e melhora que não dependa de um único item. Examinar diferenças por questão, percentual dentro de 200, F1 pareado, faixas, latência e tokens. O limiar é operacional, não significância estatística; um piloto de 12 pode deixar passar ganhos reais.

Se o sinal for fraco, contraditório ou inexistente, encerrar sem testar níveis intermediários nem migrar a busca para outros modelos.

## Etapa 3 — Ampliação condicional

Somente se o piloto justificar: executar ambas as configurações nos mesmos 60 problemas finais, sem novos ajustes. São mais 120 chamadas iniciais, totalizando no máximo 144 antes dos retries no plano completo. Comparar com controle atualizado, e não somente com A histórico.

Publicar cobertura e denominadores de rating/tags separadamente. O conjunto final já foi usado em outras experiências: descrever como avaliação adicional no dataset existente, não como teste inédito independente. O piloto não é somado ao conjunto final para formar uma métrica única.

Aceitação: runs completas ou falhas explicitamente documentadas; conclusão pareada, incluindo qualidade e custo operacional. Não abrir novas variantes com base nos erros finais.

## Etapa 4 — Fechamento sem inferência

Consolidar A, B e C do Gemini e a comparação de raciocínio, se realizada. Atualizar o relatório metodológico com hipótese, configuração, hashes, cobertura, consumo, resultado e decisão. Preparar snapshot revisável com a experiência C, identificada como sem ganho global. A exportação não publica automaticamente.

Manter A como referência salvo evidência consistente em favor de outra configuração. Congelar experimentos e seguir para os ajustes visuais/apresentação.

## Riscos e preservação

O controle A do few-shot foi executado em outra data; diferenças pequenas não isolam perfeitamente o efeito do prompt. A resposta do modelo pode variar, e raciocínio maior pode aumentar tempo, tokens e falhas. Usar nomes novos de run, não repetir seletivamente respostas ruins, não editar referências e não esconder previsões inválidas.

Não há migrações. Reversão: restaurar padrões do código se necessário e manter todas as runs novas como registros privados; nenhum resultado histórico precisa ser removido.

## Referências

- Resultado local: `backend/var/ai_lab/runs/cf60-gemini35-c-v1/comparison-a-vs-c.json`.
- Níveis de raciocínio: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking
- Migração/parâmetros Gemini API: https://github.com/google-gemini/gemini-skills/blob/main/skills/gemini-api-dev/references/migration.md
