"""Tests for Shopify crawler normalization and partial recovery behavior."""

from __future__ import annotations

from backend.app.models import StoreGap
from backend.app.services.store_crawler import StoreCrawler, extract_faqs_from_text


def test_extract_faqs_from_page_text() -> None:
    """Verify FAQ-like page text becomes structured question and answer pairs."""

    faqs = extract_faqs_from_text(
        "Do you ship internationally? We ship within the United States. "
        "Are chargers included? Only when listed on the product page."
    )
    assert len(faqs) == 2
    assert faqs[0].question == "Do you ship internationally?"
    assert faqs[0].answer == "We ship within the United States."
    assert faqs[1].question == "Are chargers included?"


def test_partial_admin_segments_still_build_context() -> None:
    """Ensure products and gaps survive when pages or policies are partial."""

    crawler = StoreCrawler(access_token="test-token")
    gaps = [StoreGap(location="general", field="shopify_pages", message="Pages failed.")]
    context = crawler._normalize_admin_segments(
        "hackathon-store.myshopify.com",
        {
            "shop": {"shop": {"name": "Hackathon Store", "primaryDomain": {"url": "https://hackathon-store.myshopify.com"}}},
            "products": {
                "products": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Product/1",
                                "title": "Demo Headphones",
                                "descriptionHtml": "<p>Noise cancelling headphones.</p>",
                                "tags": ["audio"],
                                "images": {"edges": []},
                                "variants": {
                                    "edges": [
                                        {
                                            "node": {
                                                "id": "gid://shopify/ProductVariant/1",
                                                "title": "Black",
                                                "price": "99.00",
                                                "availableForSale": True,
                                                "selectedOptions": [{"name": "Color", "value": "Black"}],
                                            }
                                        }
                                    ]
                                },
                                "metafields": {"edges": []},
                            }
                        }
                    ]
                }
            },
            "policies": {"shopPolicies": []},
            "pages": {},
        },
        gaps,
    )
    assert context.store_name == "Hackathon Store"
    assert context.products[0].title == "Demo Headphones"
    assert context.products[0].variants[0].price == "99.00"
    assert any(gap.field == "shopify_pages" for gap in context.gaps)
