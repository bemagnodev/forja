# Revisão visual consolidada — 29/10/2026

Estado final solicitado pelo usuário:

- Hovers clareiam o cinza, sem brilho ou borda colorida e sem mudar o texto para vermelho.
- Na Fila, apenas o título clicável recebe sublinhado ao passar diretamente sobre ele; faixa lateral de prioridade removida.
- Contests recentes e Questões recentes no Dashboard mantêm o fundo do painel; somente os itens internos reagem ao hover.
- Ícones sem corte circular, cores originais dos ratings e alinhamento das estimativas preservados.
- Seletores de Contests padronizados; atalhos Ver resultados/Ver placar com estilo compartilhado.
- Placar da prova com título maior e sem tag UP; a tag continua junto à questão na tabela. Resultados e tempos preservados.
- Benchmark com contagens mais destacadas; Explorar com CTA compacto e comparação explícita de referência e estimativa.
- Prévia local isolada documentada em docs/VISUAL_PREVIEW.md. Dados, logs e capturas locais não fazem parte do commit.

Validação antes do push: 178 testes frontend e 514 backend passaram; lint, TypeScript e build passaram. Chrome confirmou o sublinhado do link com a mesma cor de texto. Alterações de experimentos Gemini em andamento ficam fora deste commit.
