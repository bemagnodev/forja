# Contests: recuperação de dados e refinamento

## Diagnóstico confirmado

- Frontend novo consultava backend antigo: Render estava em `9cdffe8`, anterior
  aos campos `contest_result`, contexto de ranking e duração na resposta.
- Banco configurado ainda não tinha a migração aditiva `0011`.
- Histórico importado antes da mudança não preservava referências de sessão.
- Cinco participações eram recusadas por diferenças de um segundo entre os
  relógios absolutos e relativos retornados pela API CF.

## Operação autorizada

Auditoria inicial somente leitura, prévia SQL e plano contendo apenas a migração
0011, aplicação dos seis campos aditivos e prévias de enriquecimento por contest.
Recuperação direcionada à conta bemagno; nenhuma outra conta foi enriquecida.
O histórico de user.status foi reutilizado entre os comandos para reduzir HTTP.
Credenciais, respostas brutas e caches operacionais não entram no repositório.

Backend anterior aprovado `ec501a3` publicado no Render em
[deploy dep-dbfv4s142hec73d3gqmg](https://dashboard.render.com/web/srv-d8i726u7r5hc73cka5t0/deploys/dep-dbfv4s142hec73d3gqmg),
com estado Live confirmado. Página real do Gym 106687 passou a mostrar #45
virtual, penalidade 377, duração 240 min e horários dos sete ACs da prova.

Após a primeira recuperação, 49 de 62 participações tinham cobertura completa e
45 tinham ranking confirmado. A correção de arredondamento recuperou outras cinco:
resultado final de **54 completas e 45 com ranking confirmado**. As prévias
confirmaram as cinco antes da aplicação.
Snapshots de tracking e cursor foram comparados antes/depois e permaneceram iguais.
Não foram reexecutadas transições da FSM nem criadas submissões aceitas.

## Limites restantes

Oito participações permanecem parciais: sete não constam no histórico retornado
pela API atual; algumas também não têm duração ou placar acessível. Uma envolve
OUT_OF_COMPETITION, que não pode ser apresentada como resultado oficial confirmado.
Não assumir ausência de tentativas nem fabricar ranking. Virtual regular continua
sem ranking estimado, conforme o escopo aprovado.

## Refinamento e validação

Preservar estrutura, adotar preto/zinc e vermelho Forja, renomear Pendências e
abas Equipe/Individual, compactar cards, cabeçalho, tags e marcador de upsolving.
Gráfico com barras agrupadas, visão de ranking e penalidade, KPIs do recorte e
lacunas explícitas. Identidade usa o token `forja`, que já contém a cor #dc143c
e suporta as opacidades do Tailwind.

Após a revisão local, o usuário autorizou commit/push e publicação do refinamento
visual e da correção de arredondamento para conferir em produção. A publicação
operacional acima corresponde ao backend da etapa anterior. Validação: 487 testes backend, testes de
interface (158 casos, incluindo reexecução isolada dos três arquivos antigos que
falharam por tempo na rodada completa), build, tipos e lint; inspeção em 390, 1024 e
1440 pixels. Falhas transitórias de dependências/permissões e timeouts dos testes
antigos do frontend foram isoladas e reexecutadas sem alterar esses testes.
