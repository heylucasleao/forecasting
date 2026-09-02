"""Build the three reproducible TSF vs CPS benchmark notebooks."""

from pathlib import Path
import nbformat as nbf


ROOT = Path(__file__).parent


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)


SETUP = r'''from importlib.metadata import version
from pathlib import Path
from time import perf_counter
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
from lightgbm import LGBMRegressor
from mlforecast import MLForecast
from sklearn.ensemble import HistGradientBoostingRegressor

from tinyshift.forecasting import (
    NegativeBinomialFamily,
    TwoStageForecasterWrapper,
    WeibullFamily,
)
from tinyconformal.series import (
    ContinuousTimeSeriesConformalPredictiveSystem,
    DiscreteTimeSeriesConformalPredictiveSystem,
)

SEED = 42
H = 14
N_WINDOWS = 12
LEVEL = 0.90
DATA_DIR = Path("data/tsf_cps")
DATA_DIR.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

print({"tinyshift": version("tinyshift"), "tinyconformal": version("tinyconformal")})'''


HELPERS = r'''def make_forecaster(freq, lags):
    model = LGBMRegressor(
        n_estimators=120, learning_rate=0.05, num_leaves=15,
        verbosity=-1, random_state=SEED, n_jobs=1,
    )
    return MLForecast(models={"LGBM": model}, freq=freq, lags=lags)


def fit_tsf(train, freq, lags, family, h=H, n_windows=N_WINDOWS, step_size=None):
    model = TwoStageForecasterWrapper(make_forecaster(freq, lags), distribution=family)
    tic = perf_counter()
    model.fit(
        train, h=h, n_windows=n_windows, step_size=step_size, refit=True
    )
    fit_seconds = perf_counter() - tic
    tic = perf_counter()
    forecast = model.predict_distribution(h=h)
    predict_seconds = perf_counter() - tic
    return model, forecast, fit_seconds, predict_seconds


def fit_cps(
    train, freq, lags, discrete, h=H, n_windows=N_WINDOWS, step_size=None
):
    cls = (DiscreteTimeSeriesConformalPredictiveSystem if discrete
           else ContinuousTimeSeriesConformalPredictiveSystem)
    model = cls(
        learner=make_forecaster(freq, lags),
        dispersion_learner=HistGradientBoostingRegressor(
            max_iter=80, max_leaf_nodes=8, random_state=SEED
        ),
        horizon=h, n_windows=n_windows, alpha=1-LEVEL,
    )
    tic = perf_counter()
    model.fit(train, step_size=step_size, n_jobs=1)
    fit_seconds = perf_counter() - tic
    tic = perf_counter()
    forecast = model.predict_distribution(h=h)
    predict_seconds = perf_counter() - tic
    return model, forecast, fit_seconds, predict_seconds


def prediction_table(forecast, test, level=LEVEL):
    base = forecast.to_frame().copy()
    intervals = forecast.interval(level)
    quantiles = forecast.ppf([0.5])
    out = base.merge(test[["unique_id", "ds", "y"]], on=["unique_id", "ds"], validate="one_to_one")
    # APIs preservam a ordem do painel e nomeiam explicitamente os outputs.
    lo_col = next(c for c in intervals if "-lo-" in c)
    hi_col = next(c for c in intervals if "-hi-" in c)
    median_col = next(c for c in quantiles if "-q-50" in c)
    out["lower"] = intervals[lo_col].to_numpy()
    out["upper"] = intervals[hi_col].to_numpy()
    out["median"] = quantiles[median_col].to_numpy()
    return out


def metrics(table, method, dataset, fit_seconds, predict_seconds, level=LEVEL):
    y = table.y.to_numpy(float)
    lo, hi, pred = (table[c].to_numpy(float) for c in ["lower", "upper", "median"])
    alpha = 1-level
    covered = (y >= lo) & (y <= hi)
    winkler = (hi-lo) + (2/alpha)*(lo-y)*(y < lo) + (2/alpha)*(y-hi)*(y > hi)
    return {
        "dataset": dataset, "method": method,
        "RMSE_mediana": np.sqrt(np.mean((y-pred)**2)),
        "MAE_mediana": np.mean(np.abs(y-pred)),
        "cobertura_90": covered.mean(), "largura_media_90": np.mean(hi-lo),
        "Winkler_90": np.mean(winkler), "fit_s": fit_seconds,
        "predict_s": predict_seconds, "n_teste": len(y),
    }


def plot_intervals(tables, title):
    fig, axes = plt.subplots(len(tables), 1, figsize=(13, 3.6*len(tables)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (name, tab) in zip(axes, tables.items()):
        one = tab[tab.unique_id == tab.unique_id.iloc[0]]
        ax.plot(one.ds, one.y, "o-", color="black", label="observado", ms=3)
        ax.plot(one.ds, one["median"], color="C0", label="mediana")
        ax.fill_between(one.ds, one.lower, one.upper, alpha=.25, label="intervalo 90%")
        ax.set_title(name); ax.legend(ncol=3)
    fig.suptitle(title, y=1.01); plt.tight_layout()


def temporal_split(df, h=H):
    df = df.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    test = df.groupby("unique_id", group_keys=False).tail(h)
    train = df.drop(test.index).reset_index(drop=True)
    return train, test.reset_index(drop=True)'''


DISCRETE_LOADERS = r'''M5_URL = "https://www.kaggle.com/competitions/m5-forecasting-accuracy/data"
M5_MIRROR = "https://huggingface.co/datasets/kashif/M5/resolve/main/sales_train_evaluation.csv"
BIKE_URL = "https://raw.githubusercontent.com/udacity/deep-learning/master/first-neural-network/Bike-Sharing-Dataset/hour.csv"


def load_m5(n_series=5, n_days=700):
    """Baixa a competição oficial (aceite das regras/login Kaggle pode ser necessário)."""
    target = DATA_DIR / "m5" / "sales_train_evaluation.csv"
    if not target.exists():
        import kagglehub
        try:
            downloaded = Path(kagglehub.competition_download("m5-forecasting-accuracy"))
            candidates = list(downloaded.rglob("sales_train_evaluation.csv"))
        except Exception as exc:
            warnings.warn(f"Kaggle indisponível ({type(exc).__name__}); usando espelho público Hugging Face.")
            candidates = []
        source = candidates[0] if candidates else M5_MIRROR
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, Path):
            target.write_bytes(source.read_bytes())
        else:
            from urllib.request import urlretrieve
            urlretrieve(source, target)
    wide = pd.read_csv(target, nrows=n_series)
    day_cols = [c for c in wide if c.startswith("d_")][-n_days:]
    long = wide[["id", *day_cols]].melt("id", var_name="day", value_name="y")
    long["ds"] = pd.Timestamp("2011-01-29") + pd.to_timedelta(long.day.str[2:].astype(int)-1, unit="D")
    return long.rename(columns={"id": "unique_id"})[["unique_id", "ds", "y"]].astype({"y": int})


def load_bike():
    raw = pd.read_csv(BIKE_URL)
    raw["ds"] = pd.to_datetime(raw.dteday) + pd.to_timedelta(raw.hr, unit="h")
    # Maior trecho horário contíguo: não preenche nem sintetiza horas ausentes.
    raw = raw.sort_values("ds")
    run = raw.ds.diff().ne(pd.Timedelta(hours=1)).cumsum()
    raw = raw[run.eq(run.value_counts().idxmax())].tail(24*180)
    return pd.DataFrame({"unique_id": "CapitalBikeshare", "ds": raw.ds, "y": raw.cnt.astype(int)})


datasets = {"M5 (5 itens)": load_m5(), "UCI Bike Sharing": load_bike()}
for name, frame in datasets.items():
    print(name, frame.shape, frame.ds.min(), frame.ds.max(), "inteiros:", np.all(frame.y == np.floor(frame.y)))'''


CONT_LOADERS = r'''AIR_URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/airline-passengers.csv"
TEMP_URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/daily-min-temperatures.csv"


def load_air():
    raw = pd.read_csv(AIR_URL)
    return pd.DataFrame({"unique_id": "AirPassengers", "ds": pd.to_datetime(raw.Month),
                         "y": raw.Passengers.astype(float)})


def load_temperature():
    raw = pd.read_csv(TEMP_URL)
    out = pd.DataFrame({"unique_id": "Melbourne", "ds": pd.to_datetime(raw.Date),
                        "y": pd.to_numeric(raw.Temp, errors="coerce")}).dropna()
    # Conversão física exata °C -> K preserva os dados e satisfaz o suporte Weibull.
    out["y"] = out["y"] + 273.15
    # Mantém o trecho diário contíguo mais longo, sem imputar nem sintetizar observações.
    run = out.ds.diff().ne(pd.Timedelta(days=1)).cumsum()
    longest = run.value_counts().idxmax()
    return out[run.eq(longest)].tail(3*365).reset_index(drop=True)


datasets = {"AirPassengers": load_air(), "Melbourne min temperature": load_temperature()}
for name, frame in datasets.items():
    print(name, frame.shape, frame.ds.min(), frame.ds.max(), "mínimo:", frame.y.min())'''


def benchmark_cell(discrete, weibull=False):
    family = "WeibullFamily()" if weibull else ("NegativeBinomialFamily()" if discrete else "WeibullFamily()")
    return f'''results, predictions = [], {{}}
for dataset_name, df in datasets.items():
    freq = "MS" if dataset_name == "AirPassengers" else ("h" if "Bike" in dataset_name else "D")
    lags = [1, 12] if freq == "MS" else ([1, 24, 168] if freq == "h" else [1, 7, 28])
    step_size = 3 if dataset_name == "AirPassengers" else 7
    train, test = temporal_split(df)

    tsf, tsf_fc, tsf_fit, tsf_pred = fit_tsf(
        train, freq, lags, {family}, step_size=step_size
    )
    cps, cps_fc, cps_fit, cps_pred = fit_cps(
        train, freq, lags, discrete={discrete}, step_size=step_size
    )
    tsf_tab = prediction_table(tsf_fc, test)
    cps_tab = prediction_table(cps_fc, test)
    predictions[(dataset_name, "TSF")] = tsf_tab
    predictions[(dataset_name, "CPS")] = cps_tab
    results += [
        metrics(tsf_tab, "TSF", dataset_name, tsf_fit, tsf_pred),
        metrics(cps_tab, "CPS", dataset_name, cps_fit, cps_pred),
    ]

resultados = pd.DataFrame(results)
display(resultados.round(4))
display(resultados.pivot(index="dataset", columns="method",
                         values=["RMSE_mediana", "cobertura_90", "largura_media_90", "Winkler_90", "fit_s"]).round(4))'''


PLOTS = r'''for dataset_name in datasets:
    plot_intervals(
        {method: predictions[(dataset_name, method)] for method in ["TSF", "CPS"]},
        dataset_name,
    )

metric_cols = ["RMSE_mediana", "cobertura_90", "largura_media_90", "Winkler_90"]
fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, metric in zip(axes, metric_cols):
    sns.barplot(resultados, x="dataset", y=metric, hue="method", ax=ax)
    ax.tick_params(axis="x", rotation=25); ax.set_title(metric)
plt.tight_layout()'''


INTERPRET = r'''def winners(frame):
    rows = []
    for dataset, part in frame.groupby("dataset"):
        target = 0.90
        rows.append({
            "dataset": dataset,
            "menor_RMSE": part.loc[part.RMSE_mediana.idxmin(), "method"],
            "cobertura_mais_próxima_90%": part.loc[(part.cobertura_90-target).abs().idxmin(), "method"],
            "menor_Winkler": part.loc[part.Winkler_90.idxmin(), "method"],
            "fit_mais_rápido": part.loc[part.fit_s.idxmin(), "method"],
        })
    return pd.DataFrame(rows)

display(winners(resultados))
print("Leitura: cobertura isolada não premia intervalos excessivamente largos; por isso Winkler é a métrica principal de intervalo.")'''


def notebook(title, intro, loader, discrete, weibull=False, timing_only=False):
    nb = nbf.v4.new_notebook()
    cells = [md(f"# {title}\n\n{intro}"), code(SETUP), code(HELPERS), code(loader)]
    cells += [md("## Benchmark temporal\n\nA última janela é teste; todas as janelas anteriores são treino/calibração. O mesmo LightGBM, lags, horizonte, 12 janelas e sobreposição são usados por TSF e CPS. `step_size=3` em AirPassengers e `step_size=7` nas demais séries; como ambos são menores que `H=14`, as janelas se sobrepõem."), code(benchmark_cell(discrete, weibull))]
    if timing_only:
        cells += [md("## Comparação de tempo\n\nOs tempos abaixo são medições locais desta execução (`perf_counter`), com `n_jobs=1` e três repetições completas para reduzir ruído."), code(r'''timings = []
for dataset_name, df in datasets.items():
    freq = "MS" if dataset_name == "AirPassengers" else "D"
    lags = [1, 12] if freq == "MS" else [1, 7, 28]
    step_size = 3 if dataset_name == "AirPassengers" else 7
    train, _ = temporal_split(df)
    for method in ["TSF", "CPS"]:
        fit_times, pred_times = [], []
        for repeat in range(3):
            if method == "TSF":
                _, _, ft, pt = fit_tsf(
                    train, freq, lags, WeibullFamily(), step_size=step_size
                )
            else:
                _, _, ft, pt = fit_cps(
                    train, freq, lags, discrete=False, step_size=step_size
                )
            fit_times.append(ft); pred_times.append(pt)
        timings.append({"dataset": dataset_name, "method": method,
                        "fit_mediana_s": np.median(fit_times),
                        "predict_mediana_s": np.median(pred_times),
                        "fit_min_s": np.min(fit_times), "fit_max_s": np.max(fit_times)})
tempos = pd.DataFrame(timings)
display(tempos.round(4))
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
sns.barplot(tempos, x="dataset", y="fit_mediana_s", hue="method", ax=axes[0])
sns.barplot(tempos, x="dataset", y="predict_mediana_s", hue="method", ax=axes[1])
axes[0].set_title("Tempo mediano de ajuste"); axes[1].set_title("Tempo mediano de predição")
for ax in axes: ax.tick_params(axis="x", rotation=20)
plt.tight_layout()''')]
    else:
        cells += [md("## Visualização e síntese"), code(PLOTS), code(INTERPRET)]
    cells += [md("## Reprodutibilidade e ressalvas\n\n- Não há geração de dados sintéticos. As URLs/fontes estão explícitas no notebook.\n- Resultados dependem de hardware, versões e da janela temporal escolhida.\n- M5 exige aceitar as regras da competição e autenticar o Kaggle uma única vez.\n- TSF é paramétrico; CPS usa resíduos conformais empíricos. Nenhum método domina necessariamente em todos os critérios.")]
    nb.cells = cells
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python", "version": "3.10"}
    return nb


notebooks = {
    "12_tsf_vs_cps_discretos.ipynb": notebook(
        "TSF vs CPS — dados discretos reais",
        "Comparação entre o **Two-Stage Forecaster (TSF)** do `tinyshift` e o **Conformal Predictive System (CPS)** do `tinyconformal` em M5 e UCI Bike Sharing. Ambos são avaliados fora da amostra, com alvos inteiros e sem dados sintéticos.",
        DISCRETE_LOADERS, True,
    ),
    "13_tsf_vs_cps_continuos.ipynb": notebook(
        "TSF vs CPS — dados contínuos reais",
        "Comparação probabilística em duas séries públicas reais: AirPassengers e temperaturas mínimas diárias de Melbourne. Para o TSF é usada a família Weibull, adequada ao suporte estritamente positivo observado.",
        CONT_LOADERS, False, weibull=True,
    ),
    "14_tsf_vs_cps_tempo_weibull.ipynb": notebook(
        "TSF vs CPS — avaliação de tempo (TSF WeibullFamily)",
        "Benchmark de ajuste e predição usando os mesmos dados contínuos reais. O TSF é configurado explicitamente com `WeibullFamily`; o CPS permanece semiparamétrico/conformal.",
        CONT_LOADERS, False, weibull=True, timing_only=True,
    ),
}

for filename, nb in notebooks.items():
    nbf.write(nb, ROOT / filename)
    print("created", filename)
