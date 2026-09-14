"""Exemplo de piloto multi-ação randomizado perto de um cutoff de risco.

O script usa apenas numpy e pandas, simula dados e calcula diferenças de médias
(ITT) com intervalos de bootstrap e uma decisão econômica simples.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PilotConfig:
    n_candidates: int = 30_000
    cutoff: float = 0.50
    bandwidth: float = 0.10
    seed: int = 42
    bootstrap_draws: int = 2_000


ACTIONS = ("controle", "desconto", "contato_humano")
COST = {"controle": 0.0, "desconto": 35.0, "contato_humano": 12.0}


def simulate_pilot(config: PilotConfig) -> pd.DataFrame:
    """Cria candidatos, seleciona a banda e randomiza igualmente as ações."""
    rng = np.random.default_rng(config.seed)
    tenure = rng.exponential(18, config.n_candidates)
    complaints = rng.poisson(0.8, config.n_candidates)
    usage_change = rng.normal(-0.05, 0.25, config.n_candidates)

    logit = -0.8 - 0.025 * tenure + 0.55 * complaints - 2.2 * usage_change
    score = 1 / (1 + np.exp(-logit))
    eligible = np.abs(score - config.cutoff) <= config.bandwidth

    df = pd.DataFrame(
        {
            "customer_id": np.arange(config.n_candidates)[eligible],
            "score_pre": score[eligible],
            "tenure": tenure[eligible],
            "complaints": complaints[eligible],
            "usage_change": usage_change[eligible],
        }
    )

    # Esta é a etapa que dá identificação causal ao piloto, não o cutoff.
    df["action_assigned"] = rng.choice(ACTIONS, size=len(df), replace=True)

    # Efeitos heterogêneos: desconto ajuda mais clientes novos; contato ajuda
    # mais quem reclamou. Valores positivos elevariam churn (efeito negativo).
    effect = np.zeros(len(df))
    is_discount = df["action_assigned"].eq("desconto").to_numpy()
    is_contact = df["action_assigned"].eq("contato_humano").to_numpy()
    effect[is_discount] = -0.07 * (df.loc[is_discount, "tenure"] < 12)
    effect[is_contact] = -0.035 - 0.025 * (
        df.loc[is_contact, "complaints"] >= 2
    )

    churn_probability = np.clip(df["score_pre"].to_numpy() + effect, 0.01, 0.99)
    df["churn_90d"] = rng.binomial(1, churn_probability)
    df["ltv_at_risk"] = np.clip(500 + 20 * df["tenure"], 300, 2_500)
    return df


def bootstrap_risk_difference(
    df: pd.DataFrame, action: str, draws: int, seed: int
) -> tuple[float, float, float]:
    """Diferença de risco ação-controle e IC percentil de 95%."""
    treated = df.loc[df["action_assigned"].eq(action), "churn_90d"].to_numpy()
    control = df.loc[df["action_assigned"].eq("controle"), "churn_90d"].to_numpy()
    estimate = treated.mean() - control.mean()
    rng = np.random.default_rng(seed)
    samples = np.empty(draws)
    for draw in range(draws):
        samples[draw] = (
            rng.choice(treated, len(treated), replace=True).mean()
            - rng.choice(control, len(control), replace=True).mean()
        )
    low, high = np.quantile(samples, [0.025, 0.975])
    return float(estimate), float(low), float(high)


def summarize(df: pd.DataFrame, config: PilotConfig) -> pd.DataFrame:
    """Produz tabela de ITT e valor médio incremental por cliente."""
    average_ltv = float(df["ltv_at_risk"].mean())
    rows = []
    for index, action in enumerate(ACTIONS[1:]):
        effect, low, high = bootstrap_risk_difference(
            df, action, config.bootstrap_draws, config.seed + index + 1
        )
        rows.append(
            {
                "action": action,
                "n": int(df["action_assigned"].eq(action).sum()),
                "risk_difference": effect,
                "ci95_low": low,
                "ci95_high": high,
                # Redução do churn vira valor positivo; custo vira negativo.
                "incremental_value_per_customer": -average_ltv * effect
                - COST[action],
            }
        )
    return pd.DataFrame(rows).sort_values(
        "incremental_value_per_customer", ascending=False
    )


def main() -> None:
    config = PilotConfig()
    pilot = simulate_pilot(config)
    print(f"Clientes elegíveis na banda: {len(pilot):,}")
    print("\nTaxa observada por braço:")
    print(
        pilot.groupby("action_assigned")["churn_90d"]
        .agg(["size", "mean"])
        .to_string(float_format=lambda value: f"{value:.4f}")
    )
    print("\nEfeito causal local (ITT) e valor:")
    print(summarize(pilot, config).to_string(index=False, float_format="%.4f"))


if __name__ == "__main__":
    main()
