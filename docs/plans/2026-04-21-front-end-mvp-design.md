# Forja Tracker Frontend MVP - Design Spec

## 1. Contexto e Objetivo
Este documento define o design do Frontend MVP do projeto Forja, focado em duas telas principais: **Fila de Upsolving (Queue)** e **Dashboard de Contests**. O sistema serve como um tracker implacável para estudantes de Programação Competitiva.

## 2. Direção de Arte (Estética e Cores)
* **Tema Principal**: Dark RPG / Elite Hacker. 
* **Background Primário**: Preto profundo (HEX: `#050505` ou `#000000`). Sem tons azulados, deve ser extremamente escuro.
* **Cor de Acento 1 (Urgência)**: Vermelho Carmesim (Crimson Red). Usado para destacar tarefas prioritárias (ex: `P0`) ou abas ativas.
* **Cor de Acento 2 (Atenção)**: Laranja Queimado (Burnt Orange). Usado para prioridades secundárias (ex: `P1`).
* **Nota Estética**: Evitar botões brilhantes, neon ou excesso de bordas. O design deve parecer sóbrio, perigoso e focado na performance (semelhante à Vercel ou Notion no modo ultra dark).

## 3. Estrutura Global (App Shell)
* **Sidebar Esquerda (Navegação)**: Uma barra lateral vertical e minimalista. Deve conter ícones achatados com rótulos em português: Perfil, Equipes, Dashboard, Upsolving, e Fila. A aba "Fila" deve estar ativada com uma leve borda vermelha lateral.

## 4. Main Component: A Tabela (Queue / Upsolving)
* **Estilo Geral**: Tabela de altíssima densidade de dados focada em produtividade. Sem botões enormes de "Editar". Cada linha deve imitar uma planilha do Notion, pronta para edição *inline*.
* As colunas horizontais são:
  1. **Status**: Um pequeno checkbox cinza apagado (indicando se a dívida foi resolvida).
  2. **Problema**: O nome do problema (ex: '[Codeforces] Mathematics'). Deve ser antecedido pelo emoji 🎈. O texto deve ter peso Forte (Bold).
  3. **Data**: Data (ex: `15/04/2026`) com cor cinza bem sutil.
  4. **Prioridade** (O ponto de vida/cor da interface): Pequenos "Badges/Pills" contendo rótulos e color coding. Para badges com texto `P0`, fundo Vermelho Carmesim. Para `P1`, fundo Laranja. Para `Upsolving`, fundo magenta ou bordô sombrio.
  5. **Tags / Assuntos**: Espaço para texto descritivo esmaecido (ex: `DP, Graphs`).

## 5. Experiência de Interação (UX)
* **Edição**: Ao clicar na célula da tabela (ex: no badge P0), o usuário vê um pequeno "select/dropdown" minimalista (*inline*). 
* Todo o foco é na velocidade. O texto deve estar em tipografia moderna como inter, mas sem arredondamentos agressivos (`rounded-md` no máximo) para manter o tom militar/agressivo da ferramenta.
