# Prévia visual local da Forja

Acesse **http://127.0.0.1:5173**. O frontend usa **http://127.0.0.1:8000/api**, com as rotas reais e uma cópia SQLite independente. A faixa amarela identifica a prévia.

## Contas exclusivamente locais

Senha das três contas: `ForjaLocal2026!`.

| Conta | Conteúdo |
|---|---|
| `preview_real` | Histórico do usuário 9 na cópia do banco local: 46 participações, questões e fila reais. Datas originais preservadas. |
| `preview_qa` | Atividade recente, prova com 15 questões, erros antes/depois do AC, upsolving, conclusão manual, ratings oficiais/IA/ausentes, títulos extensos, rankings e históricos parciais. |
| `preview_empty` | Conta inicialmente vazia para revisar os estados sem histórico. |

Essas credenciais não correspondem à conta publicada. A preparação altera o login e a senha do usuário escolhido **apenas na cópia**, mantendo seus relacionamentos e histórico. As ações de revisão podem modificar as contas locais.

O banco local original tem submissões até junho de 2026. A conta `preview_real` pode mostrar sete dias sem atividade; use `preview_qa` para conferir esse card preenchido. Nenhuma data real foi deslocada.

## Iniciar a prévia existente

Dois terminais PowerShell, na pasta do projeto. Não é necessário preparar o banco novamente.

Backend:

```powershell
Set-Location C:\Users\bmbem\Bernardo\Projetos\forja\backend
$env:VISUAL_PREVIEW_DB = Join-Path (Get-Location) 'var\visual-review\preview-v2.sqlite3'
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=core.settings_visual_preview --noreload
```

Frontend:

```powershell
Set-Location C:\Users\bmbem\Bernardo\Projetos\forja\frontend
npm.cmd run dev:preview
```

Encerre cada servidor com Ctrl+C no respectivo terminal. Use as portas indicadas; o Vite interrompe a inicialização se a 5173 estiver ocupada.

## Criar ou restaurar uma cópia limpa

Pare o backend. Escolha **um nome novo**, por exemplo `preview-v3.sqlite3`, para preservar a revisão anterior. A preparação recusa sobrescrever arquivos existentes.

```powershell
Set-Location C:\Users\bmbem\Bernardo\Projetos\forja\backend
$env:VISUAL_PREVIEW_DB = Join-Path (Get-Location) 'var\visual-review\preview-v3.sqlite3'
.venv\Scripts\python.exe manage.py prepare_visual_preview --settings=core.settings_visual_preview --source-user=9
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=core.settings_visual_preview --noreload
```

O comando faz backup SQLite com origem aberta em modo somente leitura, aplica migrations exclusivamente na cópia e prepara as contas locais. `--source-user=9` é o usuário que contém as participações neste banco. Não executar migrations com os settings normais para preparar esta prévia.

## Isolamento

- Os settings substituem `DATABASE_URL` herdada por SQLite dentro de `backend/var/visual-review/` e restringem hosts a loopback.
- A chave de sessão é exclusiva da prévia; e-mails ficam em memória e links de frontend apontam para localhost.
- Sync de plataformas e classificação que grava metadados do produto retornam 403. Fila e triagem continuam editáveis na cópia.
- No Explorar, os botões **Com rating oficial** e **Sem rating oficial** carregam exemplos da base local. O seletor **Cenário da prévia** oferece sucesso, rating exato, superestimativa, subestimativa, resultado parcial, imagens não analisadas e erro do provedor. As respostas são simulações explícitas, sem scraper, provedor ou persistência. Sem cenário válido, a requisição é recusada.
- O benchmark lê os snapshots publicados do repositório pela API local. Não executa avaliações nem habilita resultados privados.
- O modo visual só é ativado em desenvolvimento, com `--mode visual-preview` e URL de API loopback. Uma URL remota sobrescrita por variável de ambiente interrompe a inicialização da API da prévia. O build de produção não habilita os controles de simulação.
- Arquivos SQLite, capturas e logs de revisão estão sob `backend/var/`, ignorados pelo Git.

Os links externos das questões continuam apontando para suas plataformas; não são necessários para revisar o layout. Os identificadores da conta sintética não representam provas publicadas.

## Roteiro de revisão

1. `preview_real`: Dashboard, as 15 barras de tópicos, Fila e detalhe de uma prova longa. Conferir títulos, ícones, ratings e contraste sem alterar a fonte do navegador.
2. Contests: acessar **Ver resultados por contest**, alternar Resoluções/Ranking, incluir upsolving, selecionar uma participação e conferir data e numerador/denominador.
3. Detalhe: verificar que a tabela precede **Placar da prova**, usar **Ver placar**, a legenda e **Ir para questão**; abrir resultado e triagem por teclado/toque.
4. `preview_qa`: a prova de 15 questões inclui A com `+` sem erro antes do AC; B com `+2`; C com CE fora do contador; E/F com resolução posterior; O com conclusão manual. Históricos parciais ficam nas outras três provas. Para abrir esses casos, sair da conta real, entrar com `preview_qa` e abrir o primeiro Treino local em Contests.
5. Fila: prioridade, descrição, concluir/desfazer, arrastar e agrupar. A faixa lateral de prioridade e seu controle experimental foram removidos; o badge continua disponível. Conferir o fundo cinza ao passar sobre a linha e o sublinhado apenas ao passar sobre o título clicável, incluindo a lista agrupada. Recarregar a página para confirmar persistência das edições. Usar `preview_empty` para o estado vazio.
6. AI Playground: conferir os três conjuntos de resultados salvos, os denominadores do MAE/F1 e a escala do mapa de calor. Selecionar um ponto agrupado; Escape fecha o detalhe e devolve foco.
7. Explorar: clicar **Com rating oficial**, escolher o cenário e clicar **Classificar**. A comparação mostra oficial, estimado e diferença com sinal, inclusive no acerto exato. **Sem rating oficial** permite verificar a ausência de referência. Nenhuma chamada de IA é necessária.

Capturas e registro dos testes: `backend/var/visual-review/`. O relatório da implementação está em `docs/plans/2026-10-29-visual-implementation-results.md`.
