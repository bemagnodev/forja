<div align="center">

# Forja

**A full-stack platform for turning competitive programming activity into structured training.**

![Status](https://img.shields.io/badge/status-active%20development-F59E0B)
![Demo](https://img.shields.io/badge/demo-online-22C55E)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

**[Live Demo](https://forja-cp.vercel.app/)** | **[Technical Highlights](#engineering-highlights)** | **[Roadmap](#roadmap)**

</div>

## Live demo

```text
Username: forja_demo
Password: DemoForja2026!
```

The demo account is populated with public data from [tourist](https://codeforces.com/profile/tourist), one of the most successful competitive programmers of all time. This provides a large, realistic dataset that fully populates the dashboard and its visualizations.

> The data is used for demonstration purposes only. Forja is not affiliated with or endorsed by tourist.

## Why Forja?

Contest history, upsolving debt, study priorities, and performance metrics are usually scattered across platforms, spreadsheets, and notes.

I designed and developed Forja independently to give my three-person competitive programming team a single training workflow. The platform is currently used by all three members to decide what to study next and track progress over time.

## Product preview

### Dashboard

![Forja dashboard](./docs/assets/dashboard.jpg)

Solved problems, acceptance rate, activity streaks, difficulty distribution, topic performance, and recent contests in one view.

### Study Queue

![Forja Study Queue](./docs/assets/study-queue.png)

A drag-and-drop workflow for prioritizing problems and theoretical study sessions, linking them to their source platforms, and tracking completion.

### Contests

![Forja contests](./docs/assets/contests.jpg)
A unified view of contest history, live solves, pending upsolving, and post-contest progress across supported platforms.

## What it does

- Synchronizes contests, problems, and submissions from **Codeforces**, **Codeforces Gym**, **AtCoder**, and **CSES**
- Tracks live solves, practice attempts, pending upsolving, and manually reviewed problems
- Organizes problems and study sessions in a priority-based queue
- Builds dashboards from submissions, topics, difficulty levels, streaks, and contest progress
- Separates each user's training data through JWT authentication

## Engineering highlights

- **Multi-platform synchronization:** API clients and scraping services normalize different platform formats into a shared model. Incremental synchronization reduces repeated requests and processing.
- **Problem state machine:** imported submission states and manual review states evolve together without overwriting completed or intentionally deferred work.
- **Analytics and performance:** database aggregations and optimized Django queries generate dashboard metrics while automated tests protect critical API, dashboard, and queue flows.

## Architecture and technologies

```text
Codeforces / Codeforces Gym / AtCoder / CSES
                      |
              Sync and scraping services
                      |
React + TypeScript <-> Django Ninja API <-> PostgreSQL
```

- **Frontend:** React, TypeScript, Vite, TanStack Query, Tailwind CSS, DnD Kit
- **Backend:** Python, Django, Django Ninja, JWT, pytest
- **Data:** PostgreSQL em produção, SQLite para desenvolvimento e testes locais

## Desenvolvimento Backend

### 1. Requisitos e Ambiente

- **Versão recomendada do Python:** 3.12 (Python 3.12.10)
- **Ambiente virtual oficial:** `backend\.venv`

### 2. Configuração e Ativação (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Validação do Django

Para checar a integridade da aplicação localmente:

```powershell
python manage.py check
```

_Nota:_ Comandos normais do Django (`manage.py runserver`, `migrate`, etc.) utilizam o banco de dados configurado no arquivo `backend\.env`.

### 4. Execução de Testes

Os testes automatizados utilizam um ambiente SQLite totalmente isolado em memória (`core.settings_test`), garantindo que a suíte nunca acesse ou afete o banco de produção/Supabase:

```powershell
python -m pytest
```

## Roadmap

- **Team analytics:** aggregated training metrics, member comparisons, and shared upsolving progress.
- **Collaborative notebook:** a shared library for algorithms, templates, snippets, and problem-solving notes.
- **AI-assisted classification:** expand the experimental AI Playground by comparing different language models and exploring machine-learning approaches for estimating difficulty, suggesting tags, and organizing training data.

## Author

Designed and developed by **Bernardo Magno**.

- [GitHub](https://github.com/bemagnodev)
- [LinkedIn](https://www.linkedin.com/in/bernardo-magno/)
