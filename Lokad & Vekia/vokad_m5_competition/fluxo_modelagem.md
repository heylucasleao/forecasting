[1. Prepara e Coleta de Dados]
         │
         ▼
 [2. Estruturação Histórica da Demanda (ISSM)]
   ├── Nível de vendas e tendência
   ├── Sazonalidade (dia da semana, eventos, promoções)
   └── Filtragem de ruído e erro
         │
         ▼
 [3. Modelagem de Incerteza (Distribuição Binomial Negativa)]
   ├── Estimativa da Média (λ) por SKU/dia
   └── Estimativa do Parâmetro de Dispersão (r / Overdispersion)
         │
         ▼
 [4. Otimização E2E com Função de Perda Pinball (Pinball Loss)]
   ├── Definição dos Quantis Alvo (50%, 67%, 95%, 99%)
   └── Treinamento por Diferenciação Automática / Gradiante
         │
         ▼
 [5. Inferência e Agregação Hieraquica]
   ├── Geração das Distribuições Probabilísticas por SKU
   └── Agregação Bottom-Up para os Níveis Superiores
         │
         ▼
 [6. Saída Final: Quantis de Previsão de Demanda]