#!/usr/bin/env python3
"""Legacy module bridge: run frozen legacy attack modules inside the engine.

Each legacy module (modules/prompt_injection.py etc.) runs its full
multi-pattern campaign through a client facade over the engine target,
then folds the campaign's attacks into a single TransformResult so the
engine report, provenance, and dashboard all work unchanged.
"""

from __future__ import annotations

import importlib
from typing import Any

from modules.engine.base import Transform, TransformContext, TransformResult
from modules.engine.registry import register_transform

LEGACY_TARGETS: dict[str, str] = {
    "legacy/prompt_injection": "prompt_injection",
    "legacy/jailbreak": "jailbreak",
    "legacy/system_prompt_extraction": "system_prompt_extraction",
    "legacy/data_extraction": "data_extraction",
    "legacy/role_confusion": "role_confusion",
    "legacy/context_injection": "context_injection",
    "legacy/adversarial_inputs": "adversarial_inputs",
    "legacy/multi_turn": "multi_turn",
    "legacy/multimodal_injection": "multimodal_injection",
}

_CLASS_NAMES = {
    "prompt_injection": "PromptInjectionModule",
    "jailbreak": "JailbreakModule",
    "system_prompt_extraction": "SystemPromptExtractionModule",
    "data_extraction": "DataExtractionModule",
    "role_confusion": "RoleConfusionModule",
    "context_injection": "ContextInjectionModule",
    "adversarial_inputs": "AdversarialInputsModule",
    "multi_turn": "MultiTurnModule",
    "multimodal_injection": "MultimodalInjectionModule",
}


class _Facade:
    """Client-shaped view of an engine target for legacy modules.

    Legacy modules duck-type a subset of LLMClient: generate(), chat(),
    and a few attributes. Missing attributes resolve to None.
    """

    def __init__(self, target: Any, model: str | None = None) -> None:
        self._target = target
        self.provider = "opencode"
        self.model = model or getattr(target, "model", None)
        self.canary_token = None
        self.target_system_prompt = None

    def generate(self, prompt: str, system_prompt: Any = None, **kwargs: Any) -> str:
        return str(self._target.generate(prompt, **kwargs))

    def chat(self, messages: list, **kwargs: Any) -> str:
        if hasattr(self._target, "chat"):
            return str(self._target.chat(messages, **kwargs))
        parts = [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages]
        return str(self._target.generate("\n\n".join(parts)))

    def get_stats(self) -> dict:
        return self._target.get_stats() if hasattr(self._target, "get_stats") else {}


def _fold_campaign(tid: str, campaign: dict) -> TransformResult:
    attacks = campaign.get("attacks", []) or []
    successful = sum(1 for a in attacks if a.get("success"))
    artifacts = [
        {
            "pattern": a.get("pattern") or a.get("prompt") or "",
            "response": a.get("response", ""),
            "category": a.get("category"),
        }
        for a in attacks
    ]
    return TransformResult(
        output=campaign.get("module") or tid,
        bypassed=successful > 0,
        refusal_detected=False,
        metrics={
            "campaign": tid,
            "intensity": campaign.get("intensity"),
            "attacks": len(attacks),
            "successful": successful,
            "categories": len({a.get("category") for a in attacks}),
        },
        artifacts=[a for a in artifacts if a["pattern"] or a["response"]],
    )


def _bridge(tid: str) -> type[Transform]:
    module_name = LEGACY_TARGETS[tid]
    class_name = _CLASS_NAMES[module_name]

    class LegacyModuleBridge(Transform):
        id = tid

        def __init__(self, intensity: str = "low", **kwargs: Any) -> None:
            self.intensity = intensity

        def transform(self, ctx: TransformContext) -> TransformResult:
            live = (ctx.config or {}).get("engine", {}).get("live", False)
            if ctx.target is None or not live:
                return TransformResult(
                    output="",
                    bypassed=False,
                    error=f"{tid} requires a live target (engine.live=true)",
                )
            try:
                mod = importlib.import_module(f"modules.{module_name}")
                module_cls = getattr(mod, class_name)
            except Exception as exc:  # noqa: BLE001
                return TransformResult(output="", bypassed=False, error=f"import failed: {exc}")
            try:
                client = _Facade(ctx.target, getattr(ctx.target, "model", None))
                cfg = dict(ctx.config or {})
                cfg.setdefault("rate_limiting", {}).setdefault("delay_between_requests", 0.0)
                instance = module_cls(client, cfg, intensity=self.intensity)
                campaign = instance.run_all_attacks()
            except Exception as exc:  # noqa: BLE001
                return TransformResult(
                    output="",
                    bypassed=False,
                    error=f"{tid} campaign failed: {exc}",
                    metrics={"intensity": self.intensity},
                )
            return _fold_campaign(tid, campaign)

    return LegacyModuleBridge


for _tid in LEGACY_TARGETS:
    register_transform(_tid)(_bridge(_tid))
del _tid
