# Plan 029: Implement `patch` and `backdoor` weight modification

> **Executor instructions**: Follow step by step. Run every verification before moving on. STOP conditions → stop and report. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat e82a0f4..HEAD -- modules/weight_manipulation.py`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: MED
- **Depends on**: none (the modification half requires a local transformers model — see STOP; the *dispatch fix* works regardless)
- **Category**: bug
- **Planned at**: commit `e82a0f4`, 2026-07-20

## Why this matters

`weight_manipulation` advertises `patch` and `backdoor` modification techniques (the two most security-relevant for LLM04 backdoor analysis) but `_test_weight_modification` only dispatches `add_noise`/`scale`/`prune`. `patch` and `backdoor` hit the `else` branch → "Modification type not implemented" → `success: False`. A user running `--module weight-manipulation` sees `patch`/`backdoor` "fail" and concludes the model resists them, when they were never attempted. False-negative coverage on the two techniques that matter most.

## Current state

- `modules/weight_manipulation.py:170-190` — `_get_adversarial_patch_patterns` (returns `patch`) and `_get_backdoor_patterns` (returns `backdoor`).
- `modules/weight_manipulation.py:328-371` — `_test_weight_modification` dispatch.

Excerpt (`modules/weight_manipulation.py:343-367`):

```python
        try:
            mod_type = modification_pattern.get('modification')
            params = modification_pattern.get('params', {})

            if mod_type == 'add_noise':
                success = self._add_noise_to_weights(params)
                result['success'] = success
                result['modification_applied'] = success
                result['indicators'].append('Noise addition attempted')

            elif mod_type == 'scale':
                success = self._scale_weights(params)
                ...

            elif mod_type == 'prune':
                success = self._prune_weights(params)
                ...

            else:
                result['indicators'].append(f'Modification type not implemented: {mod_type}')
```

Excerpt (`modules/weight_manipulation.py:170-179`):

```python
    def _get_adversarial_patch_patterns(self) -> List[Dict[str, Any]]:
        """Adversarial patch patterns"""
        return [
            {
                'name': 'adversarial_patch',
                'description': 'Inject adversarial patch',
                'modification': 'patch',
                'params': {'patch_location': 'attention', 'patch_value': 0.1}
            },
            ...
        ]
```

### Repo conventions to match

- `_add_noise_to_weights`/`_scale_weights`/`_prune_weights` (lines ~373+) return `bool`. Match the signature: `_apply_patch(self, params: Dict) -> bool`.
- `self.local_model_handler` is the loaded model (transformers `AutoModel`); `None` if unavailable (line 339 guard).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Lint | `uv run ruff check modules/weight_manipulation.py` | exit 0 |
| Typecheck | `uv run mypy modules/weight_manipulation.py` | exit 0 |
| Tests | `uv run pytest -q` (requires 001) | all pass |

## Scope

**In scope**:
- `modules/weight_manipulation.py` — add `_apply_patch` + `_apply_backdoor` methods + wire them into the dispatch.
- `tests/test_weight_modification_dispatch.py` (create — depends on 001).

**Out of scope**:
- The extraction half of the module (that's plan 037).
- `config.json` `local_models` defaults (separate concern).
- Adding a llama.cpp/GGUF loader (separate).

## Git workflow

- Branch: `advisor/029-weight-patch-backdoor`
- Commit: `fix: implement patch and backdoor weight modification dispatch`
- Do NOT push unless instructed.

## Steps

### Step 1: Add `_apply_patch` and `_apply_backdoor` methods

Add two methods near `_prune_weights` (after line ~363). They operate on `self.local_model_handler` (a transformers model). Pattern after `_add_noise_to_weights` (which iterates `model.parameters()` and adds noise):

```python
    def _apply_patch(self, params: Dict[str, Any]) -> bool:
        """Apply an adversarial weight patch to a specific layer location.
        Adds a structured perturbation to attention weights at the given location."""
        try:
            location = params.get('patch_location', 'attention')
            value = params.get('patch_value', 0.1)
            model = self.local_model_handler
            if model is None:
                return False
            with torch.no_grad():
                for name, param in model.named_parameters():
                    if location in name.lower():
                        # Structured patch: add value to a block of weights
                        flat = param.data.view(-1)
                        n = min(flat.numel(), 64)
                        flat[:n] += value
                        break
            return True
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Patch failed: {e}{Style.RESET_ALL}")
            return False

    def _apply_backdoor(self, params: Dict[str, Any]) -> bool:
        """Implant a trigger-phrase backdoor: perturb embedding weights so a
        specific trigger token biases output toward a target token."""
        try:
            trigger_token = params.get('trigger_token', '[BACKDOOR]')
            target_shift = params.get('target_shift', 0.5)
            model = self.local_model_handler
            tokenizer = getattr(self, 'tokenizer', None)
            if model is None or tokenizer is None:
                return False
            with torch.no_grad():
                # Bias the trigger token's embedding toward a high-magnitude direction
                embed_layer = model.get_input_embeddings()
                ids = tokenizer.encode(trigger_token, add_special_tokens=False)
                if ids:
                    embed_layer.weight[ids[0]] += target_shift
            return True
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Backdoor failed: {e}{Style.RESET_ALL}")
            return False
```

**Verify**: `grep -n 'def _apply_patch\|def _apply_backdoor' modules/weight_manipulation.py` → 2 matches. `uv run ruff check modules/weight_manipulation.py` → exit 0.

### Step 2: Wire them into the dispatch

In `_test_weight_modification` (line ~347-366), add `elif` branches before the `else`:

```python
            elif mod_type == 'patch':
                success = self._apply_patch(params)
                result['success'] = success
                result['modification_applied'] = success
                result['indicators'].append('Adversarial patch attempted')

            elif mod_type == 'backdoor':
                success = self._apply_backdoor(params)
                result['success'] = success
                result['modification_applied'] = success
                result['indicators'].append('Backdoor implant attempted')

            elif mod_type == 'add_adversarial':
                # add_adversarial (from _get_weight_addition_patterns) — alias to patch
                success = self._apply_patch(params)
                result['success'] = success
                result['modification_applied'] = success
                result['indicators'].append('Adversarial perturbation attempted')

            elif mod_type == 'subtract_noise':
                # subtract_noise (from _get_weight_subtraction_patterns) — mirror add_noise
                success = self._add_noise_to_weights({**params, 'invert': True})
                result['success'] = success
                result['modification_applied'] = success
                result['indicators'].append('Noise subtraction attempted')

            else:
                result['indicators'].append(f'Modification type not implemented: {mod_type}')
```

**Verify**: `grep -n "Modification type not implemented" modules/weight_manipulation.py` → still 1 (the else remains for truly-unknown types). `grep -n "mod_type == 'patch'\|mod_type == 'backdoor'" modules/weight_manipulation.py` → 2 matches.

### Step 3: Add a characterization test

Create `tests/test_weight_modification_dispatch.py` (depends on 001). Tests that `patch`/`backdoor` no longer hit the "not implemented" else:

```python
"""Test patch/backdoor dispatch no longer no-ops."""
from modules.weight_manipulation import ModelWeightManipulationModule

def test_patch_dispatched_not_else(monkeypatch):
    mod = ModelWeightManipulationModule.__new__(ModelWeightManipulationModule)
    mod.local_model_handler = None  # no model → returns False early, but via the handler
    called = {}
    def fake_patch(params):
        called['patch'] = params
        return True
    mod._apply_patch = fake_patch
    # bypass the local_model_handler None-guard by stubbing
    mod.local_model_handler = object()  # truthy
    result = mod._test_weight_modification(
        {'name': 'adversarial_patch', 'modification': 'patch', 'params': {'patch_value': 0.1}},
        'adversarial_patches',
    )
    assert 'patch' in called, "patch was not dispatched (hit the else)"
    assert result['indicators'] != [] and 'not implemented' not in result['indicators'][-1]
```

**Verify**: `uv run pytest tests/test_weight_modification_dispatch.py -q` → all pass (if 001 landed).

## Test plan

- `tests/test_weight_modification_dispatch.py` (above) — asserts `patch` is dispatched (not the else).
- Edge: without a real local model, `_apply_patch` returns False (caught exception) — the indicator should say "attempted" not "not implemented". The test stubs `_apply_patch` to isolate the dispatch logic.

## Done criteria

ALL must hold:

- [ ] `grep -n "mod_type == 'patch'\|mod_type == 'backdoor'" modules/weight_manipulation.py` returns 2 matches
- [ ] `grep -n 'def _apply_patch\|def _apply_backdoor' modules/weight_manipulation.py` returns 2 matches
- [ ] `uv run ruff check modules/weight_manipulation.py` exits 0
- [ ] `uv run mypy modules/weight_manipulation.py` exits 0
- [ ] No files outside `modules/weight_manipulation.py` (and the test) are modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- `torch` is not a dependency (it's commented in `requirements.txt:6` as optional). The methods use `torch.no_grad()` — if torch is unavailable, wrap the bodies in `try: import torch` and return False on ImportError. Report if the maintainer wants torch added as a hard dep (it's large).
- The `_add_noise_to_weights` signature doesn't accept an `invert` param (the `subtract_noise` alias above passes `{'invert': True}`) — read it; if it doesn't support inversion, implement `_subtract_noise` directly instead. Report.
- `self.local_model_handler` is not a transformers model but a different type — confirm via `_initialize_local_model` (line ~243) before assuming `.named_parameters()` / `.get_input_embeddings()` exist.

## Maintenance notes

- The modification half still requires `local_models.model_path` set + `framework=='transformers'` (see plan 037's rescope discussion). This plan fixes the *dispatch no-op*; the *runtime availability* is a separate config concern.
- A reviewer should confirm the backdoor method doesn't produce a genuinely harmful model — it perturbs an embedding by a small delta on a trigger token; the result is a slightly-biased local model used only for testing, not deployed. Keep the `enabled: false` default gate.
