# Guia de Testes do Backend da Forja

## 1. Objetivo dos Testes
Garantir a corretude das regras de negócio, resiliência do pipeline de sincronização (Codeforces, AtCoder, CSES), segurança dos fluxos de autenticação/convites e estabilidade das integrações com IA e scrapers externos sem depender de serviços externos em tempo de execução de testes.

---

## 2. Estrutura de Diretórios

```text
backend/api/tests/
├── __init__.py
├── conftest.py                   # Fixtures compartilhadas globalmente
│
├── auth/                         # Autenticação, convites e senhas
│   ├── __init__.py
│   ├── test_invite_command.py          # Comando manage.py invite_user
│   ├── test_password_reset_command.py  # Comando manage.py reset_user_password
│   ├── test_set_password_api.py        # POST /api/auth/set-password & tokens
│   └── test_password_policy.py         # Validador de complexidade de senha
│
├── sync/                         # Sincronização incremental & Pipelines
│   ├── __init__.py
│   ├── test_codeforces_pipeline.py     # Sync CF, Gym & contest participation
│   ├── test_atcoder_pipeline.py        # Sync AtCoder (Kenkoooo API & WJ)
│   └── test_sync_api.py                # Endpoints POST /api/sync/*
│
├── services/                     # Integrações e clientes HTTP
│   ├── __init__.py
│   ├── test_clients.py                 # CodeforcesClient e AtCoderClient
│   ├── test_scrapers.py                # Scrapers HTML (CF, AtCoder, CSES)
│   └── test_ai_classifier.py           # Classificador Gemini & Mock Mode
│
├── test_dashboard.py             # Endpoint GET /api/dashboard/stats
├── test_prediction.py            # Endpoint POST /api/problems/{id}/predict
├── test_queue.py                 # Fila de estudos (QueueItem CRUD & prioridades)
└── test_tracking.py              # Máquina de estados (FSM UserProblemTracking)
```

---

## 3. Configuração do Ambiente de Teste

- **`backend/pytest.ini`**: Define `DJANGO_SETTINGS_MODULE = core.settings_test` e padrões de descoberta de arquivos (`python_files = tests.py test_*.py *_tests.py`).
- **`backend/core/settings_test.py`**: Herda todas as configurações do `settings.py`, mas força estritamente `DATABASES['default']` para SQLite em memória (`:memory:`). Possui checagem de segurança em tempo de execução que interrompe a suíte se tentar conectar ao PostgreSQL ou Supabase.
- **`backend/api/tests/conftest.py`**: Contém recursos reutilizáveis compartilhados em toda a suíte.

---

## 4. Tipos de Teste

1. **Unitário**: Testes de funções isoladas e classificadores (ex: `test_ai_classifier.py`, `test_password_policy.py`).
2. **Integração**: Testes de pipelines, scrapers com HTML simulado e comandos Django (ex: `test_codeforces_pipeline.py`, `test_invite_command.py`).
3. **Teste de Integração da API / Fluxo Completo do Backend**: Chamadas HTTP para os endpoints da API Ninja via `client` do Django/Pytest e verificação do resultado persistido no banco de dados isolado de testes. *Nota: esses testes não utilizam navegador real nem validam a renderização do frontend.*

---

## 5. Padrão Arrange–Act–Assert (AAA)

Todos os testes devem seguir visualmente a divisão em 3 etapas claras:

```python
@pytest.mark.django_db
def test_fsm_promotion_to_done():
    # Arrange (Preparação de dados)
    user = User.objects.create(username="test_user")
    problem = Problem.objects.create(platform=PlatformChoices.CF_OFFICIAL, platform_id="100A", title="Watermelon")
    tracker = UserProblemTracking.objects.create(
        user=user,
        problem=problem,
        review_status=UserProblemTracking.ReviewStatus.DOABLE
    )

    # Act (Execução da ação/regra de negócio)
    tracker.system_status = UserProblemTracking.SystemStatus.PRACTICE_AC
    tracker.save()

    # Assert (Verificação do resultado)
    tracker.refresh_from_db()
    assert tracker.review_status == UserProblemTracking.ReviewStatus.DONE
```

---

## 6. Convenção de Nomes

- Arquivos: `test_<dominio_ou_recurso>.py`.
- Funções: `test_<acao>_<cenario>_<resultado_esperado>()`.
- Exemplo: `test_invite_user_fails_if_user_already_exists`.

---

## 7. Uso de Docstrings

### Testes simples
Quando o nome da função for suficiente para expressar a intenção:

```python
def test_queue_priority_future(base_user):
    ...
```

### Testes de domínio complexo
Utilize docstring estruturada descrevendo Cenário, Ação e Resultado Esperado em pipelines de sincronização, máquina de estados FSM e regras de concorrência:

```python
"""
Cenário:
Uma submissão do Codeforces cai com veredito 'TESTING' e existem submissões antigas atrás da parede incremental.

Ação:
Executar o comando 'sync_cf'.

Resultado esperado:
- O ponteiro cf_last_sync_time avança apenas até a submissão válida.
- Submissões válidas são salvas no banco.
- Submissões antigas atrás da parede incremental são ignoradas.
"""
```

---

## 8. Fixtures e Helpers

- **Fixtures globais (`conftest.py`)**: Apenas recursos de uso generalizado (`base_user`, `api_client`, `sample_problem`).
- **Fixtures específicas de arquivo**: Mantenha no próprio arquivo com nomes descritivos (ex: `prediction_user`, `setup_problem` em `test_prediction.py`) para evitar colisões ou redefinições ocultas.
- Evite criar fixtures para cenários de dados únicos de um único teste.

---

## 9. Banco de Dados e Segurança

- Todo teste que interage com o ORM do Django deve ser decorado com `@pytest.mark.django_db`.
- **Regra Absoluta**: Os testes rodam 100% isolados em memória com SQLite via `core.settings_test`.
- É proibido realizar conexões com bancos Supabase / PostgreSQL de desenvolvimento ou produção nos testes.

---

## 10. Integrações Externas e Mocks

- **`responses`**: Utilizado para interceptar requisições HTTP (`CodeforcesClient`, `AtCoderClient`, Scrapers) e retornar JSONs/HTMLs mockados.
- **`unittest.mock.patch`**: Utilizado para simular tempo (`default_token_generator._now`), serviços de IA ou funções com efeitos colaterais.
- É proibido realizar chamadas HTTP reais para APIs externas durante os testes.

---

## 11. Tarefas em Background e Isolamento de Despacho

- **Despacho Assíncrono (`dispatch_sync`)**: Os endpoints da API (`/api/sync/cf` e `/api/sync/atcoder`) delegam o início de tarefas em segundo plano para a camada de serviços através de `dispatch_sync`.
- **Testes de API**: Os testes de endpoint mockam o `dispatch_sync` (`@patch("api.api.dispatch_sync")`) para verificar se o comando e o handle corretos foram solicitados. Nenhuma thread real deve escapar do ciclo do pytest.
- **Testes de Pipelines**: Os comandos de sincronização (`sync_cf`, `sync_atcoder`) são testados sincronicamente em arquivos próprios (`test_codeforces_pipeline.py`, `test_atcoder_pipeline.py`), garantindo determinismo total e prevenindo bloqueios concorrentes no SQLite (`database table is locked`).

---

## 12. Fluxo TDD na Forja

1. **RED**: Escrever o teste para o comportamento desejado e confirmar que falha pela razão correta.
2. **GREEN**: Implementar a solução mínima no código de produção até o teste passar.
3. **REFACTOR**: Refatorar o código mantendo os testes passando.
4. **Validação**: Executar o teste direcionado e em seguida a suíte completa.

### 12.1. Tratamento de Bugs de Produção e Migrations

Ao investigar e corrigir anomalias ou inconsistências de dados originadas em produção:

1. **Reprodução Inicial em RED**: Antes de qualquer alteração de código ou schema, reproduza o bug por meio de um teste automatizado RED isolado e registre a evidência da falha.
2. **Correção Mínima em GREEN**: Implemente estritamente o reparo necessário para fazer o teste passar.
3. **Testes de Regressão**: Mantenha o teste de reprodução na suíte como proteção permanente contra regressões.
4. **Data Migrations com `MigrationExecutor`**: Migrations que alteram, consolidam ou removem registros existentes devem possuir testes que executam a transição real de schema (`migrate_from` -> `migrate_to`) usando `django.db.migrations.executor.MigrationExecutor`. Não basta testar o estado pós-migration.
5. **Auditoria Prévia Obrigatória**: Novas constraints (`UniqueConstraint`, `CheckConstraint`) só devem ser criadas após auditoria minuciosa em modo somente leitura (`read-only`) dos dados existentes.
6. **Estratégia Fail-Closed**: Toda migration de saneamento de dados deve abortar com erro explícito (`raise RuntimeError`) se encontrar registros inesperados ou ambíguos. Nunca tome decisões destrutivas silenciosas em dados de usuários.
7. **Isolamento Absoluto**: Nenhum comando de teste ou migration de teste deve conectar ou ser executado diretamente contra o Supabase ou o banco de produção. Todo teste roda contra o banco SQLite em memória (`core.settings_test`).

---

## 13. Comandos Úteis

```bash
# Na pasta backend:

# 1. Coletar a lista de testes sem executá-los
.\.venv\Scripts\python.exe -m pytest --collect-only

# 2. Executar um arquivo específico
.\.venv\Scripts\python.exe -m pytest api/tests/auth/test_invite_command.py -v

# 3. Executar um teste específico por nome
.\.venv\Scripts\python.exe -m pytest -k "test_token_expiration_after_three_days"

# 4. Executar a suíte completa do backend
.\.venv\Scripts\python.exe -m pytest
```

---

## 14. Checklist Pré-Commit

- [ ] `pytest --collect-only` confirma que a quantidade de testes coletados não diminuiu sem justificativa documentada.
- [ ] `python -m pytest` executa toda a suíte sem falhas.
- [ ] `manage.py check` não relata erros de configuração.
- [ ] `git diff --check` não retorna erros de espaçamento/whitespace.
- [ ] Nenhum `.env`, token, chave de API ou banco de dados foi incluído.

---

## 15. Guia de Testes do Frontend

### Tecnologias Utilizadas
O frontend utiliza **Vitest** como test runner principal, acompanhado de **React Testing Library**, `@testing-library/jest-dom` para matchers customizados e `@testing-library/user-event` para simulação realista de interações do usuário no ambiente `jsdom`.

### Localização Co-localizada
Os testes de frontend são co-localizados junto ao arquivo testado:
- Componentes: `src/components/ProtectedRoute.test.tsx` (ao lado de `ProtectedRoute.tsx`).
- Páginas: `src/pages/Login.test.tsx` (ao lado de `Login.tsx`).
- Contextos e Libs: `src/contexts/AuthContext.test.tsx`, `src/lib/api.test.ts`.

### Boas Práticas e Regras de Implementação
1. **Simulação de Usuário**: Prefira sempre `userEvent` sobre `fireEvent` para representar melhor o comportamento real de navegação e preenchimento do formulário.
2. **Isolamento e Limpeza**: Em todo teste (via `beforeEach`), limpe explicitamente o `localStorage`, restaure os mocks (`vi.restoreAllMocks()` / `vi.clearAllMocks()`) e restaure timers reais se fake timers foram utilizados.
3. **Proibição de Requisições HTTP Reais**: Mocke as fronteiras de API (`api.post`, `api.defaults.adapter`, `axios.post`) ou instâncias do Axios. Nenhuma chamada HTTP externa deve ser realizada durante os testes.
4. **Níveis de Teste**:
   - **Teste de Componente / Unidade**: Valida comportamentos de componentes isolados ou hooks (ex: `PriorityBadge`, `AuthContext`).
   - **Integração Frontend**: Valida a interação entre formulários, contextos, interceptadores Axios e roteamento via `MemoryRouter` (ex: `Login`, `SetPassword`, `api.test.ts`).
   - **Futuro E2E**: Testes ponta-a-ponta (Playwright/Cypress) que validam todo o stack integrado com navegador real. Não fazem parte da suíte atual do Vitest.

### Comandos de Execução

```bash
# Na pasta frontend:

# 1. Executar a suíte completa do frontend (modo CI / run único)
npm test

# 2. Executar os testes em modo watch durante desenvolvimento
npm run test:watch

# 3. Executar um arquivo de teste específico
npx vitest run src/pages/Login.test.tsx
```
