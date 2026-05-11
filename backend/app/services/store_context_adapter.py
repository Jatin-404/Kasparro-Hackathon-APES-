"""Adapters that connect Module 1 StoreContext to downstream APES modules."""

from __future__ import annotations

import re
from typing import Any

from backend.app.models import StoreContext


def ensure_store_context(value: StoreContext | dict[str, Any]) -> StoreContext:
    """Validate crawler output into the canonical StoreContext Pydantic model."""

    if isinstance(value, StoreContext):
        return value
    return StoreContext.model_validate(value)


def extract_categories(context: StoreContext) -> list[str]:
    """Extract product categories for persona query generation."""

    categories: set[str] = set()
    for product in context.products:
        if product.product_type:
            categories.add(product.product_type)
        categories.update(product.collections)
    return sorted(categories) if categories else ["Electronics"]


def build_store_summary(context: StoreContext) -> str:
    """
    Build a focused store summary for Claude while preserving important gaps.

    Null fields are explicitly rendered as not provided/specified so the agent
    simulator cannot quietly infer missing merchant data.
    """

    lines: list[str] = []
    lines.append(f"Store: {context.store_name or 'Unknown'}")
    lines.append(f"Store URL: {context.store_url}")
    lines.append(f"Currency: {context.currency or 'not specified'}")

    policies = context.policies
    lines.append(f"\nReturn Policy: {policies.return_policy.body[:300] if policies.return_policy else 'NOT PROVIDED'}")
    lines.append(f"Shipping Policy: {policies.shipping.body[:300] if policies.shipping else 'NOT PROVIDED'}")
    lines.append(f"Refund Policy: {policies.refund.body[:300] if policies.refund else 'NOT PROVIDED'}")

    lines.append(f"\nProducts ({len(context.products)} total):")
    for product in context.products[:10]:
        lines.append(f"\n- {product.title}")
        lines.append(f"  Price: {product.price_min or 'not specified'}")
        lines.append(f"  Description: {product.description[:200] if product.description else 'NOT PROVIDED'}")
        lines.append(f"  Reviews: {product.reviews_count if product.reviews_count else 'none'}")
        lines.append(f"  Publicly visible: {'yes' if product.publicly_visible else 'no'}")
        if product.variants:
            variant_titles = [variant.title or "Untitled" for variant in product.variants[:3]]
            lines.append(f"  Variants: {', '.join(variant_titles)}")

    if context.faqs:
        lines.append(f"\nFAQs ({len(context.faqs)} entries):")
        for faq in context.faqs[:5]:
            lines.append(f"  Q: {faq.question}")
            lines.append(f"  A: {(faq.answer or 'NOT PROVIDED')[:150]}")
    else:
        lines.append("\nFAQs: NONE PROVIDED")

    if context.gaps_detected:
        lines.append("\nKnown crawler gaps:")
        for gap in context.gaps_detected[:8]:
            lines.append(f"- {gap.description}")

    return "\n".join(lines)


def check_grounding(response: str, context: StoreContext) -> dict[str, Any]:
    """
    Check if an agent response references risky claims not present in StoreContext.

    Returns a dict so the deterministic classifier and Claude verification layer
    can share the same grounding signal.
    """

    ungrounded: list[str] = []
    response_lower = response.lower()

    time_patterns = [r"\d+ days?", r"\d+-\d+ days?", r"next day", r"same day", r"overnight"]
    for pattern in time_patterns:
        if re.search(pattern, response_lower) and not context.policies.shipping:
            ungrounded.append("Agent claimed delivery time but store has no shipping policy")

    if "warrant" in response_lower:
        has_warranty = any("warrant" in (product.description or "").lower() for product in context.products)
        if not has_warranty and not context.policies.return_policy:
            ungrounded.append("Agent mentioned warranty but no warranty info in store")

    if re.search(r"\d+ day.{0,10}return", response_lower) and not context.policies.return_policy:
        ungrounded.append("Agent stated return window but store has no return policy")

    return {"is_grounded": len(ungrounded) == 0, "ungrounded_claims": ungrounded}


def build_forensics_context(query: str, context: StoreContext) -> str:
    """
    Build minimal relevant context for forensics instead of sending the full store.

    This keeps token usage low and makes the root-cause prompt focus on the
    data surface the customer query actually probes.
    """

    query_lower = query.lower()
    relevant: list[str] = []

    if any(word in query_lower for word in ["return", "refund", "exchange"]):
        relevant.append(
            "Return policy: "
            f"{context.policies.return_policy.body if context.policies.return_policy else 'NOT PROVIDED'}"
        )

    if any(word in query_lower for word in ["ship", "deliver", "arrive", "when", "christmas"]):
        relevant.append(
            "Shipping policy: "
            f"{context.policies.shipping.body if context.policies.shipping else 'NOT PROVIDED'}"
        )

    if any(word in query_lower for word in ["review", "rating", "people", "others", "trust"]):
        products_with_reviews = [product for product in context.products if product.reviews_count]
        relevant.append(f"Products with reviews: {len(products_with_reviews)} of {len(context.products)}")

    relevant_products = [
        product
        for product in context.products
        if product.title.lower() in query_lower
        or any(token and token.lower() in query_lower for token in [product.product_type, product.vendor])
    ]
    for product in relevant_products[:3]:
        relevant.append(
            f"Product: {product.title}; description: {product.description or 'NOT PROVIDED'}; "
            f"reviews: {product.reviews_count if product.reviews_count else 'none'}"
        )

    relevant.append(f"Known gaps: {[gap.description for gap in context.gaps_detected]}")
    return "\n".join(relevant) if relevant else build_store_summary(context)
