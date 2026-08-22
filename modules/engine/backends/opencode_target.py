#!/usr/bin/env python3
"""Live target adapter: opencode headless CLI (opencode run).

Wraps the opencode binary as an engine target implementing the
transform contract (generate / respond). Each call spawns
`opencode run --format json` in a fixed workdir, so the model runs
with the user's real opencode configuration, model, and agent
context. Authorized use only: the caller must own the opencode
installation being exercised.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

_UNSET = object()


class OpencodeTarget:
    """Target backed by `opencode run`; model is user-configured (default)."""

    def __init__(
        self,
        workdir: str | None = None,
        model: str | None = None,
        agent: str | None = None,
        timeout: float = 180.0,
        opencode_bin: str = "opencode",
    ) -> None:
        self.workdir = workdir
        self.model = model
        self.agent = agent
        self.timeout = timeout
        self.opencode_bin = opencode_bin
        self._calls = 0

    def __repr__(self) -> str:
        return f"OpencodeTarget(model={self.model or 'default'}, workdir={self.workdir})"

    def _run(self, prompt: str) -> str:
        cmd = [
            self.opencode_bin,
            "run",
            "--format",
            "json",
            prompt,
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if self.agent:
            cmd.extend(["--agent", self.agent])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.workdir,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return f"[ERROR] opencode timed out after {self.timeout:g}s"
        except FileNotFoundError:
            return "[ERROR] opencode binary not found"
        self._calls += 1
        return self._extract(proc.stdout)

    @staticmethod
    def _extract(stdout: str) -> str:
        """Join text parts from the opencode run JSON event stream."""
        parts = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "text":
                text = event.get("part", {}).get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    def generate(
        self,
        prompt: str,
        system_prompt: Any = _UNSET,
        **kwargs: Any,
    ) -> str:
        """Transform contract: one model response for a prompt.

        system_prompt and kwargs are accepted for interface
        compatibility; opencode controls its own agent context, so
        they are advisory only.
        """
        del kwargs
        return self._run(prompt)

    def respond(self, prompt: Any) -> str:
        """Probe-loop contract (ProbePrompt wrappers tolerated)."""
        return self.generate(str(prompt))

    def chat(self, messages: list, **kwargs: Any) -> str:
        """Legacy chat contract: a list of {role, content} turns.

        opencode is stateless per call, so the transcript is rendered
        into a single prompt. kwargs are accepted for interface
        compatibility and ignored.
        """
        del kwargs
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[System instructions]\n{content}")
            elif role == "assistant":
                parts.append(f"[Assistant]\n{content}")
            else:
                parts.append(f"[User]\n{content}")
        rendered = "\n\n".join(parts) + "\n\n[Assistant]"
        return self.generate(rendered)

    def get_stats(self) -> dict:
        return {"calls": self._calls, "target": repr(self)}
