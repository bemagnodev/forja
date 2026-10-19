# Explorar e ajustes de leitura do benchmark

Desenho aprovado pelo usuário em 2026-10-17. Sem commit/push nesta implementação.

- Benchmark: barras de MAE com escala visual fixa 0–1000; excesso indicado sem alterar o número. Tooltip explica F1 micro e denominador de tags visível.
- Explorar: Gemini 3.5 Flash-Lite padrão; GPT-OSS 120B e 20B opcionais. Gemini 3.8 permanece candidato ao benchmark de cota menor.
- Reutilizar prompt v1, taxonomia, validação 800–2400 e adaptadores do AI Lab. Nenhuma mudança nos experimentos salvos.
- Ponte pequena em api/ai_lab/explore.py adapta dados dos três scrapers e contrato legado de retorno. Não criar engine genérica, migrations ou abstração de cache.
- Entrada por allowlist de enunciado, incluindo constraints de AtCoder/CSES; exemplos filtrados. Não enviar título/identificação/rating/tags oficiais/estatísticas do aluno.
- Previsões novas em platform_metadata, identificadas por modelo e hash do prompt. Cache legado sem proveniência não vale para seleção explícita. Preservar clientes antigos sem seleção e seus testes.
- Exatamente uma tentativa por clique; sem fallback/retry oculto. Erros sanitizados com mensagens específicas de chave, cota e resposta inválida. Não salvar erro como previsão válida.
- Limpar resultado ao trocar modelo/plataforma/problema; bloquear alterações durante requisição. Preservar ícones e primeira aba Explorar. Exibir modelo/cache da previsão.

TDD: RED/GREEN para escala, excesso e F1; payload do 20B em HTTP simulado; seleção, entrada filtrada e validação da ponte; API autenticada com cache separado e erros sem gravação; fluxo React de seleção/envio/limpeza. Testes novos em api/tests/ai_lab; legados intactos. Suítes completas, build, lint e conferência local sem inferência real.

Operação futura: piloto de 12 itens para Gemini 3.8 e GPT-OSS 20B exige orçamento explícito antes de chamadas reais. Com 20 requisições/dia, 60 itens exigem ao menos três janelas de cota e margem para falhas; planejar quatro dias e retomar mesma configuração. Não usar ajustes de Explorar para alterar prompt/entradas do benchmark congelado.

## Execução e revisão

- Autorização posterior recebida: até 12 tentativas por modelo, incluindo falhas, com mesmos enunciados preparados e prompt v1. Nenhuma troca de modelo/plano ou repetição de Flash-Lite/120B.
- GPT-OSS 20B: 12 tentativas, 11 ratings válidos, 10 saídas de tags válidas, uma falha de provedor na última chamada. Não houve 13ª chamada. O adaptador preservou categoria provider_error, sem status HTTP detalhado; a causa específica não foi comprovada.
- Gemini 3.8: duas tentativas com server_error e nenhum resultado; interrompido para preservar dez tentativas não usadas. Não foi observado erro de quota neste piloto.
- Comparação principal agora tem três IAs mais baseline, interseção de rating 11/12 e tags 9/12. Os números anteriores foram recalculados no novo conjunto comum; artefatos de origem foram preservados. Qwen parcial anterior intacto. Gemini 3.8 interrompido em snapshot separado, sem transformar ausência em erro zero.
- TDD RED observado para barra fixa/excesso/F1, seleção dos modelos e cache/error handling. GREEN direcionado e suítes completas: backend 271, frontend 77. 95 testes legados preservados. Build, lint dos arquivos alterados, check Django, ausência de novas migrations e git diff --check aprovados. Comparação programática TypeScript com HEAD não encontrou novos diagnósticos; o projeto ainda tem erros legados.
- A primeira suíte backend encontrou falha de criação do temporário do sandbox, não regressão; reexecução integral em diretório reservado sob var/ai_lab passou. Auxiliares privados não entram no Git.
- Revisão no navegador: Explorar primeiro, três modelos e ícones preservados; busca e resultado do cache real do piloto no SQLite exclusivo de QA; identificação modelo/cache e limpeza ao trocar modelo confirmadas, sem inferência adicional. Escala e tooltip do benchmark também conferidos.
- Dois snapshots derivados foram revisados/recalculados por allowlist: comparação principal atualizada e ensaio interrompido Gemini 3.8. API autenticada de leitura conferida sem raiz privada e sem rede de IA, em SQLite em memória.
- Nova consulta pública ao Render retornou 401 sem token na rota do benchmark, em lugar do 404 anterior. Isso comprova presença da rota; não substitui conferir CORS e gráficos com login na produção. As mudanças deste documento continuam locais, sem commit/push/deploy novo.
