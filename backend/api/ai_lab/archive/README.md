# Comparações arquivadas

Snapshots sanitizados preservados para rastreabilidade. Esta pasta não é a raiz
da vitrine. A seleção e a ordem das comparações atuais estão em
`../published/index.json`.

Foram arquivados o piloto de 12 problemas, os testes incompletos de Gemini 3.8 e
Qwen e a comparação A/B isolada do GPT-OSS 20B. Seus arquivos foram movidos sem
alterar bytes. Runs originais, enunciados e respostas brutas continuam privados
em `backend/var/ai_lab`, fora do Git.

Não usar esta pasta como origem de novas inferências. Para voltar a apresentar
um resultado, revisar explicitamente o snapshot e a seleção publicada.

`9b1d82b/cf-rating-v1-development.json` preserva também a versão exata do piloto
que estava no último commit. O arquivo na raiz desta pasta é a versão posterior
do piloto, que já incluía GPT-OSS 20B antes da curadoria da vitrine. Suas métricas
e interseções diferem; são registros de comparações distintas, não versões
intercambiáveis. Nenhuma das duas aparece na vitrine atual.
