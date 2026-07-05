# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## Tests

- `uv sync --group dev` installs pytest; `uv run pytest -q` runs the suite.
- `tests/` holds characterization tests for pure/deterministic logic only
  (`AttackEvaluator`, `auto_detect_provider`/`_extract_first_model_id` in
  `modules/llm_client.py`, `ConfigManager` dot-path + merge helpers, and the
  `main.py` end-of-run summary aggregation, which must count both attack-list
  results and the `summary` totals of `attacks`-less shapes such as
  `comparison` and lab modules).
  Keep tests offline — never construct an `LLMClient` with a model in
  `LLMClient.AUTO_MODEL_SENTINELS` (e.g. `""`, `"auto"`), since that triggers
  `discover_loaded_model()`, a real network call. Prefer testing module-level
  functions/staticmethods directly instead of instantiating `LLMClient`.
- If `LLMClient.chat` needs exercising in a future test, monkeypatch
  `requests.post` rather than hitting a live server.
