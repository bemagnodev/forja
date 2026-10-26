# TypeScript — dívida histórica fora da finalização do AI Lab

Pendências visuais de 25/10/2026: o ajuste responsivo do gráfico anual removeu
também o índice `idx` sem uso de `ActivityHeatmap.tsx`. Restam **9 diagnósticos
em dois arquivos**: `Last7DaysWidget.tsx` e `api.test.ts`. Os registros anteriores
abaixo descrevem o histórico, não a contagem atual.

Atualização de 25/10/2026 (sincronização CF): o Dashboard passou a consultar dados
via React Query, seguindo o padrão das outras páginas, e seus três diagnósticos
ESLint foram resolvidos sem desativar regras. O import `motion` também foi
removido: restam **10 diagnósticos TypeScript em três arquivos**, listados abaixo
exceto a linha histórica do Dashboard. O registro de 19/10 é preservado como
referência do estado anterior.

Verificação de 19/10/2026: `tsc --noEmit -p tsconfig.app.json` retorna **11
diagnósticos em quatro arquivos**. O comando completo foi executado, sem filtros,
sem desligar regras e sem alterar `tsconfig` para excluir testes ou arquivos.
O Dashboard recebeu somente a troca de `rightContent` por `action`, corrigindo
o botão Refresh com teste de regressão. Os diagnósticos restantes são anteriores
à entrega; não são erros nos arquivos corrigidos de AI Lab, fila ou Contests.

| Arquivo (relativo a frontend) | Linha(s) | Diagnóstico | Impacto exato |
| --- | --- | --- | --- |
| `src/components/dashboard/ActivityHeatmap.tsx` | 53 | TS6133: `idx` não utilizado | Impede checagem estrita; não altera o resultado da renderização por si só. |
| `src/components/dashboard/Last7DaysWidget.tsx` | 10 | TS6133: `days` não utilizado | Impede checagem estrita; variável sem uso no widget. |
| `src/pages/Dashboard.tsx` | 11 | TS6133: import `motion` não utilizado | Impede checagem estrita. |
| `src/lib/api.test.ts` | 1 (duas ocorrências) | TS1484: `InternalAxiosRequestConfig` e `AxiosResponse` precisam de imports de tipo | Tipagem da suíte de interceptadores; não é diagnóstico do código de runtime do cliente HTTP. |
| `src/lib/api.test.ts` | 14, 21 | TS2322: atribuição ao mock de `window.location` | O mock usado pela suíte não atende ao tipo DOM atual. Corrigir instalação/restauração do mock com a API apropriada, sem casts para esconder erro. |
| `src/lib/api.test.ts` | 20 | TS2304: `afterEach` não encontrado pelo TypeScript | A execução Vitest usa globals; falta import explícito para a checagem dessa configuração. |
| `src/lib/api.test.ts` | 340, 386, 437 | TS2339: `_retry` não pertence a `InternalAxiosRequestConfig` | O estado adicional do mock precisa de tipo explícito. Não é evidência de que a renovação de token falhou em runtime. |

As suítes frontend continuam executáveis; isso não torna o typecheck verde.
Build Vite também não substitui essa checagem. A correção histórica deve manter
os testes de interceptadores. O botão Refresh já está coberto por regressão.

ESLint do Dashboard mantém três diagnósticos anteriores: import `motion` sem uso
(linha 11), `catch` com `any` (25) e `react-hooks/set-state-in-effect` em `loadData`
(33). A correção da prop não adiciona diagnósticos. Não foram desativadas regras;
essa limpeza fica para depois da entrevista, junto da dívida histórica.

Resolvidos nesta entrega: props antigas `asChild` e `type/collapsible` nas telas
atingidas, nome acessível de ícone SVG, campo `linked_problem_id`, import de tipo
no toast, variáveis/imports sem uso nos componentes de Contests/ícones e a
tipagem `defineConfig` da configuração de testes em `vite.config.ts`.

`tsc --noEmit` na raiz do frontend não verifica automaticamente os projetos
referenciados, pois o tsconfig raiz tem `files: []`. Por isso também foram
executadas as checagens explícitas de `tsconfig.app.json` e `tsconfig.node.json`.
Não usar o sucesso do comando raiz para ocultar os 11 diagnósticos acima.
