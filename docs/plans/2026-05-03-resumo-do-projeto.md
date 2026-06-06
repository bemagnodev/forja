# Resumo do Projeto Forja — Estado Atual e Planejamento
**Data:** 03 de Maio de 2026
**Autor:** Bernardo 

Este documento é um registro técnico de alto detalhe do estado da plataforma **Forja** nesta data. Cobre a arquitetura consolidada, todos os componentes implementados, as decisões de design tomadas, o estado da suíte de testes, e os próximos passos planejados. Serve como referência para novos *sprints* e como linha de base formal do projeto.

---

## 0. Visão Geral e Filosofia

A **Forja** é uma plataforma pessoal de engenharia de dados e *tracking* para Maratonas de Programação. Sua proposta central não é apenas listar problemas resolvidos — é gerenciar a **Dívida Técnica** do competidor: mapear o que foi feito em prova (*Live*), o que foi ignorado, o que o time resolveu e o usuário não, e forçar o Upsolving estratégico. O sistema transforma dados brutos das plataformas em **inteligência de estudo acionável**.

### Princípios que guiam todas as decisões

| Princípio | Como se manifesta |
|---|---|
| **Domain-Driven Design** | A regra de negócio vive nos modelos (`models.py`). Views e scripts são "burros". |
| **DRY** | Uma lógica existe em um lugar. Funções utilitárias são extraídas imediatamente ao surgir duplicação (ex: `getRatingColor` em `lib/ratings.ts`). |
| **Single Source of Truth** | O banco de dados dita a realidade. A FSM protege o estado via hierarquia de prioridade. |
| **Test-Driven Safety** | Alterações em regras de negócio são acompanhadas de testes. O código não sobe se o teste quebrar. |

---

## 1. Backend — Arquitetura e Modelos

### 1.1 Stack Tecnológica

- **Framework:** Django 5.x + Django Ninja (API declarativa com tipagem Pydantic)
- **Banco de Dados:** SQLite (dev) / PostgreSQL (prod-ready)
- **Testes:** `pytest` + `pytest-django` + `responses` (mock HTTP)
- **IA:** `google-genai` SDK (Gemini) + `tenacity` (retry com backoff exponencial)
- **Scraping:** `BeautifulSoup4` + `requests`

### 1.2 Modelos Centrais (`backend/api/models.py`)

#### `User`
Extensão do `AbstractUser` do Django. Campos adicionais relevantes:
- `cf_handle` — handle do Codeforces para sincronização via API
- `cses_token` — cookie de sessão autenticada do CSES para scraping de submissões
- `atcoder_handle` — handle do AtCoder

#### `Problem`
Representa um problema de qualquer plataforma suportada.
- `platform` — Enum `PlatformChoices`: `CF_OFFICIAL`, `CF_GYM`, `ATCODER`, `CSES`
- `platform_id` — ID canônico da plataforma (ex: `"1A"`, `"abc300_a"`, `"1068"`)
- `title` — nome do problema
- `url` — link direto para o enunciado
- `contest` — FK para `Contest` (nullable)
- `platform_metadata` — `JSONField` livre para armazenar dados extras da plataforma:
  - `rating`, `tags` — metadados oficiais
  - `ai_rating`, `ai_tags`, `ai_reasoning` — metadados inferidos pela IA (escritos pelo endpoint `/predict`)

#### `Contest`
Representa um concurso de qualquer plataforma.
- `platform`, `platform_id`, `name`, `start_time`, `duration_seconds`
- Relacionado a `Problem` (1→N) e `ContestParticipation` (N→N via user)

#### `Submission`
Registro histórico imutável de cada submissão feita pelo usuário.
- `verdict`, `submitted_at`, `participant_type` (`CONTESTANT`, `PRACTICE`, `VIRTUAL`)
- Serve de *fonte da verdade* para calcular transições da FSM

#### `UserProblemTracking` — A FSM Central
O coração da inteligência do sistema. Cada instância representa **o relacionamento de um usuário com um problema**.

**`system_status` (calculado automaticamente pela FSM):**
```
UNATTEMPTED → PENDING_UPSOLVE → UPSOLVED
             ↘ SOLVED_LIVE
PRACTICE_WA  → PRACTICE_AC
```

Hierarquia de prioridade (protege contra downgrade):
```python
SOLVED_LIVE:     60  # Máxima prioridade — nunca pode ser rebaixada
UPSOLVED:        50
PRACTICE_AC:     40
PENDING_UPSOLVE: 30
PRACTICE_WA:     20
UNATTEMPTED:     10  # Mínima prioridade
```

**`review_status` (triagem manual do aluno):**
`PENDING_TRIAGE`, `DOABLE`, `SKIP`, `DONE`, `TEAM_DONE`, `HARD_SKIP`

O método `_sync_system_to_review()` garante que o `review_status` seja automaticamente atualizado quando um problema é resolvido (ex: `SOLVED_LIVE` → seta `DONE`).

#### `ContestParticipation`
Registra o envolvimento do usuário em um concurso específico.
- `rank`, `solved_count`, `penalty`
- Quando criada, a FSM percorre **todos os problemas do contest** e cria `UserProblemTracking` para cada um, mesmo os não tentados (marcados `UNATTEMPTED`). Isso garante que a "Dívida Técnica" seja sempre completa.

#### `QueueItem`
Fila de estudo do usuário.
- `item_type`: `PROBLEM`, `STUDY_SESSION`
- `priority`: `UPSOLVING`, `REVIEW`, `CONTEST_PREP`, `FREE`
- `is_completed`, `order` (para drag-and-drop)
- `linked_problem` — FK nullable para `Problem`

---

## 2. Backend — Pipelines de Ingestão (ETL)

### 2.1 Codeforces (`sync_cf.py`)

O comando mais complexo do sistema. Processa o histórico completo de submissões do usuário via `user.status` da API pública do CF.

**Fluxo principal:**
1. Busca todas as submissões paginadas (loop com `from_` offset)
2. Para cada submissão, identifica o `platform_type` (oficial vs gym) pelo `contestId >= 100000`
3. **Fetch dinâmico de Gyms:** Se um Gym ainda não existe no banco, faz um `contest.standings` para importar o contest e **todos os seus problemas** antes de processar a submissão do usuário — garantindo que a FSM tenha base completa
4. Upsert do `Problem` e `Submission`
5. Gestão de `ContestParticipation` com lógica para detectar participação `CONTESTANT` vs `PRACTICE`
6. Aplica a hierarquia de prioridade da FSM para nunca fazer downgrade de status

**Proteção anti-downgrade (corrigida neste sprint):**
```python
status_priority = { SOLVED_LIVE: 60, UPSOLVED: 50, ... }
if status_priority[new_status] > status_priority[current_status]:
    tracking.system_status = new_status
    tracking.save()
```

### 2.2 AtCoder (`sync_atcoder.py`, `sync_atcoder_metadata.py`)

- `atcoder_client.py` — abstração do scraping autenticado do AtCoder (sessão cookie)
- `sync_atcoder.py` — sincroniza submissões do usuário
- `sync_atcoder_metadata.py` — enriquece problemas com rating e tags via API pública

### 2.3 CSES (`import_cses.py`)

Importa os problemas do catálogo público do CSES e, quando há `cses_token`, tenta mapear o histórico de submissões do usuário.

- Importa ~400 problemas organizados por categorias (Sorting, Graphs, DP, etc.)
- Cria `UserProblemTracking` para cada problema respeitando a FSM
- Roda via: `python manage.py import_cses`

---

## 3. Backend — API (Django Ninja)

### 3.1 Estrutura Geral (`backend/api/api.py`)

API declarativa com tipagem automática. Endpoints principais:

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/problems/search` | Busca de problemas por texto + platform filter |
| `POST` | `/problems/{id}/predict` | Classificação IA (rating + tags + reasoning) |
| `GET` | `/contests` | Lista contests com métricas de progresso |
| `GET` | `/contests/{id}/problems` | Problemas de um contest com status FSM |
| `PATCH` | `/contests/{id}/problems/{pid}/status` | Atualiza `review_status` |
| `GET` | `/queue` | Lista da fila de estudo |
| `POST` | `/queue` | Adiciona item à fila |
| `PATCH` | `/queue/{id}` | Atualiza prioridade / descrição |
| `POST` | `/queue/{id}/status` | Toggle `is_completed` |
| `GET` | `/stats` | Estatísticas globais do usuário |

### 3.2 Endpoint de IA: `POST /problems/{id}/predict`

O mais sofisticado do sistema. Fluxo completo:

```
1. Verifica cache: platform_metadata tem ai_rating/ai_tags/ai_reasoning?
   → Se sim e force=False: retorna cache direto (sem custo de API)
   → Se force=True (Shift+Click no frontend): ignora cache e recalcula

2. Seleciona o Scraper correto via Factory:
   - CF_OFFICIAL / CF_GYM → CodeforcesScraper
   - ATCODER             → AtCoderScraper
   - CSES                → CSESScraper

3. Faz scraping do enunciado do problema (HTML parsing via BeautifulSoup)
   → UnparseableProblemException se o parsing falhar

4. Chama classify_problem(problem_data, model_name)
   → Gemini retorna: predicted_rating, predicted_tags, reasoning

5. Persiste ai_rating, ai_tags, ai_reasoning em platform_metadata

6. Retorna:
   { rating, tags, reasoning, raw_data, real_rating, real_tags }
```

Parâmetros:
- `model_name` — qual modelo Gemini usar (default: `gemini-3.1-flash-lite-preview`)
- `force` — bool, ignora cache e recalcula

---

## 4. Backend — Serviços de IA e Scrapers

### 4.1 Scrapers (`backend/api/services/scrapers/`)

Hierarquia baseada no padrão Template Method:

```
BaseScraper (base.py)
├── CodeforcesScraper (codeforces.py)  — extrai div.problem-statement
├── AtCoderScraper   (atcoder.py)      — extrai span.lang-en > task-statement
└── CSESScraper      (cses.py)         — extrai seções via h1 e ul
```

Todos levantam `UnparseableProblemException` em caso de falha de parsing, que é capturada pelo endpoint e retorna HTTP 400 com mensagem descritiva.

### 4.2 AI Classifier (`backend/api/services/ai_classifier.py`)

- Usa o SDK `google-genai` (v1beta)
- Modelos suportados: `gemini-3.1-flash-lite-preview`, `gemini-2.5-flash`, `gemini-3-flash-preview`
- Retry automático via `tenacity`:
  - 3 tentativas máximas
  - Backoff exponencial (2s, 4s, 8s)
  - Detecta rate-limit via `errors.APIError` com status 429
- Prompt instrui o modelo a raciocinar sobre dificuldade algorítmica antes de emitir rating e tags
- Log de uso de tokens em cada chamada (`_log_usage`)

---

## 5. Frontend — Arquitetura e Stack

### 5.1 Stack Tecnológica

- **Framework:** React 19 + Vite + TypeScript (strict)
- **Estilo:** Tailwind CSS com Design Tokens customizados em `index.css`
- **Estado/Data:** `@tanstack/react-query` (server state)
- **Drag-and-Drop:** `@dnd-kit/core` + `@dnd-kit/sortable`
- **Roteamento:** React Router DOM v6
- **Fonte:** Geist Variable (`@fontsource-variable/geist`)

### 5.2 Design System (`frontend/src/index.css`)

Tokens de cores globais:

```css
/* Cores de Rating Competitivo — Padrão Codeforces */
--rating-gray:   #808080;   /* < 1200 */
--rating-green:  #008000;   /* 1200–1399 */
--rating-cyan:   #03a8aa;   /* 1400–1599 */
--rating-blue:   #0000ff;   /* 1600–1899 */
--rating-violet: #aa00aa;   /* 1900–2099 */
--rating-orange: #ff8c00;   /* 2100–2399 */
--rating-red:    #ff0000;   /* ≥ 2400 */

/* Cor primária do sistema */
--primary: #dc143c;  /* Crimson */
```

Lógica de mapeamento centralizada em `frontend/src/lib/ratings.ts`:
```ts
export function getRatingColor(rating: number | null | undefined): string
```
Todos os componentes que exibem rating (Queue, ContestDetail, AILab) consomem essa função. Elimina duplicação e garante consistência.

---

## 6. Frontend — Páginas e Componentes

### 6.1 Roteamento (`App.tsx`)

| Rota | Componente | Status |
|------|------------|--------|
| `/` | `Queue` | ✅ Implementado |
| `/contests` | `Contests` | ✅ Implementado |
| `/contests/:id` | `ContestDetail` | ✅ Implementado |
| `/ai-lab` | `AILab` | ✅ Implementado |
| `/dashboard` | `Dashboard` | 🚧 Placeholder |
| `/teams` | `Teams` | 🚧 Placeholder |
| `/notes` | `Notes` | 🚧 Placeholder |
| `/settings` | `Settings` | 🚧 Placeholder |
| `/profile` | `Profile` | 🚧 Placeholder |

### 6.2 Queue (`frontend/src/pages/Queue.tsx`)

A fila de estudo do usuário. Funcionalidades:
- Listagem de `QueueItem` com status, prioridade, rating e tags
- Drag-and-drop para reordenação (via `@dnd-kit`)
- Toggle de conclusão com **toast de desfazer** (sistema unificado `useToast`)
- Edição inline de descrição do item (`EditableDescription`)
- Mudança de prioridade via dropdown
- Adição de novos itens via `AddItemDialog` (com busca de problema)
- Rating colorido via `getRatingColor`

**Componentes do módulo Queue:**
- `SortableRow.tsx` — linha da tabela com drag handle, checkbox, rating, tags
- `AddItemDialog.tsx` — modal de criação com busca e vinculação de problema
- `PlatformIcon.tsx` — ícone da plataforma (CF, AtCoder, CSES)
- `PriorityBadge.tsx` — badge visual de prioridade
- `EditableDescription.tsx` — campo de texto editável inline
- `constants.ts` — configurações de prioridade e cores
- `types.ts` — tipagem `QueueItem`

### 6.3 Contests (`frontend/src/pages/Contests.tsx`)

Lista de todos os contests do usuário. Funcionalidades:
- Cards de contest com gradiente de glassmorphism
- Barra de progresso mostrando Live Solve + Upsolve sobre total
- Métricas: rank, problemas resolvidos/total
- Navegação para `ContestDetail` passando estado via router

**Componentes do módulo Contests:**
- `ContestCard.tsx` — card visual com efeito glassmorphism
- `ContestProgressBar.tsx` — barra segmentada Live/Upsolve/Pendente
- `ContestMetrics.tsx` — chips de métricas (rank, solved)

### 6.4 ContestDetail (`frontend/src/pages/ContestDetail.tsx`)

Detalhamento de um contest específico. Funcionalidades:
- Tabela de todos os problemas com status FSM
- Filtros pill: Todas / Pendentes / Resolvidas / Não tentadas
- `RatingBadge` — exibe rating com a cor CF correta; se não há rating oficial, exibe `ai_rating` com ícone ✨ (Sparkles)
- Tags da IA exibidas em **fuchsia** para diferenciação visual de tags oficiais
- Badge **AC** (verde) para problemas com status `SOLVED_LIVE`, `UPSOLVED`, `PRACTICE_AC`
- `ProblemStatusSelect` — dropdown para mudar `review_status` inline
- `ProblemActionsCell` — botões de ação por linha:
  - ✨ **Predict** (Sparkles): chama `/predict` e invalida cache do React Query
  - Shift+Click: força recálculo da IA (`force=true`)
  - ➕ **Add to Queue**: adiciona o problema à fila de upsolving
- Link externo para o problema na plataforma

### 6.5 AI Lab (`frontend/src/pages/AILab.tsx`)

Playground para testar e avaliar a engine de classificação por IA. Funcionalidades:
- **Seletor de Modelo:** Gemini 3.1 Lite, Gemini 2.5 Flash, Gemini 3.0 Flash
- **Seletor de Plataforma:** Codeforces, AtCoder, CSES
- **Busca de Problema:** autocomplete com dropdown de resultados
- **Resultado da Predição:**
  - Card "Rating Previsto" com cor CF aplicada ao número
  - Card "Tags Sugeridas" em fuchsia
  - Card "Tempo de Resposta" em segundos
  - Bloco de "Raciocínio da IA" (Chain of Thought)
  - Accordion com dados brutos do scraper (JSON)
- **Painel de Acurácia:** quando o problema tem rating/tags oficiais, exibe comparação lado a lado com delta de rating colorido (verde/amarelo/vermelho)
- Ctrl+Click / Shift+Click: força recálculo ignorando cache

---

## 7. Componentes de UI Genéricos (`frontend/src/components/ui/`)

| Componente | Descrição |
|---|---|
| `accordion.tsx` | Collapse/expand com animação suave |
| `alert.tsx` | Blocos de alerta (erro, sucesso, info) |
| `badge.tsx` | Chip de badge genérico |
| `button.tsx` | Botão base com variantes |
| `checkbox.tsx` | Checkbox com estado controlado |
| `dialog.tsx` | Modal com overlay e trap de foco |
| `dropdown-menu.tsx` | Menu dropdown com submenus |
| `input.tsx` | Input text estilizado |
| `select.tsx` | Select nativo estilizado |
| `skeleton.tsx` | Placeholder de carregamento |
| `table.tsx` | Tabela HTML semântica estilizada |
| `toast.tsx` | Sistema de notificações com `useToast` hook, suporte a ação de desfazer, ícone customizável |
| `tooltip.tsx` | Tooltip hover com Radix |

---

## 8. Suíte de Testes (`backend/api/tests/`)

Todos os testes rodam com `pytest` + `pytest-django`. Cobertura atual:

| Arquivo | Cobertura |
|---|---|
| `test_fsm_tracking.py` | Transições da FSM para `UserProblemTracking`. Cobre: SOLVED_LIVE, UPSOLVED, PRACTICE_AC, PENDING_UPSOLVE, sync bidirecional com review_status |
| `test_clients.py` | Mocking das requisições HTTP de `CodeforcesClient` e `AtCoderClient`. Valida rejeição de metadados inválidos e rate limits |
| `test_sync_pipelines.py` | Testes de integração dos comandos `sync_cf` e `sync_atcoder`: atomicidade, hierarquia FSM, proteção contra downgrade, fetch dinâmico de Gyms |
| `test_scrapers.py` | TDD dos três scrapers (CF, AtCoder, CSES). Mocka HTML real e valida parse de título, seções, restrições e `UnparseableProblemException` |
| `test_api_predict.py` | Testa o endpoint `/predict`: cache hit, cache bypass via `force`, persistência de `ai_rating`/`ai_tags` no banco |
| `test_ai_classifier.py` | Testa `classify_problem`: mock do Gemini, parsing do JSON de resposta, comportamento de retry em rate limit (429) |
| `test_queue.py` | CRUD de `QueueItem`, toggle de `is_completed`, ordenação |

**Executar todos os testes:**
```bash
cd backend
.\.venv\Scripts\Activate.ps1
pytest api/tests/ -v
```

---

## 9. Estrutura de Arquivos (Snapshot)

```
forja/
├── backend/
│   ├── api/
│   │   ├── models.py                    # FSM, modelos centrais
│   │   ├── api.py                       # Endpoints Django Ninja
│   │   ├── admin.py                     # Admin customizado
│   │   ├── management/commands/
│   │   │   ├── sync_cf.py               # ETL Codeforces (com Gym dinâmico)
│   │   │   ├── sync_atcoder.py          # ETL AtCoder
│   │   │   ├── sync_atcoder_metadata.py # Enriquecimento de metadados AtCoder
│   │   │   ├── sync_cf_metadata.py      # Enriquecimento de metadados CF
│   │   │   ├── sync_cf_gym_metadata.py  # Metadados específicos de Gyms
│   │   │   ├── sync_all.py              # Orquestrador de todos os syncs
│   │   │   └── import_cses.py           # Importação do catálogo CSES
│   │   ├── services/
│   │   │   ├── codeforces_client.py     # Cliente HTTP Codeforces
│   │   │   ├── atcoder_client.py        # Cliente HTTP AtCoder
│   │   │   ├── ai_classifier.py         # Engine Gemini com retry
│   │   │   └── scrapers/
│   │   │       ├── base.py              # BaseScraper (interface)
│   │   │       ├── codeforces.py        # Parser HTML do CF
│   │   │       ├── atcoder.py           # Parser HTML do AtCoder
│   │   │       ├── cses.py              # Parser HTML do CSES
│   │   │       ├── exceptions.py        # UnparseableProblemException
│   │   │       └── __init__.py          # Exportações
│   │   └── tests/
│   │       ├── test_fsm_tracking.py
│   │       ├── test_clients.py
│   │       ├── test_sync_pipelines.py
│   │       ├── test_scrapers.py
│   │       ├── test_api_predict.py
│   │       ├── test_ai_classifier.py
│   │       └── test_queue.py
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── lib/
        │   ├── api.ts                   # Instância Axios configurada
        │   └── ratings.ts              # getRatingColor (Single Source of Truth)
        ├── pages/
        │   ├── Queue.tsx
        │   ├── Contests.tsx
        │   ├── ContestDetail.tsx
        │   └── AILab.tsx
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── layouts/PageLayout.tsx
        │   ├── contests/
        │   │   ├── ContestCard.tsx
        │   │   ├── ContestProgressBar.tsx
        │   │   ├── ContestMetrics.tsx
        │   │   ├── ProblemStatusSelect.tsx
        │   │   ├── ProblemActionsCell.tsx
        │   │   └── types.ts
        │   ├── queue/
        │   │   ├── SortableRow.tsx
        │   │   ├── AddItemDialog.tsx
        │   │   ├── PlatformIcon.tsx
        │   │   ├── PriorityBadge.tsx
        │   │   ├── EditableDescription.tsx
        │   │   ├── constants.ts
        │   │   └── types.ts
        │   └── ui/
        │       ├── accordion.tsx, alert.tsx, badge.tsx
        │       ├── button.tsx, checkbox.tsx, dialog.tsx
        │       ├── dropdown-menu.tsx, input.tsx, select.tsx
        │       ├── skeleton.tsx, table.tsx, tooltip.tsx
        │       └── toast.tsx            # Sistema unificado com useToast
        ├── App.tsx
        └── index.css                   # Design tokens + CSS vars de rating
```

---

## 10. Próximos Passos (Backlog Priorizado)

### 🔴 Alta Prioridade
1. **Dashboard de Inteligência (`/dashboard`):** Painel com gráficos de evolução do rating ao longo do tempo, tags mais erradas, distribuição Live vs Upsolve, e streak de estudo. Usar `recharts` ou `visx`.
2. **Página de Perfil (`/profile`):** Exibir métricas pessoais consolidadas, handles cadastrados, e permitir atualização de `cf_handle`, `cses_token`, `atcoder_handle`.

### 🟡 Média Prioridade
3. **Cron Jobs de Sync Automatizado:** Substituir o sync manual por tarefas periódicas (Django-Q ou Celery) para manter o banco sempre atualizado sem intervenção do usuário.
4. **Página de Caderno/Notas (`/notes`):** Editor de markdown para registrar soluções, insights de algoritmos e anotações por problema ou por sessão.
5. **Filtros Avançados na Queue:** Filtragem por plataforma, rating range, e tags. Ordenação persistida.

### 🟢 Baixa Prioridade / Futuro
6. **Suporte a Times (`/teams`):** Cadastro de time com múltiplos usuários, visão agregada do upsolving do grupo, quem resolveu o quê.
7. **Exportação de Relatórios:** PDF ou CSV com histórico de upsolving para análise offline ou compartilhamento.
8. **Expansão de Plataformas:** Suporte a SPOJ, UVa, ou Codeforces Gym via busca manual de ID.
9. **Modo Mock da IA:** Flag de desenvolvimento para simular respostas da IA sem consumir cota de API (útil para desenvolver UI do AILab sem internet ou cota).

---

## 11. Decisões Técnicas Registradas

| Decisão | Alternativa considerada | Motivo da escolha |
|---|---|---|
| Django Ninja ao invés de DRF | Django REST Framework | Tipagem automática via Pydantic, menos boilerplate, documentação OpenAPI gerada automaticamente |
| `@tanstack/react-query` para estado server | Redux / Context API | Gerenciamento de cache, invalidação e refetch automático sem boilerplate de actions/reducers |
| `getRatingColor` em arquivo utilitário | Lógica inline em cada componente | DRY: uma mudança nos breakpoints afeta todos os componentes automaticamente |
| Factory de Scraper via `if/elif` na API | Registry de classes / metaclasses | Simples, legível, extensível. Complexidade desnecessária com menos de 5 plataformas |
| `errors.APIError` do `google-genai` para rate limit | `google.api_core.exceptions.ResourceExhausted` | Novo SDK não depende de `google.api_core`; `errors.APIError` é o ponto correto |
| `UnparseableProblemException` custom | Levantar `ValueError` ou retornar `None` | Semântica clara no endpoint (converte para HTTP 400 com mensagem descritiva) |
| Forçar add de `frontend/src/lib/` no git | Mover o diretório | `.gitignore` raiz tem `lib/` (padrão Python). Correto era forçar o path específico do TS |
