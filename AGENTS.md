# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## Tests

- `uv sync --group dev` installs pytest; `uv run pytest -q` runs the suite.
- `tests/` holds characterization tests for pure/deterministic logic only
  (`AttackEvaluator`, `auto_detect_provider`/`_extract_first_model_id` in
  `modules/llm_client.py`, and `ConfigManager` dot-path + merge helpers).
  Keep tests offline — never construct an `LLMClient` with a model in
  `LLMClient.AUTO_MODEL_SENTINELS` (e.g. `""`, `"auto"`), since that triggers
  `discover_loaded_model()`, a real network call. Prefer testing module-level
  functions/staticmethods directly instead of instantiating `LLMClient`.
- If `LLMClient.chat` needs exercising in a future test, monkeypatch
  `requests.post` rather than hitting a live server.

## Lint / format / typecheck

- `requires-python` is `>=3.10` (not `3.14` — that version isn't released yet;
  CI installs `3.12`). Keep the floor aligned with what CI actually runs.
- `uv sync --group dev` also installs `ruff` and `mypy`. Run
  `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run mypy modules/ main.py` locally; the same three checks run in
  `.github/workflows/quality.yml` on every push/PR to `main`.
- As of this tooling's introduction, `ruff` and `mypy` report a large number
  of pre-existing findings across `modules/` and the attack scripts. Fixing
  those was explicitly out of scope for adding the tooling — treat them as
  known follow-up work, not new regressions, unless you touched that code.
