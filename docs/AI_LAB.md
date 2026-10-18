# AI Lab: experimentos locais e vitrine de resultados

Runbook para preparar datasets versionados, revisar entradas e executar o piloto
local. Baseline, Gemini/Groq, métricas gerais/por faixa, recuperação limitada,
API de leitura e interface estão implementados. Três modelos em dois provedores;
OpenRouter e persistência Django ficam fora da entrega atual.

### Resultados disponíveis no piloto

Os snapshots sanitizados versionados trazem `Experimento Codeforces 1`, com
Gemini/GPT-OSS e baseline nos mesmos 12 problemas, e um teste parcial separado do
Qwen. GPT-OSS completou 12 tentativas; Qwen foi interrompido após 6 tentativas e
2 respostas válidas, por erro de limite de tokens de saída. O histórico de 4
falhas 429 e as 9 pendências do Qwen ficam explícitos, sem afetar silenciosamente
a coorte da comparação principal. As métricas entre os dois experimentos têm
denominadores diferentes e não devem ser comparadas diretamente.

O piloto é exploratório. A mediana usa a regra v2 na grade de 100 pontos. O F1
da comparação principal usa as mesmas 11 questões válidas de tags em Gemini e
GPT-OSS; a previsão `sorting` do GPT-OSS foi invalidada, sem corrigir para
`sortings`. Nenhuma chamada Gemini foi repetida nessa comparação.

## Autorização de modelos

Configurar uma chave não autoriza seu uso. Antes de qualquer chamada real,
inclusive disponibilidade, apresentar provedor, ID exato, teto total de
requisições incluindo retries e condições de gratuidade. Aguardar autorização
explícita do usuário. Não usar chaves ou modelos durante os testes automatizados.

O comando padrão usa somente o baseline local. Para modelo real, exige
--classifier, --model, --allow-model com o mesmo ID e --max-requests positivo.
Exige também AI_LAB_FREE_TIER_CONFIRMED=true após conferir a conta; essa declaração
não verifica cobrança no provedor nem substitui a autorização na conversa.
Não há fallback automático para outro modelo ou plano pago.

## Ambiente e arquivos privados

Executar de backend, usando backend/.venv:

```powershell
$env:AI_LAB_SQLITE_PATH = Join-Path (Get-Location) 'var/ai_lab/pilot.sqlite3'
```

Os comandos reais exigem --settings=core.settings_ai_lab_local. O SQLite deve
ser um arquivo absoluto sob backend/var/ai_lab. Essa configuração substitui o banco
herdado antes de abrir conexões. Settings de teste e bancos remotos são rejeitados.
Nenhuma migration é necessária para o núcleo do Marco 1.

Estrutura de dados:

```text
backend/var/ai_lab/
  catalogs/<hash>.json
  datasets/<version>/development/
    manifest.json
    raw/<hash-da-url>.html
    review.html
    validation.json
  datasets/<version>/final/
    ...
  runs/<run-id>/
    run.json
    metrics.json
```

--dataset-version tem default explícito cf-rating-v1 nos três comandos. Use o mesmo
valor na preparação, validação e execução. O valor deve ter 1–64 caracteres,
começar por letra/número e usar somente letras ASCII, números, ponto, hífen ou
underscore; '..', separadores de caminho e ponto final são rejeitados.
A opção --version volta a mostrar a versão do Django; não recebe um dataset.
A mudança afeta a CLI e suas chamadas internas (dataset_version), não os arquivos salvos.

A preparação recusa um diretório version/split existente, mesmo incompleto.
Versões diferentes ficam separadas; run-id também deve ser diferente para
experimentos de versões diferentes. O manifesto registra exatamente a versão
pedida, que é conferida antes de validar ou executar.

Os caminhos legados datasets/development e datasets/final são preservados, sem
migração, exclusão ou reaproveitamento automático. Para usar os comandos novos,
regenerar explicitamente o conjunto no caminho versionado quando a coleta real
estiver autorizada. Não editar manualmente o review.html antigo.

Todo backend/var/ai_lab está ignorado pelo Git. Catálogos, enunciados completos,
revisões, respostas brutas e bancos locais não devem ser commitados ou publicados.
Somente fixtures pequenas, sintéticas ou revisadas podem entrar no repositório.

## Preparação e revisão por versão

```powershell
.\.venv\Scripts\python.exe manage.py prepare_ai_dataset --dataset-version cf-rating-v1 --split development --seed 42 --settings=core.settings_ai_lab_local
.\.venv\Scripts\python.exe manage.py validate_ai_dataset --dataset-version cf-rating-v1 --split development --settings=core.settings_ai_lab_local
```

A preparação realiza coleta pública Codeforces, não inferência. Use esses comandos
somente quando a coleta real estiver autorizada. O universo é um snapshot do
catálogo público, sem depender do histórico de usuários ou de produção.
Selecionar três itens em cada faixa 800–1100, 1200–1500, 1600–1900 e 2000–2400,
com semente fixa e até dois por contest. Falhas de parsing ficam registradas;
a seleção é refeita sobre candidatos elegíveis reduzidos, fornecendo substituições
reproduzíveis. Candidatos extras coletados podem não integrar a seleção final.
Falha de rede interrompe a coleta em vez de mudar a amostra silenciosamente.

review.html é um relatório local, privado e não versionado. O gerador extrai só
o texto de div.problem-statement, sem HTML completo da página, scripts, estilos,
analytics, navegação ou metadados externos. Texto-fonte, fórmulas, limites e
exemplos aparecem ao lado da entrada preparada, com chave, link original e hash.
Conteúdo externo é escapado e links são limitados ao domínio HTTPS do Codeforces.
O relatório indica que rating, tags, título e contest não entram no payload.

Conferir cada entrada contra a fonte antes de aprovar. Fórmulas desconhecidas
são preservadas como texto, sem apagar comandos. Diagramas e conteúdo incorporado
que não puderem ser representados fielmente ficam fora da primeira versão.
A revisão humana complementa os testes; não há aprovação automática.

Após conferir um item:

```powershell
.\.venv\Scripts\python.exe manage.py validate_ai_dataset --dataset-version cf-rating-v1 --split development --approve <CHAVE> --reviewer <NOME> --expected-hash <HASH> --settings=core.settings_ai_lab_local
```

Depois de revisar todos:

```powershell
.\.venv\Scripts\python.exe manage.py validate_ai_dataset --dataset-version cf-rating-v1 --split development --freeze --settings=core.settings_ai_lab_local
```

O congelamento verifica quantidade, quotas, referências, unicidade e hashes.
Texto alterado invalida revisão; conjunto alterado invalida execução. Não editar
referências para melhorar resultados. A preparação final procura desenvolvimento
congelado da mesma versão, antes da coleta. Os 60 finais são revisados/congelados
separadamente após o piloto; seus contests não se sobrepõem aos do desenvolvimento.

## Execução e ampliação do orçamento

Após congelar desenvolvimento, executar o baseline, sem APIs:

```powershell
.\.venv\Scripts\python.exe manage.py run_ai_benchmark --dataset-version cf-rating-v1 --classifier baseline --run-id baseline-v1 --settings=core.settings_ai_lab_local
```

O baseline estima rating pela mediana do desenvolvimento, sem estimar tags.
A versão `development-median-grid100-half-up-v2` arredonda a mediana para o múltiplo
de 100 mais próximo; empate exato sobe (850 → 900, 950 → 1000). A saída é um
inteiro na mesma grade dos modelos, sem truncar para os extremos. As referências
de desenvolvimento já são validadas entre 800 e 2400. Não ajustar a regra aos
erros do conjunto final. Execuções antigas permanecem preservadas e a nova regra
exige novo run-id. No piloto atual a mediana era 1600, portanto o MAE não muda.
Para inferência real, somente após autorização do ID e do teto:

```powershell
.\.venv\Scripts\python.exe manage.py run_ai_benchmark --dataset-version cf-rating-v1 --classifier gemini --model <ID_AUTORIZADO> --allow-model <ID_AUTORIZADO> --max-requests <TETO_TOTAL_AUTORIZADO> --run-id <EXECUCAO> --settings=core.settings_ai_lab_local
```

A configuração científica imutável registra provedor, modelo, prompt, prompt_hash,
dataset_hash e demais parâmetros científicos. Orçamento fica fora dela:

- request_count: chamadas consumidas, incluindo retries e tentativas interrompidas
  depois do incremento persistido. Nunca é zerado pela retomada.
- authorized_request_limit: teto total atualmente autorizado, persistido antes
  da primeira chamada ou antes de novas chamadas após ampliação.

Reexecutar o mesmo run-id com a mesma configuração e o mesmo teto é permitido,
mas um orçamento esgotado não avança. Após nova autorização explícita, repetir
exatamente o comando e aumentar apenas --max-requests: por exemplo, teto 2 -> 5
permite no máximo três chamadas adicionais, e não cinco. O aumento é salvo antes
de I/O. Teto menor que o anterior ou que request_count é rejeitado.

Atingir o teto encerra normalmente com itens pendentes, sem excedê-lo. A retomada normal
processa somente itens ainda sem resultado registrado; não reprocessa falhas
concluídas. Modelo, provedor, prompt, parâmetros ou dataset diferentes exigem novo run-id.
Arquivos de execução antigos que misturam orçamento à configuração não são
migrados automaticamente por este núcleo: preservar os arquivos e usar novo ID.

O lock impede uso simultâneo da mesma execução. Após encerramento forçado,
verificar que o processo terminou antes de remover manualmente um lock residual.
Não apagar lock ativo. Um crash não devolve requisições já contabilizadas.

Os relatórios mostram qualidade na interseção válida por tarefa, junto de
respondidas, válidas, cobertura, falhas e pendências. O baseline não remove F1
válido dos modelos. Latência é tempo total por item, incluindo retries e esperas;
não é inferência pura. Tokens são registrados quando retornados pelo SDK.

## TDD e critérios de verificação

### Recuperação explícita

`--retry-failures` atua somente sobre falhas transitórias já registradas: timeout,
rate limit e erro de servidor. Não inicia pendentes nem repete sucesso, erro de
validação/JSON, autenticação ou requisição inválida. É permitida uma recuperação
por item, dentro do teto total autorizado. `Retry-After` é preservado; uma espera
superior a 30 segundos mantém o item para retomada posterior. Sem orçamento,
não há chamada nem espera. O orçamento só pode crescer após nova autorização.

`attempt_history` preserva cada tentativa e sua reserva antes de I/O. Arquivos
antigos continuam legíveis; uma recuperação explícita preserva o registro legado
no histórico. Configuração científica continua imutável. Novas execuções usam
`max_attempts=1` para os dois provedores; uma execução antiga com política diferente
não deve ser retomada fingindo ter a política nova: usar identidade nova e
preservar os originais. O piloto Gemini já concluído não foi alterado.

Antes de I/O, o item também é reservado com `error=interrupted`. Se o processo
cair antes de salvar a resposta, o resultado é desconhecido: a chamada pode ter
sido consumida. A retomada não repete esse item e `--retry-failures` não o recupera
automaticamente; conferir os registros do provedor antes de decidir uma nova
execução autorizada. A quantidade de tentativas continua consumida. O histórico
conta cada falha registrada; em arquivos antigos sem eventos individuais, conta
somente os registros disponíveis, sem reconstruir categorias desconhecidas.

### Exportação e revisão antes da publicação

O modo de exportação do comando existente lê uma comparação salva, sem precisar
de chave, autorização de modelo, banco consultado ou chamada de inferência:

```powershell
.\.venv\Scripts\python.exe manage.py run_ai_benchmark --export-showcase <ID_COMPARACAO> --settings=core.settings_ai_lab_local
```

Exige a mesma configuração local explícita de SQLite para proteger o comando.
O destino padrão é privado: `var/ai_lab/exports/<ID_COMPARACAO>.json`.
`--snapshot-output` permite destino explícito; exportação não sobrescreve arquivo.
Opções de inferência não podem ser combinadas com exportação.

O envelope inclui schema_version e hash de integridade do conteúdo. A allowlist
exclui enunciados, catálogo, prompt completo, configuração privada, dados de
usuários, respostas brutas e logs HTTP. Justificativas são omitidas por padrão;
`--include-justifications` só as inclui para revisão explícita. Nunca há resumo
por outra IA. O JSON usa nome de arquivo igual ao ID da comparação na publicação.

Revisar conteúdo, métricas e diff antes de aprovar a cópia para
`api/ai_lab/published/<ID>.json` e seu commit. Apenas essa apresentação derivada é
exceção à regra de resultados reais fora do Git. Exportar não publica nem faz
commit. Comandos de execução, build e startup não exportam automaticamente.

### Design e interpretação

Experimento identificado por nome e badge de tamanho. Tabela ordenada por MAE,
com cinco colunas e explicações acessíveis; cobertura distingue falhas e
pendências. Mapa de calor usa MAE pareado por faixa oficial e escala compartilhada,
com N explícito e distinção entre zero e ausência de dados. Dispersão de um modelo
por vez mantém coordenadas e agrupa coincidências, sem códigos permanentes.
Detalhe é aberto por seleção, pode ser fechado por Escape e devolve foco ao ponto.
Metodologia e histórico ficam recolhidos. Explorar é a primeira aba e abre por
padrão, preservando os ícones de Codeforces, AtCoder e CSES na classificação.

### Comparação salva no Playground

A aba Benchmark consulta `GET /api/ai-lab/benchmarks` e
`GET /api/ai-lab/benchmarks/{id}`, ambos autenticados. São operações de leitura:
não coletam enunciados, não executam IA e não atualizam o banco.

O índice privado `backend/var/ai_lab/showcase.json` escolhe explicitamente quais
execuções entram em cada comparação. Exemplo estrutural (IDs ilustrativos):

```json
{"benchmarks":[{"id":"pilot-v1","label":"Piloto v1","version":"cf-rating-v1","split":"development","runs":["baseline-v1","modelo-v1"]}]}
```

No ambiente local explícito, `AI_LAB_USE_PRIVATE_RESULTS=True` permite leitura
de `backend/var/ai_lab`, ou da raiz privada `AI_LAB_RESULTS_ROOT`. Na configuração
normal, esse acesso fica desativado: a API lê somente snapshots em
`backend/api/ai_lab/published`, ou `AI_LAB_PUBLISHED_ROOT`. Não há fallback para
resultados privados em produção. Ausência de índice apresenta
estado vazio. Artefatos incompatíveis apresentam erro de leitura, sem executar
novamente o experimento. As execuções precisam compartilhar dataset e prompt;
baseline não tem prompt. A resposta usa campos explícitos, sem enunciados,
configuração privada ou resposta bruta. IDs e caminhos são validados.

O índice inicial local seleciona baseline e o Gemini consolidado já existentes.
Para disponibilizar outro modelo, executar seu lote autorizado e depois adicionar
o run-id ao mesmo índice. Não incluir uma execução de desenvolvimento numa
comparação final. Não commitar índice real, catálogos, enunciados ou respostas.
Em produção, somente os snapshots derivados aprovados acompanham o deploy;
a API não precisa dos datasets ou dos arquivos de execução privados.

Tabela e gráficos usam a comparação recalculada dos artefatos. MAE/F1 são pareados
na interseção válida; cobertura, falhas e pendências consideram o conjunto todo.
O gráfico de dispersão mostra todas as previsões válidas do modelo selecionado.
Proveniência de conclusão é conferida por hash e preserva falhas históricas,
separadas das falhas dos resultados atuais. Tentativas de geração não incluem
chamadas de metadados; consultar o ledger privado para a contagem total de API.

### Provedor Groq e autorização

O adaptador Groq atende somente `openai/gpt-oss-120b` e `qwen/qwen3.8-27b`.
Usa o mesmo prompt v1, JSON Schema estrito, nenhuma ferramenta, raciocínio `low`
e teto de 4096 tokens de conclusão. Parâmetros ficam na configuração científica.
Qwen envia `reasoning_format=hidden` para manter somente o JSON final; GPT-OSS
omite esse parâmetro, que não é aceito por ele. A configuração persistida e o
payload usam a mesma função de parâmetros. Documentação de contrato conferida em
2026-10-17: [Reasoning](https://console.groq.com/docs/reasoning) e
[Structured Outputs](https://console.groq.com/docs/structured-outputs). Essa
conferência pública não consome a chave e não substitui o primeiro teste real.
Não há SDK novo ou retry HTTP implícito. O comando mantém baseline como padrão.

Após autorização explícita do modelo e do orçamento, o mesmo comando pode usar
`--classifier groq`, `--model <ID>`, `--allow-model <ID>` e
`--max-requests <TETO_TOTAL>`, com `GROQ_API_KEY` privada e confirmação de free tier.
Os demais argumentos e a configuração local explícita permanecem obrigatórios
conforme a seção de execução acima. Não executar este exemplo sem autorização.

Novas execuções Gemini e Groq usam uma tentativa inicial por item. Autenticação,
requisição rejeitada ou quota interrompem o lote após salvar a falha, evitando
consumir o orçamento nos demais itens. Retomada normal processa apenas pendentes e
preserva teto e configuração. Respeitar a quota de tokens/minuto entre chamadas;
não há paralelismo nem aumento automático de orçamento ou troca de modelo.

### Verificações adicionais

Testes de Groq usam HTTP simulado para os dois modelos. Testes de resultados
usam fixtures sintéticas e cobrem autenticação, seleção explícita, mesma entrada,
leitura sem efeitos, falta de artefatos, hashes e saneamento da resposta. Testes
React cobrem tabela, gráficos, seleção, falha/vazio e as duas abas da página.
Os testes legados permanecem nos locais originais.

No Windows, caso o diretório temporário padrão apresente bloqueios, reservar uma
pasta de testes sob a raiz ignorada. Criar o pai de `--basetemp` antes da suíte.
Para Vitest, `TEMP`/`TMP` podem apontar para
`frontend/node_modules/.cache/test-temp`, com `--pool=threads --maxWorkers=1`. Nunca usar pastas
de dados reais como diretório temporário.

Seguir docs/TESTING.md: RED pelo comportamento esperado, GREEN mínimo, REFACTOR.
Testes novos ficam em api/tests/ai_lab; fixtures específicas ficam em conftest.py.
Não mover, renomear ou alterar testes antigos fora dessa pasta. test_commands.py
cobre a CLI e suas proteções. HTTP e respostas de modelos são simulados; testes
ORM usam core.settings_test e SQLite em memória, nunca produção.

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest api/tests/ai_lab --basetemp=var/ai_lab/pytest-fix -q
.\.venv\Scripts\python.exe -m pytest --basetemp=var/ai_lab/pytest-full-fix -q
.\.venv\Scripts\python.exe manage.py check --settings=core.settings_test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=core.settings_test
# Na raiz do repositório:
git diff --check
git status --short
```

Critérios: suíte direcionada e suíte completa verdes, contagem total sem redução,
checks do Django/schema e Git aprovados, e artefatos privados fora do Git.
Validar separadamente as etapas operacionais de revisão e autorização do piloto.

pytest limpa o diretório --basetemp. Reservar esses caminhos exclusivamente para
testes; nunca apontar para datasets, catalogs ou runs. Se houver artefatos a
preservar em um diretório de teste, escolher um novo diretório temporário antes
da execução. As verificações automáticas não exigem coleta ou inferência real.
