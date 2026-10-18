# Benchmark de classificação de problemas

> Histórico do plano inicial. A referência atual de escopo e execução é
> [AI Lab — revisão geral](2026-10-17-ai-lab-revisao-geral-plan.md), que substitui
> as decisões conflitantes abaixo sobre provedores, persistência e apresentação.

Data: 2026-10-17
Estado: núcleo do Marco 1 implementado; 12 enunciados revisados e piloto real
Gemini 3.5 Flash-Lite concluído. Marcos 2 e 3 pendentes.
Operação e evidências TDD: [AI_LAB.md](../AI_LAB.md).
Próxima sequência proposta, ainda sujeita à aprovação:
[comparação de modelos e demonstração](2026-10-17-ai-lab-multi-model-benchmark-plan.md).

Implementado no Marco 1: os comandos prepare_ai_dataset, validate_ai_dataset e
run_ai_benchmark, seleção/preparação local, prompt v1, baseline, métricas,
adaptador Gemini com testes simulados e retomada por arquivos. Revisão dos textos
e piloto real concluídos; resultados permanecem privados. Groq, OpenRouter,
persistência Django, API e frontend não estão implementados; seguem nos Marcos 2/3.

## Objetivo e escopo

Evoluir o AI Playground da Forja para comparar estimativas de rating e tags de
problemas do Codeforces. Rating é o objetivo principal. Entregar evidência
reproduzível, erros inspecionáveis e uma demonstração baseada em resultados salvos.

Implementar em três marcos: núcleo e piloto, benchmark, showcase. Manter três
provedores gratuitos no escopo, cada um com adaptador próprio e testes separados.
Preservar o teste individual existente. Contest Review, ML, cache genérico,
execução de lotes pelo navegador e gráficos adicionais ficam para depois.

## Marco 1 — Núcleo e piloto

Entregar seleção reproduzível e revisão dos 12 problemas de desenvolvimento
(três por faixa), preparação de entrada, prompt v1, contrato comum, baseline,
métricas e execução local em arquivos. Não depender dos novos models Django.
Usar baseline local e ao menos um adaptador validado para o piloto; os outros
adaptadores podem ser adicionados neste marco, cada um em ciclo TDD independente.
A conclusão do Marco 2 exige os três provedores efetivamente disponíveis.

Ordem de comportamentos, todos por RED -> GREEN -> REFACTOR:

1. Fidelidade de coleta: testes com fixtures pequenas verificam fórmulas,
   restrições, limites, listas, exemplos e rejeição de CAPTCHA/HTML incompleto.
   Observar falha relevante antes de corrigir parser ou validador. Refatorar
   mantendo os testes existentes das outras plataformas. Não apagar comandos
   matemáticos desconhecidos; preservar representação ou exigir revisão.
2. Seleção: testes com catálogo simulado verificam mesma lista para o mesmo
   snapshot/seed, três itens por faixa, limites por contest, reservas e erro por
   insuficiência. Implementar sorteio separado da rede e depois simplificá-lo.
3. Preparação e revisão: testes verificam allowlist, ausência de rating/tags/URL
   no payload, preservação matemática e bloqueio de itens não revisados ou com
   hash alterado. Implementar barreira antes de permitir chamadas de modelos.
4. Contrato e prompt: testar domínio de rating, taxonomia, saída inválida e
   registro do texto/hash do prompt antes de implementar validação e carregamento.
5. Baseline e métricas: testar mediana e exemplos calculados manualmente antes
   de implementar MAE, percentual dentro de +/-200 e micro-F1. Ajustar baseline
   somente nos 12 itens de desenvolvimento; não usar referências finais.
6. Execução local e adaptador inicial: testar com provedor mockado payload sem
   ferramentas, falhas e retry limitado; implementar o mínimo. Não criar cache
   genérico. Preservar resultados por execução/item em arquivos locais.

Piloto real separado do pytest: coletar, revisar os 12 contra a fonte, congelar
essa divisão e só então chamar o modelo. Ajustes do prompt usam apenas esses
12 problemas; registrar versões e congelar o prompt antes do benchmark final.

Pronto: 12 itens revisados, manifesto reproduzível, piloto local inspecionável,
baseline e métricas corretos, testes direcionados e suíte completa passando.
Não aplicar migrations em produção durante o piloto.

## Marco 2 — Benchmark

Entregar conjunto final revisado de 60 problemas, três provedores/modelos
estritamente gratuitos, persistência Django, idempotência, retomada e comparação.

1. Finalizar seleção após o piloto: testes verificam 15 itens por faixa, contests
   distintos dos 12 de desenvolvimento, reservas e congelamento independente.
   Implementar sem flexibilizar critérios silenciosamente. Revisar os 60 antes
   de qualquer inferência nesses itens, mesmo com modelos já usados no piloto.
2. Cada adaptador recebe seu próprio ciclo RED/GREEN/REFACTOR: payload, parsing,
   validação, autenticação, erros recuperáveis, retry e ferramentas desativadas.
   Não aceitar testar só um provedor e assumir equivalência dos demais.
3. Persistência: testes ORM verificam separação entrada/referência, histórico
   imutável da configuração e unicidade execução/item. Adicionar os modelos em
   seção identificada de api/models.py e migrations aditivas. Testes sempre em
   SQLite em memória. Modularização dos models será refatoração independente.
4. Retomada: reproduzir interrupção e retomada em RED, depois persistir progresso
   por item. Não repetir sucessos; falhas só são reprocessadas por ação explícita,
   registrando tentativas. Impedir dois processos de executar o mesmo item da
   mesma execução simultaneamente. Não reutilizar cache legado nem sobrescrever
   previsões usadas pelo produto. Alterar configuração científica cria nova
   execução; ampliar apenas orçamento autorizado não muda a experiência.
5. Comparação: testes com cobertura desigual verificam interseção válida e
   denominadores, inclusive interseção vazia. Implementar relatório que mostre
   simultaneamente qualidade, quantidade respondida, cobertura e falhas.

Após validação/revisão/congelamento dos 60, verificar acesso gratuito de cada
provedor usando somente desenvolvimento e iniciar o lote final. Bugs encontrados
voltam a RED com reprodução isolada. Não ajustar prompt usando o resultado final
sem identificar uma nova experiência exploratória.

Pronto: três provedores executados, 60 itens congelados, resultados e falhas
persistidos, retomada demonstrada, comparação reproduzível e suíte completa verde.
Falhas de disponibilidade não podem ser ocultadas como benchmark concluído com
três provedores; registrar bloqueio e resultados parciais.

## Marco 3 — Showcase

API autenticada e frontend consultam resultados previamente salvos. Não disparar
lotes ou inferências ao carregar a tela. Manter fluxo individual existente.

Escopo obrigatório: tabela comparativa, cobertura/falhas, gráfico previsto versus
oficial e detalhe por problema. Filtros simples por conjunto e execução; estados
vazio, carregando e erro. MAE por modelo, erro por faixa e outras telas/gráficos
são opcionais após essa entrega funcionar.

RED API: autenticação, paginação, detalhe sem texto completo e rejeição de
comparação de versões de conjuntos diferentes. GREEN: router de leitura.
RED frontend: seleção de execuções, métricas corretas, denominadores explícitos,
falhas e abertura de detalhe; mockar HTTP. GREEN: componentes mínimos.
REFACTOR: extrair apenas componentes usados, sem recalcular métricas no cliente.
Testar dados, rótulos e tabela acessível; não detalhes internos de SVG.

Detalhe mostra previsão, referência, erro, justificativa e proveniência não
sensível; não publicar enunciado completo, catálogo ou payload com enunciado.
Na interface usar “Justificativa da classificação”, sem prometer acesso ao
raciocínio interno do modelo. Inspeção do texto completo fica local e privada.

Pronto: demonstração sem API de IA ao vivo, backend e frontend com suítes completas
verdes, build válido e dados de resultados disponíveis sem depender de disco efêmero.

## Três provedores e contrato comum

Regra do usuário: nenhuma chamada real de modelo, nem preflight, sem autorização
explícita prévia do provedor, ID e quantidade máxima de chamadas incluindo retry.
Ter API key configurada não é autorização. Comando padrão deve ser baseline local;
modelo real exige ID autorizado e teto explícito. Não executar automaticamente
modelos ao verificar disponibilidade de chaves. Confirmar free tier da conta antes.

Google/Gemini e Groq são dois provedores candidatos. Dois modelos Gemini mais
um Groq NÃO satisfazem três provedores. Um terceiro provedor e respectivo modelo
gratuito devem ser selecionados e validados antes da execução final do Marco 2.
Registrar como decisão pendente; não inventar disponibilidade nem trocar para
opção paga. Confirmar IDs, free tier, quotas e saída estruturada em fontes oficiais
e na conta no momento da implementação. Nenhum fallback automático pago.

Contrato mínimo em contracts.py: entrada preparada, configuração explícita e
resultado com rating, tags, justificativa opcional, status/erro, duração e tokens
quando fornecidos. Usar funções e tipos concretos; não construir framework de
plugins, hierarquias de ML ou interfaces vazias. Cada provedor tem módulo próprio,
mesmo contrato e testes próprios em test_classification.py (grupos separados).

Retry: no máximo três tentativas totais para timeout, 429 ou 5xx recuperável,
respeitando Retry-After e pausa limitada. Se a espera exigida exceder o limite
configurado, registrar falha retomável em vez de tentar cedo. Não repetir erro
de autenticação, validação ou parsing automaticamente. Registrar todas as tentativas.

## Domínio de rating e normalização de tags

Seleção e saída esperada: rating inteiro, múltiplo de 100, entre 800 e 2400
inclusive. Booleano, float e string numérica não contam como inteiro válido.
Valor numérico fora da faixa recebe out_of_domain; formato inválido recebe
invalid_output. Preservar resposta original em armazenamento local privado.
Nunca truncar, arredondar ou substituir automaticamente por 800/2400.

Taxonomia: lista canônica oficial de tags Codeforces, versionada, com fonte e
data registradas antes do piloto e mantida igual para todos os provedores.
A lista pode orientar o prompt; tags de referência do problema não entram nele.

Normalização única para referências e previsões:
- Exigir array de strings; rejeitar null, elementos não textuais e string vazia.
- Remover espaços nas pontas, converter letras para minúsculas e colapsar espaços
  internos consecutivos para um espaço. Não remover pontuação significativa.
- Exigir correspondência exata com a taxonomia após essas operações.
- Deduplicar tags idênticas e ordenar para armazenamento/comparação como conjunto.
- Exigir ao menos uma tag válida, sem limite artificial de três na primeira versão.
- Tag desconhecida invalida a saída de tags inteira; registrar valor e motivo,
  sem descartá-la para melhorar o F1. Nenhum sinônimo, tradução, fuzzy matching
  ou mapeamento automático (por exemplo, “dynamic programming” não vira “dp”).

Validar rating e tags independentemente. Uma resposta pode ter rating válido e
tags inválidas; registrar ambos os estados e calcular cobertura por tarefa.
Referências desconhecidas exigem revisão do item antes do congelamento.

## Seleção, origem e fidelidade dos dados

Os três comandos usam --version, com default explícito cf-rating-v1, e caminhos
datasets/<version>/<split>/. O manifesto registra exatamente a versão solicitada;
validação e benchmark conferem esse campo. Versão tem formato seguro, sem '..',
barras, caminho absoluto ou caracteres inválidos. Não sobrescrever version/split
existente. Final exige desenvolvimento congelado da mesma versão antes de coletar.
Artefatos legados datasets/development e datasets/final são preservados, sem
migração automática; regenerar explicitamente no caminho versionado quando houver
autorização para coleta. Nunca editar o relatório antigo para ajustar o gerador.

Origem: snapshot local do catálogo público do Codeforces via cliente existente,
sem depender dos problemas presentes no banco/histórico de usuários da Forja e
sem acessar produção. Identidade de Problem pode ser reaproveitada no Marco 2,
mas não determina elegibilidade nem altera metadados de treino existentes.

Faixas inclusivas: 800-1100, 1200-1500, 1600-1900, 2000-2400. Desenvolvimento:
3 por faixa; final: 15 por faixa. Exigir rating/tags de referência e contest
identificável; excluir interativos, output-only e conteúdo não representável.
Deduplicar por contestId/index e registrar duplicações conhecidas entre fontes.

Ordenar candidatos por chave pública e usar gerador local com seed 42. Registrar
snapshot/hash, versão do algoritmo e parâmetros. Sortear desenvolvimento primeiro,
no máximo dois itens por contest; registrar reservas ordenadas por faixa.
Após o piloto, sortear final com a mesma política, excluindo todos os contests
usados no desenvolvimento. Congelar manifestos separados; substituições por
falha de coleta/revisão mantêm faixa, limite por contest e disjunção entre divisões.
Nunca substituir por desempenho do modelo. Se faltarem candidatos, abortar com
déficit explícito. Mostrar distribuição de tags como diagnóstico de diversidade.

Entrada permitida: descrição, entrada/saída, limites, exemplos e notas necessárias.
Excluir título, ID, índice, URL, contest, rating, tags, editoriais e estatísticas.
Nenhuma ferramenta de busca, navegação ou execução é oferecida aos modelos.
Remover identificação não elimina possível memorização de enunciados públicos.

Qualidade por divisão: collected -> validated -> reviewed -> frozen. Primeiro
validar e revisar os 12; depois do piloto validar e revisar os 60 separadamente.
Conferir cada texto preparado contra a fonte: fórmulas, restrições, limites e
exemplos. Registrar revisor, data e hash. Texto alterado perde aprovação anterior.
Campos essenciais ausentes, imagem necessária ou fórmula sem preservação de
significado bloqueiam item; ausência de nota opcional não. Testes usam fixtures
revisadas independentemente do parser, incluindo CAPTCHA com HTTP 200, múltiplos
exemplos e LaTeX. Revisão humana complementa testes; não garante equivalência
semântica automática. Runner recusa divisão não congelada ou hash alterado.

Enunciados completos e catálogos NÃO serão commitados nem publicados, inclusive
por endpoints, exportações do showcase ou payloads de erro. Apenas fixtures
pequenas e revisadas podem entrar no Git. Snapshots e respostas brutas ficam em
armazenamento local privado ignorado pelo Git; publicar somente resultados
necessários sem reproduzir os textos completos. Nenhuma chave ou banco entra no Git.

## Métricas e comparações sem viés de cobertura

MAE de rating é principal; percentual dentro de +/-200 inclusive é complementar.
Micro-F1 de tags: 2TP/(2TP+FP+FN), somando contagens sobre conjuntos normalizados.
Denominador zero ou interseção vazia retorna indisponível, nunca zero inventado.
Baseline: mediana dos ratings de desenvolvimento, arredondada ao múltiplo de 100
mais próximo, com empate exato para cima, sem truncamento automático; saída inteira
na mesma grade dos modelos. Regra `development-median-grid100-half-up-v2`, sem usar
referências do conjunto final; preservar execuções da versão contínua anterior.

Para cada tarefa (rating/tags), calcular qualidade sobre a mesma interseção de
itens válidos entre as execuções selecionadas. Mostrar tamanho/identidade desse
subconjunto e, simultaneamente, por execução sobre os N itens do conjunto:
- quantidade respondida: resposta recebida, mesmo inválida;
- quantidade válida e cobertura válida = válidas/N;
- taxa de falha = itens sem resultado válido/N, discriminando transporte,
  saída inválida, fora do domínio e falhas de validação da tarefa;
- quantidade pendente separada: não chamar execução incompleta de resultado final.
Em progresso, identificar taxa como provisória e calcular falhas observadas/N,
sem contar pendentes como falhas concluídas. Latência mediana de chamadas com
resposta, identificando retries/esperas; manter essa população explícita.

Falhas nunca viram rating zero ou lista vazia válida. Não ranquear só pelo MAE:
qualidade condicional e cobertura devem permanecer juntas na tabela e no relato.
A amostra balanceada é exploratória e não representa automaticamente a frequência
real de dificuldades dos usuários. Tags oficiais são referência incompleta.

## Estrutura inicial de arquivos

Estrutura proposta, criada somente conforme a responsabilidade for implementada.
Não mover/renomear módulos ou testes existentes. Nenhum novo app Django é necessário.

```text
backend/api/
  models.py                         # seção AI Lab: novos modelos no Marco 2
  api.py                            # inclui router de leitura no Marco 3
  ai_lab/
    __init__.py
    contracts.py                    # tipos e validação, sem abstrações de ML
    dataset.py                      # catálogo, seleção, preparo e revisão
    classification.py               # prompt, baseline e despacho explícito
    metrics.py                      # métricas e comparação puras
    runner.py                       # execução local; persistência/retomada no M2
    review.py                       # relatório privado com texto da problem-statement
    prompts/classification_v1.txt    # instruções separadas e versionadas
    providers/
      __init__.py
      gemini.py
      groq.py
      <terceiro_provedor>.py         # criar só após escolha real
    router.py                       # M3: schemas e consultas de resultados
  management/commands/
    prepare_ai_dataset.py
    validate_ai_dataset.py
    run_ai_benchmark.py
  tests/ai_lab/
    __init__.py
    conftest.py                      # fixtures específicas do AI Lab
    test_dataset.py
    test_classification.py           # testes distintos por adaptador
    test_metrics.py
    fixtures/codeforces/             # pequenos HTMLs revisados
backend/var/ai_lab/                   # privado, ignorado pelo Git
  catalogs/<snapshot-id>.json
  datasets/<version>/<split>/        # manifesto, raw, prepared e revisão
  runs/<run-id>/                     # piloto local e exportação privada
frontend/src/
  pages/AILab.tsx                    # mantém fluxo existente
  features/ai-lab/
    api.ts
    types.ts
    ExperimentComparison.tsx        # tabela, cobertura/falhas e estados
    RatingScatterChart.tsx
    PredictionDetail.tsx
    # testes co-localizados .test.ts/.test.tsx
```

Os três arquivos de teste são o ponto inicial. Acrescentar test_runner.py,
test_models.py ou test_api.py apenas quando os Marcos 2/3 justificarem essas
responsabilidades; nunca migrar testes legados para a nova pasta. Dividir módulos
crescentes quando necessário, sem diretórios vazios para uso futuro.
Novos models permanecem em api/models.py. Não criar ai_lab/models.py ou importação
indireta dos models neste escopo. API consulta registros persistidos, não disco
efêmero do deploy. Arquivos do Marco 1 são artefatos locais; importação no Marco 2
preserva IDs, hashes e proveniência, sem criar duas fontes concorrentes de verdade.

## TDD, isolamento e commits futuros

Seguir docs/TESTING.md: AAA, RED pelo motivo esperado -> GREEN mínimo -> REFACTOR.
Registrar evidência RED/GREEN por comportamento. Testes que caracterizam algo
existente não precisam ser artificialmente quebrados. HTTP sempre mockado;
testes ORM usam core.settings_test e SQLite em memória. Testes frontend usam
Vitest/Testing Library, userEvent e limpeza de mocks, conforme guia.

Reorganização estritamente aditiva: não mover, renomear ou remover testes
existentes. Registrar lista e contagem coletada antes do primeiro marco e
comparar a cada marco, preservando testes anteriores e acrescentando novos.
Executar testes direcionados durante os ciclos e suíte completa do backend em
cada marco; também suíte completa do frontend e build no Marco 3. Se alterações
anteriores afetarem frontend, executar sua suíte naquele marco também.
Validar check do Django, migrations locais quando aplicável e git diff --check.
Migrations de dados, se surgirem, exigem teste de transição com MigrationExecutor;
auditar dados antes de constraints sobre tabelas existentes conforme o guia.

Na futura execução, organizar commits pequenos e reversíveis por comportamento:
por exemplo, fidelidade de parsing; seleção; contrato/prompt; métricas/baseline;
cada adaptador separadamente; persistência; retomada; comparação; API; UI.
Não acumular um único commit por marco. Cada commit preserva testes verdes;
registrar ciclos RED/GREEN no relatório sem commit de estado quebrado.
Não reescrever histórico nem incluir dados privados ou mudanças alheias.
Nesta revisão documental não realizar commit, push ou implementação.

## Comandos reais e proteção do ambiente

Os três comandos do Marco 1 já foram implementados por TDD. Os exemplos abaixo
descrevem a CLI local existente; nenhuma chamada real está implícita no plano.
Exigir --settings explícito apontando para core.settings_ai_lab_local,
nunca core.settings_test.
A configuração real não herda credenciais de banco de produção: exige arquivo
SQLite local por caminho absoluto explícito, sob diretório privado do laboratório.
Sem configuração, com PostgreSQL/Supabase, caminho fora da raiz local permitida
ou settings de teste, abortar antes de conectar, coletar ou chamar provedores.
Testes dessas proteções não devem abrir conexão real para provar a rejeição.

```powershell
# Futura interface; configuração local e caminho SQLite validados antes de I/O.
python manage.py prepare_ai_dataset --version cf-rating-v1 --split development --seed 42 --settings=core.settings_ai_lab_local
python manage.py validate_ai_dataset --version cf-rating-v1 --split development --settings=core.settings_ai_lab_local
python manage.py run_ai_benchmark --version cf-rating-v1 --split development --classifier baseline --run-id baseline-v1 --settings=core.settings_ai_lab_local
# Somente após autorização explícita do modelo/teto e conferência de free tier:
python manage.py run_ai_benchmark --version cf-rating-v1 --split development --classifier gemini --model <ID_AUTORIZADO> --allow-model <ID_AUTORIZADO> --max-requests <TETO_TOTAL> --run-id <RUN_ID> --settings=core.settings_ai_lab_local
# Retomar: repetir mesmo run-id/configuração, com teto igual ou maior autorizado.
```

Configuração científica permanece imutável: provedor, modelo, prompt, prompt_hash,
dataset_hash e demais parâmetros científicos. Guardar fora dela request_count
(consumo incluindo retries) e authorized_request_limit (teto total autorizado).
Criar/persistir o teto antes de qualquer chamada. Na retomada, teto igual é aceito;
teto maior é salvo antes de novas chamadas; teto menor que o anterior ou o consumo
é rejeitado. Não zerar request_count. Incrementar e persistir antes de cada I/O,
inclusive retry; crash não devolve orçamento. Teto esgotado encerra incompleto,
sem exceder o limite. Não reprocessar falhas concluídas neste marco.

review.html é gerado somente na área privada versionada, usando texto legível
extraído de div.problem-statement ao lado da entrada preparada, com chave, link
original e hash. Excluir scripts, estilos, CSRF, analytics, navegação e metadados
da página; escapar conteúdo externo e restringir URLs. Preservar fórmulas como
texto. Explicitar que rating, tags, título e contest não integram o payload.
Não publicar/commitar o relatório e não modificar artefatos legados existentes.

O Marco 1 funciona com arquivos, sem exigir migrations novas. No Marco 2 aplicar
migrations apenas no SQLite local explicitamente configurado. Nenhuma migration
em produção durante o piloto. Deploy e importação para o showcase são operações
posteriores explícitas, fora dos comandos de piloto/teste, sem transferência dos
catálogos ou enunciados completos para publicação. Pytest continua usando somente
settings_test; nunca confundir testes isolados com coleta/inferência real.

## Pendências e limitações registradas

Escolher terceiro provedor gratuito e validar contas/quotas antes do benchmark.
Não substituir três provedores por três modelos de dois provedores. Confirmar
disponibilidade real antes de prometer conclusão. Não há garantia de ausência
de memorização, superioridade universal ou transferência para Gyms/CSES.
Uma execução por modelo não mede variabilidade entre repetições. Futuras versões
podem avaliar novos prompts, dados e ML, em experiências separadas e identificadas.
