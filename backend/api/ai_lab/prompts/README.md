# Prompts de classificação

| Versão | Experimento | Estado |
|---|---|---|
| classification_v1 | A: referência | Preservado sem alterações |
| classification_v2 | B: rubrica | Matriz A/B concluída; arquivo preservado sem alterações |
| classification_v3 | C: exemplos | Quatro exemplos aprovados e integrados; exige arquivo privado e datasets congelados |
| product_classification_v1 | Produto: fila/Contests/Explorar | Derivado de A; domínio 800–3500 e instrução textual para marcadores de imagens |

Os prompts A/B e a validação do benchmark continuam em 800–2400. O prompt do
produto tem versão/hash/domínio próprios no cache e não pode ser usado pelo
runner do benchmark. Aceitar 2500–3500 no produto não demonstra qualidade nessa
faixa: o Gemini venceu somente o recorte avaliado em 800–2400. Não foi criado
dataset adicional. Marcadores não representam análise visual; nenhum suporte
multimodal completo foi implementado.

V2 aplica a proposta do usuário, acrescentando solução viável mais simples e
âncoras flexíveis. Avalia descoberta, conhecimento, prova, implementação e
restrições; não muda o contrato rating/tags/justification nem expõe avaliações
internas. O experimento mede o efeito dessa instrução; não comprova adesão interna
do modelo à rubrica.

V3 mantém o texto do v1 como prefixo e acrescenta apenas instruções/exemplos
few-shot. Não contém a rubrica do v2. `{taxonomy}` é substituído pela taxonomia
oficial; `{examples}` é preenchido a partir do arquivo privado. Sem esse arquivo
e os datasets de origem/avaliação, o carregador bloqueia a execução.

Os exemplos completos não serão commitados. A seleção 520A/1270B/106C/1849E foi
aprovada pelo usuário; os payloads vêm do desenvolvimento congelado, com rating
e tags oficiais e justificativas nossas revisadas. O arquivo local fica em
`backend/var/ai_lab/prompts/classification_v3_examples.json`; não editar v3 para
colar enunciados no Git. Cada exemplo usa `<example>`, entrada JSON preparada
em `<input>` e JSON válido com as três chaves em `<output>`.

`--examples-file` passa esse arquivo ao comando do benchmark. O carregador valida
quatro exemplos únicos, uma faixa por exemplo em ordem crescente, origem/hash,
entrada idêntica à revisada, referências oficiais, justificativa não vazia e
ausência de sobreposição com a avaliação por questão/contest. Valores JSON
escapam delimitadores XML sem alterar o conteúdo recuperado por um parser JSON.
IDs, títulos, URLs e metadados de revisão não são inseridos como campos nos
exemplos efetivos. O prompt/hash efetivo e os hashes do arquivo/origem entram na
identidade da run; qualquer alteração exige nova run. O texto e os hashes são
obtidos da mesma leitura do arquivo, evitando atribuição a versões diferentes.

Não executar C sobre as 12 questões que contêm seus próprios exemplos. Uma futura
verificação técnica pode usar a execução final congelada com teto pequeno e
retomada posterior, após autorização específica. A/B não aceitam arquivo de
exemplos, evitando mudar silenciosamente a estratégia.

Não incluir códigos/títulos/URLs das questões no conteúdo efetivo dos exemplos.
Manter sua ordem fixa e igual para os três modelos. Exemplos não podem pertencer
aos 60 nem aos contests do conjunto final. Escolha e justificativas independem
dos acertos/erros anteriores dos modelos. A proposta está em
`docs/plans/2026-10-18-ai-lab-prompts-examples.md` na raiz do projeto.

O runner registra o texto efetivo e seu hash. Após uma execução, preservar a
versão usada; qualquer alteração requer outra identidade de prompt/run.
O prompt C montado tem 9.313 caracteres (9.443 bytes UTF-8). É uma medição de
texto, não contagem exata de tokens. A maior questão final tem 4.173 caracteres.
Não foram medidas performance nem cotas reais para B/C; os arquivos não autorizam
chamadas reais ou confirmam disponibilidade dos provedores.
