"""AI-powered content repair generator for APES findings."""

from __future__ import annotations

import logging
import os

from backend.app.models import FixProposal, ForensicFinding, PersonaQuery, StoreContext
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.json_utils import extract_json_object

logger = logging.getLogger(__name__)


class FixGenerator:
    """Rewrite weak store content so AI shopping agents can answer confidently."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        """Accept a Claude client for fix generation and demos without hard dependency."""

        self.claude = claude or ClaudeClient()

    async def generate_many(
        self,
        store_context: StoreContext,
        findings: list[ForensicFinding],
        queries: list[PersonaQuery],
        demo_mode: bool = False,
    ) -> list[FixProposal]:
        """Generate one fix per forensic finding with stable impact estimates."""

        query_by_id = {query.id: query for query in queries}
        return [
            await self.generate(store_context, finding, query_by_id[finding.query_id], demo_mode=demo_mode)
            for finding in findings
        ]

    async def generate(
        self,
        store_context: StoreContext,
        finding: ForensicFinding,
        query: PersonaQuery,
        demo_mode: bool = False,
    ) -> FixProposal:
        """Generate a concrete content rewrite for one gap with fallback copy."""

        original = original_content_for_location(store_context, finding.location)
        content_type = content_type_for_location(finding.location)
        should_use_ollama = (
            self.claude.is_ollama and os.getenv("OLLAMA_GENERATE_FIXES", "false").lower() == "true"
        )
        if demo_mode or not self.claude.is_configured or (self.claude.is_ollama and not should_use_ollama):
            return fallback_fix(finding, query, original, content_type)
        prompt = (
            f"Rewrite this {content_type} to be clear, specific, and complete\n"
            " so an AI shopping agent can answer customer questions about it\n"
            " confidently.\n"
            f" Original: {original}\n"
            f" Gap identified: {finding.specific_issue}\n"
            f" Persona asking: {query.persona}\n\n"
            " Return JSON only: { improved_content, changes_made[],\n"
            "                confidence_improvement_reason }"
        )
        try:
            text = await self.claude.complete_json("Return strict JSON only.", prompt, max_tokens=450)
            item = extract_json_object(text)
            return FixProposal(
                query_id=finding.query_id,
                content_type=content_type,
                original_content=original,
                improved_content=str(item.get("improved_content", "")),
                changes_made=[str(change) for change in item.get("changes_made", [])],
                confidence_improvement_reason=str(item.get("confidence_improvement_reason", "")),
                impact_points=impact_points_for(finding.severity),
            )
        except Exception as exc:
            logger.warning("Fix generation fell back to deterministic copy: %s: %r", type(exc).__name__, exc)
            return fallback_fix(finding, query, original, content_type)


def original_content_for_location(store_context: StoreContext, location: str) -> str | None:
    """Find the original content that should be rewritten for a gap location."""

    if location == "policy:shipping":
        return store_context.policies.shipping.body if store_context.policies.shipping else None
    if location == "policy:refund":
        return store_context.policies.refund.body if store_context.policies.refund else None
    if location == "policy:warranty":
        return store_context.policies.warranty.body if store_context.policies.warranty else None
    if location == "policy:return":
        return store_context.policies.return_policy.body if store_context.policies.return_policy else None
    if location == "faq":
        return "\n".join(f"{faq.question} {faq.answer or ''}".strip() for faq in store_context.faqs)
    if location.startswith("product:"):
        product_id = location.replace("product:", "")
        product = next((item for item in store_context.products if item.id == product_id), None)
        return product.description if product else None
    return None


def content_type_for_location(location: str) -> str:
    """Map a forensic location to the content type Claude should rewrite."""

    if location.startswith("policy:"):
        return location.replace("policy:", "") + " policy"
    if location == "faq":
        return "FAQ answer"
    if location.startswith("product:"):
        return "product description"
    return "store content"


def impact_points_for(severity: str) -> int:
    """Estimate score impact for dashboard badges from finding severity."""

    return {"high": 11, "medium": 6, "low": 3}.get(severity, 5)


def fallback_fix(finding: ForensicFinding, query: PersonaQuery, original: str | None, content_type: str) -> FixProposal:
    """Return deterministic repair copy that keeps the demo usable without Claude."""

    improved_by_query = {
        "q06": (
            "Standard U.S. orders placed by December 18 ship within 1 business day and are expected "
            "to arrive before Christmas for continental U.S. addresses. Orders placed after December "
            "18 may arrive after December 25. Expedited shipping is not currently offered."
        ),
        "q07": "Refunds are issued to the original payment method within 5 business days after a returned item is inspected and approved.",
        "q08": "Electronics include a 1-year limited warranty covering manufacturing defects. Damage from accidents or misuse is not covered.",
        "q10": "Standard shipping is available only. Expedited shipping is not currently offered.",
        "q12": "Add review prompts for ChargeStack buyers and show verified ratings once collected.",
        "q14": "Add verified PixelBeam buyer reviews and a short quality summary before promoting it as a trust-backed gift.",
        "q16": "Chargers are included only when listed in the product description. NovaSound includes USB-C charging; product pages should confirm each accessory.",
    }
    improved = improved_by_query.get(finding.query_id)
    if improved is None and content_type == "shipping policy":
        improved = (
            "Standard U.S. orders ship within 1 business day and usually arrive in 3-5 business days. "
            "Orders placed by December 18 are expected to arrive before Christmas for continental U.S. "
            "addresses. Expedited shipping is available at checkout when supported by the destination."
        )
    elif improved is None and content_type == "return policy":
        improved = (
            "Eligible electronics can be returned within 30 days of delivery if all original accessories "
            "and packaging are included. Refunds are issued to the original payment method within 5 "
            "business days after inspection."
        )
    elif improved is None and content_type == "warranty policy":
        improved = (
            "Electronics include a 1-year limited warranty covering manufacturing defects under normal use. "
            "Accidental damage, misuse, and unauthorized repairs are not covered."
        )
    elif improved is None and content_type == "FAQ answer":
        improved = (
            "Holiday delivery, return conditions, included accessories, and product compatibility are listed "
            "in each product page or policy. Contact support if a product page does not state the detail."
        )
    elif improved is None:
        improved = f"{original or 'Product details'}\n\nClarification: {finding.specific_issue}"
    return FixProposal(
        query_id=finding.query_id,
        content_type=content_type,
        original_content=original,
        improved_content=improved,
        changes_made=[
            "Added concrete answerable details.",
            "Removed ambiguous wording.",
            "Aligned content with the exact customer intent.",
        ],
        confidence_improvement_reason=(
            f"{query.persona} can now receive a grounded answer because the missing evidence is explicit."
        ),
        impact_points=impact_points_for(finding.severity),
    )
