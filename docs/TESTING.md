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
3. **Fluxo Completo / E2E de API**: Simulação de ponta a ponta chamando endpoints da API Ninja via `client` HTTP e validando alterações persistidas no banco (ex: `test_set_password_api.py`, `test_dashboard.py`).

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

## 11. Tarefas em Background e Pendências Conhecidas

- Tarefas disparadas assincronamente ou via threads em segundo plano devem ser controladas ou mockadas durante a suíte.
- **Pendência conhecida no AtCoder**: O endpoint `/api/sync/atcoder` dispara uma thread em background (`threading.Thread`) para o scraper do AtCoder em ambiente real. Em suítes de teste usando SQLite em memória (`:memory:`), o acesso concorrente da thread ao banco em memória pode gerar o log `database table is locked: api_user` no console. O teste valida que a resposta HTTP 200 é emitida corretamente.

---

## 12. Fluxo TDD na Forja

1. **RED**: Escrever o teste para o comportamento desejado e confirmar que falha pela razão correta.
2. **GREEN**: Implementar a solução mínima no código de produção até o teste passar.
3. **REFACTOR**: Refatorar o código mantendo os testes passando.
4. **Validação**: Executar o teste direcionado e em seguida a suíte completa.

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

- [ ] `pytest --collect-only` confirma que nenhum teste foi perdido ou desativado.
- [ ] `python -m pytest` executa 100% verde (63 passed).
- [ ] `manage.py check` não relata erros de configuração.
- [ ] `git diff --check` não retorna erros de espaçamento/whitespace.
- [ ] Nenhum `.env`, token, chave de API ou banco de dados foi incluído.
