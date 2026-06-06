# Resumo do Projeto Forja - Status de Desenvolvimento
**Data:** 28 de Abril de 2026

Este documento compila as realizações arquitetônicas, componentes implementados e metodologias estabelecidas até o momento, cobrindo o Backend (Cérebro da aplicação), Frontend (Apresentação Visual) e os Testes em relação ao framework da "Forja". Serve como base formal de planejamento para os próximos *sprints*.

---

## 1. Backend (🧠 Cérebro Mestre e Modelagem)

A estrutura da API tem como espinha dorsal a aplicação de **Domain-Driven Design (DDD)**, onde as regras de transição de estado estão encapsuladas dentro dos próprios modelos. 

### Modelos Centralizados (Single Source of Truth)
- **`Problem`, `Contest`, `Submission`, `Team`, `User`:** Os recursos basilares do projeto, implementados com abstrações para acomodar flexivelmente plataformas como Codeforces (Oficial e Gyms), AtCoder e CSES.
- **`UserProblemTracking`:** Centraliza a inteligência de acompanhamento da "Dívida Técnica" e "Triagem". O estado de resolução baseia-se em uma "State Machine" que sincroniza a visão técnica do sistema (`system_status` — `SOLVED_LIVE`, `PENDING_UPSOLVE`, `UPSOLVED`, `PRACTICE_AC`, etc) bidirecionalmente com a triagem manual do aluno (`review_status` — `DOABLE`, `PENDING_TRIAGE`, `DONE`, `TEAM_DONE`, etc). O modelo detecta magicamente transições de estado pelo método `_sync_system_to_review` e protege progressos de sucesso prévios.
- **`ContestParticipation` & `QueueItem`:** Mapeamento do envolvimento do usuário em concursos para geração de métricas de Live Solve vs Upsolving, e o modelo `QueueItem` concebido para a UI da Matriz de Fila, gerindo estudos não apenas técnicos isolados, como pormenores teóricos (`STUDY_SESSION`).

### Arquitetura de Integração (ETL - Extração, Transformação e Carga)
As pipelines de ingestão de plataformas garantem um processamento robusto para extrair metadados e os históricos dos estudantes:
- **Separação Responsável:** Separação canônica entre lógicas de requisições web (`api/services/codeforces_client.py`, `atcoder_client.py`) e fluxos de dados organizados em *management commands* (`sync_cf.py`, `sync_atcoder.py`).
- **Lógica de Sincronização Incremental:** Abordagem utilizando *timestamps* e contadores de epoch para não congestionar as APIs de terceiros.
- **Tratamento Específico de Codeforces Gyms:** A complexidade da API restrita de "Gyms" foi desvendada; a plataforma lida ativamente com Gyms distinguindo contagem de submissões em tempo oficial `SOLVED_LIVE` e `UPSOLVED`.
- **Hierarquia Estrita de FSM:** Corrigido o bug de regressão de status ao processar submissões em ordem cronológica (Ex: `PRACTICE_AC` agora não pode mais sobrescrever um `SOLVED_LIVE` anterior). O histórico de "Dívida Técnica" não sofre rebaixamentos em resubmissões, garantindo a integridade da jornada do aluno.
- **Admin App:** Utilização ágil do Admin do Django customizado para supervisionar, depurar o estado dos eventos e validar se os metadados brutos (tags JSON, rates de cor) estão entrando corretamente.

---

## 2. Frontend (🎨 UX, Estética Premium e Componentização)

No ambiente gráfico, buscamos abolir o visual monótono das plataformas competitivas e forjar uma experiência com "Aesthetics Premium" capaz de guiar o fluxo e despertar engajamento produtivo através do *design vivo*.

- **Base de Ferramentas:** Utilização de `React.js` + `Vite` tipado restritamente por `TypeScript` aliando com os utilitários massivos do `Tailwind CSS`.
- **System Design & Cores de Avaliação (Competitivas):** Cores de preenchimento (`var(--text-grandmaster)`, `var(--bg-expert)` etc) referenciando os níveis clássicos do Codeforces/AtCoder agora injetados como Design Tokens globais num `index.css` de alto volume, viabilizando temas com *Glassmorphism* (efeitos translúcidos, `backdrop-blur`).
- **Componentização Inicial:**
  - `PageLayout.tsx`: Configuração de contêineres e margens com visual refinado, servindo de shell para as seções de app.
  - Componentes responsivos criados na filosofia atômica (`checkbox.tsx`, `PageTitle`).
  - **Queue Interface:** Concepção da tabela matriz "Fila" que reflete as instâncias de `QueueItem`, com formatação de colunas dimensionada e colorificações nativas acopláveis dinamicamente ao Rating dos problemas.
  - **Contests Dashboard (`Contests.tsx` & `ContestDetail.tsx`):** Criação de um painel visual unificado para rastreamento de concursos, incorporando `ContestCard` interativos com efeitos *glassmorphism* e hover guiado pela cor primária. Apresentação em tempo real do nível de Upsolving ("Dívida Técnica") através da barra de progresso (`ContestProgressBar`), e uma tabela rica com formatação condicional baseada na FSM (`ProblemStatusSelect`).

---

## 3. Testes e Garantia de Qualidade (🧪 Test-Driven Safety)

Adotado para reverter e rastrear inconsistências com segurança algorítmica. O servidor de testes valida e previne *regressões lógicas* essenciais no controle da complexidade da Máquina de Estados (State Machine) e Injeções:

- **Unidades de Testes Implementadas (`backend/api/tests/`):**
  - **`test_fsm_tracking.py`:** Cobertura implacável das dezenas de transições para o tracker individual (`UserProblemTracking`). Exposição programática atestando que, se um usuário tiver feito submissão com flag de "PRACTICE", o estado correto (`PRACTICE_AC` e review status adaptado) será refletido, ou de Live para Contestando.
  - **`test_clients.py`:** Estabelecimento de *mocking* e interceptação das chamadas de requisições de serviço (`CodeforcesClient` e `AtCoderClient`) para validar que metadados incorretos e rate-limits são rejeitados com as *Exceptions* apropriadas.
  - **`test_sync_pipelines.py`:** Proteção sobre o banco confirmando a atomicidade das gravações para que nenhuma inconsistência trave a rotina `sync_all`.

---

## 4. Oportunidades para Planejamento Futuro (Próximos Passos)

1. **Desenvolvimento de APIs RESTful:** Expor os Dados via DRF (Django Rest Framework) usando Serializers seguros conectando a visão do DRF ao React.
2. **Dashboard Visual (Frontend):** Plugar a "Queue Interface" finalizada com o DRF, testando mutações interativas (Drag & Drop na fila, mudança de tags e status e sincronizar retroativamente ao Django).
3. **ETL Avançado:** Melhorar extração em massa (cron jobs) ou webhooks, automatizar o CSES usando scrapers via requests avançadas. 
4. **Relatórios e Gráficos de Ritmo:** Aproveitar a completude dos dados das sessões registradas para exibir visualizações gerenciais (Live vs Upsolve, tags mais erradas).
