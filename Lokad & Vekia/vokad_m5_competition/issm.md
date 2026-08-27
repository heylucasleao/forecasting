┌─────────────────────────────────────────────────────────────────────────────┐
│                             1. FASE DE TREINO                               │
└─────────────────────────────────────────────────────────────────────────────┘
  
   DataFrame Treino (id, ds, y, sell_price, is_holiday_window)
                              │
                              ▼
                  MLForecast.preprocess()
               (Gera Lags, MVs, dayofweek)
                              │
                              ▼
                     Matriz de Treino (X_train, y_train)
                              │
                              ▼
                     LightGBM (Poisson) .fit()
                              │
                              ▼
                   Prever lambda_t (Histórico)
                              │
                              ▼
              Ajustar 'r' por SKU via SciPy (MLE)
            (Gera dicionário: {SKU_A: 2.3, SKU_B: 0.8})

───────────────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│                            2. FASE DE PREVISÃO                              │
└─────────────────────────────────────────────────────────────────────────────┘

   Novo Horizonte Future (h passos à frente) + Variáveis Exógenas Conhecidas
              (id, ds, sell_price futuro, is_holiday_window futuro)
                              │
                              ▼
                  MLForecast.predict(h=h, X_df=X_df)
                   ┌───────────────────────────────┐
                   │    Loop Recursivo do Nixtla:  │
                   │ 1. Calcula Lags/MVs t+1       │
                   │ 2. LightGBM prevê lambda_{t+1}│
                   │ 3. Atualiza estado            │
                   │ 4. Repete até t+h             │
                   └───────────────────────────────┘
                              │
                              ▼
                  Dataframe com lambda_t Futuro
                              │
                              ▼
              Mapeia o 'r' salvo no treino de cada SKU
                              │
                              ▼
             Aplica a Inversa da DBN (scipy.nbinom.ppf)
       Calcula P(y <= Q) para os quantis [50%, 67%, 95%, 99%]