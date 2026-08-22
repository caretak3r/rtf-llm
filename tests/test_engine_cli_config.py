"""build_engine_config: explicit live gate + best_of_n passthrough."""

from main import build_engine_config


def test_live_defaults_off_and_params_set():
    cfg = build_engine_config(
        {"llm": {"provider": "openai"}}, live=False, n_samples=5, diversity_temp=0.9
    )
    assert cfg["engine"]["live"] is False
    assert cfg["engine"]["best_of_n"] == {"n_samples": 5, "diversity_temp": 0.9}
    assert cfg["llm"]["provider"] == "openai"  # passthrough preserved


def test_live_true_overrides_config_default():
    cfg = build_engine_config(
        {"engine": {"live": False}}, live=True, n_samples=1, diversity_temp=0.0
    )
    assert cfg["engine"]["live"] is True
