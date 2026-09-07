# Guia de Autenticação, Sessão e Convites da Forja

Este documento resume as melhorias arquiteturais de segurança, estabilização da suíte de testes e o novo fluxo de convites para membros da equipe na plataforma **Forja**.

---

## 1. O que Mudou?

### 🛡️ Segurança & Infraestrutura
- **Remoção de Credenciais Estáticas**: O comando provisório `seed_users.py` e suas chamadas no `build.sh` foram completamente eliminados.
- **Isolamento de Deploy**: O script de build do Render agora cuida estritamente de infraestrutura (`collectstatic`, `migrate`), sem semear dados de negócio.
- **Eliminação de Arquivos de Rascunho**: Scripts temporários de teste soltos na raiz foram removidos, permitindo a execução limpa do `pytest`.

### ⏱️ Sessão Duradoura e Renovação Silenciosa (Silent Refresh)
- **Token JWT com 30 Dias de Vida**:
  - `ACCESS_TOKEN_LIFETIME`: 1 dia (enviado nas requisições).
  - `REFRESH_TOKEN_LIFETIME`: 30 dias (usado para renovar o acesso).
- **Interceptador no Axios (`api.ts`)**:
  - Quando o token expira (`HTTP 401`), o frontend intercepta o erro em background, chama `/api/token/refresh` usando o `refresh_token`, atualiza o `localStorage` e repete a requisição original de forma 100% transparente para o usuário.
  - O usuário não é mais deslogado no meio do uso.

### 👥 Novo Sistema de Convite e Definição de Senha
- **Comando de Gerenciamento (`invite_user`)**: Permite ao administrador convidar ou resetar a senha de membros gerando links criptográficos seguros e temporários.
- **Endpoint Seguro (`/api/auth/set-password`)**: Valida o token nativo do Django e grava o hash da nova senha no banco.
- **Interface Visual (`/set-password`)**: Página responsiva com feedback visual e integração ao tema visual da Forja.

### 🧪 Suíte de Testes 100% Verde
- **38 testes passando no `pytest`** cobrindo todos os módulos: FSM de tracking, predição IA com Gemini, scrapers de Codeforces/AtCoder/CSES, fila de estudos e autenticação.

---

## 2. Como Usar o Sistema de Convite de Usuários

### Passo 1: Gerar o Link de Convite
No terminal do seu computador (na pasta `backend`), execute o comando `invite_user`:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py invite_user <username> --cf_handle <handle_cf> --atcoder_handle <handle_atcoder>
```

#### Exemplo Prático:
```powershell
.\.venv\Scripts\python.exe manage.py invite_user bernardomaia --cf_handle bernardomaia
```

O terminal exibirá uma saída como esta:
```text
✅ Usuário 'bernardomaia' criado no banco de dados!

======================================================================
🔗 LINK DE CONVITE / DEFINIÇÃO DE SENHA GERADO COM SUCESSO:

   https://forja-cp.vercel.app/set-password?uid=MQ&token=csm14e-b537c356b2cf77fa33d1b3799616d2b5

======================================================================
Copie e envie esse link para o membro da equipe.
Esse link expira automaticamente e torna-se inválido após o uso.
```

---

### Passo 2: O Colega Define a Própria Senha
1. Você envia o link gerado para o colega (via WhatsApp, Discord, etc.).
2. Ele acessa a página e digita a senha escolhida com confirmação.
3. Ao salvar, a conta é ativada imediatamente e ele é redirecionado para a tela de login.

---

## 3. Comandos Úteis do Projeto

### Rodar os Testes Automatizados do Backend
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

### Compilar o Frontend
```powershell
cd frontend
npm run build
```

### Iniciar o Servidor de Desenvolvimento Local
```powershell
# Backend (Terminal 1)
cd backend
.\.venv\Scripts\python.exe manage.py runserver

# Frontend (Terminal 2)
cd frontend
npm run dev
```
