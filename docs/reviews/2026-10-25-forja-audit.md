# Auditoria da Forja — 25/10/2026

## Escopo e conclusão

Revisão do código e navegação autenticada em produção: Dashboard, fila, detalhe de contest, Explorar e as três comparações públicas do benchmark. Outras telas foram examinadas no código. Não foram disparadas sincronizações, classificações com IA ou alterações de dados pela interface. Uma reprodução de integridade utilizou exclusivamente SQLite em memória, com settings de teste.

A Forja já tem uma demonstração de IA consistente. A prioridade é tornar os fluxos existentes confiáveis e explicar corretamente seus dados, antes de acrescentar funcionalidades. Não encontrei evidência de um incidente crítico ativo em produção; encontrei defeitos confirmados e riscos de integridade que merecem tratamento dirigido. Esta revisão não substitui uma auditoria de segurança ou dos dados reais do banco.

Base examinada: `0cd70ede7aed828120513dd1308d2280cb1643f5`. Os testes da rodada anterior foram reportados como 455 backend e 123 frontend; não foram repetidos nesta revisão sem mudanças de código. O typecheck possui dívida histórica documentada separadamente.

Prioridades: **P1** antes de ampliar/divulgar a demonstração; **P2** próxima rodada de acabamento; **P3** adiar. Os riscos de integridade exigem diagnóstico dos dados antes de qualquer migração.

## P1 — confiabilidade e apresentação

### 1. A fila confirma ações antes de saber se foram salvas

**Evidência no código:** `frontend/src/pages/Queue.tsx:33–83`. A conclusão altera o cache local e mostra sucesso imediatamente; a mutation não possui rollback nem tratamento de erro. Criação, edição e reordenação também não apresentam uma recuperação consistente. `AddItemDialog.tsx:51–63` fecha e limpa o formulário antes da resposta do servidor.

**Impacto:** em falha de rede, o item pode desaparecer visualmente sem ter sido concluído; o usuário recebe uma confirmação falsa ou perde o texto que digitou. Não provoquei essa falha no servidor de produção.

**Correção pequena:** manter a atualização otimista com snapshot/rollback e aviso de erro, ou esperar a confirmação. Fechar e limpar o formulário somente após sucesso; bloquear envio duplicado enquanto pendente. Reordenação também precisa de recuperação.

**Teste necessário:** simular timeout/500 nas quatro operações; conferir restauração do item, preservação do formulário, ausência de toast de sucesso indevido e possibilidade de tentar novamente.

### 2. A prioridade fica escondida na fila mesmo no desktop

**Confirmado visualmente em 1366 px:** tabela de aproximadamente 1145 px dentro de área útil de 1050 px. A coluna Prioridade começa junto à borda direita e exige rolagem horizontal. Tags, descrição e contest consomem espaço demais para a decisão principal da fila.

**Recomendação:** manter questão, rating, prioridade e ação visíveis; limitar tags e descrição com expansão/tooltip; reduzir ou agrupar contest como informação secundária. Não é necessário remover funcionalidades nem redesenhar a página inteira.

**Aceite visual:** 1280 e 1366 px sem esconder prioridade; título legível e ações acessíveis. Teste unitário de classes CSS não substitui essa conferência.

### 3. O detalhe de contest depende de como o usuário chegou à página

**Confirmado:** clicar no contest recente do Dashboard abriu `/contests/3993` com título genérico “Detalhe do Contest”, sem os metadados do cabeçalho. A lista de problemas carregou corretamente.

**Causa:** `RecentContestsList.tsx:46` navega apenas pelo ID; `ContestDetail.tsx:49` recebe nome, URL, ranking e progresso exclusivamente de `location.state`. A navegação pelos cards fornece esses dados, mas o Dashboard e um link direto não fornecem. Não é correto afirmar que todo refresh perde o state: o histórico do navegador pode preservá-lo.

**Correção:** buscar os metadados pelo ID, usando o state somente como preenchimento inicial. O progresso do cabeçalho também deve acompanhar os dados atuais. `ProblemStatusSelect.tsx:31–32` invalida apenas os problemas do contest; revisar invalidação de resumo, lista, Dashboard e fila quando houver dependência.

**Testes:** abrir pela lista, Dashboard e URL direta; alterar status com API simulada e conferir resumos sem recarregamento manual.

### 4. Métricas do Dashboard precisam dizer exatamente o que medem

**Confirmado no código e, quando indicado, em SQLite isolado:**

| Exibição | Cálculo atual | Ajuste recomendado |
| --- | --- | --- |
| Resolvidos no mês | Últimos 30 dias, `dashboard_service.py:31` | Renomear para “Últimos 30 dias”, ou calcular mês civil. Uma submissão de setembro entrou no “mês” de outubro na reprodução. |
| Atividade / submissões | Somente submissões aceitas | Explicitar “Questões recentes”, pois o título é mais intuitivo e já está claro que inclui apenas AC; não incluir tentativas erradas sem decidir a nova definição. |
| Sequência e dias | Uso de datas UTC apesar do fuso São Paulo | Usar a mesma data local na agregação e na interface. À noite de 25/10, a última célula já indicava 26/10. |
| Domínio de tópicos | Quantidade resolvida, barra relativa ao tópico mais frequente, top 15 | Renomear para “Resolvidos por tópico” e “15 mais frequentes”. Contagem não demonstra domínio ou proficiência. |
| Dificuldade e tópicos | Apenas `metadata.rating/tags`, sem previsões de IA | Manter origem explícita e cobertura. Não misturar estimativas com dados de referência silenciosamente. |

O Dashboard mostrou 344 problemas com dificuldade entre 758 resolvidos. Isso é uma cobertura parcial, não necessariamente erro de cálculo. A semana também combina janela móvel de 168 horas com apresentação em dias: vale alinhar ambos a sete dias de calendário local.

**Decisão anterior a preservar:** marcar revisão como DONE promove um problema não tentado para UPSOLVED. Há teste explícito desse comportamento. Isso exige distinguir conclusão manual de aceite na plataforma na narrativa; não recomendo desfazer automaticamente essa regra durante uma limpeza visual.

**Testes:** virada de mês, horário entre 21h e meia-noite em São Paulo, ausência de rating, mais de 15 tópicos e conclusão manual sem submissão aceita.

### 5. O gráfico anual cabe, mas perdeu qualidade visual

**Confirmado em 1366 px:** cartão com aproximadamente 294 px de altura e grade de apenas 82 px. O `h-full` e o `mt-auto` em `ActivityHeatmap.tsx:40–50` deixam um vazio grande e empurram a grade para baixo. Faltam meses e referência dos dias da semana; os 365 dias são distribuídos a partir de uma data móvel, sem alinhamento de calendário.

O ajuste anterior resolveu a rolagem, mas não resolveu a composição. Sua crítica visual procede.

**Recomendação:** altura natural, grade alinhada a semanas de calendário, poucos rótulos de meses e dias, legenda proporcional e menos espaço vazio. Harmonizar a altura com o resumo semanal ou dar uma linha própria ao calendário. Evitar reduzir ainda mais os pontos. No resumo semanal, os sete ícones também precisam de indicação dos dias.

**Aceite:** conferir dados vazios, ano com atividade densa e larguras 1280/1366/1600; datas e células corretas antes de ajustar cores.

### 6. A navegação promete telas ainda indisponíveis

Notes, Settings, Profile e Teams exibem “em construção” no código, embora existam caminhos de navegação para elas. Isso passa sensação de produto incompleto na apresentação.

**Recomendação:** manter os atalhos e as telas acessíveis, sinalizando “Em breve” na navegação e explicando em cada página o que ainda está em desenvolvimento. Não remover nem desabilitar esses acessos, nem implementar quatro módulos apenas para resolver este problema de apresentação. Adicionar saída da conta em um lugar visível: existe `logout` no AuthContext, mas não encontrei sua utilização na interface.

### 7. Proteção operacional da conta demo — P3, adiada

O README divulga credenciais de demonstração. Não encontrei uma restrição específica de demo nos fluxos de escrita, IA e sincronização; a proteção observada é a autenticação normal.

**Risco condicional:** se essa conta continuar ativa com as permissões comuns, um visitante pode modificar a demonstração e consumir cotas compartilhadas de IA/sincronização. Não testei essas ações com a conta pública, nem reproduzi consumo.

**Decisão:** não tratar este ponto agora. A proteção específica da conta demo fica adiada, fora do escopo da rodada atual, sem bloquear a apresentação. O risco permanece registrado para revisão futura.

### 8. O README subestima justamente a entrega mais relevante

`README.md:122` ainda descreve a comparação de modelos no AI Playground como expansão futura. Já existem três comparações de 60 problemas revisados, prompts versionados, métricas pareadas e uma decisão de modelo.

**Recomendação:** substituir essa promessa por uma descrição curta do que foi entregue, uma imagem atual e links para metodologia/resultados. Explicar por que a classificação direta foi mantida e por que a rubrica não melhorou o resultado observado. Preservar a ressalva: avaliação Codeforces 800–2400, sem validação equivalente do produto em 2500–3500. Não afirmar superioridade estatística ou generalização universal.

## IIntegridade — investigar antes de ampliar importações

### 9. Identidade de submissão não separa plataformas

**O que significa:** um ID identifica uma submissão dentro da plataforma que o emitiu; não há garantia de que esse número seja exclusivo entre plataformas diferentes. Por exemplo, Codeforces e AtCoder podem ter, cada um, uma submissão `12345`, sem qualquer erro nas plataformas. Para a Forja, as identidades corretas seriam `(Codeforces, 12345)` e `(AtCoder, 12345)`: duas submissões distintas. O problema não é o ID interno da Forja se repetir, mas usar somente o ID externo para identificar registros de fontes diferentes.

**Defeito reproduzido em SQLite em memória:** `Submission.platform_submission_id` é globalmente único (`models.py:130`), e os importadores fazem `update_or_create` somente por esse campo (`sync_cf.py:169–170`, `sync_atcoder.py:101–102`). Assim, a restrição impede duas linhas com o mesmo ID externo, mas não impede a corrupção: ao importar a segunda plataforma, o código encontra a linha da primeira e a atualiza. Na reprodução, inserir IDs iguais das duas plataformas deixou uma única linha, agora vinculada ao problema AtCoder.

**Gravidade:** é um defeito sério de integridade, com possibilidade de sobrescrever problema, usuário e demais dados de uma submissão. Isso pode afetar históricos e métricas. O mecanismo foi confirmado em teste isolado; **não foi confirmado que houve colisão ou perda de dados em produção**. A ausência de IDs duplicados no banco não descartaria o problema, porque uma colisão pode ter sobrescrito a linha anterior.

**Próximos passos, em ordem:**

1. **Conter o risco:** suspender preventivamente as sincronizações CF/AtCoder que usam essa identificação até corrigir o caminho de escrita; não ampliar importações nesse intervalo. Preservar backup e logs antes de qualquer reparo.
2. **Diagnosticar sem alterar dados:** auditar registros, relações com problemas/plataformas e logs disponíveis; confrontar com as fontes quando necessário. Procurar inconsistências de origem e proprietário, não apenas IDs duplicados. Registrar o que foi confirmado e o que não pode ser reconstruído com a evidência disponível.
3. **Definir a identidade e a propriedade:** usar o par `(plataforma, ID externo)` como identidade da submissão. Decidir separadamente como associá-la às contas Forja quando duas contas usam o mesmo handle; acrescentar a plataforma não resolve sozinho essa questão.
4. **Corrigir com testes:** primeiro reproduzir a colisão em teste; depois ajustar a restrição de unicidade e todos os importadores. Garantir que IDs iguais de plataformas diferentes coexistam, que reimportar a mesma submissão não crie duplicatas e que a associação aos usuários siga a política definida.
5. **Migrar e reparar com revisão:** preparar a migração e o preenchimento da plataforma nos registros antigos apenas quando houver evidência confiável. Separar casos ambíguos para análise, sem adivinhar a origem. Validar em cópia do banco, com backup e plano de reversão, antes de aplicar em produção.
6. **Retomar com validação:** conferir históricos e métricas afetados e só então reativar as sincronizações. Alterar a chave evita novas colisões, mas não recupera automaticamente dados eventualmente sobrescritos.

### 10. Importação CSES mistura estimativa, data de importação e data de resolução

`import_cses.py:130–131` grava `official_rating/official_tags`, mas os consumidores principais leem `rating/tags`. O rating é heurístico, não um rating oficial equivalente ao Codeforces. A reprodução mostrou um problema CSES resolvido sem participação nos gráficos de dificuldade/tópicos.

Além disso, `creation_time=timezone.now()` no upsert (`:147–153`) representa a importação como resolução recente e pode mover o histórico em uma reimportação.

**Correção recomendada:** normalizar metadados com origem explícita; separar data conhecida de resolução de data de importação. Se a fonte não fornecer data histórica, registrar essa limitação e não inventar atividade diária. Testar reimportação idempotente.

### 11. A dificuldade AtCoder não é nativa na mesma acepção do Codeforces

O cliente obtém uma dificuldade estatística externa e a converte para escala CF; `sync_atcoder_metadata.py:109` salva isso como `rating`. A interface trata esse campo como rating nativo. Na fila, um exemplo real aparecia como 1261.

**Recomendação:** distinguir “Codeforces oficial”, “AtCoder estimado/convertido” e “IA”. Não mudar os valores durante um ajuste de rótulo nem impor a grade do contrato de IA sobre dados históricos de outra origem. A restrição de reclassificar deve considerar essa política de origem conscientemente.

## P2 — acabamento e resiliência

1. **Estado vazio da fila incorreto:** ao filtrar UPSOLVING sem resultados, a tela declarou que a dívida estava completamente paga, embora existissem 12 itens ativos. Separar “Nenhum item neste filtro” de “Fila vazia”; oferecer limpar filtro. Considerar acesso a concluídos além do Desfazer temporário.
2. **Busca no Explorar e inclusão na fila:** diferenciar carregamento, sem resultados e falha. Associar labels aos inputs e dar nome acessível a botões de ícone. Não fazer uma falha de busca parecer ausência de problemas.
3. **Textos:** retirar mensagens como “Django está rodando?” da experiência publicada. Padronizar Refresh/Atualizar, FUTURE, Upsolved/Upsolvados e nomes de telas. Termos técnicos podem ficar nos detalhes do benchmark; o fluxo principal deve explicar a tarefa.
4. **Cache por sessão:** QueryClient permanece fora do AuthProvider; chaves como queue/contests/dashboard não incluem usuário e login/logout não limpam cache. Existe risco de mostrar temporariamente dados da conta anterior ao trocar de usuário. Não reproduzido em produção. Limpar cache na transição e testar duas sessões simuladas, incluindo cabeçalho de autorização.
5. **Login e erros de rede:** o tratamento genérico apresenta credenciais inválidas mesmo quando a causa pode ser rede ou indisponibilidade. Separar 401 de falha de serviço. Definir timeout consciente do cold start do Render, sem retry infinito nem repetição automática de chamadas de IA.
6. **Sincronização AtCoder:** revisar confirmação de término e atualização das queries, em vez de confundir disparo com conclusão. O cliente também deve distinguir página vazia de falha de obtenção. Não é evidência de perda permanente: o próximo incremental pode recuperar dados.
7. **Consistência dos contests:** o Dashboard mostrou um Gym com nome provisório que a listagem principal filtra. Compartilhar critérios de inclusão. Corrigir abreviações pouco reconhecíveis na fila, sem esconder a identificação útil.
8. **Acessibilidade:** cards clicáveis implementados com div e edição por clique precisam de teclado/foco; ícones semanais e textos muito apagados prejudicam leitura em compartilhamento de tela. Não medi conformidade WCAG completa.
9. **Responsividade:** a 390 px, o main tinha aproximadamente 166 px por causa da sidebar fixa. O layout móvel não é utilizável apenas escondendo overflow. Se a entrevista for desktop, corrigir primeiro 1280–1366; menu recolhível móvel pode vir depois.
10. **Movimento:** atrasos encadeados de animação deixam cards aparecerem depois de aproximadamente um segundo. Reduzir duração/delay e respeitar preferência por movimento reduzido; não precisa remover a identidade visual.
11. **Validação de API:** campos de status/prioridade recebidos como strings merecem enums; IDs inexistentes devem retornar 404/422, não exceção genérica. Testar payload inválido e reordenação inválida com transação. Não foram enviados payloads de teste ao servidor real.
12. **TypeScript e documentação de dívida:** há nove diagnósticos históricos registrados em Last7DaysWidget e api.test. Corrigir sem esconder erros; consolidar o documento, que mantém contagens históricas contraditórias em parágrafos posteriores. Build Vite não substitui typecheck dos projetos referenciados.
13. **Verificação automática:** não encontrei workflow de CI versionado. Um pipeline curto com suítes existentes, typecheck e build tem mais valor agora que novas abstrações. Adicionar poucos testes de integração/visuais para os defeitos desta auditoria, evitando snapshots excessivos.
14. **Rotas desconhecidas:** apresentar uma página de não encontrado com retorno à navegação, em vez de deixar apenas o layout vazio.

## AI Lab — preservar o que já funciona

As três comparações aprovadas carregaram corretamente, com nomes das técnicas, prompts acessíveis, ordenação pelo erro, cobertura, falhas e domínio documentado. A comparação entre prompts usa interseção própria, por isso seus MAEs não precisam coincidir com os da comparação entre modelos. Isso é correto; não ajustar números para ficarem iguais.

Não recomendo novos gráficos ou experimentos nesta rodada. Um resumo curto do principal resultado pode ajudar mais: Gemini teve o menor MAE observado; a rubrica não trouxe ganho no conjunto avaliado. Manter denominadores e não transformar uma diferença pequena em alegação estatística.

Preservar: Explorar como primeira aba, ícones das plataformas, apenas três comparações públicas, pilotos arquivados, separação produto/benchmark, domínio de produto 800–3500 sem truncamento, cache versionado do produto e ausência de escrita pelo Explorar. As falhas anteriores do Codeforces não justificam mexer novamente no transporte que acabou de funcionar em produção; manter diagnóstico e limites existentes.

## Ordem sugerida de trabalho

1. **Confiança dos fluxos:** TDD para falhas da fila, persistência do formulário, detalhe de contest independente da navegação e invalidação dos resumos.
2. **Dashboard:** decidir nomes e períodos, testar datas/fuso e dados parciais; depois ajustar calendário e layout da fila em desktop. Não começar pelas cores.
3. **Demonstração:** ocultar telas incompletas, proteger conta demo, disponibilizar logout e atualizar README. Revisar a história da apresentação sem aumentar a arquitetura.
4. **Integridade:** verificar colisões e proveniência com acesso somente leitura; definir correções CF/AtCoder/CSES antes de ampliar importações. Planejar migrações separadamente, com autorização e reversibilidade.
5. **Próxima rodada:** dívida TypeScript, busca, acessibilidade, validação de entradas e mobile conforme público/prioridade.

Cada comportamento deve ter teste vermelho antes da correção, teste verde depois e regressão pertinente. Para calendário, largura e contraste, acrescentar conferência visual real: testes unitários não comprovam boa composição. Somente após implementação autorizada executar novamente as suítes completas e checagens de entrega.

## O que adiar

Refatoração geral de `api.py`, novas camadas abstratas, fila distribuída, novos provedores/modelos, benchmark adicional, implementação de Teams/Notes/Profile e redesign completo. Esses itens têm retorno menor que eliminar confirmações falsas, dados ambíguos e caminhos incompletos na apresentação atual.

## Limites e ações realizadas nesta auditoria

Somente este relatório foi adicionado ao repositório. Nenhuma implementação, migration de produção, chamada real de IA, sincronização, commit, push ou deploy foi realizada. As conclusões de risco distinguem código/reprodução isolada de confirmação em produção. Configuração efetiva de DEBUG/hosts e permissões da conta demo ainda precisa ser verificada; defaults permissivos no código não provam que produção esteja usando esses valores.
