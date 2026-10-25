# Diagnóstico de acesso ao Codeforces

## Pergunta investigada

O serviço Render Free (Oregon) recebeu HTTP 403 com
`cf-mitigated: challenge`. Isso confirma um desafio antes do enunciado, mas
não identifica qual regra o disparou. A coleta automática continua sendo
requisito do produto; esta investigação não substitui a funcionalidade por
entrada manual nem modifica o scraper ativo.

## Comparação histórica e controle local

- Antes da unificação (`8f49944^`), o scraper já usava
  `requests.get(url, timeout=10)` e `raise_for_status()`, sem headers customizados
  nem sessão persistente. `9b23d23` encapsulou essa mesma chamada para devolver
  erros seguros. O parser só é executado após a resposta HTTP ser aceita.
- As rotas geradas por `Problem.url` para official/Gym já eram as mesmas.
- `requests==2.32.5` e `urllib3==2.6.3` já estavam declarados antes da unificação.
  Isso não comprova quais dependências ou runtime estavam instalados em um deploy
  antigo; por isso cada execução atual registra versões e hash do diagnóstico.
- Em 25/10/2026, o controle local inicial obteve 200 nas páginas individuais
  de 1542/D e 106682/H e nas duas páginas consolidadas. Cada problema teve dois
  pares de exemplos; H preservou um marcador de imagem. Ainda não é um teste
  a partir do Render, nem uma medição de estabilidade.
- Uma segunda rodada confirmou também `/contest/1542/problem/D` e a consolidada
  oficial. A individual Gym retornou 200, mas excedeu o limite de leitura;
  a rodada terminou por orçamento de tempo antes dos dois alvos finais.
  Esses casos são inconclusivos, não sucessos nem evidência de desafio.
- No Render Free/Oregon, duas rodadas (`plain` e `session`) concluíram cinco
  alvos cada: todos responderam 403 com `cloudflare_challenge`, incluindo as
  consolidadas. Os hashes do script coincidiram com o controle local. Isso não
  determina se a causa é IP, características do cliente ou outra regra.

## Script e limites

`backend/scripts/probe_codeforces.py` é standalone: não inicializa Django,
não carrega `.env`, não consulta banco e não importa adaptadores de IA.
Ele consulta apenas cinco URLs fixas no host `codeforces.com`: as quatro
rotas individuais/consolidadas e a rota alternativa do problemset.

- Sem retries, sem seguir redirecionamentos, intervalo de três segundos.
- Timeout de rede de dez segundos, leitura limitada a 1 MiB por resposta.
- Após 45 segundos não inicia novos alvos; uma operação em curso pode terminar
  depois disso, respeitando seus limites de rede/leitura. Não é deadline rígido.
- Não registra HTML, títulos, cookies, Location, exceções brutas ou chaves.
- Um status 200 só vira `statement_valid` se o índice esperado for único e
  o parser atual validar as seções. Não seleciona a primeira questão do contest.
- Desafio é detectado pelo cabeçalho mesmo com HTTP 200. O script não o resolve.

Perfil `plain`: `requests.get`, como o transporte atual, com leitura controlada.
Perfil `session`: conexões reutilizáveis e headers identificando
`ForjaDiagnostics/1.0`, HTML e idioma inglês. Não é navegador nem login.
Esse segundo perfil muda um conjunto de condições: sucesso isolado não permite
atribuir a melhora somente ao header ou à sessão.

Perfil `curl_chrome`: somente duas buscas, nas páginas individuais official e
Gym. Usa `curl_cffi==0.16.3` e perfil fixo `chrome150`, sem proxy de ambiente,
sem cookies pessoais, sem persistir cookies e com certificado verificado.
A dependência é instalada pelo requirements, mas importada somente nesse
perfil; o scraper do produto continua usando requests. Sem navegador completo,
execução de JavaScript, serviço pago, fallback ou retry. Os testes simulam esse
transporte e bloqueiam também a fronteira nativa de rede do libcurl.

Em 25/10/2026, esse perfil validou localmente os dois enunciados com HTTP 200:
1542/D em 797 ms e 106682/H em 1312 ms. Ambos tiveram dois pares de exemplos;
H preservou uma imagem. Não é comparação pareada de velocidade nem comprovação
de funcionamento no Render. O campo `openssl` informa a biblioteca do Python,
não o backend TLS usado pelo curl_cffi.

## Rodar localmente

Na pasta `backend`, com dependências instaladas:

```powershell
.\.venv\Scripts\python.exe scripts/probe_codeforces.py --environment local --profile plain
```

`--environment` é uma etiqueta fornecida pelo operador, não detecção automática.
Relatórios locais ficam em `backend/var/ai_lab/scraper-diagnosis/`, ignorados no Git.

## Rodar no Render Free

Primeiro disponibilizar o script em um deploy aprovado. Não mudar o Build Command,
não criar endpoint e não adicionar variáveis com chaves. Em **Settings → Build &
Deploy → Start Command**, usar temporariamente:

```sh
python -u scripts/probe_codeforces.py --environment render --profile plain; exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

O separador `;` permite iniciar o Gunicorn mesmo se o diagnóstico falhar.
A coleta acontece no runtime do serviço, antes do Gunicorn, adicionando alguns
segundos à inicialização. Ela roda novamente em cada restart enquanto esse
comando permanecer configurado: não deixar ativo nem repetir deploys à toa.

Nos logs, copiar somente os JSONs com `event: start`, `target`, `stop` e `end`.
Conferir o hash do script, versões, outcomes, índices e Ray IDs. Não enviar os
logs completos se contiverem informações de outras operações.

Depois da rodada, restaurar o comando original e salvar:

```sh
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

Essa restauração pode iniciar outro deploy. Perfil `session` só deve ser rodado
em uma rodada deliberada, trocando `--profile plain` por `--profile session`.
Não instalar navegadores ou modificar extração antes da comparação inicial.

## Próxima rodada: curl_chrome

Após publicar a revisão que inclui a dependência fixa, usar temporariamente:

```sh
python -u scripts/probe_codeforces.py --environment render --profile curl_chrome; exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

Não alterar o Build Command que já instala requirements.txt. O JSON `start`
deve informar `curl_cffi: 0.16.3`, `impersonate: chrome150` e `max_requests: 2`.
Se faltar a biblioteca ou houver versão divergente, o script registra `stop`
e não faz fallback. Copiar o resultado de uma única execução e restaurar o
Start Command original acima. Não deixar essa busca em cada restart.

Se funcionar, repetir deliberadamente em outro momento antes de integrar ao
produto. Se falhar, não concluir automaticamente bloqueio por IP nem insistir
em tentativas de outros perfis sem uma hipótese nova.

## Decisão após os resultados

- Consolidada válida, individual bloqueada: testar estabilidade da rota
  consolidada antes de adaptar a seleção do parser.
- Todas desafiadas no Render e válidas localmente: investigar acesso/origem;
  reverter o parser não demonstra solução. Sessão/headers podem ser comparados
  na segunda rodada, sem promessa de resolver o desafio.
- 200 sem problema correto ou com extração inválida: investigar HTML e identidade
  separadamente do acesso. Ausência de desafio não comprova que o Gym seja público.
- Redirecionamento, timeout ou orçamento de tempo: rodada inconclusiva para esse
  alvo; não registrar como falha de qualidade do modelo.

O diagnóstico não altera dataset congelado, previsões ou métricas do benchmark.
