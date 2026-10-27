# Contests: refinamento visual e recuperação de dados

Escopo solicitado em 26/10/2026. Preservar a estrutura aprovada e a FSM.

1. **Dados:** auditar migração 0011, metadados de sessão e cobertura; executar
   prévia e enriquecimento direcionado dos contests existentes. Preservar triagem,
   submissões e cursor. Ranking só da linha correspondente, sem estimativa.
2. **Identidade:** fundos preto/zinc, vermelho Forja `#dc143c` em seleção, hover,
   bordas e foco. Verde/azul apenas para significado de resultado. Evitar painéis
   inteiros azuis/roxos. Estrutura e espaçamento seguem Dashboard/Fila.
3. **Histórico:** abas Todos / Equipe / Individual (convenção temporária Gym/regular),
   métrica Pendências, cards com data DD/MM/AAAA, logo existente do Codeforces,
   ícones de grupo/pessoa, números maiores, hover vermelho e sem chamada redundante.
4. **Detalhe:** metadados agrupados e ações separadas no cabeçalho; faixa compacta
   sem legenda textual; Upsolvada como pequeno marcador lateral com tooltip.
   Rating e até duas tags em uma linha, excedente em tooltip, como na Fila.
5. **Evolução:** abas Resoluções / Ranking / Penalidade. Resoluções em barras
   agrupadas, sem empilhar AC e upsolving. Ranking com menor posição mais alta;
   penalidade ICPC em escala própria. Nunca sobrepor unidades diferentes. KPIs
   contextuais e detalhe acessível por hover, foco e toque; lacunas explícitas.
6. **Verificação:** RED/GREEN para abas, dados ausentes, séries, datas e componentes
   compactos; regressões existentes; build/tipos/lint e inspeção em três larguras.

Alternativas consideradas: apenas recolorir deixaria a sobreposição do gráfico;
vários gráficos simultâneos aumentariam o ruído. Abas mantêm a página compacta e
permitem analisar resultado, ranking e penalidade com escalas claras.

Sem AtCoder novo, revisão com IA, novos estados ou módulo de equipes. O pedido
autoriza iniciar a implementação e recuperar os dados necessários; nenhum push
novo está previsto sem solicitação posterior.
