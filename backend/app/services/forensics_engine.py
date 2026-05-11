"""AI-powered forensic root-cause analysis for failed simulations."""

from __future__ import annotations

import logging
import os

from backend.app.models import FailureVerification, ForensicFinding, SimulationResult, StoreContext
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.demo_data import demo_forensic_finding
from backend.app.services.json_utils import extract_json_object
from backend.app.services.store_context_adapter import build_forensics_context

logger = logging.getLogger(__name__)


class ForensicsEngine:
    """Trace each non-confident answer to an exact merchant data gap."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        """Accept a Claude client for forensic reasoning while preserving fallback behavior."""

        self.claude = claude or ClaudeClient()

    async def analyze_many(
        self,
        store_context: StoreContext,
        simulations: list[SimulationResult],
        verifications: list[FailureVerification],
        demo_mode: bool = False,
    ) -> list[ForensicFinding]:
        """Analyze every failed simulation and skip confident-correct answers."""

        verification_by_id = {verification.query_id: verification for verification in verifications}
        findings: list[ForensicFinding] = []
        for simulation in simulations:
            verification = verification_by_id[simulation.query_id]
            if verification.classification == "CONFIDENT_CORRECT":
                continue
            findings.append(await self.analyze(store_context, simulation, verification, demo_mode=demo_mode))
        return findings

    async def analyze(
        self,
        store_context: StoreContext,
        simulation: SimulationResult,
        verification: FailureVerification,
        demo_mode: bool = False,
    ) -> ForensicFinding:
        """Identify the exact data gap behind one failed response."""

        if demo_mode:
            return demo_forensic_finding(simulation.query)
        should_use_ollama = (
            self.claude.is_ollama and os.getenv("OLLAMA_FORENSICS", "false").lower() == "true"
        )
        if not self.claude.is_configured or (self.claude.is_ollama and not should_use_ollama):
            return deterministic_forensic_finding(store_context, simulation, verification)
        focused_context = build_forensics_context(simulation.query.query, store_context)
        prompt = (
            "The AI agent failed to answer this customer query well.\n"
            f"Store Data: {focused_context}\n"
            f"Failed Query: {simulation.query.query}\n"
            f"Agent Response: {simulation.response}\n"
            f"Failure Type: {verification.classification}\n\n"
            "Identify the EXACT data gap. Be specific.\n"
            "Return JSON only: {\n"
            "  gap_type: 'missing_field|ambiguous_content|contradictory_data|no_reviews|policy_gap',\n"
            "  specific_issue: '...',\n"
            "  location: 'product:{id}|policy:{type}|faq|general',\n"
            "  severity: 'high|medium|low',\n"
            "  impact_on_conversion: '...'\n"
            " }"
        )
        try:
            text = await self.claude.complete_json("Return strict JSON only.", prompt, max_tokens=400)
            item = extract_json_object(text)
            return ForensicFinding(
                query_id=simulation.query_id,
                gap_type=item.get("gap_type", "missing_field"),
                specific_issue=str(item.get("specific_issue", "A needed store detail is missing.")),
                location=str(item.get("location", "general")),
                severity=item.get("severity", "medium"),
                impact_on_conversion=str(item.get("impact_on_conversion", "The agent cannot answer confidently.")),
            )
        except Exception as exc:
            logger.warning("Forensics fell back to deterministic root cause: %s: %r", type(exc).__name__, exc)
            return deterministic_forensic_finding(store_context, simulation, verification)


def deterministic_forensic_finding(
    store_context: StoreContext,
    simulation: SimulationResult,
    verification: FailureVerification,
) -> ForensicFinding:
    """Create a real-store root cause when the AI forensics call is unavailable."""

    query = simulation.query
    query_lower = query.query.lower()
    if any(word in query_lower for word in ["ship", "deliver", "arrive", "christmas", "expedited"]):
        return ForensicFinding(
            query_id=query.id,
            gap_type="policy_gap",
            specific_issue="Shipping timelines, cutoff dates, or expedited shipping details are not provided.",
            location="policy:shipping",
            severity="high",
            impact_on_conversion="The agent cannot answer delivery-sensitive buying questions confidently.",
        )
    if any(word in query_lower for word in ["return", "refund", "opened"]):
        return ForensicFinding(
            query_id=query.id,
            gap_type="policy_gap",
            specific_issue="Return eligibility and refund timing are not specific enough.",
            location="policy:return",
            severity="high",
            impact_on_conversion="The agent cannot reduce purchase risk for cautious shoppers.",
        )
    if "warrant" in query_lower:
        return ForensicFinding(
            query_id=query.id,
            gap_type="policy_gap",
            specific_issue="Warranty coverage is not stated in product or policy content.",
            location="policy:warranty",
            severity="high",
            impact_on_conversion="The agent cannot reassure shoppers about post-purchase support.",
        )
    if any(word in query_lower for word in ["review", "buyer", "social proof", "trust"]):
        product = find_relevant_product(store_context, query.query)
        return ForensicFinding(
            query_id=query.id,
            gap_type="no_reviews",
            specific_issue="Customer reviews or ratings are missing for the product being evaluated.",
            location=f"product:{product.id}" if product else "general",
            severity="medium",
            impact_on_conversion="The agent cannot cite trust signals for skeptical shoppers.",
        )
    if "faq" in query_lower or "accessories" in query_lower or "included" in query_lower:
        return ForensicFinding(
            query_id=query.id,
            gap_type="missing_field",
            specific_issue="FAQ coverage is missing or incomplete for this customer question.",
            location="faq",
            severity="medium",
            impact_on_conversion="The agent cannot answer common pre-purchase questions from store support content.",
        )
    product = find_relevant_product(store_context, query.query)
    return ForensicFinding(
        query_id=query.id,
        gap_type="missing_field",
        specific_issue=f"Product content is not specific enough for a {verification.classification.lower()} answer.",
        location=f"product:{product.id}" if product else "general",
        severity="medium",
        impact_on_conversion="The agent cannot convert product interest into a confident recommendation.",
    )


def find_relevant_product(store_context: StoreContext, query: str):
    """Find the product most likely referenced by a query."""

    query_lower = query.lower()
    for product in store_context.products:
        if product.title.lower() in query_lower:
            return product
    for product in store_context.products:
        tokens = [product.vendor, product.product_type, *product.title.split()[:2]]
        if any(token and token.lower() in query_lower for token in tokens):
            return product
    return store_context.products[0] if store_context.products else None
