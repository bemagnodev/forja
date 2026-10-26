# Contests: avaliação e design da primeira entrega

Data: 25/10/2026. Status: direção de produto aprovada em conversa.

Este documento reúne o diagnóstico das telas atuais, a investigação de viabilidade
e o desenho aprovado. Não implementa funcionalidades, não altera o banco e não
executa sincronizações ou chamadas de IA. Os detalhes de migração, endpoints e
provedor de inferência ainda precisam de um plano de implementação.

## 1. Objetivo e decisões aprovadas

Transformar Contests em um histórico claro de desempenho e estudo. A página deve
permitir entender o resultado obtido durante uma prova, o progresso posterior e
o que cada pessoa ainda precisa aprender.

Decisões validadas com o usuário:

- Abas **Todos / Individuais / Equipe**. Plataforma e participação oficial ou
  virtual são filtros independentes.
- Manter os **cards de contests**, limitando a quantidade exibida. Referência
  inicial: nove cards por página, com paginação, busca e ordenação.
- Considerar apenas o histórico de contests realizados. Descoberta de provas
  recentes ou futuras fica fora do escopo.
- Manter a identidade escura e vermelha da Forja, com mais legibilidade e melhor
  hierarquia visual.
- Separar resultado na prova, resolução posterior e acompanhamento pessoal.
- Adicionar registro retroativo de AtCoder virtual por **início e duração**.
  Classificação manual do resultado de cada questão não entra nesta entrega.
- Incluir **revisão com IA na primeira entrega**: relatório por contest, notas
  opcionais, evidências e sugestões de treino. Comparação de vários contests
  por IA não faz parte do primeiro escopo.

Contexto de uso confirmado: no Codeforces, cada integrante usa sua conta, mas
participa de uma equipe da própria plataforma. As submissões contam para o time.
No AtCoder, as contas são individuais. Portanto, uma submissão aparecer no
histórico de alguém não demonstra que essa pessoa resolveu sozinha o problema.

## 2. Evidências e limites da avaliação

Foram lidos os componentes das duas telas, os modelos, endpoints, importadores,
testes relacionados e o design anterior de Upsolving. Também foram inspecionadas
as duas telas em produção na sessão aberta do usuário.

Exemplo observado no Hong Kong Joint Collegiate Programming Contest 2026:
o card apresenta **7 ACs durante a prova e 1 upsolvida**; o detalhe resume ambos
como **8/12**, e as oito questões recebem o mesmo selo AC. O dado existe, mas a
interface perde sua distinção.

O diagnóstico estrutural abaixo vem da leitura do código. Não houve auditoria de
registros no banco de produção nem reprodução de corrupção de dados. Riscos
identificados no modelo não significam que todos já ocorreram nos dados atuais.

| Achado | Efeito na experiência | Evidência no código atual |
| --- | --- | --- |
| `SOLVED_LIVE`, `UPSOLVED` e `PRACTICE_AC` recebem o mesmo AC | O detalhe esconde quando a questão foi resolvida | `frontend/src/pages/ContestDetail.tsx`, aproximadamente linhas 243–248 |
| O único dropdown representa revisão pessoal | O usuário não vê claramente resultado técnico e planejamento como informações distintas | `frontend/src/components/contests/ProblemStatusSelect.tsx` |
| Cabeçalho, ranking e progresso vêm de `location.state` | Uma URL aberta diretamente não dispõe de uma fonte completa de metadados; o resumo também pode ficar desatualizado | `frontend/src/pages/ContestDetail.tsx:49` |
| `rank` existe, mas os importadores examinados não o preenchem | Um componente visual de ranking já existe, porém falta a obtenção do resultado | `backend/api/models.py:103`, `backend/api/api.py:803` |
| A consulta de Gym pede apenas a primeira linha do placar e usa o catálogo | Essa resposta não identifica a colocação da equipe do usuário | `backend/api/services/codeforces_client.py:236`, `backend/api/services/codeforces_gym_service.py` |
| Equipes existem no modelo, mas listagem e importação se concentram em `user` | O resultado coletivo perde identidade e contexto | `backend/api/models.py:20`, `backend/api/api.py:927`, `backend/api/management/commands/sync_cf.py` |
| Submissão tem um ID global único e um único usuário | Há risco de colisão entre plataformas e de sobrescrita da associação quando o mesmo envio aparece nos históricos dos integrantes | `backend/api/models.py:124`, importadores CF e AtCoder com `update_or_create` pelo ID |
| Marcar revisão como `DONE` pode promover o status técnico para `UPSOLVED` | Uma confirmação manual de estudo pode ser contada como resolução posterior, mesmo sem AC importado | `backend/api/models.py:185` |
| O total do progresso é contado a partir de trackings | Pode representar menos questões que o catálogo; estados de prática entram no total sem segmento próprio | `backend/api/api.py:940` |
| AtCoder usa a janela original do contest | Identifica esforço durante a janela oficial por inferência, mas não reconhece uma sessão virtual posterior | `backend/api/management/commands/sync_atcoder.py:93` |
| O importador AtCoder usado pelo botão não tem a mesma hierarquia protetora do CF | Submissões posteriores podem rebaixar o status técnico; é necessário validar e corrigir isso antes das análises | `backend/api/management/commands/sync_atcoder.py:157`, comparação com `sync_cf.py:225` |
| Há convenções específicas de CF em componentes compartilhados | AtCoder pode receber origem incorreta na fila e índices mal apresentados | `frontend/src/components/contests/ProblemActionsCell.tsx:26`, `backend/api/api.py`, resolver de índice |

A página de Equipes ainda é um placeholder. A separação proposta em Contests
precisa reconhecer as participações coletivas, mas não exige construir agora um
módulo completo de administração de equipes.

## 3. Abordagens consideradas

| Abordagem | Benefício | Custo ou limitação |
| --- | --- | --- |
| **Entrega integrada e focada — escolhida** | Redesenha as telas, corrige o significado dos dados, permite AtCoder virtual e oferece uma revisão de IA utilizável | Requer trabalho de dados e sincronização antes de parte das análises |
| Reforma apenas visual | Melhora rapidamente legibilidade, filtros e cards | Mantém ambiguidades de equipe, ranking e participação virtual |
| Centro amplo de análises | Permite comparação histórica avançada, muitos gráficos e revisão longitudinal | Amplia bastante as dependências e o esforço antes de validar o uso básico |

A primeira abordagem foi inicialmente apresentada em etapas. O usuário definiu
que a IA deve integrar a primeira entrega; o escopo foi ajustado para incluir
um relatório por contest, preservando o restante da evolução em etapas.

## 4. Conceitos que a interface deve separar

Há quatro informações diferentes:

1. **Origem:** Codeforces regular, Codeforces Gym ou AtCoder.
2. **Participante:** pessoa ou equipe.
3. **Modo:** participação oficial ou virtual; prática avulsa permanece distinta.
4. **Aprendizagem:** o que a pessoa estudou, entendeu ou colocou na fila.

Gym não é sinônimo de equipe. Um Gym individual deve aparecer em Individuais;
uma participação coletiva deve ser reconhecida pelos dados da party ou por um
vínculo confirmado, independentemente da origem. Casos históricos sem evidência
suficiente devem indicar classificação pendente, sem inventar uma equipe.

O resultado da equipe também não é a soma dos resultados pessoais. Uma questão
aceita uma vez pelo time vale uma vez no resultado coletivo, mesmo que a mesma
submissão seja observada na sincronização dos três integrantes.

## 5. Página principal

### Organização e navegação

O topo apresenta título, contexto selecionado e ação **Registrar participação**.
Em seguida vêm as abas Todos / Individuais / Equipe, filtros de plataforma,
oficial/virtual, período, busca por nome e ordenação. A ordenação inicial é por
participação mais recente; dívida de upsolving pode ser uma ordenação alternativa.

Os cards continuam sendo a unidade principal do histórico. A referência inicial
é nove por página: três colunas em telas largas, duas em intermediárias e uma
em telas estreitas. Filtros e busca voltam à primeira página; contexto e posição
de navegação devem ser recuperáveis ao voltar de um detalhe.

Os indicadores representam **todo o histórico filtrado**, e não apenas os nove
cards visíveis. O gráfico pode mostrar os últimos dez contests desse conjunto,
indicando explicitamente esse recorte.

### Conteúdo dos cards

- Plataforma, modo e identificação da equipe quando aplicável.
- Nome legível, permitindo quebra de linha, e data efetiva da participação.
- Resultado explícito: por exemplo, **7/12 na prova · +1 upsolvida**.
- Progresso posterior e quantidade selecionada para estudar.
- Colocação apenas quando houver fonte e contexto conhecidos.
- Barra segmentada com legenda consistente com o detalhe.

O vermelho continua sendo o destaque de marca e ação. Os estados usam texto,
ícone e cor: verde para resolução durante a prova, azul para resolução posterior,
âmbar para estudo pendente e neutro para não tentada. Cor sozinha não transmite
o significado. Notas de plataforma e IA ficam visualmente secundárias.

### Indicadores e gráfico

Manter poucos números úteis: participações no recorte, resoluções durante as
provas, resoluções posteriores e itens efetivamente selecionados para upsolving.
Uma questão não tentada não vira automaticamente uma obrigação de estudo.

O primeiro gráfico compara, por contest, resoluções durante a prova e posteriores.
O total de problemas fica visível para dar contexto. Contests de durações e
formatos diferentes podem ser exibidos, mas isso não sustenta sozinho uma
afirmação de melhora ou piora. Tendências devem usar grupos comparáveis.

Não entram feed de provas novas, calendário de competições, radar genérico de
habilidades nem uma média única de rating que misture plataformas.

## 6. Página de um contest

### Cabeçalho e resultado

O detalhe carrega os próprios metadados pela API. O estado de navegação pode
ajudar na transição, mas não é a fonte exclusiva do nome ou dos indicadores.

Exibir nome, plataforma, modo, equipe e participantes quando aplicáveis, data do
treino, duração, link da prova e acesso ao placar ou editorial quando disponível.
A data original da competição e a data da participação virtual são distintas.

Separar dois resumos:

- **Resultado na prova:** resoluções durante a sessão, pontos e penalidade quando
  conhecidos, colocação com contexto e duração.
- **Progresso posterior:** novas resoluções, itens selecionados para estudar e
  revisão pessoal. Esse progresso não modifica o resultado histórico da prova.

### Mapa, tabela e filtros

Um mapa compacto A–L, ou os índices reais da plataforma, permite identificar o
resultado de cada questão rapidamente. Cada item pode levar à linha correspondente.

A tabela continua sendo a ferramenta de trabalho. Ela distingue:

| Informação | Exemplos de apresentação |
| --- | --- |
| Resultado na prova | AC no contest; tentada sem AC; não tentada; já conhecida antes |
| Resolução posterior | Upsolvida, com data quando disponível; sem AC posterior |
| Revisão pessoal | Preciso estudar; em estudo/fila; revisada; adiada; ignorada |

Quando o time resolve uma questão, a tabela pode mostrar **Time: AC no contest**
e **Você: precisa estudar** simultaneamente. A autoria individual só aparece
quando realmente conhecida; os membros de uma party não identificam quem
escreveu o código.

Filtros rápidos: Todas / No contest / Upsolvidas / A estudar / Não tentadas.
Busca, dificuldade e temas são filtros adicionais. Tags de questões pendentes
podem ficar ocultas até serem solicitadas, preservando a tentativa sem spoiler.

Rating nativo, dificuldade derivada de outra fonte e estimativa de IA precisam
de procedência explícita. A conversão atual da dificuldade do AtCoder para uma
escala semelhante à CF não deve ser apresentada como um rating oficial do CF.

As ações de fila permanecem acessíveis com teclado e toque. A classificação de
rating/tags continua sendo uma ação por problema; a revisão do contest é uma
ação própria, com outro propósito e outro relatório.

### Linha do tempo

Um gráfico em degraus mostra a evolução das resoluções durante a sessão. O fim
do contest é marcado; o upsolving posterior aparece em contexto separado, evitando
comprimir dias de estudo na mesma escala de uma prova de poucas horas.

Tentativas e intervalos podem ser exibidos quando conhecidos. Intervalo entre
submissões não equivale a tempo de raciocínio, de implementação ou tempo perdido.

## 7. AtCoder virtual: viabilidade e fluxo escolhido

**É viável com início e duração informados pelo usuário.** A Forja já possui
submissões com horário, identificador de problema, usuário e veredito. O dado que
falta é a sessão virtual à qual essas submissões devem ser associadas.

A integração atual usa a API comunitária do **AtCoder Problems/Kenkoooo**. Seu
[contrato de submissão](https://github.com/kenkoooo/AtCoderProblems/blob/main/atcoder-problems-frontend/src/interfaces/Submission.ts)
não inclui um campo equivalente a `participantType=VIRTUAL` do Codeforces.

O próprio projeto oferece
[contests virtuais](https://kenkoooo.com/atcoder/book/en/virtual_contest.html).
Seu [cliente de resultados virtuais](https://github.com/kenkoooo/AtCoderProblems/blob/main/atcoder-problems-frontend/src/api/APIClient.ts)
consulta submissões por usuários, problemas e intervalo de tempo. Isso fundamenta
a viabilidade da mesma abordagem de associação na Forja; não constitui uma
integração já implementada ou testada nesta aplicação.

### Fluxo aprovado

1. Selecionar o contest do catálogo ou informar seu identificador/link.
2. Confirmar a conta individual utilizada no AtCoder.
3. Informar data e horário de início no fuso exibido pela Forja.
4. Confirmar a duração; a duração original é uma sugestão quando disponível.
5. Conferir a prévia das questões e das submissões associadas.
6. Salvar a participação virtual e seus resultados derivados.

O registro é retroativo. Não é necessário ter iniciado um cronômetro na Forja.
Na primeira entrega, início e duração são obrigatórios; sem esses dados não há
classificação manual alternativa por questão.

### Regras de associação

- A sessão usa uma janela bem definida: início inclusivo e fim exclusivo.
- Só participam da apuração as contas e os problemas vinculados à sessão.
- AC dentro da janela conta no resultado da prova; primeiro AC posterior conta
  como resolução posterior quando não houve AC anterior elegível.
- AC anterior ao início identifica questão já conhecida. Ela não representa
  uma resolução inédita do virtual; uma nova submissão pode ser registrada
  separadamente sem apagar esse contexto.
- Se o horário for alterado, mostrar a diferença da apuração antes de confirmar.
- Detectar janelas sobrepostas com os mesmos problemas e conta, evitando uma
  associação silenciosa ambígua.
- Manter a origem da classificação: importada, informada pelo usuário ou derivada.
  Uma sessão manual não transforma o dado bruto do provedor em uma declaração
  de participação virtual feita pela plataforma.
- Sincronizações seguintes preservam a sessão e suas configurações. Um registro
  retroativo precisa considerar o histórico anterior ao cursor incremental.

Apenas marcar `is_virtual=true` resolve o rótulo, mas não os limites do resultado.
Usar a primeira submissão como horário automático de início também seria
impreciso: ela omite o tempo de leitura e raciocínio anterior ao primeiro envio.

Importar futuramente um link de virtual do Kenkoooo pode reduzir o preenchimento.
Essa integração exigiria validar acesso, contrato e correspondência de contas;
fica como evolução, sem ser requisito do fluxo manual aprovado.

## 8. Rankings e outras informações

O [Codeforces descreve](https://codeforces.com/apiHelp/objects#RanklistRow)
posição, pontos, penalidade e resultados por problema no placar. A party também
pode informar equipe, membros e início de participação virtual. O importador
atual não preserva todo esse contexto.

Para exibir a colocação correta é necessário obter a linha da party correspondente
àquela participação, identificando equipe e sessão. A primeira linha do placar
usada hoje para importar o catálogo não serve para isso.

A [documentação atual de standings](https://codeforces.com/apiHelp/methods#contest.standings)
distingue o acesso autenticado de Gym do acesso público a contests regulares.
Neste último, a documentação restringe a consulta anônima a `contestId` e ao
placar oficial público. Portanto, não se deve prometer ranking virtual regular
apenas acrescentando `showUnofficial=true` a uma consulta pública.

Apresentações diferentes:

- **Colocação oficial**, no universo de participantes oficiais conhecido.
- **Colocação virtual**, no placar virtual e recorte efetivamente obtidos.
- **Comparação estimada**, somente se houver cálculo explícito com as regras
  corretas; não entra como promessa da primeira entrega.

Se houver denominador confiável, exibir posição e total de participantes do mesmo
recorte. Percentil sem esse denominador ou sem tratamento de empates não deve
ser publicado. Falta de dado aparece como indisponível, nunca como posição zero.

Para AtCoder oficial, o projeto upstream usa o histórico
`/users/<handle>/history/json`, com posição, rating anterior/novo e performance,
conforme seu [contrato](https://github.com/kenkoooo/AtCoderProblems/blob/main/atcoder-problems-frontend/src/interfaces/ContestParticipation.ts).
É uma fonte candidata para uma etapa de integração; o acesso direto não foi
validado nesta avaliação. Esse histórico não fornece a colocação de uma sessão
virtual criada manualmente na Forja.

Outras informações úteis, condicionadas à disponibilidade: tentativas até o AC,
minuto de cada resolução, pontuação e penalidade segundo as regras da prova,
questões já conhecidas e links para submissões ou editorial. Não inferir
pontuação ou penalidade apenas contando ACs de formatos diferentes.

## 9. Revisão com IA na primeira entrega

### Experiência e saída

Um botão **Revisar contest** gera um relatório persistido daquela participação.
Antes de gerar, o usuário pode acrescentar notas sobre leitura, implementação,
estratégia ou divisão de tarefas. As notas são opcionais.

O relatório contém:

- Resumo factual do resultado e do progresso posterior.
- Pontos fortes sustentados por evidências.
- Possíveis gargalos, identificados como hipóteses quando necessário.
- Até três ações concretas de treino, com questões ou temas relacionados.
- Distinção entre recomendações para o time e para o estudo pessoal.
- Limitações dos dados utilizados.

Uma sugestão pode oferecer **Adicionar à fila**, executada somente pela ação do
usuário. A IA não modifica resultados, revisões pessoais ou a fila automaticamente.
Uma questão não resolvida, sozinha, não comprova falta de conhecimento em todos
os seus temas; tags e dificuldade estimadas devem manter sua procedência.

### Dados e confiabilidade

A Forja calcula os números antes da inferência. A IA recebe um conjunto estruturado
com resultados, tentativas, tempos, metadados e notas, em vez de ser responsável
por descobrir ou somar os dados. Cada conclusão referencia evidências existentes.

Não é necessário enviar código-fonte ou importar todos os editoriais para uma
revisão inicial de desempenho. Análise profunda de solução é outro escopo.

A infraestrutura atual de classificação de problemas oferece componentes
reutilizáveis de provedores, diagnóstico e cache, mas a revisão exige contrato,
prompt e persistência próprios. O benchmark de rating/tags não valida a qualidade
de revisão estratégica e deve permanecer separado.

O modelo e os limites operacionais serão definidos no planejamento. Esta aprovação
é do recurso de produto; nenhuma chamada real de IA foi feita neste brainstorm.

### Geração, cache e falhas

Gerar somente sob demanda. Reutilizar o relatório quando participação, resultados,
metadados relevantes, notas, modelo e prompt não mudarem. Caso mudem, indicar que
a análise pode ser atualizada, preservando a versão anterior e sua data.

Coordenar cliques simultâneos e limitar tamanho da entrada e frequência de geração.
Não fazer inferência automaticamente a cada visita ou sincronização. Uma falha
não apaga a revisão anterior nem bloqueia o restante do detalhe.

Com dados insuficientes, produzir uma análise parcial e indicar o que não pode
ser concluído. Afirmações como falta de comunicação ou tempo perdido não são
dedutíveis apenas das submissões. Eventuais relatos do usuário são contexto
declarado, distinguido dos eventos importados.

## 10. Arquitetura conceitual e fluxo de dados

Separar as responsabilidades abaixo; os nomes de tabelas e endpoints ficam para
o plano técnico:

| Responsabilidade | Informação preservada |
| --- | --- |
| Contest e catálogo | Identidade da prova, origem, questões, duração e metadados |
| Participação e sessão | Pessoa/equipe, integrantes naquele momento, modo, origem, início e fim |
| Submissão importada | Identidade por plataforma e ID, horário, veredito e party/contas observadas |
| Resultado por sessão e questão | Conhecimento anterior, resultado durante a janela e resolução posterior |
| Acompanhamento pessoal | Triagem, prioridade e confirmação manual de estudo |
| Snapshot de placar | Colocação, universo, regra, fonte e data de obtenção |
| Revisão de IA | Dados usados, versão, modelo, notas e relatório gerado |

O histórico de integrantes deve permanecer ligado à participação. Trocar os
membros de uma equipe hoje não pode reescrever a formação de um treino passado.

As constraints recentes de unicidade de participação não devem ser removidas
simplesmente para permitir virtuais. Caso seja necessário suportar várias
tentativas do mesmo contest, distinguir sessões da identidade de participação.
A interface de comparação de repetidas tentativas fica fora da primeira entrega.

Fluxo: importar catálogo/submissões → resolver identidade e participação → apurar
resultado da sessão → consultar acompanhamento pessoal → calcular agregados →
exibir telas → gerar revisão de IA por solicitação.

Resultados e agregados devem ser reprodutíveis e idempotentes. Repetir a
sincronização dos três integrantes não triplica o placar nem muda o autor de uma
observação já registrada. Identificadores de submissão precisam incluir a
plataforma, e a relação de observação não pode depender de um único usuário
sobrescrito pelo último sync.

O total de problemas vem do catálogo vinculado à prova. Tracking pessoal ausente
não faz uma questão desaparecer do denominador. Dados legados de revisão manual
devem ser preservados sem serem convertidos retroativamente em ACs comprovados.

## 11. Erros, validação e critérios de aceite

Estados de carregamento, histórico vazio e nenhum resultado para os filtros são
distintos. Filtros que removem todos os cards oferecem uma forma clara de limpar
o recorte. Uma falha de ranking ou IA não esconde a tabela de problemas.

Registrar uma sessão valida conta, contest, catálogo, início, duração positiva e
conflitos. Fuso local aparece na prévia; a persistência usa horário normalizado.
Dados de APIs e metadados podem estar parciais ou atrasados: o produto informa
isso sem inventar valores. A API comunitária do AtCoder pede intervalos entre
requisições, conforme sua [documentação](https://github.com/kenkoooo/AtCoderProblems/blob/main/doc/api.md).

Critérios verificáveis para a implementação:

1. Cards de individual e equipe respeitam a participação, inclusive Gym individual.
2. Filtros, paginação e totais seguem o mesmo recorte; indicadores não mudam só
   porque o usuário avançou de página.
3. O detalhe funciona por URL direta e atualiza os indicadores após mudanças.
4. O exemplo de 7 resoluções durante a prova e 1 posterior continua mostrando
   esses dois números em cards, resumo, mapa, tabela e gráficos.
5. Resultado coletivo permanece visível quando o usuário marca que precisa
   estudar uma questão que o time resolveu.
6. AtCoder virtual classifica corretamente envios antes, dentro e depois da
   janela, inclusive nos limites de horário e para questões já conhecidas.
7. Registro retroativo considera submissões antigas e permanece correto após
   novas sincronizações. Uma falha de sync não aparece como ausência de esforço.
8. A mesma submissão observada em contas de integrantes é contada uma vez no
   resultado coletivo. IDs iguais de plataformas diferentes não se sobrescrevem.
9. Submissões posteriores com erro não apagam um AC anterior comprovado.
10. Ranking indisponível, oficial e virtual têm representações distintas.
11. Revisão de IA valida referências a questões/evidências, distingue hipótese
    de fato, reutiliza cache e indica desatualização após mudanças relevantes.
12. Falha ou saída inválida da IA preserva a versão anterior; gerar revisão não
    altera a fila nem o acompanhamento pessoal.
13. Interface funciona com teclado e toque, contraste legível e texto para os
    estados, incluindo layout estreito e nomes longos de contests.

Esses são testes planejados para a mudança. Nenhuma suíte foi executada como
comprovação de funcionalidades que ainda não foram implementadas.

## 12. Ordem de execução e limites do escopo

Todos os blocos abaixo pertencem à primeira entrega aprovada; a ordem explicita
dependências técnicas, não adia a IA para outra versão:

1. **Fundação:** identidade de submissão, participação coletiva, resultado por
   sessão e separação do acompanhamento pessoal. Corrigir inconsistências de
   agregação e comportamento do importador AtCoder.
2. **Interface e AtCoder:** cards paginados, filtros, detalhe completo, classificação
   visual dos resultados e registro virtual por início e duração.
3. **Análises e ranking:** gráfico histórico, linha do tempo e importação/exibição
   de classificação onde houver acesso e correspondência confiáveis.
4. **Revisão com IA:** relatório por contest, notas opcionais, evidências, cache e
   ação explícita de envio das sugestões à fila.

Evoluções possíveis: importar link de virtual externo, comparar repetidas
tentativas, revisão longitudinal com IA, análise de código e editoriais, módulo
completo de equipes e rating histórico por plataforma. Não são requisitos desta
entrega. Ranking estimado de virtual não será apresentado como oficial.

Principais dependências ainda abertas: desenho detalhado da migração de dados
legados, validação das fontes de placar na infraestrutura atual e escolha/configuração
do modelo de revisão. Esses itens exigem planejamento e validação próprios;
não invalidam a solução de AtCoder por janela manual.
