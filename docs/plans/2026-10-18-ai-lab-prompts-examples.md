# Prompts A/B/C e proposta de exemplos

## Atualização — exemplos aprovados e integração concluída

Usuário aprovou 520A, 1270B, 106C e 1849E e autorizou os itens 1–2. O texto abaixo
registra a proposta original; o estado atual é C montável com arquivo privado,
sem execução real. Exemplos em `backend/var/ai_lab/prompts/classification_v3_examples.json`;
prévia efetiva e relatório local no mesmo diretório, todos ignorados pelo Git.

Justificativas autorais finalizadas: 520A, normalização/contagem O(n), espaço
constante; 1270B, par adjacente e prova pela variação O(n), espaço constante;
106C, mochila limitada O(n*(1+sum(q_i))), q_i=floor(a_i/b_i), espaço O(n),
inicializada com a opção sem recheio; 1849E, análise da solução oficial com pilhas
monotônicas/conjunto ordenado O(n log n), espaço O(n). Cada posição entra/sai das
pilhas uma vez e há O(n) operações ordenadas. Fonte para a última análise:
https://codeforces.com/blog/entry/118752

Checks locais adicionais: observação de 1270B comparada por enumeração exaustiva
em arrays de valores 0–3 e comprimentos 2–6; mochila de 106C conferida nos exemplos
salvos; semântica de contagem de 1849E conferida por força bruta nos exemplos, e
complexidade revisada pela leitura da solução oficial (não execução otimizada).
Pangrama também conferido nos exemplos. Não se atribuem justificativas ao editorial.

Integração com TDD valida contrato JSON, igualdade com entradas/referências
congeladas, unicidade, quatro faixas, ausência de sobreposição por contest/key,
delimitadores, origem privada e imutabilidade ao retomar. `--examples-file` é
explícito e só pode apontar para JSON sob o root privado do AI Lab. Metadados de
origem/revisão e identificação ficam fora dos blocos enviados ao modelo.

C efetivo: 9.313 caracteres, 9.443 bytes UTF-8. Não é contagem de tokens. Hash do
prompt `bc18e8aa0bbb54625d255de6ca04f205513a9ab53a553fc3d3104d9a1294d392`.
Hash do arquivo de exemplos `b52bcffcd7ec17fb32e13872bd193f94b1c4cf8d7d045bb1604505dd93f49a4b`.
O hash dos 60 congelados permanece inalterado. Primeiro smoke/lote real e ensino
dos comandos continuam pendentes; nenhum consumo está autorizado por este arquivo.

Validação final desta integração: RED observado antes da API de exemplos privados;
129 testes direcionados aprovados em rodada intermediária, suíte completa final
com **315 testes de backend e 78 de frontend aprovados**. Testes cobrem o comando
Django com geradores simulados Google/Groq, retomada e rejeição de alteração no
arquivo. `git diff --check` aprovado; exemplos, prévia e relatório confirmados
como ignorados pelo Git. Avisos legados permanecem. Sem chamada de classificação
real, migration, commit, push ou mudança no dataset final congelado.

## Estado

Usuário aprovou a revisão dos 60 HTMLs e a sequência de preparação. O conjunto
final foi congelado após registrar essa aprovação nos hashes atuais dos 60
payloads, sem alterações na seleção/referências. Hash congelado:
`7ea7ea0585d6a6c74877fe2f9c96ac6f70a521589bb4c395f84bb0a3f1315400`.
Manifest anterior ao congelamento preservado em revisão privada.

Nenhuma execução real de modelo autorizada ou efetuada nesta etapa. A escolha
dos exemplos abaixo é uma proposta, não uma aprovação atribuída ao usuário.

## Arquivos de prompt

- `backend/api/ai_lab/prompts/classification_v1.txt`: A, preservado byte a byte.
- `backend/api/ai_lab/prompts/classification_v2.txt`: B, rubrica do usuário com
  solução viável mais simples e faixas explicitamente flexíveis. Pronto para
  carregamento local, ainda sem evidência de desempenho.
- `backend/api/ai_lab/prompts/classification_v3.txt`: C, v1 como prefixo inalterado
  e instruções few-shot. `{examples}` é intencionalmente pendente e bloqueado
  pelo carregador antes de qualquer inferência. Sem enunciados completos no Git.
- `backend/api/ai_lab/prompts/README.md`: estados, contrato e uso dos arquivos.

As três variantes preservam rating/tags/justification. Não registrar os fatores
internos da rubrica como se fossem observações verificáveis. C não inclui B:
assim a comparação não mistura rubrica e exemplos na mesma intervenção.

## Critérios anteriores à avaliação final

Uma questão de cada faixa; nenhuma sobreposição de questão/contest com os 60;
variedade de habilidades, legibilidade e exemplos completos; payloads pequenos;
referências oficiais do snapshot de desenvolvimento. Não foram consultados
resultados de acurácia/erro dos modelos para escolher candidatos. As 12 de
desenvolvimento já tinham sido usadas em pilotos; estes não são uma seleção
independente de toda a história do projeto. Os 60 não participaram da escolha.

| Ordem proposta | Questão | Rating | Por que usar |
|---|---|---:|---|
| 1 | 520A — Pangram | 800 | Contagem de letras após normalizar maiúsculas/minúsculas; âncora de implementação direta e strings, com entrada curta. |
| 2 | 1270B — Interesting Subarray | 1200 | A observação sobre diferenças adjacentes reduz a construção a uma varredura linear. Ensina que insight/prova e tamanho de código são fatores diferentes. |
| 3 | 106C — Buns | 1700 | Modelagem de mochila com estoque limitado e opção sem recheio; contrasta técnica conhecida/estados/limites com as observações dos exemplos mais fáceis. |
| 4 | 1849E — Max to the Right of Min | 2300 | Enunciado curto, mas contagem de subarrays sob n até 10^6 exige tratamento eficiente dos extremos. Contraponto a estimar dificuldade pelo tamanho do texto. |

Os ratings/tags acima vêm do manifest congelado de desenvolvimento. Para 1270B,
se nenhuma diferença adjacente tem módulo pelo menos 2, a variação em qualquer
subarray de tamanho k é no máximo k−1; portanto não há resposta. Caso contrário,
um par adjacente basta. Essa observação fundamenta a escolha, sem depender da
previsão de um modelo.

Em 106C a descrição comporta uma mochila limitada pelo estoque de recheio e
capacidade de massa. A justificativa final deverá especificar a implementação
escolhida e sua complexidade. Em 1849E a técnica/complexidade exata da justificativa
também precisa ser revisada com uma solução correta/editorial; a proposta não
finge que listar tags oficiais é uma explicação suficiente do algoritmo.

Referência oficial consultada para 1849E:
https://codeforces.com/problemset/problem/1849/E

## Tags propostas, sem remapeamento

- 520A: implementation, strings.
- 1270B: constructive algorithms, greedy, math.
- 106C: dp.
- 1849E: binary search, data structures, divide and conquer, dp, dsu, two pointers.

Todas pertencem à taxonomia do projeto. Em 1849E a lista oficial reflete várias
abordagens possíveis; não afirmar que uma solução precisa aplicar todas elas.
Não retirar tags oficiais só para deixar o exemplo mais elegante ou facilitar F1.
As justificativas serão nossas, revisadas; não atribuídas ao Codeforces.

## Limitações e alternativas

Quatro exemplos não cobrem toda a taxonomia: esta proposta não inclui grafos,
geometria ou jogos. Aumentar essa cobertura exigiria mais exemplos ou trocar
candidatos por questões externas, com custo de coleta/revisão. Não descrever o
few-shot como amostra representativa de todos os temas.

Não escolhi 1629B como âncora inicial porque tem observação aritmética e exceções,
enquanto 520A oferece uma referência mais direta. Na faixa intermediária,
1690E é alternativa válida a 1270B, com ordenação/restos/dois ponteiros e rating
1500; custa uma entrada maior. 1537D é alternativa ao 106C para incluir jogos,
mas perde-se o exemplo de mochila. Para o topo, 2005D/1620G são alternativas
válidas; manter 1849E oferece texto mais curto e uma tarefa de contagem distinta.
Não se escolheu nenhum candidato por ser melhor classificado pelos modelos.

## Verificações antes das chamadas

Verificado localmente: v1 inalterado, v2 com taxonomia resolvida, três campos de
saída, v3 bloqueado sem exemplos, quatro candidatos únicos e sem sobreposição
de contest/questão com o final, rating/tags válidos no contrato e hashes do
desenvolvimento íntegros. V1 efetivo tem 1.189 caracteres; B tem 3.320; os quatro
payloads propostos somam 6.053 caracteres. A maior entrada dos 60 tem 4.173.
São medidas de caracteres, não contagens exatas de tokens. A contagem final
de C ainda depende das justificativas e da montagem dos blocos.

TDD: RED observado antes dos novos arquivos/guard de exemplos; GREEN e suíte
completa final com 301 testes de backend e 78 de frontend aprovados. Diff sem
erros de whitespace; avisos legados permanecem. Nenhuma chamada real de IA,
migration, commit ou push. Congelamento só alterou artefatos privados locais.

Após aprovação dos quatro: revisar justificativas, preparar arquivo privado de
exemplos com origem/hashes e integrar sua montagem ao carregador com TDD; validar
quatro outputs JSON, conteúdo/ordem fixos, ausência de placeholders e tamanho
final. Depois ensinar o comando ao usuário e aprovar o teto real incluindo
recuperações. Não executar o rascunho C nem começar lotes por conta própria.

Três prompts × três modelos × 60 problemas = 540 chamadas iniciais, mais reserva
de recuperação a aprovar. O usuário conduzirá a primeira execução com orientação.
