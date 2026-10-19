# Revisão pré-commit e proposta de apresentação do AI Lab

Revisão inicial de 19/10/2026, seguida da implementação após o usuário aprovar
com “prossiga”. Não houve chamada de IA, commit, push, deploy ou migration.

## Escopo e evidências

Revisados o diff pendente de resultados/runner/adaptadores/rotas, os arquivos
novos de Explorar e merge de metadados, a página Benchmark e os quatro snapshots
de 60 problemas. MAE, proporção dentro de ±200 e F1 foram recalculados de forma
independente a partir das previsões sanitizadas. Hashes dos snapshots e chamadas
acumuladas/proveniência também foram conferidos. Nenhuma divergência encontrada.

Essa leitura não é uma auditoria exaustiva de todos os 50 arquivos pendentes.
O diff também inclui sincronização, cache do produto e parser compartilhado,
anteriores à última entrega de resultados. Não agrupar tudo sob um único commit
de “gráficos”. As últimas suítes aprovadas foram 315 testes backend e 83 frontend;
não foram repetidas nesta rodada de revisão sem mudanças de comportamento.

## Pontos para corrigir antes de fechar a apresentação

1. A listagem publicada em `results.list_snapshots` descobre todos os JSONs por
   glob e os ordena pelo nome do arquivo. A tela abre no primeiro elemento.
   Isso mistura pilotos, testes interrompidos e resultados finais, sem curadoria
   nem ordenação editorial. Uma lista explícita deve definir as três comparações
   visíveis e sua ordem; arquivos arquivados ficam fora do diretório consultado.
   Não resolver somente escondendo opções por nome no React.
2. `BenchmarkResults` mostra letras/versões técnicas, como `classification_v1`.
   O nome legível da estratégia deve vir de metadados de apresentação e manter
   versão/hash como informação técnica. Não renomear runs, arquivos de prompt
   ou identificadores internos para alterar títulos.
3. A tabela mostra cobertura de rating; a cobertura de tags está recolhida nos
   detalhes. Mostrar a cobertura de tags também junto do F1, em texto secundário
   ou ajuda, para evitar impressão de que toda resposta entrou na métrica.
   Não é necessário adicionar outra coluna principal.
4. A página não explica a escolha do modelo da terceira comparação nem por que
   seus números diferem da primeira. Informar: escolhido pelo menor MAE em A,
   cobertura mínima 57/60; terceira comparação pareada usa todos os 60 ratings
   válidos de Gemini, enquanto a comparação entre modelos usa 59. Todas as
   candidatas passaram pelo corte; não houve seleção oportunista de subconjunto.
5. O texto de latência mistura políticas antigas e atuais. Em `managed-v1`, a
   medição da tentativa começa depois da espera de cadência; não inclui os 60s
   entre chamadas nem o tempo de pausa entre retomadas. Corrigir a explicação
   para as comparações finais; não tratar o campo como duração total do lote.

Não foram identificados nesta rodada indícios de vazamento de chaves/enunciados
nos snapshots finais ou incorreção das métricas verificadas. Isso não equivale
a comprovar toda a segurança do diff pendente, nem bloqueio PostgreSQL por
testes SQLite. A revisão de sincronização/merge deve permanecer separada.

## Decisão confirmada pelo usuário

Arquivar Gemini 3.8 e Qwen fora da vitrine, preservando seus arquivos e histórico.
Não excluir definitivamente suas execuções. Os pilotos anteriores e a comparação
A/B isolada do GPT-OSS 20B também devem permanecer preservados, fora da seleção
final. A organização física ainda não foi executada.

## Desenho aprovado

Três títulos de apresentação:

1. **Classificação direta — comparação de modelos**.
2. **Classificação com rubrica — comparação de modelos**.
3. **Impacto da rubrica — Gemini Flash-Lite**.

Explicar “zero-shot” como classificação sem exemplos. Tanto A como B são
zero-shot; B acrescenta critérios de avaliação e referências de dificuldade.
Não apresentar zero-shot e rubric prompting como categorias mutuamente exclusivas,
nem afirmar que B é few-shot. O nome rubric prompting descreve a estratégia;
o teste compara dois prompts completos e não isola causalmente cada instrução.
B também acrescenta a orientação de considerar a solução viável mais simples.

Bloco recolhível **Técnica e prompt**, com explicação curta e instruções completas:

- Exibir o texto efetivamente usado na run, com taxonomia expandida, versão e
  hash validados. Não ler silenciosamente o template atual no momento da página.
- Exibir uma única cópia por prompt, mesmo quando três modelos o compartilham.
- Na terceira visão, permitir alternar entre Classificação direta e Com rubrica.
- Botão para copiar texto; conteúdo como texto, sem interpretar HTML/Markdown
  do prompt como conteúdo executável.
- Explicar que esse bloco era a instrução de sistema; cada enunciado preparado
  era enviado separadamente. Não publicar enunciados ou respostas brutas.

A solicitação aprovada autoriza a publicação de A/B revisados; a regra
histórica de não publicar prompts deve ser atualizada especificamente para eles,
sem tornar automática a publicação de C ou de exemplos privados. Não copiar
configurações inteiras das runs para os snapshots. Usar campos explícitos para
os prompts revisados; novas estratégias exigem revisão própria.

Sem painel de administração, novo banco, novas inferências, novo sistema de
experimentos ou refatoração ampla. O AI Lab atual tem Explorar com uma chamada
por classificação e sem persistir previsão global, mais uma vitrine de resultados
salvos. As métricas não alteram automaticamente o modelo ou prompt do produto.

## Validação proposta em TDD

1. RED para seleção/ordem explícita e exclusão dos arquivos arquivados da
   listagem/consulta da vitrine; GREEN com curadoria simples. Preservar históricos.
2. RED para nomes corretos nas três comparações e explicação do critério do
   modelo selecionado, sem alterar run IDs, métricas, hash do dataset ou previsões.
3. RED para exportação somente de A/B revisados, igualdade do texto/hash com o
   prompt original, ausência de exemplos/enunciados e compatibilidade dos
   snapshots legados; GREEN com allowlist explícita de campos.
4. RED para abrir/alternar/copiar prompt sem disparar inferência, mostrar cobertura
   de tags junto do F1 e explicar corretamente a duração; GREEN com ajustes locais.
5. Executar suítes pertinentes e completas, revisar os três snapshots e a página
   real. Depois organizar commits pequenos por comportamento. Sem commit nesta fase.

## Limitações que devem continuar claras

Uma rodada, 60 problemas textuais públicos; sem significância estatística ou
prova de generalização. Prompts A/B, modelos e configurações de geração formam
as combinações avaliadas: GPT-OSS usa reasoning low e teto4096; Gemini conserva
defaults do provedor além do schema. Não é comparação com orçamento de raciocínio
igualado. Sem chamadas novas apenas para “corrigir” uma conclusão desfavorável.

## Implementação e validação

`published/index.json` seleciona somente as três comparações, na ordem proposta.
O leitor rejeita consulta de IDs fora da seleção. Pastas legadas sem índice
mantêm compatibilidade. Os quatro snapshots anteriores foram movidos para
`api/ai_lab/archive`, com verificação de igualdade byte a byte. O índice privado
foi curado na mesma ordem, com backup e lista arquivada fora do Git.

A reexportação mudou apenas apresentação/metadados e incluiu os prompts A/B.
Dataset, previsões, interseções, bandas, métricas e contadores permaneceram
iguais aos backups. O exportador verifica os hashes aprovados, usa o texto
registrado e elimina duplicatas. Não publica configuração inteira ou exemplos.

Foi adicionado o componente `PromptDetails`, com conteúdo recolhível, alternância,
cópia e texto escapado. Tags válidas ficam junto do F1. A terceira visão explica
critério e denominadores. A explicação de latência distingue tentativa de resposta
de duração total do lote. Ícones e primeira aba Explorar foram preservados.

TDD: RED observado para curadoria, publicação de prompt, texto/cópia e cobertura;
GREEN nos testes específicos. Suítes completas: 322 backend e 85 frontend
aprovados. A primeira execução de frontend teve timeout em um teste de senha
não alterado; a repetição sem a carga paralela passou, sem relaxar verificações.
Build e lint dos arquivos alterados aprovados. Conferência na página local
incluiu nomes/ordem, cobertura, prompt completo, cópia e alternância A/B.

O servidor auxiliar de QA, iniciado anteriormente sem reloader, precisou ser
reiniciado para carregar o leitor novo. Foi usado o mesmo SQLite de revisão,
sem migration, alteração de banco de produção ou chamada de modelo.
