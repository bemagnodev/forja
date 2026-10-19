# AI Lab — revisão para publicação

19/10/2026. Base revisada: `9b1d82b`. Organização local autorizada pelo usuário;
nenhum push, deploy, nova inferência, benchmark ou migration operacional nesta revisão.

## Commits organizados

| Commit | Responsabilidade | Evidência principal |
| --- | --- | --- |
| `8f49944` | Parser compartilhado de Codeforces, preparação da entrada e marcadores de imagens nos scrapers | Testes de extração, seleção reproduzível e contrato de entrada |
| `bcbad17` | Runner com orçamento, retomada, retry limitado, diagnóstico seguro e prompts versionados | Regressões de interrupção, erro inesperado, resposta não serializável e limites |
| `3b4d5b4` | Contrato de produto 800–3500, cache com proveniência, Explorar sem escrita e persistência textual com aviso de imagens | Integração simulada de fila/Contests/Explorar, preservação dos metadados nas sincronizações |
| `d6877a6` | Remoção isolada do classificador antigo e dos sete testes exclusivos | Imports ativos usam o caminho atual; suíte completa cobre os novos fluxos |
| `ba4fe46` | Três comparações públicas sanitizadas, seleção explícita da vitrine e arquivo dos históricos | Integridade dos snapshots, proveniência, allowlist e testes da API |
| `a4d8e62` | Frontend, prompts completos, escala de MAE, avisos persistentes e compatibilidade Base UI | 96 testes, build e lint dos 25 arquivos alterados |
| Commit de documentação que contém este relatório | Resultados, decisões, instruções e ressalvas de validação | Relatórios e planos preservados; sem arquivos privados de execução |

Os commits seguem essa ordem de dependência. A separação é por comportamento;
as suítes completas foram executadas sobre a árvore final, não em cada estado
intermediário dos commits organizados retrospectivamente. O histórico de RED/GREEN
durante a implementação está no relatório final; a organização não recria esse histórico.

## Conferência desta revisão

- Backend: **348 testes passaram**, SQLite de teste e bloqueio de rede externo.
- Frontend: **96 testes passaram em 16 arquivos**, fronteiras de API simuladas.
- Build Vite, ESLint dos 25 arquivos alterados, configuração TypeScript de Node,
  Django check e verificação de whitespace: aprovados.
- TypeScript da aplicação: **12 erros históricos em quatro arquivos não alterados**.
  Detalhes e impacto em [AI_LAB_TYPESCRIPT_DEBT.md](AI_LAB_TYPESCRIPT_DEBT.md).
- Os 32 artefatos protegidos continuam byte a byte iguais, incluindo dataset
  congelado, prompts A/B, snapshots e 20 arquivos de runs reais.
- Seletor publicado: exatamente três comparações; todas usam os 60 problemas.
  Gemini venceu neste recorte textual 800–2400. A faixa 2500–3500 do produto
  ainda não foi validada por este benchmark.
- O `main` remoto foi consultado somente para leitura e ainda aponta para
  `9b1d82b29d3c9f623a12459011f43fe6740e7ce8` nesta conferência.

Não foi identificada falha crítica nova nesta revisão. Isso não é garantia de
ausência de falhas: testes usam provedores simulados e não verificam credenciais,
cotas, scraping atual dos sites externos ou configuração do servidor em produção.

## Pontos que merecem revisão

1. **TypeScript global não está verde.** A pendência é anterior e foi delimitada
   por autorização do usuário. Recomendo uma correção separada antes de exigir
   um gate global de TypeScript; o build atual passa sem realizar esse gate.
   Um dos erros é o `rightContent` incompatível do Dashboard, com possível impacto
   no botão de atualização dessa tela; não pertence às telas entregues aqui.
2. **Concorrência real de PostgreSQL não foi reproduzida.** A gravação de
   metadados usa transação e bloqueio de linha após a inferência. Os testes
   verificam mesclagem e interleavings determinísticos em SQLite; não provam
   comportamento sob carga concorrente em PostgreSQL. Não há migration nesta entrega.
3. **Operação em produção depende do deploy.** O repositório não versiona o
   comando de inicialização do Render. Conferir timeout do servidor/proxy:
   scraping e inferência são síncronos, e o limite do provedor não substitui o
   limite do servidor. Não houve alteração nem validação dessa configuração.
4. **Peso do frontend.** O build avisa sobre o bundle de aproximadamente 821 kB
   e Browserslist antigo. Otimização de carregamento é uma tarefa posterior;
   não bloqueia a comparação dos resultados já salvos.
5. **Limites científicos.** Amostra balanceada textual de 60 problemas,
   possível conhecimento prévio dos enunciados pelos modelos, uma rodada por
   configuração e nenhuma prova de significância. Diferenças pequenas não
   justificam alegações universais. A comparação A/B do vencedor é pareada;
   não subtrair médias de comparações com interseções diferentes.

## O que falta para encerrar

**Experimento e entrega local:** concluídos no escopo combinado. As três
comparações e a explicação dos resultados já existem. Não falta executar C,
testar mais modelos, aumentar o dataset ou criar uma avaliação 2500–3500.

**Publicação:** após aprovação do relatório, realizar push normal e acompanhar
o deploy de backend e frontend. Em seguida, verificar com sessão autenticada,
sem clicar em classificar e sem inferências:

1. `GET /api/ai-lab/benchmarks` retorna 200 e os três IDs aprovados.
2. Os três detalhes retornam 200, 60 problemas, métricas e prompts A/B corretos.
3. A interface em produção mostra tabelas, dispersão, mapa de calor e prompts;
   não depende de `backend/var/ai_lab` existir no Render.
4. Fila, Contests e Explorar carregam, os ícones continuam visíveis e previsões
   já salvas com imagens mantêm o aviso; não fazer chamadas de IA para esse check.

**Preservação:** confirmar backup privado dos arquivos congelados e runs,
fora do Git. Este trabalho verificou as cópias locais, não comprovou backup
externo. Os snapshots sanitizados são suficientes para a vitrine, mas não
substituem os artefatos privados para auditoria/reprodução futura.

O push e o deploy ainda não foram realizados. A validação visual simulada anterior
e seus limites estão em [AI_LAB_FINAL_REVIEW.md](AI_LAB_FINAL_REVIEW.md).
