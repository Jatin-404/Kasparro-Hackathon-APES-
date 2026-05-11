"""Deterministic failure detector with optional Claude verification."""

from __future__ import annotations

import logging
import os

from backend.app.models import Classification, FailureVerification, SimulationResult, StoreContext
from backend.app.services.agent_simulator import HEDGING_TERMS, REFUSAL_TERMS, contains_any
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.demo_data import demo_expected_classification
from backend.app.services.json_utils import extract_json_object
from backend.app.services.store_context_adapter import build_store_summary, check_grounding

logger = logging.getLogger(__name__)


class FailureDetector:
    """Classify agent answers using rules first and Claude verification second."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        """Accept a Claude client for the verification layer."""

        self.claude = claude or ClaudeClient()

    async def classify_many(
        self,
        store_context: StoreContext,
        simulations: list[SimulationResult],
        demo_mode: bool = False,
    ) -> list[FailureVerification]:
        """Classify every simulation result without exposing raw model internals."""

        return [await self.classify(store_context, simulation, demo_mode=demo_mode) for simulation in simulations]

    async def classify(
        self,
        store_context: StoreContext,
        simulation: SimulationResult,
        demo_mode: bool = False,
    ) -> FailureVerification:
        """Classify one response and verify it when Claude is available."""

        grounding = check_grounding(simulation.response, store_context)
        rule_classification = pre_classify_response(simulation.response, store_context, grounding)
        if demo_mode:
            expected = demo_expected_classification(simulation.query_id, fixed_context=simulation.fixed_context)
            return FailureVerification(
                query_id=simulation.query_id,
                classification=expected,  # type: ignore[arg-type]
                confidence=0.97,
                reason="Demo verification pins the response to the seeded store gaps.",
                rule_classification=rule_classification,
                grounding=grounding,
            )
        should_verify = self.claude.is_configured and (
            not self.claude.is_ollama or os.getenv("OLLAMA_VERIFY_FAILURES", "false").lower() == "true"
        )
        if should_verify:
            prompt = (
                "Given this store data and agent response, verify the classification.\n"
                "Did the agent answer accurately based ONLY on store data provided?\n"
                "Return JSON only: { classification, confidence, reason }\n\n"
                f"Store Data: {build_store_summary(store_context)}\n"
                f"Agent Response: {simulation.response}\n"
                f"Rule Classification: {rule_classification}\n"
                f"Grounding Check: {grounding}"
            )
            try:
                text = await self.claude.complete_json("Return strict JSON only.", prompt, max_tokens=300)
                verified = extract_json_object(text)
                return FailureVerification(
                    query_id=simulation.query_id,
                    classification=normalize_classification(verified.get("classification"), rule_classification),
                    confidence=normalize_confidence(verified.get("confidence", 0.75)),
                    reason=str(verified.get("reason", "Verified by Claude.")),
                    rule_classification=rule_classification,
                    grounding=grounding,
                )
            except Exception as exc:
                logger.warning("Failure verification fell back to rules: %s: %r", type(exc).__name__, exc)
        return FailureVerification(
            query_id=simulation.query_id,
            classification=rule_classification,
            confidence=0.72,
            reason="Claude unavailable; rule-based classifier was used.",
            rule_classification=rule_classification,
            grounding=grounding,
        )


def pre_classify_response(response: str, store_context: StoreContext, grounding: dict | None = None) -> Classification:
    """Apply deterministic labels before any AI verification is attempted."""

    if contains_any(response, REFUSAL_TERMS):
        return "REFUSED"
    if contains_any(response, HEDGING_TERMS):
        return "VAGUE"
    if grounding is not None and not grounding.get("is_grounded", True):
        return "HALLUCINATED"
    if looks_hallucinated(response, store_context):
        return "HALLUCINATED"
    return "CONFIDENT_CORRECT"


def normalize_classification(value: object, fallback: Classification) -> Classification:
    """Coerce model classification text into the allowed enum."""

    text = str(value or "").strip().upper()
    if text in {"REFUSED", "VAGUE", "HALLUCINATED", "CONFIDENT_CORRECT"}:
        return text  # type: ignore[return-value]
    return fallback


def normalize_confidence(value: object) -> float:
    """Accept numeric or label confidence values from local models."""

    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    text = str(value or "").strip().lower()
    labels = {"high": 0.85, "medium": 0.65, "low": 0.4}
    if text in labels:
        return labels[text]
    try:
        parsed = float(text)
        if parsed > 1:
            parsed = parsed / 100
        return max(0.0, min(parsed, 1.0))
    except ValueError:
        return 0.75


def looks_hallucinated(response: str, store_context: StoreContext) -> bool:
    """Flag confident answers that cite unsupported high-risk commerce claims."""

    lowered = response.lower()
    unsupported_claims = ["expedited", "guaranteed", "same-day", "confirmed", "exact", "christmas"]
    context_text = store_context.model_dump_json(by_alias=True, exclude_none=False).lower()
    return any(claim in lowered and claim not in context_text for claim in unsupported_claims)
