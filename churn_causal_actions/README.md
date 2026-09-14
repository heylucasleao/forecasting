# Ações causais para churn

Este diretório descreve como passar de um **modelo de risco** (quem provavelmente
vai churnar) para uma **política de ação** (qual ação reduz churn para cada
cliente). As duas perguntas não são equivalentes: a probabilidade prevista não é
um efeito causal.

## Resposta curta à ideia do limiar

Selecionar clientes perto de um ponto de inflexão do score pode ser útil para:

- concentrar o estudo onde há dúvida operacional;
- aumentar a comparabilidade e o overlap entre ações;
- criar uma população-alvo local bem definida.

Mas isso **não cria automaticamente uma regressão descontínua (RD)**. RD só é
identificável quando uma regra externa atribui (ou muda fortemente a
probabilidade de) tratamento em um cutoff conhecido, o score é calculado antes
da ação e não pode ser manipulado ao redor do cutoff.

Se você apenas observa que pessoas acima e abaixo do cutoff receberam ações
diferentes, diferenças de churn podem vir tanto da ação quanto da forma como a
empresa escolheu quem tratar.

## Desenho recomendado: experimento local

1. Defina a unidade (cliente, conta ou domicílio), o horizonte de churn e a data
   índice. Uma linha deve representar uma decisão possível em uma data.
2. Congele um modelo de risco usando somente informação disponível **antes** da
   data índice. Gere scores fora da amostra (cross-fitting ou holdout temporal).
3. Escolha uma banda ao redor de um limiar operacional, por exemplo clientes
   com score entre 0,40 e 0,60. Declare que o efeito estimado valerá para essa
   população local, não para toda a base.
4. Dentro da banda, randomize `nenhuma_acao`, `desconto`, `contato_humano`, etc.
   Se não puder obrigar a ação, randomize uma oferta/incentivo: isso identifica
   inicialmente o efeito da intenção de tratar (ITT); adesão pode ser analisada
   como *fuzzy design*/variável instrumental.
5. Estime, para cada ação, risco de churn, diferença absoluta de risco,
   intervalo de confiança e valor líquido. Pré-defina métricas, horizonte,
   exclusões e tamanho de amostra.
6. Antes de lançar a política, valide-a em um novo holdout randomizado.

Com randomização, não é preciso que o ponto seja uma “inflexão” matemática. Um
cutoff operacional e uma banda que tenham volume, relevância e segurança são
mais importantes. Também não se deve ajustar o cutoff olhando o resultado do
mesmo experimento.

## Quando só há dados observacionais

Monte uma tabela longitudinal com:

| campo | significado |
|---|---|
| `id`, `data_indice` | unidade e momento da decisão |
| `acao` | ação efetivamente recebida |
| `churn_h` | churn até um horizonte fixo |
| `X_pre` | causas comuns da ação e do churn, medidas antes da ação |
| `score_oof` | risco fora da amostra, também pré-tratamento |
| `exposicao_rede` | ações recebidas por unidades conectadas |
| `cluster` | loja, agente, domicílio, região ou comunidade |

Depois:

1. desenhe um DAG e inclua causas comuns da ação e do churn; não ajuste por
   mediadores ou variáveis medidas depois da ação;
2. diagnostique overlap por ação; restrinja a população quando propensidades
   forem extremas;
3. estime efeitos com cross-fitting e um estimador duplamente robusto (AIPW/DR),
   comparando cada ação a `nenhuma_acao`;
4. reporte ATE e CATE, mas use CATE para decidir somente após validação fora da
   amostra;
5. faça análises de sensibilidade a confundimento não observado, definição de
   churn, janela, trimming e especificação dos modelos;
6. avalie a política aprendida prospectivamente.

As hipóteses principais passam a ser consistência, positividade e
ignorabilidade condicional. Elas não são verificáveis apenas nos dados.

## Sem SUTVA: interferência e versões do tratamento

“Sem garantir SUTVA” precisa virar uma hipótese mais específica; do contrário o
efeito `Y(acao) - Y(controle)` nem está completamente definido.

- **Interferência:** represente uma exposição, por exemplo proporção de colegas
  ou membros do domicílio tratados. Estime efeitos diretos e spillovers como
  funções de `(acao_propria, exposicao_rede)`.
- **Interferência parcial:** assuma que spillovers ficam dentro de clusters
  conhecidos e randomize/estime por cluster. Use erro-padrão ou bootstrap no
  nível do cluster.
- **Versões da ação:** registre canal, valor, duração, agente e adesão. “Recebeu
  contato” não é um tratamento único se suas versões têm efeitos diferentes.
- **Contaminação temporal:** uma ação hoje pode mudar ações futuras. Para
  decisões repetidas, use um desenho longitudinal (g-formula, MSM/IPW ou
  longitudinal TMLE), não uma tabela transversal ingênua.

Se a rede for conhecida, uma randomização em dois estágios é forte: randomize a
intensidade por cluster e, dentro do cluster, quais clientes recebem a ação.
Isso permite separar efeito direto e spillover sob uma exposição previamente
definida.

## Como escolher a “melhor” ação

Para cliente com covariáveis `x`, estime o efeito incremental de cada ação em
relação ao controle:

`tau_a(x) = P(churn | do(a), x) - P(churn | do(controle), x)`.

Valor menor é melhor. Uma regra econômica simples é:

`valor_a(x) = - LTV_em_risco(x) * tau_a(x) - custo_a(x)`.

Escolha a ação de maior valor apenas se superar `nenhuma_acao`, sujeita a
capacidade, equidade, frequência máxima e incerteza. Uma ação pode ter ótimo
uplift e ainda destruir valor se o custo for alto.

## Exemplo executável

[`example_local_randomized.py`](example_local_randomized.py) simula um piloto
randomizado dentro de uma banda do score, estima ITT por ação e calcula valor
líquido com intervalos por bootstrap:

```bash
uv run python churn_causal_actions/example_local_randomized.py
```

O exemplo mantém **score**, **estimador causal** e **decisão econômica** como
componentes separados. Ele é um esqueleto educacional; para produção, tamanho
de amostra, perdas de seguimento, multiplicidade, clusters e monitoramento
precisam ser especificados para o caso real.

Para dados históricos já existentes, use
[`churn_observational_dml.ipynb`](churn_observational_dml.ipynb). O notebook
compara cada ação ao controle com `DoubleMLIRM`, inclui diagnóstico de overlap,
sensibilidade a confundimento não observado e efeitos por grupos. A primeira
célula concentra o mapeamento do arquivo, outcome, ações e covariáveis.

O arquivo [`../data/churn.csv`](../data/churn.csv) é uma amostra **sintética**
para permitir a execução imediata do notebook. Ele não representa evidência
real e deve ser substituído pelos dados históricos, mantendo ou remapeando as
colunas na célula de configuração.

## Checklist mínimo antes da análise

- O score usa apenas dados pré-ação e foi produzido fora da amostra?
- A atribuição foi realmente randomizada? Há logs da oferta e da adesão?
- A janela e o cutoff foram definidos antes de olhar churn?
- Churn, horizonte, custo e LTV estão definidos sem ambiguidade?
- Há overlap suficiente para todas as ações comparadas?
- Quais unidades podem interferir umas nas outras?
- Existem versões relevantes da mesma ação?
- A inferência respeita clusters e decisões repetidas?
- A política final será validada prospectivamente?
