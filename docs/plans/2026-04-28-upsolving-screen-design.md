# Design: Tela de Upsolving

**Data:** 2026-04-28  
**Autor:** Bernardo + Raul (Agente)  
**Status:** Aprovado ✅

---

## Visão Geral

A Tela de Upsolving é o coração da proposta de valor da Forja: ela transforma os dados brutos de submissões coletados pelos ETLs em **inteligência acionável de estudo**. O fluxo narrativo é:

> "Quais contests me deixaram dívida?" → "Quais questões exatamente precisam ser resolvidas?"

A feature é composta por duas rotas novas:

| Rota | Descrição |
|------|-----------|
| `/contests` | Lista de todos os contests com participação do usuário |
| `/contests/:id` | Detalhe de um contest específico com tabela de upsolving |

---

## Tela 1 — `/contests` (Lista de Contests)

### Header de Métricas Globais
Quatro cards estatísticos no topo da página, alimentados pelo endpoint `GET /stats` já existente:
- **Total de Contests** participados
- **Questões Resolvidas Live** (durante o contest)
- **Dívidas Abertas** (PENDING_UPSOLVE ainda sem resolução)
- **Questões Upsolvadas** (resolvidas após o contest)

### Grid de Cards de Contest
Cada card exibe:
- **Badge de Plataforma** colorido: `CF_OFICIAL` (azul), `CF_GYM` (roxo), `ATCODER` (laranja)
- **Nome do Contest** + Data de participação
- **Barra de Progresso Segmentada:** representação visual das questões
  - 🟢 Verde: AC durante o contest (`SOLVED_LIVE`)
  - 🟡 Amarelo: Pendente de upsolving (`PENDING_UPSOLVE`)
  - ⬛ Cinza: Não tentada (`UNATTEMPTED`)
  - 🔵 Azul: Upsolvada (`UPSOLVED`)
- **Contagem textual:** `3 AC · 2 dívidas · 1 não tentada`
- **Tag de dívida** em destaque vermelho/amarelo se `upsolve_count > 0`: `2 dívidas abertas`

### Ordenação Padrão
Contests com dívidas abertas aparecem primeiro. Dentro do grupo, ordena por data (mais recente primeiro).

---

## Tela 2 — `/contests/:id` (Detalhe do Contest)

### Header do Contest
- Nome, data e plataforma
- Mini-barra de progresso igual ao card

### Filtros Pill
Botões de filtro rápido sobre a tabela:
`Todas | Pendentes | Resolvidas | Não Tentadas`

### Tabela de Problemas
| Coluna | Descrição |
|--------|-----------|
| **#** | Index da questão (A, B, C...) |
| **Título** | Nome do problema |
| **Rating** | Colorizado com as cores de rating do CF |
| **Tags** | Chips de tags (truncadas se muitas) |
| **Status** | Dropdown inline para alterar `review_status` |
| **Ações** | Conjunto de ícones de ação |

### Ações por Linha (coluna "Ações")
- 🔗 **Link Externo** — abre o problema na plataforma original em nova aba
- 📋 **Adicionar à Fila** — adiciona ao `QueueItem` com `priority=UPSOLVING`, sem dialog, exibe toast de confirmação
- 🤖 **IA (placeholder)** — botão desabilitado com tooltip "Em breve: Estimar rating e tags com IA"

### Status Inline (Dropdown)
Permite alterar o `review_status` do `UserProblemTracking` diretamente na tabela:
- `PENDING_TRIAGE` → Pendente de Triagem
- `DOABLE` → Dá pra fazer
- `DONE` → Concluído
- `FUTURE` → Muito avançada
- `IGNORED` → Ignorada

---

## Arquitetura de Backend (Gaps a Resolver)

### Novos Endpoints Necessários em `api.py`

#### `GET /contests`
Retorna lista de `ContestParticipation` do usuário com contagens dinâmicas calculadas via `UserProblemTracking`.

#### `GET /contests/{contest_id}/problems`
Retorna todos os `Problem` ligados ao contest com o `UserProblemTracking` do usuário injetado em cada item.

#### `PATCH /tracking/{problem_id}`
Atualiza o `review_status` de um `UserProblemTracking`. O modelo já tem a State Machine protegida no `save()`.

### Fix no `sync_cf.py`
Os campos `solve_count`, `upsolve_count` e `total_problems` do `ContestParticipation` são criados zerados. A contagem deve ser calculada dinamicamente na query do endpoint `/contests` usando `UserProblemTracking`, eliminando a necessidade de corrigi-los no sync (abordagem mais robusta).

---

## Decisões de Design

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Layout dos contests | Cards em grid | Mais visual e expressivo que tabela simples |
| Adicionar à fila | Sem dialog, priority=UPSOLVING | Fluxo ágil, menos fricção |
| Status inline | Dropdown na tabela | Ferramenta de trabalho ativa, não só visualização |
| Botão IA | Placeholder desabilitado | Reserva o espaço na UI sem overhead agora |
| Contagens de contest | Dinâmicas via query | Mais robusto que campos cacheados no sync |

---

## Componentes Frontend Novos

```
src/
  pages/
    Contests.tsx          # Lista de contests
    ContestDetail.tsx     # Detalhe + tabela de upsolving
  components/
    contests/
      ContestCard.tsx         # Card individual de contest
      ContestMetrics.tsx      # Header com 4 métricas globais
      ContestProgressBar.tsx  # Barra segmentada visual
      ProblemStatusSelect.tsx # Dropdown inline de review_status
      ProblemActionsCell.tsx  # Célula de ações (link + fila + IA)
```
