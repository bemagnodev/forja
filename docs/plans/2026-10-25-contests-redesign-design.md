# Contests: plano de design, usabilidade e insights

Criado em 25/10/2026. Revisado em 26/10/2026 conforme o novo recorte do usuário.
Este texto registra o recorte aprovado e implementado. Procedimentos de publicação,
enriquecimento histórico e testes manuais: [guia de Contests](../CONTESTS.md).

## 1. Foco e limites

Melhorar a página Contests e o detalhe: apresentação, navegação, resultado da prova
e evolução dos treinos, aproveitando os dados do Codeforces.

- Separação simples: **Todos / Gym / Codeforces regular**.
- Nesta etapa, assumir **Gym = treino em equipe**, como convenção de interface.
  Não implementar detecção de equipes, gestão de membros ou comparação individual.
- AtCoder virtual e revisão de contests com IA foram adiados e registrados no
  [backlog do Notion](https://app.notion.com/p/37e185f977514baebb767df3347d31e3).
  A integração AtCoder já existente não precisa ser removida.
- Manter estimativa de rating/tags por questão e adição à fila. Essas ações atuais
  são distintas da revisão de desempenho com IA que foi adiada.
- Sem feed de novas provas, análise de código ou reforma ampla do modelo de equipes.

## 2. Página principal: cards primeiro, evolução abaixo

Ordem da página: **título e filtros → resumo do recorte → cards e paginação →
gráfico de evolução**.

**Cards e navegação**
- Preservar três linhas de cards: nove em desktop, seis em duas colunas e três
  no celular.
- Busca por nome, filtro Gym/regular e oficial/virtual, período e ordenação.
  Padrão: participação mais recente.
- Cada card mostra nome, data efetiva do treino, plataforma/modo, **AC na prova /
  total**, **+ questões upsolvadas** e ranking quando disponível.
- Barra segmentada e legenda consistentes com o detalhe; títulos e números mais
  legíveis, menos brilho e melhor contraste, preservando a identidade da Forja.
- Ao voltar do detalhe, recuperar filtros, página e posição de navegação.

**Gráfico de evolução abaixo dos cards**
- Barras dos últimos 10 ou 20 contests do recorte, em ordem cronológica.
- No filtro Gym, mostrar a evolução dos treinos tratados como equipe nesta etapa.
- Métrica principal: ACs durante cada prova. Upsolving aparece como série opcional,
  separada pela legenda, para não alterar a leitura do desempenho original.
- Detalhe da barra por hover, foco ou toque com nome, data, ACs/total e upsolving.
  Alternar contagem absoluta e percentual de questões resolvidas facilita a comparação.
- O gráfico e os indicadores usam o histórico filtrado, independentemente da página
  de cards aberta. Explicitar o número de contests exibidos.
- Sem conclusões automáticas de melhora: duração e dificuldade das provas variam.

## 3. Detalhe: resumo útil e tabela preservada

**Cabeçalho:** nome, plataforma, oficial/virtual, data do treino, duração e links
para contest, placar e editorial quando disponíveis.

**Resumo:** ACs na prova, upsolving, ranking contextualizado e total de erros.
Um detalhamento compacto separa **WA / erro de execução (RE) / TLE / outros**;
CE pode aparecer no detalhamento, sem ser confundido com erro que gera penalidade.

**Tabela de questões**

| Coluna | Apresentação |
| --- | --- |
| Questão | Índice e título com link direto para a plataforma |
| Resultado | `+`, `+2`, `−2` ou `−`, horário HH:MM e selo Upsolvada |
| Rating e tags | Identificar estimativas de IA; preservar informações atuais |
| Triagem | Manter o status manual atual, distinto do resultado importado |
| Ações | Estimar rating/tags e adicionar à fila, acessíveis por teclado e toque |

Uma faixa horizontal com os índices reais das questões usa o mesmo componente
de Resultado da tabela; clicar na letra leva à linha correspondente.

O horário HH:MM é o da **primeira submissão aceita durante a participação**,
relativo ao início real ou virtual, descartando segundos. O número junto ao sinal
conta erros de julgamento antes desse AC; sem AC, conta os erros de toda a prova.
CE fica fora do contador. O tooltip separa vereditos, erros posteriores ao AC e CE,
com acesso por hover, foco e toque. Upsolving preserva o sinal original da prova.
Sem referência confiável de início, exibir “—”; não usar o primeiro envio como início.

Filtros rápidos: **Todas / No contest / Upsolvadas / A estudar / Não tentadas**.
Busca e ordenação por índice, rating, momento do AC ou quantidade de erros.
Cabeçalho da tabela fixo quando útil; largura suficiente para títulos e controles.
O resumo deve carregar também ao abrir o detalhe por URL direta.

## 4. Métricas: o que trazer e o que exige dados adicionais

| Informação | Viabilidade e regra |
| --- | --- |
| ACs e upsolving | Prioridade alta; já existem estados importados. Diferenciar visualmente e conferir denominador pelo catálogo |
| WA, RE, TLE e outros | Contar submissões únicas por veredito, só na participação exibida; separar erros posteriores de treino |
| Total de submissões | Pode complementar o detalhamento de erros, distinguindo tentativas de questões resolvidas |
| Minuto do primeiro AC por questão | A API CF oferece tempo relativo ao início oficial/virtual; o importador atual precisa preservá-lo ou recuperar o início correto |
| Ranking e penalidade | Importar apenas a linha confiável da participação; penalidade ICPC, sem estimativa local |
| Questões aceitas sem erros e primeiro/último AC da prova | Bons resumos derivados, após validar cobertura de vereditos e tempos |

“Views” foi esclarecido pelo usuário como erros/WAs; não há requisito de
visualizações de páginas.

**Regras para números confiáveis:** WA significa `WRONG_ANSWER`; RE e TLE têm
contagens próprias. `rejectedAttemptCount` do placar não equivale a WAs específicos,
e quantidade de erros não equivale automaticamente à penalidade oficial.
Não somar os históricos dos três integrantes para produzir um placar.
Contar cada submissão uma vez e não juntar sessões virtuais diferentes.
Se o histórico estiver incompleto, indicar cobertura parcial.

Para ranking, buscar a linha correspondente à participação, com seu contexto
oficial ou virtual. Não apresentar posição estimada como oficial, nem usar
posição zero para dado ausente. Acesso a Gym depende da autenticação já prevista;
a disponibilidade será validada sem ampliar o acesso a conteúdos privados.

Fontes: [objetos da API CF](https://codeforces.com/apiHelp/objects#Submission)
e [consulta de placar](https://codeforces.com/apiHelp/methods#contest.standings).

## 5. Limites e ideias adiadas

- A faixa compacta acima da tabela substitui a proposta de linha do tempo.
- Não criar estados: manter `SOLVED_LIVE`, `UPSOLVED`, `PENDING_UPSOLVE` e demais
  valores, transições do dropdown e proteção contra rebaixamento após novos erros.
- Resultado da prova é uma projeção de leitura; não somar integrantes nem juntar
  sessões virtuais. `PRACTICE_AC` não fabrica AC na prova. Dados incompletos ficam
  parciais, sem inventar zero tentativas. Conclusão manual sem AC é identificada.
- Consultas das páginas não sincronizam nem chamam APIs externas. Metadados antigos
  são enriquecidos por comando específico, com prévia e `--apply`, sem repetir a FSM.
- **Ocultar tags de pendentes:** sem prioridade nesta etapa; avaliar futuramente
  para preservar a tentativa de upsolving sem spoiler.
- **“Estimar pendentes do contest”**: conveniência opcional que reutiliza a
  classificação atual por questão, sem novo modelo ou revisão com IA. Aplicar
  apenas a questões elegíveis sem rating nativo e sem classificação válida;
  mostrar quantidade, progresso e falhas por questão, evitando reprocessar o que
  já existe. Não incluir como requisito obrigatório antes da avaliação do usuário.

Ocultação de tags e classificação em lote permanecem sem prioridade nesta entrega.

## 6. Ordem de trabalho e conferência

Cada implementação segue RED → GREEN → refatoração: apuração de submissões,
sincronização e API, componente compartilhado, integração e regressões funcionais.
Conferir desktop/notebook/mobile, navegação de retorno, acesso direto ao detalhe,
estados sem dados e filtros sem resultados; executar testes, tipos e build.

Validar que **7 ACs na prova + 1 upsolvada** permanecem distintos em toda a tela;
que WA/RE/TLE e tempos excluem upsolving; que cards, gráfico e totais respeitam os
filtros; e que link da questão, estimativa de rating/tags e adição à fila continuam
funcionando. Manter regressões para erros após AC, conclusão manual, sessões
distintas e enriquecimento sem alteração de tracking. A validação local não
substitui os testes de produção descritos no guia.

## 7. Próximas etapas no Notion

- [Adicionar participação virtual de AtCoder aos contests](https://app.notion.com/p/4056091e5536813fbb5addd948e7883b).
- [Revisar desempenho de contests com IA](https://app.notion.com/p/4056091e553681c0be84dc0e0caa5b93).

Ambas registradas como **Backlog / Futuro / P3 — Futuro**, fora desta entrega.
