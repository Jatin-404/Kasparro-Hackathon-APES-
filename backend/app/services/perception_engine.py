"""Generate merchant-readable AI perception summaries from audit evidence."""

from __future__ import annotations

import logging
import os
from collections import Counter

from backend.app.models import (
    CurrentPerception,
    FailureVerification,
    ForensicFinding,
    SimulationResult,
    StoreContext,
)
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.json_utils import extract_json_object

logger = logging.getLogger(__name__)

PERCEPTION_SYSTEM_PROMPT = """You analyze how AI shopping agents perceive Shopify stores.
Use only the supplied simulation evidence. Be specific, honest, and merchant-readable.
Return strict JSON only."""


class PerceptionEngine:
    """Summarize how agents currently understand and trust the store."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        self.claude = claude or ClaudeClient()

    async def generate(
        self,
        store_context: StoreContext,
        simulations: list[SimulationResult],
        verifications: list[FailureVerification],
        findings: list[ForensicFinding],
        demo_mode: bool = False,
    ) -> CurrentPerception:
        """Create current AI perception summary with graceful deterministic fallback."""

        if demo_mode:
            return deterministic_perception(store_context, simulations, verifications, findings)

        should_use_ai = self.claude.is_configured and (
            not self.claude.is_ollama or os.getenv("OLLAMA_GENERATE_PERCEPTION", "true").lower() == "true"
        )
        if should_use_ai:
            try:
                text = await self.claude.complete_json(
                    PERCEPTION_SYSTEM_PROMPT,
                    build_perception_prompt(store_context, simulations, verifications, findings),
                    max_tokens=600,
                )
                return normalize_perception(extract_json_object(text))
            except Exception as exc:
                logger.warning("Perception generation fell back to deterministic summary: %s", exc)
        return deterministic_perception(store_context, simulations, verifications, findings)


def build_perception_prompt(
    store_context: StoreContext,
    simulations: list[SimulationResult],
    verifications: list[FailureVerification],
    findings: list[ForensicFinding],
) -> str:
    """Build the prompt described in the Desired Brand Representation feature."""

    counts = Counter(item.classification for item in verifications)
    product_types = sorted(
        {str(product.product_type or product.vendor or "product") for product in store_context.products if product}
    )
    top_failures = "\n".join(
        f"- {finding.specific_issue} ({finding.location}, {finding.severity})"
        for finding in sorted(findings, key=lambda item: severity_rank(item.severity), reverse=True)[:5]
    )
    gaps = "\n".join(
        f"- {gap.location}: {gap.message}" for gap in store_context.gaps_detected[:8]
    ) or "- No structured gaps were detected."
    return f"""Store Name: {store_context.store_name or store_context.store_url}
Store Category: {", ".join(product_types[:8]) or "unknown"}
Simulation Summary:

Total queries: {len(simulations)}
Failed queries: {sum(1 for item in verifications if item.classification != "CONFIDENT_CORRECT")}
HALLUCINATED: {counts.get("HALLUCINATED", 0)}
VAGUE: {counts.get("VAGUE", 0)}
REFUSED: {counts.get("REFUSED", 0)}
CONFIDENT_CORRECT: {counts.get("CONFIDENT_CORRECT", 0)}

Key failures:
{top_failures or "- No failed query root causes were found."}

Known data gaps:
{gaps}

Write a 2-3 sentence summary of how AI shopping agents currently perceive this store.
Be specific and honest. Write from the perspective of an AI agent that just tried to
answer customer questions about this store and struggled.

Return JSON only:
{{
  "perception_summary": "string",
  "perceived_as": "string",
  "confidence_level": "very low|low|medium|high",
  "confidence_reason": "string",
  "biggest_perception_problems": ["string", "string", "string"]
}}"""


def deterministic_perception(
    store_context: StoreContext,
    simulations: list[SimulationResult],
    verifications: list[FailureVerification],
    findings: list[ForensicFinding],
) -> CurrentPerception:
    """Local fallback summary that does not depend on an LLM."""

    counts = Counter(item.classification for item in verifications)
    failed = sum(1 for item in verifications if item.classification != "CONFIDENT_CORRECT")
    total = max(1, len(verifications))
    confidence_level = confidence_for_failure_rate(failed / total)
    category = category_label(store_context)
    top_problems = [finding.specific_issue for finding in findings[:3]]
    while len(top_problems) < 3:
        top_problems.append("Store data is not detailed enough for confident AI recommendations.")
    summary = (
        f"AI shopping agents perceive this as {article_for(category)} {category}, but with {confidence_level} "
        f"confidence because {failed} of {total} tested shopper questions did not receive confident grounded answers. "
        f"The biggest blockers are {top_problems[0].lower()}, {top_problems[1].lower()}, and "
        f"{top_problems[2].lower()}."
    )
    reason = (
        f"{counts.get('REFUSED', 0)} refused, {counts.get('VAGUE', 0)} vague, and "
        f"{counts.get('HALLUCINATED', 0)} hallucinated responses indicate incomplete or ambiguous store data."
    )
    return CurrentPerception(
        perception_summary=summary,
        perceived_as=category,
        confidence_level=confidence_level,
        confidence_reason=reason,
        biggest_perception_problems=top_problems[:3],
    )


def normalize_perception(value: dict) -> CurrentPerception:
    """Coerce model JSON into the exact response schema."""

    problems = value.get("biggest_perception_problems") or []
    if not isinstance(problems, list):
        problems = [str(problems)]
    confidence = str(value.get("confidence_level", "low")).strip().lower()
    if confidence not in {"very low", "low", "medium", "high"}:
        confidence = "low"
    return CurrentPerception(
        perception_summary=str(value.get("perception_summary", "")).strip()
        or "AI agents cannot form a confident perception from the current store data.",
        perceived_as=str(value.get("perceived_as", "store with incomplete AI-readable data")).strip(),
        confidence_level=confidence,  # type: ignore[arg-type]
        confidence_reason=str(value.get("confidence_reason", "Key store evidence is incomplete.")).strip(),
        biggest_perception_problems=[str(item).strip() for item in problems if str(item).strip()][:3]
        or ["Missing or ambiguous store data blocks confident answers."],
    )


def category_label(store_context: StoreContext) -> str:
    product_types = [product.product_type for product in store_context.products if product.product_type]
    if product_types:
        common = Counter(product_types).most_common(2)
        label = " and ".join(item[0].lower() for item in common)
        return f"{label} store with incomplete AI-readable data"
    vendors = [product.vendor for product in store_context.products if product.vendor]
    if vendors:
        return "multi-brand store with incomplete AI-readable data"
    return "store with incomplete AI-readable data"


def confidence_for_failure_rate(rate: float) -> str:
    if rate >= 0.65:
        return "very low"
    if rate >= 0.4:
        return "low"
    if rate >= 0.2:
        return "medium"
    return "high"


def severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(severity, 0)


def article_for(text: str) -> str:
    return "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
