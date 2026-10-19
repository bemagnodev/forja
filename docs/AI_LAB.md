# AI Lab: experimentos locais e vitrine de resultados

Operação das novas runs `managed-v1`, prompts selecionáveis, recuperação
automática limitada e consulta de progresso: [roteiro de experimentos](AI_LAB_EXPERIMENTS.md).
As políticas de tentativa única descritas abaixo são históricas dos pilotos;
não se aplicam às novas runs gerenciadas. Os artefatos antigos são preservados.

Runbook para preparar datasets versionados, revisar entradas e executar o piloto
local. Baseline, Gemini/Groq, métricas gerais/por faixa, recuperação limitada,
API de leitura e interface estão implementados. Modelos Google e Groq;
OpenRouter e persistência Django ficam fora da entrega atual.

### Vitrine atual — três comparações finais

O índice `backend/api/ai_lab/published/index.json` seleciona e ordena somente:
classificação direta, classificação com rubrica e impacto da rubrica no Gemini.
As seis combinações usam os mesmos 60 problemas revisados. Resultados e limites
estão no [relatório A/B](AI_LAB_BENCHMARK_AB_RESULTS.md). Pilotos e testes
interrompidos foram preservados em `backend/api/ai_lab/archive`, fora da vitrine.

A interface mostra a cobertura de tags junto do F1 e, em **Técnica e prompt**,
as instruções completas A/B, taxonomia preenchida, versão, hash e opção de cópia.
São textos gravados nas runs, não o conteúdo atual do template. A e B são ambos
zero-shot; B usa rubrica. Enunciados e o prompt C não são publicados.

### Validação e publicação

Verificação local em 19/10/2026: 372 testes backend e 103 frontend aprovados,
build Vite e Django check aprovados. APIs e IA simuladas nos testes; nenhuma
chamada real para validar a entrega. O botão Refresh do Dashboard tem regressão
que verifica visibilidade e nova busca ao clicar. Restam 11 diagnósticos de
TypeScript anteriores, detalhados em [dívida técnica](AI_LAB_TYPESCRIPT_DEBT.md).
Build aprovado não substitui a checagem de tipos.

Antes de considerar a publicação conferida:

- Verificar com sessão autenticada a listagem e os três detalhes em
  `/api/ai-lab/benchmarks`: HTTP 200, 60 problemas e prompts A/B corretos.
- Conferir gráficos, prompts e carregamento de Explorar, fila e Contests em
  produção, sem solicitar classificações ou depender da pasta privada `var`.
- Conferir timeout do servidor/proxy para scraping e inferência síncronos.
- Manter backup privado do dataset congelado e das runs; snapshots sanitizados
  não substituem esses artefatos. Não publicar enunciados ou respostas brutas.

A mesclagem de metadados foi testada em SQLite, sem reproduzir concorrência real
de PostgreSQL. A avaliação do Gemini cobre 800–2400; aceitar 2500–3500 no produto
não comprova qualidade nessa faixa. O Prompt C permanece pausado.

### Histórico do piloto (arquivado)

Os snapshots arquivados registram `Experimento Codeforces 1`, com Gemini 3.5
Flash-Lite, GPT-OSS 120B, GPT-OSS 20B e baseline. O conjunto tem 12 problemas;
a interseção válida de rating tem 11 e a de tags tem 9. O GPT-OSS 20B teve
11 ratings válidos, 10 saídas de tags válidas e uma falha `provider_error` nas
12 tentativas autorizadas. O status HTTP específico dessa última falha não foi
preservado pelo adaptador; não atribuir automaticamente a quota ou a tamanho.

Qwen continua no teste parcial anterior: 6 tentativas, 2 respostas válidas,
4 falhas 429 e 9 pendências, por limitação de tokens de saída. Gemini 3.8 Flash
fica num ensaio interrompido separado: 2 tentativas, ambas `server_error`,
0 respostas válidas e 10 pendências. Nenhum dos dois é incluído na interseção
principal, que ficaria vazia com Gemini 3.8. Comparações têm denominadores
diferentes e não devem ter seus MAEs confrontados diretamente.

O piloto é exploratório. A mediana usa a regra v2 na grade de 100 pontos. O F1
da comparação principal usa as mesmas 9 questões válidas de tags nos três
modelos. A previsão `sorting` do GPT-OSS 120B e uma saída de tags do 20B foram
invalidadas, sem corrigir sinônimos. Mudanças nos números de modelos anteriores
decorrem da nova interseção, não de novas previsões. Não repetimos Flash-Lite
ou GPT-OSS 120B. Esta continuação consumiu 14 novas tentativas: 12 do 20B e 2
do Gemini 3.8; 10 tentativas autorizadas do Gemini 3.8 não foram consumidas.

MAE pareado em 11 itens: GPT-OSS 120B 327,3; Gemini 3.5 Flash-Lite 400,0;
baseline 436,4; GPT-OSS 20B 463,6. Cobertura de rating 12/12, 12/12, 12/12
e 11/12, respectivamente. O resultado do 20B não supera o baseline neste piloto;
não extrapolar essa observação para outros conjuntos ou modelos.

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
exclui enunciados, catálogo, configuração privada, dados de
usuários, respostas brutas e logs HTTP. Justificativas são omitidas por padrão;
`--include-justifications` só as inclui para revisão explícita. Nunca há resumo
por outra IA. O JSON usa nome de arquivo igual ao ID da comparação na publicação.

Prompts completos também são omitidos por padrão. Excepcionalmente, os dois
prompts A/B revisados e autorizados podem ser incluídos por `publish_prompts=true`
na entrada privada da comparação. O exportador exige versão e hash aprovados
em `results.REVIEWED_PROMPTS`, valida o texto registrado, elimina duplicatas e
exporta somente texto, versão, hash, nome e descrição da técnica. Não publica
configurações inteiras, nem inclui C ou exemplos privados automaticamente.

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
resultados privados em produção. `published/index.json` define seleção e ordem;
arquivos fora dessa seleção não são listados nem consultados pela API. Pastas
legadas sem esse índice continuam legíveis por compatibilidade. Uma seleção
vazia apresenta estado vazio. Artefatos selecionados incompatíveis apresentam
erro de leitura, sem executar novamente o experimento. As execuções compartilham
dataset; comparação de prompts diferentes exige `compare_prompts=true` explícito.
Baseline não tem prompt. A resposta usa campos explícitos, sem enunciados,
configuração privada ou resposta bruta. IDs e caminhos são validados.

O índice inicial local seleciona baseline e o Gemini consolidado já existentes.
Para disponibilizar outro modelo, executar seu lote autorizado e depois adicionar
o run-id ao mesmo índice. Não incluir uma execução de desenvolvimento numa
comparação final. Não commitar o índice privado real, catálogos, enunciados ou
respostas brutas. O índice público sanitizado é parte da apresentação versionável.
Em produção, somente os snapshots derivados aprovados acompanham o deploy;
a API não precisa dos datasets ou dos arquivos de execução privados.

Tabela e gráficos usam a comparação recalculada dos artefatos. MAE/F1 são pareados
na interseção válida; cobertura, falhas e pendências consideram o conjunto todo.
O gráfico de dispersão mostra todas as previsões válidas do modelo selecionado.
Proveniência de conclusão é conferida por hash e preserva falhas históricas,
separadas das falhas dos resultados atuais. Tentativas de geração não incluem
chamadas de metadados; consultar o ledger privado para a contagem total de API.

### Provedor Groq e autorização

O adaptador Groq atende `openai/gpt-oss-120b`, `openai/gpt-oss-20b` e `qwen/qwen3.8-27b`.
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

Testes de Groq usam HTTP simulado para os três modelos. Testes de resultados
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

## Explorar: classificação individual

As falhas de classificação incluem `detail` e um diagnóstico seguro: etapa,
código, modelo, plataforma, status HTTP externo quando conhecido e `request_id`
para localizar o registro do backend. Explorar permite copiar esses detalhes;
fila e Contests preservam o motivo e o identificador na notificação. Nenhum
corpo externo, enunciado, chave ou traceback entra nesse registro. Não há retry
automático. Falhas de busca e preparação acontecem antes da inferência.

AtCoder e CSES incluem exemplos públicos pareados de entrada/saída, com quebras
de linha preservadas; CSES lê as seções dentro de `.md`. HTML real consultado
para diagnóstico fica somente em `var/ai_lab`, fora do Git. Uma busca local
bem-sucedida não comprova acesso ao Codeforces a partir do Render.

A página oferece `gemini-3.5-flash-lite` (padrão), `openai/gpt-oss-120b` e
`openai/gpt-oss-20b`. Cada clique explícito pode executar no máximo uma chamada,
sem retry de inferência ou troca automática de modelo. A autenticação pode ser
renovada antes de a API processar a operação; isso não repete inferência concluída.
O provedor é resolvido pelo catálogo, não por parâmetro arbitrário do navegador.
Configurar `GEMINI_API_KEY` e `GROQ_API_KEY` no backend usando contas Free Tier.
O código não consulta faturamento nem garante o plano da conta pelo nome do modelo.

`api/ai_lab/explore.py` usa `product_classification_v1`, derivado do Prompt 1,
com contrato próprio em `api/ai_lab/product.py`: múltiplos de 100 entre 800 e
3500, sem truncamento. Taxonomia e adaptadores são compartilhados; a validação
do benchmark permanece em 800–2400, sem mudança em A/B ou nas previsões. O Gemini
foi escolhido no recorte 800–2400; sua qualidade em 2500–3500 **não foi avaliada**.
Nenhum dataset adicional dessa faixa foi criado nesta versão.

A entrada contém somente campos textuais do enunciado e marcadores de imagens; inclui
`constraints` de AtCoder/CSES quando disponível, mas não título/ID/rating/tags
oficiais ou estatísticas. Imagens não são enviadas como conteúdo multimodal nem
seus bytes são baixados; o produto não alega análise visual. Ao contrário
do conjunto congelado, a exploração é uma consulta individual sem revisão humana
prévia; seus resultados não são incorporados automaticamente ao benchmark.

Explorar usa `POST /api/ai-lab/problems/{id}/classify`. Cada clique explícito faz
uma nova chamada; não consulta cache de classificação, não salva no navegador e
não grava no banco. O resultado fica apenas no estado da tela. Selecionar modelo,
problema ou aba não executa inferência. Ctrl/Shift não tem função especial aqui.

Fila e contests mantêm `POST /api/problems/{id}/predict`, o cache persistido em
`platform_metadata.ai_rating/ai_tags/ai_reasoning` e o recálculo manual existente.
Novas previsões de produto usam Flash-Lite, o padrão já definido; outros modelos
são testados exclusivamente no Explorar. A rota do produto não aceita selecionar
um modelo experimental para sobrescrever a previsão global. Registros anteriores
sem modelo conhecido não são reatribuídos; não há limpeza ou migration. O cache
válido exige modelo, `ai_prompt_version`, `ai_prompt_hash`, `ai_rating_domain`
e estado visual conhecido. Previsões com outra versão/domínio não são reutilizadas;
somente um clique explícito pode gerar uma nova classificação. O domínio salvo é
`cf-rating-800-3500-grid100-v1`.

Questões com imagens podem receber uma estimativa textual válida. O produto
salva `ai_visual_status=unprocessed` junto da previsão. Fila, Contests e Explorar
mostram: “Esta questão contém imagens que não foram analisadas; a estimativa pode
ser menos precisa.” O aviso volta pelas APIs de fila/contests após recarregar e
ao reutilizar o cache. Explorar mostra o aviso, mas continua sem gravação.

Classificação de produto e atualizações de catálogo (CF, Gym, AtCoder, CSES) usam
`api/services/problem_metadata.py`: leem a linha atual com bloqueio e mesclam
somente os campos atualizados numa transação curta, após chamadas externas.
Isso preserva metadados oficiais, previsões e outros campos; nenhuma transação
do helper fica aberta durante scraping ou IA. Testes SQLite cobrem interleavings
determinísticos e preservação dos campos, não a semântica real dos bloqueios
PostgreSQL. Não foi usado banco de produção para validar concorrência.

Trocar modelo, plataforma ou problema limpa o resultado exibido. Controles de
seleção ficam bloqueados enquanto há requisição. A resposta identifica modelo e
os estados independentes de rating/tags. Explorar aproveita rating válido,
justificativa e tags oficiais conhecidas mesmo numa resposta parcial, com aviso
e quantidade de tags descartadas. Não corrige sinônimos. Rating inválido não é
truncado nem ganha delta fictício. O produto preserva sua previsão anterior se
receber rating/tags inválidos; a presença de imagens por si só não impede salvar
um resultado textual válido com aviso. A regra estrita do benchmark continua intacta:
uma tag desconhecida invalida sua tarefa de tags, sem invalidar rating válido.

Novas falhas de provedor registram categoria e `http_status` quando conhecido no
histórico privado. Timeout/legado podem não ter status. Não são registrados
corpos HTTP, credenciais ou URLs autenticadas; não se inventa status para erros
antigos. Na API, status/categoria seguros também aparecem na mensagem de erro
quando conhecidos. A vitrine distingue ausência de previsão de erro zero.
Não houve alteração de retry ou timeout nesta fase; essa decisão é do passo 2.

Na aba Benchmark, barras de MAE usam escala visual fixa 0–1000, com excesso
indicado e número integral preservado. F1 micro soma acertos/extras/omissões de
tags; não é porcentagem de problemas totalmente corretos. O denominador válido
de tags é mostrado abaixo da tabela. Essas mudanças não recalculam previsões.

## Avaliação em mais de um dia

Com a cota informada pelo usuário de 20 requisições/dia do Gemini 3.8 Flash,
60 itens exigem no mínimo três janelas de cota sem falhas e sem outros usos.
Planejar quatro dias dá margem operacional. Retomar o mesmo run-id preserva
dataset, prompt, parâmetros e tentativas; não recriar execução por dia nem somar
novamente resultados já concluídos. `--max-requests` é um teto acumulado, não
uma cota diária: novos tetos acumulados exigem orçamento previamente autorizado.
Falhas e recuperações consomem o teto. Não há agendamento automático nesta entrega.
Preservar as datas das tentativas; latência de dias diferentes não isola a
velocidade do provedor. O conjunto final de 60 ainda exige revisão/congelamento
e autorização própria; os pilotos de desenvolvimento não autorizam esse lote.
Validar separadamente as etapas operacionais de revisão e autorização do piloto.

pytest limpa o diretório --basetemp. Reservar esses caminhos exclusivamente para
testes; nunca apontar para datasets, catalogs ou runs. Se houver artefatos a
preservar em um diretório de teste, escolher um novo diretório temporário antes
da execução. As verificações automáticas não exigem coleta ou inferência real.
