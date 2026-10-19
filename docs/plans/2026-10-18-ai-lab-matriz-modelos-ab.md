# Matriz de modelos e prompts A/B — protocolo aprovado

## Objetivo e apresentação

Comparar Gemini 3.5 Flash-Lite, GPT-OSS 120B e GPT-OSS 20B no mesmo
dataset textual de 60 problemas revisados. Não confundir variação de prompt
com comparação entre modelos. Prompt C permanece pausado.

Três visões finais, reutilizando seis combinações modelo/prompt:

1. Prompt A (`classification_v1`): três modelos e baseline.
2. Prompt B (`classification_v2`): os mesmos três modelos e baseline.
3. Modelo escolhido em A: A versus B e baseline, sem novas inferências.

Escolher pelo MAE na interseção válida comum de A, exigindo pelo menos 95%
de cobertura de rating (57/60). Se nenhum modelo atender, declarar que não há
vencedor elegível; não escolher pelo subconjunto mais conveniente. Empate exato
de MAE deve ser declarado. Cobertura, falhas e F1 permanecem visíveis; não são
ocultados para favorecer uma conclusão. Uma diferença pequena não demonstra
superioridade estatística. O modelo escolhido não precisa melhorar com B.

## Integridade

Dataset `cf-rating-v1/final`, hash
`7ea7ea0585d6a6c74877fe2f9c96ac6f70a521589bb4c395f84bb0a3f1315400`.
Manter seleção, preparação, referências, prompts e parâmetros de geração.
Registrar versão de adaptador e política por run. Modelos remotos podem mudar
sob o mesmo identificador; datas distintas são uma limitação da comparação.

Reutilizar `cf60-gpt20-a-v1-continued` e `cf60-gpt20-b-v1-continued2` com
proveniência validada. Não repetir sucessos, saídas inválidas ou erros definitivos.
Não editar as previsões anteriores para melhorar métricas.

MAE e tolerância usam a interseção válida de rating da respectiva comparação;
F1 usa sua própria interseção válida de tags. Mostrar denominadores e cobertura
sobre os 60. As duas visões de três modelos podem ter interseções diferentes;
a terceira é a comparação pareada A/B do modelo selecionado. Não comparar
diretamente médias de visões com denominadores distintos.

## Escopo aprovado e orçamento operacional proposto

Somente os três identificadores aprovados, nos projetos Free Tier configurados.
Sem troca de modelo, fallback pago ou repetição do GPT-OSS 20B. Sem migrations,
commit, push ou deploy. O acompanhamento antigo de A/B/C foi substituído pelo
escopo desta matriz, preservando a cadência de 30 minutos. C continua pausado
e o GPT-OSS 20B não recebe novas chamadas.

Runs restantes:

| Run | Modelo | Prompt | Intervalo após chamada | Teto acumulado inicial |
|---|---|---|---:|---:|
| cf60-gemini35-a-v1 | gemini-3.5-flash-lite | classification_v1 | 6 s | 75 |
| cf60-gemini35-b-v1 | gemini-3.5-flash-lite | classification_v2 | 6 s | 75 |
| cf60-gpt120-a-v1 | openai/gpt-oss-120b | classification_v1 | 60 s | 75 |
| cf60-gpt120-b-v1 | openai/gpt-oss-120b | classification_v2 | 60 s | 75 |

Teto inicial operacional autorizado de 300 tentativas para essas quatro runs,
incluindo as duas chamadas iniciais já realizadas. Após a revisão automática
solicitar confirmação do orçamento e da execução em segundo plano, o usuário
respondeu explicitamente: “Autorizo os quatro lotes com esses limites”. Os dois
workers foram iniciados, um por provedor. Não herda a autorização de 150 do GPT-OSS
20B. Não ampliar automaticamente. Cada teste inicial é a primeira questão real
do lote, não uma chamada extra. `managed-v1`, até três tentativas por item,
espera máxima de 60 s antes de devolver o controle e respeito a Retry-After.
O teto preservado pode crescer de 1 (checagem inicial) para 75 sem alterar a
configuração científica nem apagar consumo anterior.

Executar A antes de B em cada provedor. Provedores diferentes podem trabalhar
simultaneamente. Parar a sequência se A não completar, sem iniciar B enquanto
o bloqueio não for analisado. Lock impede duplicação da mesma run.

Os limites publicados pela Groq para GPT-OSS 120B são 8 mil tokens/minuto,
200 mil/dia, 30 requisições/minuto e mil/dia; limites efetivos são os da conta.
Google orienta conferir limites ativos no AI Studio. O print previamente
fornecido pelo usuário mostrava 15 RPM, 250 mil TPM e 500 RPD para Flash-Lite;
isso não comprova saldo atual. Intervalos reduzem pressão por minuto, não
garantem cota diária nem gratuidade se a conta tiver faturamento alterado.

Fontes consultadas: https://console.groq.com/docs/rate-limits e
https://ai.google.dev/gemini-api/docs/rate-limits.

## Entrega e validação

Não publicar comparação incompleta como resultado final. Validar hashes,
proveniência, contadores, 60 itens tentados e motivo de parada antes de exportar.
Usar o leitor/exportador existentes; exportações sanitizadas não contêm
enunciados, prompts, respostas brutas ou chaves. Não apagar pilotos nesta etapa.

Não há alteração do runner, adaptadores, modelos Django ou frontend neste
passo operacional. Se forem necessárias correções de comportamento, fazê-las
com teste RED que reproduza o erro, implementação GREEN e suíte pertinente,
preservando a identidade das execuções anteriores. Não modificar contrato ou
prompt no meio de uma run.

Resultados operacionais e logs ficam privados em `backend/var/ai_lab/`.
Ao terminar a matriz, criar as três entradas/snapshots com os componentes já
existentes; verificar interpretação e apresentação antes de qualquer deploy.

As duas chamadas iniciais retornaram rating e tags válidos. Os 16 testes
existentes de leitura/API/exportação de resultados passaram. A primeira
tentativa de rodar esses testes falhou por permissão no diretório temporário
do sandbox; rodar com `--basetemp var/ai_lab/test-temp-ab-review-20261019`
resolveu a configuração, sem alteração de código. Os workers usam comandos
reais com settings locais, separadamente dos testes simulados.
