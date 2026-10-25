# Sincronização Codeforces: credencial temporária e integridade

Decisão aprovada em 25/10/2026: usar temporariamente a chave de API do
proprietário da Forja no backend do Render. O proprietário configura
`CF_API_KEY` e `CF_API_SECRET`; nenhum valor é armazenado nesta documentação.

## Contexto e limites

O histórico público de `bemagno` contém participação virtual no Gym 106687.
O catálogo desse Gym exige autenticação: a consulta anônima falhou e a
consulta local autenticada retornou 12 problemas. Render estava sem as chaves.
A validação autenticada no Render ainda depende do teste após configuração.

A chave autoriza como seu proprietário, independentemente do handle consultado.
Esta solução é temporária para o uso controlado atual e conteúdo público;
não representa um desenho de autorização para contests privados multiusuário.
Não habilitar grupos privados ou acesso de gerente. Credenciais individuais e
isolamento de catálogos privados precisam de outro desenho antes dessa expansão.
Manter consultas públicas anônimas e assinar apenas consultas que precisam disso.
Nunca enviar chaves ao frontend, Git ou logs.

## Escopo aprovado e TDD

1. Reproduzir falha de paginação e distingui-la de histórico vazio. Em falha,
   preservar o ponto incremental; repetição deve ser idempotente.
2. Respeitar pelo menos dois segundos entre chamadas da API, inclusive após
   erros, e impedir sincronizações CF simultâneas. Testar com tempo/rede simulados.
3. Expor início, conclusão e falha reais ao botão, atualizar dados após conclusão
   e testar esses estados sem threads ou HTTP externos escaparem dos testes.
4. Validar Gym 106687 pela interface. Recuperação histórica é condicional;
   não transformar todo clique em full sync nem executar reparos automaticamente.

Sem novos benchmarks, chamadas de IA ou alterações nos resultados congelados.
Sem commit, push ou migrations de produção nesta etapa.

## Implementação e limites operacionais

- O histórico passa a retornar resultado tipado. Uma página com falha interrompe
  a coleta antes do processamento; resultado vazio válido encerra a paginação.
- Falha transitória do catálogo retém o ponto incremental mesmo quando já existe
  parte do catálogo local. O resultado da tarefa será incompleto, nunca sucesso.
- HTTP 403/404 sem mensagem explícita de inexistência/privacidade não autoriza
  fallback permanente: pode ser bloqueio de infraestrutura.
- Um lock de sistema operacional exclui sincronizações CF simultâneas, tanto
  pela interface quanto pelo comando `sync_cf`. O relógio da API é compartilhado
  entre processos no mesmo servidor e inclui requisições que falharam.
- `POST /api/sync/cf` inicia a tarefa e retorna seu identificador;
  `GET /api/sync/cf/status?run_id=...` consulta somente o handle do usuário
  autenticado. A interface consulta a cada três segundos, por até 15 minutos,
  e invalida os dados relevantes somente após conclusão. Não repete o sync.
- Locks e estado JSON ficam em `backend/var/cf_sync/` (fora do Git), sem respostas
  da API ou credenciais. O SO libera o lock quando o processo termina; um estado
  em andamento sem lock é informado como interrompido. Se os arquivos sumirem,
  informa estado desconhecido. Nunca presumir conclusão nem retomar sozinho.
- Solução para uma instância Render com filesystem compartilhado entre workers.
  Não é fila durável, não coordena múltiplas instâncias e o disco Free é efêmero.
  Recarregar a página perde o acompanhamento local; os registros do produto já
  persistidos continuam no banco. Uma tentativa posterior é idempotente.
- A restrição a conteúdo público é o escopo operacional temporário aprovado,
  não uma autorização multiusuário para importar contests privados. Essa expansão
  exige desenho próprio; uma chave por si só não oferece esse isolamento.

## Referências

- https://codeforces.com/apiHelp/ — limite de uma requisição a cada dois segundos.
- https://codeforces.com/apiHelp/methods — autenticação de standings de Gym.

## Conferência após publicação autorizada

1. Configurar as duas variáveis no Render e aguardar o backend iniciar.
2. Com o handle `bemagno`, clicar uma vez em Sincronizar CF. O botão deve
   permanecer ocupado até o resultado real, sem permitir uma segunda execução.
3. Após conclusão, conferir Gym 106687, participação virtual, catálogo A–L
   (12 problemas) e resoluções. Fila, Contests e Dashboard devem atualizar.
4. Sem novas submissões, sincronizar novamente: não pode duplicar registros.
5. Se dados antigos continuarem ausentes, investigar o ponto incremental e
   planejar recuperação específica; não disparar full sync automaticamente.

Falhas de API, paginação e interrupção são verificadas com simulação: não é
necessário remover chaves nem provocar falhas deliberadamente em produção.

Validação local: 455 testes de backend e 120 de frontend aprovados, incluindo
regressões adicionadas sem remoção dos testes anteriores. Build, lint dos arquivos
frontend alterados, Django check com `settings_test` e `git diff --check` passaram.
O typecheck explícito da aplicação mantém 10 diagnósticos históricos em três
arquivos, detalhados em `docs/AI_LAB_TYPESCRIPT_DEBT.md`; nenhum nos arquivos
alterados. Banco SQLite isolado e integrações simuladas; nenhuma sincronização
de produção, chamada real de IA, migration, commit ou push nesta implementação.
