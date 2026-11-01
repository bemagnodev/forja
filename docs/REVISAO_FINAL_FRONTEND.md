# Revisão final de frontend — 01/11/2026

Implementação preparada e validada na prévia local antes do envio ao repositório.

## Acesso

- Endereço: http://127.0.0.1:5173
- Conta: `preview_qa`
- Senha exclusivamente local: `ForjaLocal2026!`
- A faixa amarela deve informar cópia do banco e IA simulada. Não usar a conta publicada.
- Instruções de inicialização: [VISUAL_PREVIEW.md](VISUAL_PREVIEW.md).

Foram preparadas 20 participações sintéticas nesta conta, incluindo rankings #1 e #537 e dois rankings ausentes. As questões do treino principal e as edições anteriores da cópia foram preservadas. Os cenários do Explorar não chamam provedores de IA.

## Lista objetiva para revisar

### 1. Contests → Ver resultados → Ranking

- [ ] Alternar Últimos 10 e Últimos 20: linha tracejada liga as bolinhas correspondentes.
- [ ] Bolinhas de #1 e #537 aparecem inteiras, com espaço nas extremidades.
- [ ] Em 18/10 e 26/10, o ranking ausente interrompe o tracejado; não aparece como zero.
- [ ] Passar o mouse, clicar ou focar um ponto atualiza o detalhe da participação.

### 2. Detalhe do treino principal

Abrir http://127.0.0.1:5173/contests/3707.

- [ ] A e C: `+` verde vivo. B: `+2` verde vivo, apesar dos erros anteriores.
- [ ] E até I: `−1` vermelho vivo; upsolving posterior não transforma o resultado da prova em AC.
- [ ] E e F: UP centralizada em relação ao título de duas linhas. O também conserva UP por conclusão manual.
- [ ] Cabeçalho sem “Histórico da prova e estudo posterior preservados”.
- [ ] Ver placar: sem legenda de sinais e sem UP; resultados e horários continuam disponíveis.
- [ ] Clicar no resultado de B/C/E: tooltip conserva erros, CE e informação de resolução posterior.

Para verificar aviso de histórico parcial, abrir um dos treinos “histórico parcial” em Contests. Esse aviso específico deve continuar aparecendo.

### 3. AI Lab → Explorar

Abrir http://127.0.0.1:5173/ai-lab, clicar **Com rating oficial**, selecionar **Questão com imagens** e clicar **Classificar**.

- [ ] Nome da página e menu lateral: AI Lab.
- [ ] Aviso âmbar dentro do card “Estimativa × referência oficial”, abaixo dos valores.
- [ ] Texto e ícone contidos no card, sem corte; conferir também com janela estreita.
- [ ] Rating oficial, estimativa e diferença continuam visíveis.
- [ ] Selecionar Sucesso e classificar novamente: o aviso de imagens desaparece.

## Verificação realizada

- Testes novos observados falhando antes das mudanças e passando depois.
- Suíte frontend: 186 testes, 35 arquivos, todos passaram.
- Lint, TypeScript e build passaram. Build mantém os avisos anteriores de tamanho do bundle e Browserslist desatualizado.
- Chrome: gráfico com 20 participações e 15 segmentos, lacunas preservadas; UP com diferença vertical de centro de 0px nos três títulos; aviso contido e sem overflow em largura de 600px.
- Logs e capturas ignorados pelo Git em `backend/var/visual-review/`: `final-review-frontend-all.txt`, `final-rank-20.png`, `final-contest-colors-up.png`, `final-image-warning.png` e `final-image-warning-narrow.png`.

Não houve mudança de backend, contrato de API, benchmark ou cores de rating. Nome AI Lab e AC verde após erros já existiam no código atual e foram preservados. Os sinais continuam `−N` sem AC e `+N` com AC, conforme confirmado.
