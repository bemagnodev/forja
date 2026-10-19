# AI Lab — relatório final antes do commit

Data: 19/10/2026. Registro da validação anterior à organização dos commits,
quando HEAD ainda era `9b1d82b`. Para a organização posterior, ressalvas e
pendências de publicação, consultar [revisão para publicação](AI_LAB_RELEASE_REVIEW.md).
Este relatório atualiza a revisão
anterior e registra a execução do desenho aprovado em
[finalização do produto](plans/2026-10-19-ai-lab-product-finalization.md).

## Resultado e ressalva

Os sete grupos solicitados foram tratados, com TDD e conferência local simulada.
Backend: **348 testes aprovados**. Frontend: **96 aprovados**. Build, ESLint dos
arquivos alterados, Django check e diff check aprovados.

**TypeScript da aplicação inteira ainda falha com 12 diagnósticos históricos em
quatro arquivos fora desta entrega.** Os arquivos corrigidos de AI Lab, fila,
Contests e notificações não aparecem nos diagnósticos restantes. Nenhuma regra
foi desligada e nenhum arquivo foi excluído da configuração. Arquivos, linhas,
mensagens e impactos estão em [dívida histórica de TypeScript](AI_LAB_TYPESCRIPT_DEBT.md).
Não interpretar build verde ou sucesso do tsconfig raiz como typecheck global verde.

## 1. Benchmark e produto têm contratos separados

| Caminho | Prompt e domínio | Persistência |
| --- | --- | --- |
| Benchmark | A/B originais; múltiplos de 100 em 800–2400 | Runs/snapshots existentes, preservados |
| Fila e Contests | `product_classification_v1`; múltiplos de 100 em 800–3500; Gemini Flash-Lite | Previsão válida e proveniência em `Problem.platform_metadata` |
| Explorar | Mesmo contrato/prompt de produto; Gemini padrão, GPT-OSS 120B/20B selecionáveis | Nenhuma gravação de classificação, nem cache global |

`api/ai_lab/product.py` separa a validação do produto. A taxonomia e a normalização
continuam compartilhadas, sem mapeamento de sinônimos. A função do benchmark não
foi ampliada. Valores fora do domínio e valores fora da grade são inválidos, sem
clamp/arredondamento automático. Explorar devolve os estados independentes; a
rota de produto não substitui uma previsão válida por rating/tags inválidos.

O novo arquivo `api/ai_lab/prompts/product_classification_v1.txt` deriva do Prompt
1: domínio ampliado e instrução explícita para não alegar análise de imagens.
Seu hash efetivo, com taxonomia expandida, é
`93fda28a28e8d1ef8b9a2c6dadda8df13836b3ec11335820a04831c9ed710a2d`.
O runner recusa o namespace `product_` antes de iniciar um benchmark, evitando
mistura acidental dos contratos. A/B e o protocolo científico não foram alterados.

O Gemini venceu no recorte **800–2400** do benchmark. Aceitar 2500–3500 no produto
**não comprova qualidade nessa faixa**. Isso está documentado também na página
Explorar. Nenhum dataset adicional de 2500–3500 foi criado ou executado.

### Identidade do cache

O produto exige simultaneamente:

- `ai_model = gemini-3.5-flash-lite`;
- `ai_prompt_version = product_classification_v1`;
- `ai_prompt_hash` igual ao texto efetivamente usado;
- `ai_rating_domain = cf-rating-800-3500-grid100-v1`;
- rating/tags válidos e estado visual conhecido.

O cache de Prompt A, outro modelo, versão/hash/domínio diferente ou estado visual
ausente não é reutilizado. Isso não dispara inferências ao abrir páginas nem
reclassifica o banco em massa: o usuário precisa solicitar a classificação.
Shift+clique conserva o recálculo explícito. Metadados oficiais continuam preservados.

## 2. Questões com imagens recebem estimativa textual com aviso

Os scrapers de Codeforces, AtCoder e CSES preservam marcadores `[image:N]` e a
presença de imagens. Um helper comum evita duplicar essa preparação. Imagens HTML
e SVG inline não são interpretados; seus bytes não são baixados. O payload do
modelo contém somente campos textuais e marcadores, sem a lista de URLs de imagens
nem conteúdo multimodal.

Um rating/tags válido pode ser salvo com `ai_visual_status = unprocessed`.
As APIs de fila e Contests devolvem esse estado, inclusive na leitura posterior
e na resposta de cache. O componente compartilhado `AIVisualWarning` mostra,
junto da previsão:

> Esta questão contém imagens que não foram analisadas; a estimativa pode ser menos precisa.

O aviso é visível, não depende de hover e reaparece após recarregar. Quando existe
rating oficial, a estimativa de IA é identificada para não atribuir o aviso ao
rating oficial. Explorar exibe o mesmo aviso sem gravar. A justificativa recebe
o prefixo explícito de avaliação textual parcial.

O benchmark continua textual e recusa imagens no congelamento. Não houve suporte
multimodal, novo recorte de avaliação ou reextração das 60 questões congeladas.

## 3. Classificador antigo removido

Confirmada ausência de imports no runtime antes da remoção. Foram removidos:

- `backend/api/services/ai_classifier.py`;
- `backend/api/tests/services/test_ai_classifier.py` — sete testes exclusivos.

Nenhuma função exclusiva útil precisou ser migrada: carregamento lazy do cliente,
adaptadores, validação e bridge já existem na implementação ativa. Contadores de
cota estimada, taxonomia duplicada, prompts e retry antigos não foram preservados.
`AI_MOCK_MODE`/`GEMINI_DEFAULT_MODEL` do serviço removido não controlam o runtime
ativo. Simulação de testes é feita nas fronteiras atuais de scraper/adaptador.

Tenacity foi mantido nas dependências: `google-genai` também o requer. Não houve
instalação de pacotes ou mudança de dependências nesta revisão.

**Commit futuro separado:** a exclusão dos dois arquivos e os ajustes de
documentação relativos à limpeza devem formar um commit próprio, depois de o
bridge ativo e suas dependências terem sido commitados. Não houve staging ou
commit nesta rodada. A cobertura do caminho ativo permanece nos testes de produto,
Explorar, adaptadores, scrapers e API.

## 4. Exceções inesperadas do runner

Tanto a política legada quanto a gerenciada registram `stop_reason=unexpected_error`
quando uma exceção imprevista ocorre durante a execução. O diagnóstico adicional
contém somente `{type, at}`, com horário UTC. Tipos customizados são reduzidos a
`Exception`; mensagens, corpo, traceback e segredos não entram nesse diagnóstico.
A exceção propagada também usa mensagem genérica.

Orçamento reservado, previsões anteriores e histórico são preservados. O item
cujo resultado ficou incerto conserva `error=interrupted` e não é repetido
automaticamente. Retomada manual pode continuar somente os outros itens dentro
do orçamento já registrado.

Uma regressão adicional cobriu resposta Python não serializável: a persistência
é verificada antes de substituir a reserva da tentativa. Assim, uma resposta
defeituosa não impede salvar o diagnóstico ou contamina o histórico. A remoção
do lock fica em `finally`, inclusive se a gravação final levantar erro.

Não foram editadas runs reais para mudar seus estados. Runs concluídas e Prompt
C permaneceram intactos; nenhum experimento foi retomado.

## 5. TypeScript, Base UI e componentes relacionados

Corrigidos sem desligar regras:

- `DialogTrigger`, `DialogClose`, `DropdownMenuTrigger` e `TooltipTrigger` sem
  props antigas `asChild` nem botões aninhados nas telas atingidas;
- acordeão de Explorar com a API atual de Base UI, testado ao abrir e recolher;
- nome acessível do ícone em Contests e campo `linked_problem_id` tipado;
- imports/variáveis não usados nos componentes de Contests/ícones;
- entrada do modal de fila com tipo explícito, sem `any`;
- callback nomeado da fila, mantendo o comportamento de Desfazer sem referência
  à variável antes da declaração;
- import de tipo e dependência do callback de notificações;
- `toast-context.ts` separando hook/contexto de componente para atender Fast
  Refresh. Login/SetPassword só trocaram o caminho desse import; sua lógica de
  autenticação não mudou;
- `vite.config.ts` usando `defineConfig` tipado de `vitest/config`, sem alterar
  ambiente, exclusões ou regras dos testes.

Os 12 diagnósticos históricos de Dashboard/testes de interceptadores foram
preservados para tratamento delimitado, conforme autorização do escopo.

## 6. Evidências de TDD e validação final

RED observado para domínio/cache/imagens; extração de marcadores em AtCoder/CSES;
estado inesperado e resposta não serializável nas duas políticas do runner;
entrada indevida de prompt de produto no benchmark; avisos persistentes e
composição de componentes. Os diagnósticos de TypeScript e lint também foram
observados antes das correções correspondentes.

| Verificação | Resultado |
| --- | --- |
| Backend completo: `python -m pytest api -q` | **348 passaram**; 332 anteriores + 23 novos − 7 exclusivos removidos por autorização |
| Frontend completo: Vitest, um worker | **96 passaram**; seis testes novos, sem remover os anteriores |
| TypeScript da aplicação: `tsc --noEmit -p tsconfig.app.json` | **Falha com 12 diagnósticos históricos**, documentados separadamente |
| TypeScript de configuração: `tsc --noEmit -p tsconfig.node.json` | Passou |
| `tsc --noEmit` no tsconfig raiz | Passou; não substitui checagem dos projetos referenciados |
| Build Vite local | Passou; alerta de bundle ~821 kB e Browserslist desatualizado |
| ESLint dos arquivos frontend alterados e configuração Vite | Passou, sem desligar regras |
| Django check com settings de teste isolados | Passou |
| `git diff --check` | Passou |
| Navegador com scraper/IA simulados | Fila, Contests e Explorar conferidos |

Os dois testes novos de temporizador inicialmente tiveram timeout por interação
de `userEvent` com relógio simulado. Foram corrigidos para usar evento síncrono
nesses testes específicos, mantendo as verificações de remoção em 4 segundos e
permanência com duração infinita. Não foi ampliado timeout ou relaxada asserção.

O fixture automático do backend bloqueia DNS e conexões reais e falha mesmo se
a aplicação capturar a tentativa. As suítes frontend simulam suas fronteiras de
API; o navegador usou servidor exclusivo com scraper e gerador falsos. Não houve
smoke test real de chave, cota ou qualidade de qualquer modelo nesta rodada.

### Conferência no navegador

No SQLite privado de QA, um problema sintético com marcador recebeu **3500/math**:

1. Fila salvou modelo, prompt, hash, domínio e `unprocessed`; aviso visível.
2. Recarregar a fila preservou a previsão e o aviso sem inferência automática.
3. Contests exibiu os mesmos dados e reutilizou o cache. O log continuou com
   apenas **uma geração simulada**.
4. Explorar gerou a segunda resposta simulada, exibiu o aviso e os três ícones.
   Um hash dos metadados antes/depois confirmou **nenhuma escrita pelo Explorar**.

O mock exigia modelo/prompt exatos e ausência da lista de imagens no payload.
O aviso foi ajustado para quebrar linhas com largura legível nas tabelas. As
fixtures foram removidas e o servidor local anterior foi restaurado sem migration.
Screenshots e logs permanecem em `backend/var/ai_lab`, ignorado pelo Git.

## 7. Integridade e confidencialidade

Foram comparados hashes de **32 artefatos protegidos**, incluindo 20 arquivos de
runs reais, A/B, dataset final, snapshots públicos e arquivos históricos. Todos
permanecem iguais, e o conjunto de run IDs reais não cresceu.

Dataset final: 60 problemas, hash
`7ea7ea0585d6a6c74877fe2f9c96ac6f70a521589bb4c395f84bb0a3f1315400`.
Somente as três comparações públicas aprovadas continuam selecionadas:

- `cf60-prompt-a-models-v1`;
- `cf60-prompt-b-models-v1`;
- `cf60-best-model-prompts-ab-v1`.

Pilotos, Qwen e Gemini 3.8 permanecem arquivados fora da vitrine. Não houve mudança
em previsões, métricas ou prompts A/B; nenhum dataset adicional foi produzido.
Não foram adicionados enunciados reais, respostas brutas, exemplos privados ou
chaves ao conjunto de arquivos candidatos ao Git. A varredura por padrões de
credenciais e caminhos privados não encontrou ocorrências nos candidatos
verificados; dados de trabalho e ferramentas de QA continuam ignorados.

Na etapa de implementação descrita aqui, nenhum commit, push, deploy ou migration operacional foi realizado. As migrations
internas da suíte ficaram restritas ao banco de teste isolado. Nenhum banco de
produção foi consultado ou alterado. Não executar novos benchmarks para validar
estas correções de contrato, interface ou tratamento de erro.
