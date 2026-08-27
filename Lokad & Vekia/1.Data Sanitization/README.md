1. Diagnóstico de Prateleira Aberta (identify_stockout)

O que faz: Descobre quais dias a loja realmente teve oportunidade de vender e quais dias a prateleira esteve vazia (estoque zero no ERP).

Plano de Emergência: Se o sistema não tiver o dado de estoque, assume que a loja funcionou normalmente para não inventar vendas virtuais sem certeza.

2. Remoção do Efeito 'Gordura' de Marketing (extract_promo_baseline)

O que faz: Separa o giro orgânico (corrente) do pico temporário gerado por descontos ou encartes. Revela quanto o produto vende sozinho, sem incentivo de margem.

Plano de Emergência: Se a promoção foi fraca, os dados forem inconsistentes ou o pico for irreal (>5x), o sistema ignora o efeito para não distorcer a base com "falsos milagres" de vendas.

3. Higienização de Picos Anômalos (filter_organic_outliers)

O que faz: Limpa distorções pontuais (ex: uma empresa comprou todo o estoque de uma vez) sem confundir datas comemorativas reais (Natal, Black Friday) com erros de dados.

Plano de Emergência: Garante que produtos de baixo giro (vendas picadas) não tenham suas poucas vendas zeradas por engano pela régua estatística.

4. Reconstrução da Demanda Reprimida (impute_latent_demand)

Imputação por Perfil de Giro: Calcula quanto a loja deixou de vender enquanto a prateleira esteve vazia. Produtos de alto giro recebem a média dos dias vizinhos; produtos de giro esporádico recebem sua taxa média de presença.

Devolução da Força Comercial: Se o produto acabou no meio de uma promoção, o sistema calcula a perda considerando a demanda com a promoção ativa, e não a venda comum.

Plano de Emergência (Piso Físico): Garante que a demanda recalculada para um dia de ruptura nunca fique abaixo do que o cliente efetivamente pagou no caixa antes do estoque zerar.