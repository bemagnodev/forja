# Finalização do AI Lab — desenho aprovado e validação

Implementar o pedido de 19/10 sem novas inferências, benchmarks, migrations
operacionais, commits, push ou deploy. A separação abaixo foi especificada pelo
usuário; não muda as três comparações públicas nem a avaliação congelada.

## Estrutura e decisões

- `api/ai_lab/product.py`: contrato 800–3500, identificação do domínio e do
  prompt de produto. Taxonomia compartilhada, sem sinônimos automáticos.
- `api/ai_lab/prompts/product_classification_v1.txt`: derivado de Prompt 1,
  alterando o domínio e explicitando que marcadores não representam imagem vista.
- `explore.py`: bridge único ativo, usando o contrato de produto. Adapters
  continuam sem ferramentas, fallback ou retry implícito.
- Cache do produto exige modelo, versão, hash, domínio e estado visual conhecido.
  Metadados JSON existentes, sem alteração de schema.
- Resultado textual válido pode ter `ai_visual_status=unprocessed`; um componente
  compartilhado de aviso acompanha a previsão em fila, Contests e Explorar.
- Scrapers preservam marcadores e presença de imagens, sem baixar imagens ou
  declarar análise visual. Dataset textual continua recusando imagens.
- Runner registra exceção inesperada de forma segura, mantém tentativa incerta
  reservada e remove o lock. Nenhum arquivo de run real será editado.
- Remover serviço antigo e testes exclusivos; registrar essa remoção como grupo
  separado para commit futuro. Não há função exclusiva a migrar se já coberta
  pelo bridge, pelos adaptadores e pelos contratos atuais.

## Sequência TDD

1. RED/GREEN para limites 800–3500, grid, versão/hash/domínio do cache e invariância
   do contrato benchmark 800–2400.
2. RED/GREEN para imagens: extração de marcadores, payload textual, salvamento e
   recuperação do aviso via fila/Contests, Explorar sem gravação.
3. RED/GREEN para exceção inesperada, metadados seguros, lock e não repetição.
4. Confirmar ausência de imports ativos; remover implementação antiga e testes
   exclusivos, mantendo cobertura dos fluxos atuais.
5. RED/GREEN nos componentes e interações de Base UI; executar TypeScript e
   corrigir diagnósticos relacionados sem desligar regras.
6. Suítes completas, build, lint delimitado, Django check e diff check. Navegador
   com scraper/IA simulados e SQLite privado, seguido de limpeza das fixtures.
7. Relatório com contagens, pendências históricas e integridade dos artefatos.

O vencedor foi avaliado apenas em 800–2400. Aceitar 2500–3500 no produto não é
evidência de qualidade nesse intervalo; nenhum dataset adicional será criado.

## Conclusão da execução

Implementação concluída e verificada com 348 testes backend e 96 frontend.
Build, lint delimitado, Django check e diff check aprovados. TypeScript dos
arquivos corrigidos sem diagnósticos; 12 erros históricos fora do escopo estão
documentados, sem exclusões ou desligamento de regras. Relatório completo em
[revisão final](../AI_LAB_FINAL_REVIEW.md). Não houve commit, push, deploy,
migration operacional ou inferência real.
