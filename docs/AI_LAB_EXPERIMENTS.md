# Operação local de experimentos do AI Lab

## Apresentação final em 19/10/2026

A vitrine seleciona três comparações em `api/ai_lab/published/index.json`, com
nomes das técnicas. Pilotos, Qwen, Gemini 3.8 e A/B isolado do 20B foram arquivados
em `api/ai_lab/archive`, preservando bytes. Runs e datasets originais não mudaram.
O índice privado foi curado na mesma ordem e seu histórico preservado localmente.

`publish_prompts=true` inclui somente os textos A/B expressamente revisados,
extraídos das configurações registradas e conferidos contra os hashes aprovados.
O painel **Técnica e prompt** exibe/copia esses textos sem inferência. Essa é
uma exceção explícita à política histórica de não publicar prompts, restrita
a A/B sem enunciados/exemplos. C continua privado e pausado.

## Matriz A/B concluída em 19/10/2026

As seis combinações terminaram. Resultados, denominadores, cobertura e limites
estão no [relatório da matriz](AI_LAB_BENCHMARK_AB_RESULTS.md). As três visões
foram exportadas e conferidas no AI Lab local. Gemini 3.5 Flash-Lite foi escolhido
em A; na comparação pareada de 60 problemas, B não melhorou seu MAE.
Os quatro novos lotes consumiram 242 das 300 tentativas autorizadas. O
acompanhamento recorrente foi pausado ao concluir; nenhuma run C foi retomada.

## Histórico da autorização e preparação da matriz de três modelos com A/B

O protocolo atual está em
[matriz de modelos A/B](plans/2026-10-18-ai-lab-matriz-modelos-ab.md).
Serão três visões: Prompt A nos três modelos, Prompt B nos mesmos três e
A versus B no modelo escolhido pela comparação A. A terceira reutiliza
resultados, sem inferência adicional. Não apresentar os testes A/B do GPT-OSS
20B como se já representassem os três modelos.

A/B do GPT-OSS 20B já estão completos e serão reaproveitados. O prompt C
continua pausado. O acompanhamento a cada 30 minutos agora segue
somente esta matriz A/B. As verificações iniciais do dataset
final no Gemini 3.5 Flash-Lite e no GPT-OSS 120B produziram uma resposta válida
em cada modelo. O usuário autorizou explicitamente os quatro lotes restantes
em segundo plano, com teto acumulado de 75 tentativas por combinação, incluindo
essas verificações iniciais. Dois workers iniciados executam A e depois B em
cada provedor, parando a sequência se houver bloqueio ou pausa.

O restante deste documento contém registros históricos de etapas anteriores;
frases como “nenhuma chamada real foi feita” descrevem aquela etapa, não o
estado atual dos experimentos.

## Preparação A/B/C e aprovação do dataset

Após o usuário aprovar a revisão HTML, os 60 itens foram registrados como
revisados e congelados nos hashes atuais, preservando o manifest anterior.
Hash final: `7ea7ea0585d6a6c74877fe2f9c96ac6f70a521589bb4c395f84bb0a3f1315400`.
Os parágrafos históricos abaixo sobre collected descrevem o estado anterior.

Prompt A preservado; B salvo como `classification_v2.txt`; C usa o template
`classification_v3.txt` mais os quatro exemplos privados aprovados e integrados.
A escolha das questões e verificações está em
[plano dos prompts e exemplos](plans/2026-10-18-ai-lab-prompts-examples.md).
Sem arquivo privado/contexto válido C continua bloqueado. Nenhuma chamada real
foi feita. O dataset final congelado e os pilotos permanecem intactos.

## Parser compartilhado — atualização de 2026-10-18

`api/services/scrapers/codeforces.py` contém o único parser HTML do Codeforces:
`scrape(url)` baixa e chama `parse_html(html, source_url)`. O benchmark usa o mesmo
parser nos HTMLs salvos. `api/ai_lab/dataset.py::parse_statement` é apenas uma
entrada de compatibilidade, sem interpretação própria de HTML.

`api/services/scrapers/preparation.py` concentra a montagem do payload, removendo
título, identificação, referências oficiais e campos extras dos exemplos.
Explorar e produto usam essa função, assim como o dataset. A validação do dataset
exige limites e exemplos completos; para AtCoder/CSES, os campos opcionais do
contrato anterior são preservados. Isso não altera o payload de um mesmo HTML CF.
BaseScraper e as classes separadas de AtCoder/CSES foram mantidas.

LaTeX desconhecido não é apagado. Descrição pode ocupar vários blocos e todos os
pares de exemplos são preservados. Imagens `img` recebem URL resolvida, alt,
posição ordinal e marcador `[image:N]` no texto. Não são baixadas nem enviadas
como conteúdo multimodal. Imagens HTML e SVG inline recebem marcadores de conteúdo
não processado; iframe/script/object continuam explicitamente não suportados no
parser Codeforces. AtCoder e CSES também preservam presença e marcadores de imagens.

Explorar retorna avaliação textual com `visual_status=unprocessed` e aviso, sem
gravação. Fila/Contests podem salvar uma previsão textual com rating/tags válidos
e `ai_visual_status=unprocessed`; exibem o mesmo aviso após recarregar e ao usar
cache. Cache já existente não é reclassificado nem apagado automaticamente.
Suporte multimodal é outra etapa. O prompt de produto é `product_classification_v1`,
800–3500; os experimentos seguem com A/B e validação 800–2400. O vencedor só foi
avaliado no recorte do benchmark; não há validação de qualidade em 2500–3500 nem
dataset adicional para essa faixa nesta entrega.
O protocolo textual do benchmark mantém uma regra de elegibilidade explícita para
conteúdo visual; não se trata mais de uma segunda decisão de extração escondida.
Não é permitido congelar entrada visual como se fosse avaliação multimodal completa.

As mesmas 60 questões foram reprocessadas localmente. Resultado: **zero mudanças
nos payloads**, nenhuma troca de questão, zero chamadas de rede/IA. O manifest
recebeu `preparation_version=shared-codeforces-v1`; naquele momento ficou collected.
O desenvolvimento congelado de 12 itens permaneceu idêntico byte a byte. Backup
privado da revisão anterior em `final/revisions/pre-shared-parser/` e relatório
em `final/reprocessing-report.json`. HTML de revisão regenerado no caminho atual.

TDD reproduziu perda de LaTeX, perda de grupos de exemplos e diferenças de payload.
Teste legado do scraper CF teve apenas as expectativas de conversão matemática
atualizadas para a preservação aprovada; nenhum teste foi movido ou removido.
Validação final: 299 testes de backend e 78 de frontend aprovados; diff sem
erros de whitespace. Sem chamadas reais, migrations, commit, push ou publicação.

## Conjunto de 60 preparado em 2026-10-18

Coleta autorizada pelo usuário, sem inferência. O comando existente é
`prepare_ai_dataset --settings core.settings_ai_lab_local --dataset-version
cf-rating-v1 --split final --seed 42` (configurar o SQLite local como abaixo).
Usa catálogo público do Codeforces, não escolha manual ou previsões do banco.

O conjunto está em `var/ai_lab/datasets/cf-rating-v1/final/`: 60 questões,
15 por faixa 800–1100, 1200–1500, 1600–1900 e 2000–2400. Todos os contests das
12 questões antigas foram excluídos. Sobreposição de questões/contests: zero.
O limite configurado é duas questões por contest; neste sorteio houve uma por
contest. A semente 42 e o snapshot do catálogo permitem reproduzir a seleção.
Catálogo: `16460dbaa1f1536f05c2dd16d866026ca0c36c7f42e71dc9e8749f45c908138c`.

Durante a coleta foi corrigido, com TDD, um problema de eficiência: excluir um
enunciado incompatível reembaralhava o restante do catálogo. A nova seleção
`stratified-v2-stable-replacement` mantém a ordem sorteada antes de excluir itens
incompatíveis, respeitando as cotas por faixa/contest. Os manifests antigos
permanecem intactos. A coleta interrompida foi concluída reaproveitando HTMLs
privados locais e baixando 15 páginas faltantes com um helper privado; não houve
uso de modelos ou banco remoto. Os candidatos extras baixados na tentativa
anterior não fazem parte do conjunto final e não foram publicados.

O manifest registra 15 exclusões por imagem/conteúdo incorporado. Isso limita
a população avaliada a problemas de texto compatíveis com o preparador atual;
não deve ser descrito como amostra de todos os tipos de problema do Codeforces.
Falhas de rede não são motivo para substituir questões silenciosamente.

Estado atual: **frozen**, após aprovação humana registrada. Na coleta inicial os
60 ficaram collected, sem aprovação automática.
Validação local: 25 testes de dataset e 294 testes da suíte completa aprovados;
60 artigos no HTML, hashes do desenvolvimento válidos e arquivos privados
confirmados como ignorados pelo Git.
`review.html` compara o texto-fonte com a entrada preparada. Conferir:

- descrição completa e fórmulas preservadas;
- restrições, limites de tempo/memória e formato de entrada/saída;
- todos os exemplos e notas relevantes;
- ausência de rating/tags oficiais, título e identificação no payload;
- trechos que mencionem outro problema, imagem ou contexto ausente.

Informar a chave da questão e o trecho problemático se houver divergência.
Não substituir itens pelo desempenho posterior dos modelos. Congelamento e
execuções só ocorrerão depois da revisão. A página oficial, acessível pelo link
Original, é a referência para dúvidas sobre o texto-fonte exibido no HTML.

## Identidade e arquivos

Uma run é um modelo + prompt + dataset + parâmetros + política de execução.
Novas runs usam `managed-v1`; pilotos anteriores conservam sua política legada.
Não editar um arquivo de prompt já usado: criar outro, por exemplo
`backend/api/ai_lab/prompts/classification_v2.txt`. O nome sem extensão é o
argumento `--prompt`. V1 e v2 carregam diretamente; v3 exige `--examples-file`
apontando para `var/ai_lab/prompts/classification_v3_examples.json` no terminal
backend. O comando resolve essa origem privada sob var/ai_lab, valida os dois
datasets e inclui texto/hashes na identidade. Usar A/B com exemplos é rejeitado.
`{taxonomy}` é preenchido com as tags oficiais. O enunciado continua separado.

O executor registra o texto efetivo/hash do prompt, hash do dataset, modelo,
parâmetros explícitos, versão do adaptador, timeout e política. Mudar qualquer
um desses dados exige outro `--run-id`. Isso não fixa para sempre a versão
remota de um modelo cujo provedor atualize o mesmo identificador.

Arquivos privados e ignorados pelo Git:

```text
backend/var/ai_lab/
  datasets/<versão>/<development|final>/manifest.json
  runs/<run-id>/run.json       # previsões, histórico, orçamento, próximo horário
  runs/<run-id>/metrics.json   # relatório derivado ao retornar normalmente
  showcase.json               # lista explícita de runs por comparação
  exports/<comparação>.json    # exportação sanitizada para revisão
```

Os enunciados, catálogos e respostas privadas não devem ser publicados. A página
Benchmark lê snapshots revisados em `backend/api/ai_lab/published/`; Explorar não
alimenta esses arquivos. Neste trabalho nenhum snapshot antigo foi reexportado.

## Política nova

- Uma execução por modelo, sequencial, com intervalo padrão de 5 segundos.
  Ajustar o intervalo às cotas reais de requisições e tokens da conta.
- Até 3 tentativas totais por item, contando retomadas; o teto acumulado
  `--max-requests` sempre prevalece. Ele não é uma franquia por dia ou por comando.
- Timeout, HTTP 5xx e rate limit podem ser recuperados. Espera progressiva com
  variação aleatória, respeitando `Retry-After` e a cadência configurada.
- Após esgotar tentativas de timeout/servidor, registrar e seguir. Após esgotar
  tentativas de rate limit, pausar o provedor. Espera acima de `--max-wait`
  (padrão/máximo 60 segundos) também pausa, preservando o próximo horário.
- HTTP 429 não informa necessariamente se a cota é diária. Não inventar essa
  distinção: consultar o painel quando o provedor não fornecer um prazo útil.
- Autenticação e requisição incompatível interrompem a run. Não retomar às cegas;
  corrigir a causa e revisar a necessidade de nova identidade/configuração.
- Resposta com rating/tags inválidos não é repetida para melhorar métricas.
- Resultado desconhecido após interrupção durante a chamada fica `interrupted`:
  não há repetição automática, pois o provedor pode ter consumido a requisição.
- Sem troca de modelo, fallback, scheduler ou retry escondido no adaptador.
  `--retry-failures` continua disponível apenas para runs legadas.

## Preparar o terminal

Os exemplos abaixo são instruções, não autorização de consumo. Antes do lote,
aprovar modelo exato, prompt, dataset e teto incluindo recuperações. Confirmar
no provedor que a conta/projeto é gratuito: a variável de confirmação é uma
declaração local, não uma verificação técnica de faturamento.

No PowerShell, dentro de `backend`, configurar explicitamente um SQLite local:

```powershell
$env:AI_LAB_SQLITE_PATH = Join-Path (Get-Location) 'var/ai_lab/experiments.sqlite3'
$env:AI_LAB_FREE_TIER_CONFIRMED = 'true'
```

As chaves ficam na configuração privada existente. Nunca colar/exportar seu
conteúdo. Comandos reais exigem `core.settings_ai_lab_local`; não usar
`settings_test`. O executor valida o destino SQLite sob `var/ai_lab` e rejeita
PostgreSQL/Supabase. Nenhuma migration de produção é necessária para esse fluxo.

## Iniciar e retomar

Exemplo futuro, **somente após congelamento e autorização dos 60**. O teto 75
ilustra 60 chamadas iniciais + até 15 recuperações; pode se esgotar antes de
atingir todos os itens se houver muitas falhas. Não está autorizado por este doc.

```powershell
.\.venv\Scripts\python.exe manage.py run_ai_benchmark `
  --settings core.settings_ai_lab_local `
  --dataset-version cf-rating-v1 --split final `
  --run-id cf60-gpt20-v1 --classifier groq `
  --model openai/gpt-oss-20b --allow-model openai/gpt-oss-20b `
  --prompt classification_v1 --max-attempts 3 `
  --request-interval 5 --max-wait 60 --max-requests 75
```

Para retomar, executar **o mesmo comando**. Ele recupera falhas transitórias
e avança nos pendentes, sem refazer sucessos. Aumentar o teto requer orçamento
adicional aprovado; repetir o comando não renova o orçamento. Usar novo run-id
para v2 e para cada modelo. Gemini usa `--classifier gemini`; os dois GPT-OSS
usam `groq`. Nunca substituir o modelo silenciosamente.

`Ctrl+C` interrompe. O `run.json` é a fonte de verdade; `metrics.json` pode estar
desatualizado após interrupção. Cada tentativa reserva orçamento e item antes
da rede e salva o resultado depois. Uma trava impede dois processos no mesmo
run-id. Após encerramento forçado do processo, uma trava órfã pode exigir remoção
manual, apenas depois de confirmar que não existe processo executando a run.

## Consultar sem executar IA

```powershell
.\.venv\Scripts\python.exe manage.py run_ai_benchmark `
  --settings core.settings_ai_lab_local `
  --dataset-version cf-rating-v1 --split final `
  --run-id cf60-gpt20-v1 --status
```

Mostra pendentes, válidos por tarefa, ratings válidos na primeira tentativa,
chamadas consumidas, teto, motivo da parada e próximo horário Unix quando houver.
Não precisa de autorização de modelo ou de chave para consultar arquivos.
`completed` significa que não restam itens elegíveis: pode haver falhas definitivas.
Não significa cobertura de 100%. `request_cap` exige revisar o orçamento;
`provider_pause` exige aguardar/verificar a cota.

## Comparar prompts

Por padrão, comparações privadas continuam exigindo o mesmo prompt. Para uma
comparação intencional entre v1 e v2, adicionar `"compare_prompts": true` à entrada
correspondente do índice privado `showcase.json`, listando explicitamente as runs.
O dataset precisa continuar idêntico. Cada linha identifica modelo e prompt;
o hash fica por run, sem fingir que existe um único prompt comum. Exportar só
depois de revisar a comparação. Essa opção não altera nem republica snapshots
antigos e não cria automaticamente um experimento na página.

Qualidade é comparada na interseção válida, junto de cobertura e falhas. O
histórico preserva tentativas fracassadas mesmo após recuperação. O resumo local
expõe ratings válidos na primeira tentativa; a tabela publicada mantém as métricas
existentes. A avaliação de tags continua estrita, sem filtragem para melhorar F1.

## Verificação sem serviços externos

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests/ai_lab -q `
  --basetemp=var/ai_lab/test-temp/experiments-check
```

`pytest` usa `settings_test` e respostas simuladas. O caminho `--basetemp` é
descartável: nunca apontar para datasets ou runs. Para fechar o marco, executar
a suíte completa. As 60 questões e o prompt v2 continuam pendentes de revisão.
