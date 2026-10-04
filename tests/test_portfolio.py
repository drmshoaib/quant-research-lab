import numpy as np
import pandas as pd

from quantlab.portfolio import rank_weights, optimise_weights


def test_rank_weights_constraints():
    scores = pd.Series(np.linspace(-1, 1, 20), index=[f"A{i}" for i in range(20)])
    w = rank_weights(scores, gross_limit=1.0, max_abs_weight=0.08)
    assert abs(w.sum()) < 1e-10
    assert w.abs().sum() <= 1.0 + 1e-10
    assert w.abs().max() <= 0.08 + 1e-10


def test_optimizer_constraints():
    names = [f"A{i}" for i in range(12)]
    alpha = pd.Series(np.linspace(-0.02, 0.02, len(names)), index=names)
    cov = pd.DataFrame(np.eye(len(names)) * 0.01, index=names, columns=names)
    w = optimise_weights(alpha, cov, gross_limit=1.0, max_abs_weight=0.15)
    assert abs(w.sum()) < 1e-5
    assert w.abs().sum() <= 1.001
    assert w.abs().max() <= 0.1501
