# Etapa 1 — seleção de participantes

Esta etapa constrói um score de churn com cross-fitting, estima um cutoff de
priorização e seleciona clientes próximos a ele para um piloto 1:1 entre
controle e tratamento.

Use o notebook
[`selecao_por_inflexao.ipynb`](selecao_por_inflexao.ipynb). Ele produz
`data/churn_pilot_assignment.csv` com a alocação proposta.

Se `data/churn.csv` não existir, a função `generate_synthetic_churn` dentro do
notebook cria uma base didática automaticamente. Quando o arquivo existir, o
notebook sempre prefere os dados fornecidos.

## Interpretação correta

O cutoff é a probabilidade bruta na qual uma curva logística de calibração
ajustada sobre previsões out-of-fold atinge risco calibrado de 50%. Esse é um
conceito operacional reprodutível de inflexão, não uma propriedade causal do
modelo. O notebook também mostra métricas e a curva de calibração para que o
cutoff não seja aceito sem diagnóstico.

A proximidade do cutoff define apenas a população do piloto. É a randomização
posterior que cria grupos causalmente comparáveis. DML será usado na etapa de
estimação quando houver outcome pós-intervenção, especialmente se ocorrer
não adesão ou a atribuição não tiver sido perfeitamente randomizada.

## Uso real

O exemplo usa `data/churn.csv` para demonstrar o pipeline retrospectivamente.
Em produção:

1. desenvolva e valide o modelo em uma base histórica;
2. congele modelo, features, cutoff e largura da janela;
3. calcule o score em uma nova coorte elegível, antes de qualquer ação;
4. randomize apenas essa nova coorte;
5. registre oferta, tratamento recebido, contaminação e churn futuro.
