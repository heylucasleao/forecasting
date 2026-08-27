[Input Data: Série Temporal Sanitizada (y) + Tabela SKUs/Lojas + Calendário + Custos (c_u, c_o)]
   │
   ├──► [1. FEATURE ENGINEERING PIPELINE (Engenharia de Variáveis)]
   │    ├──► Lags Autoregressivos da Demanda Sanitizada
   │    │    ├─ Lags curtos (y_lag_1, y_lag_2, y_lag_3, y_lag_7)
   │    │    └─ Lags sazonais (y_lag_14, y_lag_28, y_lag_364)
   │    │
   │    ├──► Estatísticas Móveis (Rolling Windows sobre y sanitizado)
   │    │    ├─ Médias e Desvios Padrão (7d, 14d, 28d, 90d)
   │    │    └─ Proporção de dias com zero vendas (Zero Ratio 28d)
   │    │
   │    ├──► Coordenadas de Calendário & Temporalidade
   │    │    ├─ Dia da semana, Dia do mês, Mês, Trimestre
   │    │    └─ Seno/Cosseno do dia do ano (Sazonalidade cíclica)
   │    │
   │    └──► Exógenas Planejadas (Horizonte t+1 até t+h)
   │         ├─ Preço futuro planejado e Variação percentual (Price Discount %)
   │         ├─ Indicador de Promoção planejada (is_promo_planned)
   │         └─ Eventos Especiais & Feriados Futuros (Dias para o evento / Dias após)
   │
   ├──► [2. MODELING STRATEGY (Treinamento LightGBM Multi-Quantil Direct)]
   │    ├──► Estratégia de Janela de Treino
   │    │    └─ Direct Multi-Step: Treina 1 modelo por dia do horizonte (t+1, ..., t+h)
   │    │
   │    ├──► Objective Functions (Pinball Loss Direta)
   │    │    ├─ Quantil P10 (Cenário Pessimista / alpha = 0.10)
   │    │    ├─ Quantil P50 (Mediana / alpha = 0.50)
   │    │    └─ Quantil P90 (Cenário Otimista / alpha = 0.90)
   │    │
   │    └──► Validação Cruzada Temporal (Expanding Window)
   │         └─ Ausência total de Lookahead Bias
   │
   ├──► [3. PROBABILISTIC CALIBRATION & MONOTONICITY]
   │    ├──► Pós-Processamento: Monotonicity Enforcement
   │    │    └─ Correção in-place: Garante estritamente que P10 <= P50 <= P90
   │    │
   │    └──► Verificação de Distribuição Empírica
   │         └─ Formatação dos arrays (lo-80 = P10, median = P50, hi-80 = P90)
   │
   └──► [4. FINANCIAL OPTIMIZATION & DECISION MAKING (Newsvendor Solver)]
        ├──► Cálculo do Quantil Crítico (q_star)
        │    └─ q_star = c_u / (c_u + c_o) em nível de SKU/Período
        │
        ├──► Interpolação (2 Segmentos)
        │    └─ Mapeamento de q_star sobre os pontos (P10, 0.10), (P50, 0.50), (P90, 0.90)
        │
        ├──► Trava Limite de Risco & Truncamento
        │    └─ Clipping físico: np.clip(y_final, P10, P90) e não-negatividade
        │
        └──► OUTPUT FINAL DE SUPRIMENTOS / S&OP
             ├─ y_optimal: Quantidade exata a ser comprada/produzida (Unidades)
             ├─ P50: Demanda esperada para relatórios financeiros (DRE)
             └─ Tail Risk Metrics: Avaliação de VaR/CVaR do plano de estoque