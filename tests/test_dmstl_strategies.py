import pandas as pd

from tinyshift.series import DMSTLGlobalWrapper, DMSTLLocalWrapper, DMSTLWrapper
from tinyshift.series.dmstl import base


class ResidualModel:
    def fit(self, frame, **kwargs):
        self.frame = frame


def test_wrapper_selects_requested_residual_strategy():
    assert isinstance(DMSTLWrapper(mode="local", freq="D"), DMSTLLocalWrapper)
    assert isinstance(DMSTLWrapper(mode="global", freq="D"), DMSTLGlobalWrapper)


def test_global_strategy_unions_per_sku_pami_lags(monkeypatch):
    global_wrapper = DMSTLGlobalWrapper(
        residual_model_callable=lambda nlags, freq: ResidualModel(), freq="D"
    )
    monkeypatch.setattr(
        base,
        "select_pami_lag",
        lambda residual, **kwargs: (2 if residual[0] == 1 else 3, None, None),
    )
    assert global_wrapper._get_residual_lags("sku-a", pd.Series([1]).to_numpy()) == [2]
    assert global_wrapper._get_residual_lags("sku-b", pd.Series([2]).to_numpy()) == [3]

    global_wrapper.id_col_ = "unique_id"
    global_wrapper.time_col_ = "ds"
    global_wrapper.target_col_ = "y"
    global_wrapper._fit_residuals(
        [
            ("sku-a", pd.DataFrame({"unique_id": ["sku-a"], "ds": [1], "y": [0]}), [2]),
            ("sku-b", pd.DataFrame({"unique_id": ["sku-b"], "ds": [1], "y": [0]}), [3]),
        ],
        prediction_intervals=None,
        static_features=None,
    )
    assert global_wrapper.residual_mlforecast_.frame["unique_id"].tolist() == [
        "sku-a",
        "sku-b",
    ]
