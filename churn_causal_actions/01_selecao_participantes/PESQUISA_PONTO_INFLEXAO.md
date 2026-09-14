# Pesquisa: “ponto de inflexão” para selecionar o piloto

## Conclusão

Não encontrei fundamento para tratar genericamente o “ponto de inflexão da
probabilidade de churn” como um cutoff causal. Há quatro ideias diferentes:

1. **Inflexão matemática.** Uma curva logística tem máxima inclinação quando a
   probabilidade ajustada é 0,5. Em árvores ou boosting, porém, não há
   necessariamente uma curva unidimensional suave nem uma única inflexão. A
   inflexão da calibração usada no notebook é uma convenção diagnóstica.
2. **Limiar de decisão.** Converter probabilidade em ação é um problema de
   decisão separado da estimação do risco. O padrão 0,5 raramente representa o
   custo, a capacidade ou o benefício do negócio. A documentação oficial do
   scikit-learn recomenda ajustar o threshold por uma métrica/utility em dados
   separados ou por validação cruzada e alerta contra usar os mesmos dados para
   treinar e ajustar o cutoff.
3. **Amostragem por incerteza.** Em active learning, selecionar pontos perto da
   fronteira serve para obter rótulos informativos e melhorar um classificador.
   Isso não prova que tais clientes são os que mais respondem a uma ação de
   retenção e não produz identificação causal.
4. **Regressão descontínua.** RD exige que a probabilidade de receber tratamento
   mude no cutoff de uma variável de atribuição. Selecionar uma janela ao redor
   de um cutoff predito, por si só, não cria RD. Se randomizarmos dentro da
   janela, a identificação vem da randomização.

## Implicação para este projeto

O notebook calcula a inflexão da curva logística de calibração porque ela é uma
definição reprodutível da ideia solicitada. Para uma decisão real, devem ser
comparados pelo menos:

- cutoff por valor econômico esperado;
- cutoff por capacidade máxima do piloto;
- cutoff por uma métrica predefinida e validada fora da amostra;
- estabilidade do cutoff entre folds, períodos e segmentos.

A janela ao redor do cutoff define a **população local de interesse**. Controle
e tratamento são então sorteados 1:1, estratificados pelo score. Não se deve
chamar os dois lados do cutoff de controle e tratamento, a menos que uma regra
de atribuição real use o próprio cutoff — caso em que o desenho e seus testes de
validade precisam seguir RD.

## Fontes

- [Scikit-learn — Tuning the decision threshold for class prediction](https://scikit-learn.org/stable/modules/classification_threshold.html)
- [Scikit-learn — Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Imbens e Lemieux — Regression Discontinuity Designs: A Guide to Practice](https://www.nber.org/papers/t0337)
- [Settles — Active Learning Literature Survey (University of Wisconsin–Madison)](https://minds.wisconsin.edu/handle/1793/60660)
