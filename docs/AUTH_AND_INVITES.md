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

### 👥 Novo Sistema de Convite e Redefinição de Senha
- **Comando de Convite (`invite_user`)**: Cria estritamente novos usuários no banco com `is_active=False` e senha inutilizável (`set_unusable_password()`). Caso o username já exista, falha com `CommandError` orientando o uso do comando de reset.
- **Comando de Redefinição (`reset_user_password`)**: Gera um link de redefinição para usuários previamente cadastrados sem alterar seus dados, handles ou status, preservando a senha atual até o uso efetivo do link.
- **Validade do Link**: Configurado explicitamente para 3 dias (`PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3`).
- **Política de Senha da Forja**: Mínimo de 8 caracteres, contendo pelo menos uma letra, um dígito numérico e um caractere especial (espaço não conta).
- **Endpoint Transacional (`/api/auth/set-password`)**: Valida o token nativo do Django com lock de linha (`select_for_update`) dentro de `transaction.atomic()`, grava a nova senha e ativa o usuário (`is_active=True`).
- **Interface Visual (`/set-password`)**: Página responsiva com validação local espelhada, bloqueio de múltiplos envios e feedback integrado ao tema da Forja.

---

## 2. Como Usar o Sistema de Convite e Reset

### 2.1 Convidar Novo Membro (`invite_user`)
Para registrar um novo membro da equipe:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py invite_user <username> --cf_handle <handle_cf> --atcoder_handle <handle_atcoder> --email <email>
```

#### Exemplo em Desenvolvimento Local:
```powershell
.\.venv\Scripts\python.exe manage.py invite_user novato --cf_handle novato_cf --base_url http://localhost:5173
```

#### Exemplo em Produção / Render:
```bash
python manage.py invite_user novato --cf_handle novato_cf
```

O terminal exibirá uma saída com token fictício ilustrativo:
```text
✅ Usuário 'novato' criado no banco de dados!

======================================================================
🔗 LINK DE CONVITE / DEFINIÇÃO DE SENHA GERADO COM SUCESSO:

   https://forja-cp.vercel.app/set-password?uid=TOKEN_FICTICIO_UID&token=TOKEN_FICTICIO_SECRET

======================================================================
Copie e envie esse link para o membro da equipe.
Esse link expira em 3 dias e torna-se inválido após o uso.
```

---

### 2.2 Redefinir Senha ou Reenviar Convite Pendente (`reset_user_password`)
Para gerar um link para quem já possui registro no sistema:
- **Usuário Ativo**: Gera o link de redefinição de senha. A senha atual permanece ativa até o uso do link.
- **Usuário Inativo**: Regenera o link de convite pendente. Gerar o link **não ativa** a conta; a ativação ocorre somente ao consumir o link com sucesso em `/set-password`.

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py reset_user_password <username>
```

#### Exemplo com `--base_url` customizado:
```powershell
.\.venv\Scripts\python.exe manage.py reset_user_password novato --base_url http://localhost:5173
```

O terminal exibirá:
```text
ℹ️ Usuário 'novato' localizado.

======================================================================
🔗 LINK DE DEFINIÇÃO / REDEFINIÇÃO GERADO COM SUCESSO:

   http://localhost:5173/set-password?uid=TOKEN_FICTICIO_UID&token=TOKEN_FICTICIO_SECRET

======================================================================
Copie e envie esse link para o membro da equipe.
A senha atual continua ativa até que este link seja utilizado.
(ou: A conta permanece inativa até que este link seja utilizado para definir a senha.)
```

---

### 2.3 Ativação e Definição da Senha
1. O administrador envia o link gerado para o colega.
2. O usuário acessa `/set-password` e digita a nova senha respeitando a política (mínimo 8 caracteres, letra, número e símbolo).
3. Ao enviar, a operação atômica grava a nova senha, define `is_active=True` (no caso de convite pendente) e invalida o token contra reuso.
4. O usuário é redirecionado para o login.

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
