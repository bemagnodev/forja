# Contests: placar, histórico e manutenção

As telas preservam os estados atuais de tracking. O placar é uma projeção de
submissões da participação: conclusão manual e prática posterior não reescrevem
o resultado obtido durante a prova.

## Interface

- Histórico com busca, filtros, ordenação e três linhas de cards: 9/6/3 conforme
  a largura. Voltar do detalhe recupera filtros, página e rolagem.
- Abaixo dos cards, evolução das últimas 10/20 participações do recorte. A série
  de upsolving começa desligada. Indicadores não se limitam à página dos cards.
- Faixa de questões e coluna Resultado compartilham o mesmo componente: `+`,
  `+2`, `−2`, `−`, tempo HH:MM e selo Upsolvada.
- O contador inclui erros de julgamento anteriores ao primeiro AC, ou todos os
  da sessão se não houve AC. O tooltip separa vereditos, erros posteriores ao AC
  e CE; compilação não entra no contador principal.
- `+?`, `−?`, `?` e tempo `—` indicam informação parcial; não equivalem a zero
  tentativas. O selo de uma conclusão manual explicita a ausência de AC confirmado.
- Gym é tratado como treino de equipe apenas no agrupamento visual. Não há nova
  gestão de equipes ou soma dos históricos dos integrantes.

## Persistência e API

A migração Django `0011_contest_result_metadata` é aditiva. Deve ser aplicada
antes de publicar o backend que consulta as novas colunas. Não altera enums ou
transições da máquina de estados e não executa backfill de dados externos.

Submissões passam a preservar `relative_time_seconds` e `session_start_time`.
Participações preservam início, cobertura conhecida do histórico, contexto da
colocação e penalidade importada. O sync normal registra esses metadados para os
novos dados sem baixar todo o histórico a cada clique.

`GET /contests/{id}/problems` exige participação do usuário e acrescenta
`contest_result`, sem remover os campos anteriores. Esse bloco contém:

- `accepted`, `failed_attempts`, `first_ac_seconds` e `coverage`;
- `errors_before_ac`, `errors_after_ac` e `compilation_errors`;
- `is_upsolved`, `upsolved_at` e `manual_completion`.

As leituras não fazem HTTP externo nem salvam tracking. A apuração busca as
submissões em lote, deduplica IDs e seleciona a sessão compatível com a
participação. Não usa o horário do primeiro envio como início de um virtual.
Submissões virtuais sem referência de sessão ficam fora da apuração e mantêm
a cobertura parcial, mesmo quando seu horário coincide com a janela da prova.
Quando há cobertura completa, cards, gráfico e resumo usam essa mesma projeção,
sem contar AC de outra sessão ou prática anterior como resultado da prova.
Históricos parciais preservam os totais legados de tracking. Um AC importado sem
referência de início não é apresentado como conclusão manual ou horário confirmado
de upsolving.

## Enriquecer um contest antigo

Use o ambiente virtual oficial em `backend`. O comando consulta o histórico
público CF para um handle e um contest já importados:

```powershell
.\.venv\Scripts\python.exe manage.py hydrate_cf_contest_stats --handle HANDLE --contest-id 106687
```

Por padrão, mostra uma prévia e não salva nada. Para aplicar explicitamente:

```powershell
.\.venv\Scripts\python.exe manage.py hydrate_cf_contest_stats --handle HANDLE --contest-id 106687 --apply
```

A aplicação atualiza apenas metadados de submissões existentes e da participação.
Não cria ACs, não repete a máquina de estados, não altera a triagem e não avança
o cursor incremental. Uma falha de histórico impede a gravação. Submissões que
existam no provedor, mas não tenham sido importadas, mantêm a cobertura parcial.

O modo de aplicação também tenta obter a linha exata no placar, respeitando
handle, modo e início virtual. Colocações ambíguas ficam indisponíveis. Gym usa
a autenticação já configurada no backend; CF regular usa o placar público oficial.
Ranking virtual regular não é estimado. Penalidade só é importada de placar ICPC.
Falha de placar preserva o resultado anterior, sem impedir os metadados de tempo.

## Validação

O desenvolvimento começou com testes RED para apuração, integração e componentes.
Os testes usam SQLite isolado e HTTP/IA simulados. Casos cobrem CE, vereditos,
sessões diferentes, prática, conclusão manual, dados parciais, isolamento do usuário,
duplicatas e enriquecimento sem mudanças no tracking.

Comandos de verificação a partir dos respectivos diretórios:

```powershell
# backend: evitar cópias de testes em diretórios de artefatos/var
.\.venv\Scripts\python.exe -m pytest api/tests -q
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=core.settings_test
.\.venv\Scripts\python.exe manage.py check --settings=core.settings_test
```

```powershell
# frontend
npm.cmd test
npx.cmd tsc -p tsconfig.app.json --noEmit
npm.cmd run build
```

AtCoder virtual, revisão com IA e classificação em lote permanecem fora desta
entrega. Nenhuma migração ou hidratação de produção foi executada na validação.

## Testes manuais após o deploy

Use uma conta de teste para alterações de triagem/fila. Para comparar resultados,
escolha uma participação já importada com placar disponível no Codeforces.

1. **Publicação:** conferir backend e frontend na revisão publicada e a migração
   `0011_contest_result_metadata` aplicada. `backend/build.sh` executa `migrate`;
   confirmar a execução nos logs do ambiente, sem presumir sucesso pelo push.
2. **Histórico:** conferir 9 cards em desktop, 6 em notebook e 3 no celular, se
   houver participações suficientes. Testar Gym/regular, busca, modo, período,
   ordenação, paginação e limpeza de filtros sem resultados.
3. **Retorno:** abrir um card da segunda página após rolar e aplicar filtros.
   Voltar pelo botão da tela e pelo navegador; página, filtros e posição devem voltar.
4. **Evolução:** alternar 10/20, percentual e upsolving. A série posterior começa
   desligada; paginação dos cards não altera o gráfico nem os totais. Hover, foco
   e toque nas barras devem mostrar o contest correto.
5. **Placar:** comparar faixa e tabela com o CF: AC direto `+`, dois erros antes
   do AC `+2`, dois erros sem AC `−2`, nenhum julgamento `−`. Conferir HH:MM desde
   o início da participação, inclusive virtual; segundos são descartados.
6. **Vereditos e navegação:** conferir WA/TLE/RE no tooltip por hover, Tab e toque.
   CE fica separado; erros posteriores ao AC não aumentam `+N` nem apagam o sucesso.
   Clicar na letra deve revelar a linha mesmo com filtro ou busca ativos.
7. **Upsolving e triagem:** um WA durante a prova e AC posterior mantém `−1` com
   selo Upsolvada. Concluir manualmente sem AC não fabrica `+`; o tooltip deve
   informar a conclusão manual. Recarregar e reabrir deve preservar o resultado.
8. **Ações preservadas:** abrir o link da questão, adicionar à fila, alterar triagem
   e estimar rating/tags em uma questão elegível. A estimativa usa a IA existente
   e pode consumir crédito; basta uma chamada de teste, sem execução em lote.
9. **Histórico antigo:** antes do enriquecimento, dados desconhecidos aparecem
   parciais, sem zero/tempo/ranking inventados. Rodar o comando primeiro sem
   `--apply`; aplicar somente ao handle/ID CF desejado e conferir que triagem e
   cursor não mudaram. Ranking/penalidade só aparecem se importados com contexto.
10. **Sessões e acesso:** se houver contest repetido, conferir que AC de outra
    sessão não muda a prova selecionada. Abrir o detalhe por URL direta e atualizar
    a página; conta sem aquela participação recebe indisponível/404, sem dados alheios.

Se Gym ou placar falharem por indisponibilidade/403 no provedor, preservar os dados
anteriores e registrar o erro; falha externa não deve aparecer como zero tentativas.
