from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from modules.engine.base import Transform, TransformContext, TransformResult


@dataclass(frozen=True)
class ProbePrompt:
    text: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProbeResponse:
    text: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProbeTurn:
    prompt: ProbePrompt
    response: ProbeResponse


@dataclass(frozen=True)
class Conversation:
    turns: tuple[ProbeTurn, ...] = ()

    def with_turn(self, t: ProbeTurn) -> Conversation:
        return Conversation(self.turns + (t,))

    def last(self) -> ProbeTurn | None:
        return self.turns[-1] if self.turns else None


@dataclass(frozen=True)
class ProbeResult:
    conversation: Conversation
    succeeded: bool
    reason: str
    final_score: float | None = None


class Target(ABC):
    @abstractmethod
    def respond(self, prompt: ProbePrompt) -> ProbeResponse: ...


class Attacker(ABC):
    @abstractmethod
    def rewrite(self, history: Conversation) -> ProbePrompt: ...


class StopJudge(ABC):
    @abstractmethod
    def should_stop(self, history: Conversation) -> tuple[bool, str]: ...


class ProbeLoop(Transform):
    def __init__(
        self,
        attacker: Attacker,
        target: Target,
        judge: StopJudge,
        max_turns: int = 10,
    ) -> None:
        self._attacker = attacker
        self._target = target
        self._judge = judge
        self._max_turns = max_turns

    @property
    def id(self) -> str:
        return "adaptive/probe_loop"

    def transform(self, ctx: TransformContext) -> TransformResult:
        result = self._run(ctx.input)
        return TransformResult(
            output=result.conversation.turns[-1].response.text if result.conversation.turns else "",
            bypassed=result.succeeded,
            metrics={
                "turns": len(result.conversation.turns),
                "reason": result.reason,
                "final_score": result.final_score,
            },
        )

    def _run(self, seed_text: str) -> ProbeResult:
        history = Conversation()
        prompt = ProbePrompt(seed_text)

        for _ in range(self._max_turns):
            response = self._target.respond(prompt)
            history = history.with_turn(ProbeTurn(prompt, response))
            stop, reason = self._judge.should_stop(history)
            if stop:
                return ProbeResult(history, succeeded="objective" in reason.lower(), reason=reason)
            prompt = self._attacker.rewrite(history)

        return ProbeResult(history, succeeded=False, reason="turn_budget_exhausted")
