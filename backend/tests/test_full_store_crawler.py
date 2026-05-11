"""Tests for the exact-schema Module 1 crawler."""

from __future__ import annotations

import pytest

from backend.app.services.full_store_crawler import (
    FullStoreCrawler,
    build_demo_store_context,
    detect_structural_gaps,
    parse_faq_pairs,
)


def test_demo_crawl_context_matches_hackathon_expectations() -> None:
    """Verify the fast demo context has 25 products and intentional gaps."""

    context = build_demo_store_context()
    assert len(context["products"]) == 25
    assert context["policies"]["return"] is None
    assert context["policies"]["shipping"] is None
    assert context["policies"]["refund"] is None
    assert context["faqs"] == []
    assert len(context["gaps_detected"]) >= 5


def test_parse_faq_pairs_supports_q_and_a_pattern() -> None:
    """Verify common FAQ text becomes structured pairs."""

    pairs = parse_faq_pairs("Q: Do you ship? A: Yes, within the United States. Q: Are chargers included? A: Only when listed.")
    assert pairs == [
        ("Do you ship?", "Yes, within the United States."),
        ("Are chargers included?", "Only when listed."),
    ]


def test_structural_gap_detection_preserves_missing_fields() -> None:
    """Verify deterministic gap scan reports missing policies, FAQs, descriptions, and reviews."""

    context = {
        "policies": {"return": None, "shipping": None, "refund": None, "privacy": None},
        "products": [
            {
                "description": None,
                "reviews_count": None,
                "publicly_visible": True,
            }
        ],
        "faqs": [],
        "crawl_coverage": {"storefront": True},
    }
    gap_types = [gap["type"] for gap in detect_structural_gaps(context)]
    assert gap_types.count("missing_policy") == 3
    assert "no_product_descriptions" in gap_types
    assert "no_reviews" in gap_types
    assert "missing_faq" in gap_types


@pytest.mark.asyncio
async def test_safe_fetch_partial_failure_returns_none() -> None:
    """Verify one failed section becomes None instead of crashing the crawl."""

    crawler = FullStoreCrawler("hackathon-store.myshopify.com", "token")

    async def failing_section() -> None:
        raise RuntimeError("boom")

    result = await crawler.safe_fetch(failing_section, "pages")
    assert result is None
    assert crawler.steps == [{"section": "pages", "status": "failed", "reason": "boom"}]
