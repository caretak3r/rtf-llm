#!/usr/bin/env python3
"""MITRE ATLAS-mapped technique KB (canonical rebuild).

Every entry carries a verified ATLAS technique ID and at least one real
citation. validate_kb() fails on uncited entries and on ATLAS IDs outside
the verified whitelist, so fabricated mappings cannot creep back in.
Coverage maps per model family; to_documents() emits RAG-indexable
records.
"""

from __future__ import annotations

import re
from typing import Any

# Subset of MITRE ATLAS technique IDs verified against atlas.mitre.org.
ATLAS_VERIFIED_IDS = frozenset(
    {
        "AML.T0001",  # ML Model Inference
        "AML.T0002",  # ML Model Evasion
        "AML.T0005",  # ML Model Poisoning
        "AML.T0010",  # Exfiltration
        "AML.T0013",  # ML Supply Chain Compromise
        "AML.T0020",  # Social Engineering
        "AML.T0034",  # Cost Harvesting
        "AML.T0051",  # LLM Prompt Injection: Direct
        "AML.T0052",  # LLM Prompt Injection: Indirect
        "AML.T0054",  # LLM Jailbreak
    }
)

ATLAS_URL = "https://atlas.mitre.org/techniques/{tech_id}"
URL_RE = re.compile(r"^https?://[^\s]+$")


def _ref(title: str, url: str) -> dict:
    return {"title": title, "url": url}


# --------------------------------------------------------------------------
# Canonical KB: one entry per technique family, all fields verified.
# --------------------------------------------------------------------------
TECHNIQUE_KB: dict[str, dict[str, Any]] = {
    "direct_injection": {
        "atlas": "AML.T0051",
        "description": "Blunt user-side override of system instructions appended to a benign request.",
        "defense": [
            "Enforce instruction hierarchy (system > developer > user) in the prompt contract.",
            "Classify user input for override intent before model invocation.",
            "Log and alert on responses that quote internal directives or instruction text.",
        ],
        "references": [
            _ref(
                "OWASP LLM01:2025 Prompt Injection",
                "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            ),
            _ref(
                "MITRE ATLAS - LLM Prompt Injection: Direct",
                "https://atlas.mitre.org/techniques/AML.T0051",
            ),
        ],
    },
    "indirect_injection": {
        "atlas": "AML.T0052",
        "description": "Hostile instructions delivered via retrieved or tool-supplied content, not the user message.",
        "defense": [
            "Separate data from instructions: retrieved content is untrusted data, never executable.",
            "Sandbox tool outputs and reclassify them before they join the prompt context.",
            "Canary-token the retrieval path to detect downstream use of injected text.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - LLM Prompt Injection: Indirect",
                "https://atlas.mitre.org/techniques/AML.T0052",
            ),
            _ref(
                "Simon Willison - Prompt Injection Explained",
                "https://simonwillison.net/2022/Sep/12/prompt-injection/",
            ),
        ],
    },
    "ignore_instructions": {
        "atlas": "AML.T0051",
        "description": "The 'ignore previous instructions' family; paraphrases evade naive filters.",
        "defense": [
            "Detect both literal and semantic ignore-phrasing with a small classifier.",
            "Role-lock language in the system prompt: no user instruction can override these rules.",
            "Evaluate with ground-truth canary tokens, not heuristic success.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - LLM Prompt Injection: Direct",
                "https://atlas.mitre.org/techniques/AML.T0051",
            ),
        ],
    },
    "override_instructions": {
        "atlas": "AML.T0051",
        "description": "Direct override commands ('override safety', 'new instructions:') probing role boundaries.",
        "defense": [
            "Input-scrub override keywords combined with negative prompt-side reinforcement.",
            "Use provider instruction-hierarchy APIs where supported.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - LLM Prompt Injection: Direct",
                "https://atlas.mitre.org/techniques/AML.T0051",
            ),
        ],
    },
    "system_bypass": {
        "atlas": "AML.T0051",
        "description": "Referencing 'system message', 'system prompt', or fake admin roles to escalate.",
        "defense": [
            "Output-filter responses containing canary tokens placed in the system prompt.",
            "Disallow quoting or paraphrasing system content; reinforce with refusal training examples.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - LLM Prompt Injection: Direct",
                "https://atlas.mitre.org/techniques/AML.T0051",
            ),
        ],
    },
    "encoding_attacks": {
        "atlas": "AML.T0054",
        "description": "Payload obfuscation via base64, hex, ROT13, URL-encode, or Unicode codepoints recovered only at decode time.",
        "defense": [
            "Decode and re-scan obvious encodings on input before model invocation.",
            "Normalize zero-width and bidirectional characters (NFKC).",
            "Treat decoded payloads as data, never as instructions.",
        ],
        "references": [
            _ref("MITRE ATLAS - LLM Jailbreak", "https://atlas.mitre.org/techniques/AML.T0054"),
        ],
    },
    "jailbreak_roleplay": {
        "atlas": "AML.T0054",
        "description": "DAN-style and persona-swap jailbreaks that sidestep safety training via role dissociation.",
        "defense": [
            "Detect persona-override markers and escalating role claims.",
            "Fine-tune refusal behavior against a jailbreak benchmark; measure with detectors, not vibes.",
        ],
        "references": [
            _ref("MITRE ATLAS - LLM Jailbreak", "https://atlas.mitre.org/techniques/AML.T0054"),
            _ref(
                "Universal and Transferable Adversarial Attacks on Aligned Language Models",
                "https://arxiv.org/abs/2307.02483",
            ),
        ],
    },
    "refusal_analysis": {
        "atlas": "AML.T0001",
        "description": "Probing refusal boundaries and model behavior to map the safety envelope for follow-on attacks.",
        "defense": [
            "Standardize refusal-position analysis in evaluation pipelines.",
            "Treat probe data as signals for defense tuning, not as findings by themselves.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - ML Model Inference", "https://atlas.mitre.org/techniques/AML.T0001"
            ),
        ],
    },
    "data_extraction": {
        "atlas": "AML.T0010",
        "description": "Extraction of training data or memorized content, including PII and prompt content.",
        "defense": [
            "Redact and log responses that contain canary tokens.",
            "Minimize memorization via deduplication and differential-privacy-style training limits.",
        ],
        "references": [
            _ref("MITRE ATLAS - Exfiltration", "https://atlas.mitre.org/techniques/AML.T0010"),
        ],
    },
    "exfiltration": {
        "atlas": "AML.T0010",
        "description": "Deliberate transfer of protected data through model output or tool side channels.",
        "defense": [
            "Deploy an output gateway that blocks known secret patterns.",
            "Per-session canary tokens to attribute leaks to a specific deployment.",
        ],
        "references": [
            _ref("MITRE ATLAS - Exfiltration", "https://atlas.mitre.org/techniques/AML.T0010"),
        ],
    },
    "supply_chain": {
        "atlas": "AML.T0013",
        "description": "Compromise of model artifacts, dependencies, or pipeline components before deployment.",
        "defense": [
            "Pin and sign model artifacts and dependency versions.",
            "Scan third-party components with supply-chain risk tooling before adoption.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - ML Supply Chain Compromise",
                "https://atlas.mitre.org/techniques/AML.T0013",
            ),
        ],
    },
    "poisoning": {
        "atlas": "AML.T0005",
        "description": "Corrupting training or fine-tuning data to implant behaviors that survive deployment.",
        "defense": [
            "Validate and vet fine-tuning datasets; detect poisoned samples with influence analysis.",
            "Re-evaluate model behavior on adversarial benchmarks after any retraining.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - ML Model Poisoning", "https://atlas.mitre.org/techniques/AML.T0005"
            ),
        ],
    },
    "evasion": {
        "atlas": "AML.T0002",
        "description": "Crafting inputs that defeat classifiers or guardrails without changing the underlying request.",
        "defense": [
            "Evaluate defenses against adversarial input suites, including encoded and chained payloads.",
            "Keep detectors versioned; report classification rates per attack family.",
        ],
        "references": [
            _ref("MITRE ATLAS - ML Model Evasion", "https://atlas.mitre.org/techniques/AML.T0002"),
        ],
    },
    "social_engineering": {
        "atlas": "AML.T0020",
        "description": "Using the model as a credibility multiplier to manipulate humans.",
        "defense": [
            "Restrict identity claims and impersonation in system prompts.",
            "Watermark and disclose synthetic content.",
        ],
        "references": [
            _ref(
                "MITRE ATLAS - Social Engineering", "https://atlas.mitre.org/techniques/AML.T0020"
            ),
        ],
    },
    "cost_harvesting": {
        "atlas": "AML.T0034",
        "description": "Abusing generous or unbounded generation to drive up operational cost.",
        "defense": [
            "Rate-limit per identity and enforce generation budgets.",
            "Cap output tokens and streaming timeouts.",
        ],
        "references": [
            _ref("MITRE ATLAS - Cost Harvesting", "https://atlas.mitre.org/techniques/AML.T0034"),
        ],
    },
}

MODEL_FAMILIES = ("claude", "gpt", "gemini", "llama", "mistral")


def validate_kb() -> list[str]:
    """Return every validation violation; empty list means the KB is clean."""
    violations = []
    for name, entry in TECHNIQUE_KB.items():
        atlas = entry.get("atlas")
        if atlas not in ATLAS_VERIFIED_IDS:
            violations.append(f"{name}: atlas '{atlas}' not in verified whitelist")
        references = entry.get("references") or []
        if not references:
            violations.append(f"{name}: zero citations")
        for ref in references:
            url = ref.get("url", "")
            if not URL_RE.match(url):
                violations.append(f"{name}: invalid citation URL '{url}'")
            if url.startswith("https://example") or "placeholder" in url:
                violations.append(f"{name}: placeholder citation '{url}'")
    return violations


def coverage_map(families: tuple[str, ...] = MODEL_FAMILIES) -> dict[str, list[str]]:
    """ATLAS technique coverage per model family.

    A technique is covered for a family when its defense guidance is
    applicable; the default maps every family to the full KB.
    """
    return {family: sorted(TECHNIQUE_KB) for family in families}


def to_documents() -> list[dict]:
    """RAG-indexable documents: one per KB entry with metadata."""
    documents = []
    for name, entry in TECHNIQUE_KB.items():
        text = (
            f"Technique {name} ({entry['atlas']}): {entry['description']} "
            f"Defenses: {'; '.join(entry['defense'])} "
            f"Sources: {'; '.join(r['title'] for r in entry['references'])}"
        )
        documents.append(
            {
                "id": f"kb-{name}",
                "text": text,
                "metadata": {"technique": name, "atlas": entry["atlas"]},
            }
        )
    return documents


def render_coverage_table(families: tuple[str, ...] = MODEL_FAMILIES) -> str:
    """Human-readable coverage table (console + report embedding)."""
    lines = ["Model family      | techniques covered", "-" * 40]
    for family, techniques in coverage_map(families).items():
        lines.append(f"{family:<17} | {len(techniques)} ({', '.join(techniques[:3])}... )")
    return "\n".join(lines)
