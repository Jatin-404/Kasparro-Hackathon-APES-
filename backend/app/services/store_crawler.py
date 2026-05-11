"""Deterministic Shopify crawler that normalizes data into StoreContext JSON."""

from __future__ import annotations

import logging
import os
import re
import asyncio
from html import unescape
from typing import Any

import httpx

from backend.app.models import (
    Collection,
    FAQ,
    Policies,
    Product,
    ProductImage,
    ProductVariant,
    StoreContext,
    StoreGap,
    StorePage,
)
from backend.app.services.demo_data import build_demo_store_context

logger = logging.getLogger(__name__)


SHOP_QUERY = """
query ApesShop {
  shop {
    name
    myshopifyDomain
    primaryDomain { url }
  }
}
"""

PRODUCTS_QUERY = """
query ApesProducts {
  products(first: 25) {
    edges {
      node {
        id
        title
        descriptionHtml
        tags
        images(first: 10) {
          edges { node { url altText } }
        }
        variants(first: 20) {
          edges {
            node {
              id
              title
              sku
              inventoryQuantity
              availableForSale
              price
              selectedOptions { name value }
            }
          }
        }
        metafields(first: 20) {
          edges { node { namespace key value type } }
        }
        collections(first: 10) {
          edges { node { id title } }
        }
      }
    }
  }
}
"""

POLICIES_QUERY = """
query ApesPolicies {
  shopPolicies {
    title
    body
    type
  }
}
"""

PAGES_QUERY = """
query ApesPages {
  pages(first: 50) {
    edges {
      node {
        id
        title
        handle
        body
      }
    }
  }
}
"""

SHOPIFY_STOREFRONT_QUERY = """
query ApesPublicContext {
  products(first: 25) {
    edges {
      node {
        id
        title
        description
        tags
        images(first: 10) {
          edges { node { url altText } }
        }
        variants(first: 20) {
          edges {
            node {
              id
              title
              availableForSale
              price { amount currencyCode }
              selectedOptions { name value }
            }
          }
        }
      }
    }
  }
}
"""


class StoreCrawler:
    """Fetch Shopify data deterministically and preserve gaps as structured facts."""

    def __init__(
        self,
        access_token: str | None = None,
        storefront_token: str | None = None,
        api_version: str = "2024-01",
    ) -> None:
        """Store Shopify credentials and API version for repeatable crawl behavior."""

        self.access_token = access_token or os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        self.storefront_token = storefront_token or os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN")
        self.api_version = api_version

    async def fetch_store_context(self, store_url: str, demo_mode: bool = False) -> StoreContext:
        """Return normalized store data, using demo data when requested or unconfigured."""

        normalized_url = normalize_shop_domain(store_url)
        if demo_mode or not self.access_token:
            return build_demo_store_context(normalized_url)
        endpoint = f"https://{normalized_url}/admin/api/{self.api_version}/graphql.json"
        gaps: list[StoreGap] = []
        data = await self._fetch_admin_segments(endpoint, gaps)
        context = self._normalize_admin_segments(normalized_url, data, gaps)
        return await self._merge_storefront_overlay(normalized_url, context)

    async def _fetch_admin_segments(self, endpoint: str, gaps: list[StoreGap]) -> dict[str, Any]:
        """Fetch Shopify resources separately so one failed section does not kill the crawl."""

        segments = {
            "shop": SHOP_QUERY,
            "products": PRODUCTS_QUERY,
            "policies": POLICIES_QUERY,
            "pages": PAGES_QUERY,
        }
        data: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=20.0) as client:
            for name, query in segments.items():
                try:
                    data[name] = await self._post_graphql(client, endpoint, query, token_header="X-Shopify-Access-Token", token=self.access_token or "")
                except Exception as exc:
                    logger.warning("Shopify %s segment failed gracefully: %s", name, exc)
                    gaps.append(
                        StoreGap(
                            location="general",
                            field=f"shopify_{name}",
                            message=f"Shopify {name} data could not be crawled; APES continued with partial context.",
                            severity="high" if name == "products" else "medium",
                        )
                    )
        return data

    async def _post_graphql(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        query: str,
        token_header: str,
        token: str,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Post a GraphQL query with rate-limit retry handling and sanitized errors."""

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = await client.post(
                    endpoint,
                    json={"query": query},
                    headers={
                        token_header: token,
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code == 429:
                    await asyncio.sleep(retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                payload = response.json()
                errors = payload.get("errors") or []
                if has_throttle_error(errors):
                    await asyncio.sleep(retry_delay(response, attempt))
                    continue
                if errors:
                    raise RuntimeError(first_graphql_error(errors))
                return payload.get("data") or {}
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
        raise RuntimeError("GraphQL request failed") from last_error

    def _normalize_admin_segments(
        self,
        store_url: str,
        segments: dict[str, Any],
        gaps: list[StoreGap],
    ) -> StoreContext:
        """Normalize partial Admin API segment data into one StoreContext."""

        shop = segments.get("shop", {}).get("shop") or {}
        products = self._normalize_products(segments.get("products", {}).get("products", {}), gaps)
        policies = self._normalize_policies(segments.get("policies", {}).get("shopPolicies") or [], gaps)
        pages = self._normalize_pages(segments.get("pages", {}).get("pages", {}), gaps)
        collections = self._derive_collections(products)
        faqs = self._extract_faqs(pages, gaps)
        return StoreContext(
            store_name=shop.get("name") or store_url,
            store_url=(shop.get("primaryDomain") or {}).get("url") or f"https://{store_url}",
            products=products,
            policies=policies,
            faqs=faqs,
            pages=pages,
            collections=collections,
            gaps=gaps,
        )

    async def _legacy_fetch_store_context(self, normalized_url: str) -> StoreContext:
        """Retain the original monolithic crawler path for emergency debugging."""

        endpoint = f"https://{normalized_url}/admin/api/{self.api_version}/graphql.json"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    endpoint,
                    json={"query": PRODUCTS_QUERY},
                    headers={
                        "X-Shopify-Access-Token": self.access_token,
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("Shopify crawl failed gracefully: %s", exc)
            context = build_demo_store_context(normalized_url)
            context.gaps.append(
                StoreGap(
                    location="general",
                    field="shopify_api",
                    message="Live Shopify crawl failed; demo context was used for a recoverable audit.",
                    severity="medium",
                )
            )
            return context
        context = self._normalize_shopify_payload(normalized_url, payload)
        return await self._merge_storefront_overlay(normalized_url, context)

    async def _merge_storefront_overlay(self, store_url: str, context: StoreContext) -> StoreContext:
        """Overlay public Storefront API data because agents see customer-facing product facts."""

        if not self.storefront_token:
            context.gaps.append(
                StoreGap(
                    location="general",
                    field="storefront_api",
                    message="Storefront API token is not configured, so public-facing overlay was skipped.",
                    severity="low",
                )
            )
            return context
        endpoint = f"https://{store_url}/api/{self.api_version}/graphql.json"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                payload_data = await self._post_graphql(
                    client,
                    endpoint,
                    SHOPIFY_STOREFRONT_QUERY,
                    token_header="X-Shopify-Storefront-Access-Token",
                    token=self.storefront_token,
                )
        except Exception as exc:
            logger.warning("Storefront overlay failed gracefully: %s", exc)
            context.gaps.append(
                StoreGap(
                    location="general",
                    field="storefront_api",
                    message="Storefront API overlay failed; Admin-normalized context was retained.",
                    severity="low",
                )
            )
            return context
        storefront_products = payload_data.get("products", {}).get("edges", [])
        products_by_title = {product.title.lower(): product for product in context.products}
        for edge in storefront_products:
            node = edge.get("node") or {}
            product = products_by_title.get(str(node.get("title") or "").lower())
            if product is None:
                continue
            if node.get("description"):
                product.description = node.get("description")
            if node.get("tags"):
                product.tags = list(dict.fromkeys([*product.tags, *node.get("tags", [])]))
            storefront_images = [
                ProductImage(url=(image_edge.get("node") or {}).get("url"), alt_text=(image_edge.get("node") or {}).get("altText"))
                for image_edge in (node.get("images") or {}).get("edges", [])
            ]
            if storefront_images:
                product.images = storefront_images
        return context

    def _normalize_shopify_payload(self, store_url: str, payload: dict[str, Any]) -> StoreContext:
        """Convert Shopify GraphQL data into StoreContext while logging missing fields."""

        data = payload.get("data") or {}
        shop = data.get("shop") or {}
        gaps: list[StoreGap] = []
        products = self._normalize_products(data.get("products", {}), gaps)
        policies = self._normalize_policies(data.get("shopPolicies") or [], gaps)
        collections = self._derive_collections(products)
        pages: list[StorePage] = []
        return StoreContext(
            store_name=shop.get("name") or store_url,
            store_url=(shop.get("primaryDomain") or {}).get("url") or f"https://{store_url}",
            products=products,
            policies=policies,
            faqs=self._extract_faqs(pages, gaps),
            pages=pages,
            collections=collections,
            gaps=gaps,
        )

    def _normalize_products(self, products_payload: dict[str, Any], gaps: list[StoreGap]) -> list[Product]:
        """Normalize Shopify product edges and record missing descriptions, media, and metadata."""

        products: list[Product] = []
        for edge in products_payload.get("edges", []):
            node = edge.get("node") or {}
            product_id = node.get("id") or "unknown-product"
            description = html_to_text(node.get("descriptionHtml"))
            if not description:
                gaps.append(StoreGap(location=f"product:{product_id}", field="description", message="Product description is missing.", severity="high"))
            images = [
                ProductImage(url=(image_edge.get("node") or {}).get("url"), alt_text=(image_edge.get("node") or {}).get("altText"))
                for image_edge in (node.get("images") or {}).get("edges", [])
            ]
            if not images:
                gaps.append(StoreGap(location=f"product:{product_id}", field="images", message="Product has no images.", severity="medium"))
            variants = [self._normalize_variant(variant_edge.get("node") or {}) for variant_edge in (node.get("variants") or {}).get("edges", [])]
            if not variants:
                gaps.append(StoreGap(location=f"product:{product_id}", field="variants", message="Product has no variants.", severity="high"))
            metafields = {
                f"{metafield.get('namespace')}.{metafield.get('key')}": metafield.get("value")
                for metafield_edge in (node.get("metafields") or {}).get("edges", [])
                for metafield in [metafield_edge.get("node") or {}]
            }
            products.append(
                Product(
                    id=product_id,
                    title=node.get("title") or "Untitled product",
                    description=description,
                    variants=variants,
                    images=images,
                    metafields=metafields,
                    reviews=[],
                    tags=node.get("tags") or [],
                )
            )
            gaps.append(
                StoreGap(
                    location=f"product:{product_id}",
                    field="reviews",
                    message="No native review source was detected for this product.",
                    severity="medium",
                )
            )
        if not products:
            gaps.append(StoreGap(location="general", field="products", message="No products were returned by Shopify.", severity="high"))
        return products

    def _normalize_variant(self, node: dict[str, Any]) -> ProductVariant:
        """Normalize a Shopify variant without failing on absent inventory or option fields."""

        options = {option.get("name", ""): option.get("value") for option in node.get("selectedOptions", [])}
        return ProductVariant(
            id=node.get("id") or "unknown-variant",
            title=node.get("title"),
            price=str(node.get("price")) if node.get("price") is not None else None,
            sku=node.get("sku"),
            inventory_quantity=node.get("inventoryQuantity"),
            available_for_sale=node.get("availableForSale"),
            options=options,
        )

    def _normalize_policies(self, policies_payload: list[dict[str, Any]], gaps: list[StoreGap]) -> Policies:
        """Map Shopify policy records onto APES policy slots and record absent ones."""

        values: dict[str, str | None] = {"return": None, "shipping": None, "refund": None, "warranty": None}
        for policy in policies_payload:
            title = str(policy.get("title") or policy.get("type") or "").lower()
            body = html_to_text(policy.get("body"))
            if "shipping" in title:
                values["shipping"] = body
            elif "refund" in title:
                values["refund"] = body
            elif "return" in title:
                values["return"] = body
            elif "warranty" in title:
                values["warranty"] = body
        for key, value in values.items():
            if not value:
                gaps.append(StoreGap(location=f"policy:{key}", field=key, message=f"{key.title()} policy is missing or empty.", severity="high" if key in {"shipping", "refund"} else "medium"))
        return Policies(**values)

    def _normalize_pages(self, pages_payload: dict[str, Any], gaps: list[StoreGap]) -> list[StorePage]:
        """Normalize Shopify Online Store pages for FAQ and policy-like context."""

        pages: list[StorePage] = []
        for edge in pages_payload.get("edges", []):
            node = edge.get("node") or {}
            page_id = node.get("id") or f"page:{node.get('handle') or len(pages) + 1}"
            body = html_to_text(node.get("body"))
            pages.append(
                StorePage(
                    id=page_id,
                    title=node.get("title") or "Untitled page",
                    handle=node.get("handle"),
                    body=body,
                    source="admin",
                )
            )
            if not body:
                gaps.append(
                    StoreGap(
                        location=f"page:{page_id}",
                        field="body",
                        message="Online Store page exists but has no readable body content.",
                        severity="medium",
                    )
                )
        if not pages:
            gaps.append(
                StoreGap(
                    location="page",
                    field="pages",
                    message="No Online Store pages were returned by Shopify.",
                    severity="medium",
                )
            )
        return pages

    def _derive_collections(self, products: list[Product]) -> list[Collection]:
        """Build lightweight collections from tags when Shopify collection data is absent."""

        grouped: dict[str, list[str]] = {}
        for product in products:
            for tag in product.tags:
                grouped.setdefault(tag.title(), []).append(product.id)
        return [Collection(name=name, products=ids) for name, ids in grouped.items()]

    def _extract_faqs(self, pages: list[StorePage], gaps: list[StoreGap]) -> list[FAQ]:
        """Extract FAQ entries from FAQ-like Shopify pages using deterministic patterns."""

        faqs: list[FAQ] = []
        for page in pages:
            page_text = f"{page.title} {page.handle or ''}".lower()
            if "faq" not in page_text and "frequently" not in page_text and "question" not in page_text:
                continue
            faqs.extend(extract_faqs_from_text(page.body or ""))
        if not faqs:
            gaps.append(StoreGap(location="faq", field="source", message="No FAQ entries were detected in Online Store pages.", severity="medium"))
        return faqs


def normalize_shop_domain(store_url: str) -> str:
    """Normalize user input to a Shopify host for deterministic endpoint construction."""

    value = store_url.strip().replace("https://", "").replace("http://", "").strip("/")
    if "/" in value:
        value = value.split("/")[0]
    if "." not in value:
        value = f"{value}.myshopify.com"
    return value


def html_to_text(value: str | None) -> str | None:
    """Convert Shopify HTML snippets into readable text for AI-safe StoreContext."""

    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text or None


def retry_delay(response: httpx.Response, attempt: int) -> float:
    """Calculate a small retry delay from Shopify headers or exponential fallback."""

    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.5)
        except ValueError:
            return 1.0
    return 0.75 * (attempt + 1)


def has_throttle_error(errors: list[Any]) -> bool:
    """Detect Shopify GraphQL throttling errors from a response payload."""

    return any("THROTTLED" in str(error).upper() or "THROTTLE" in str(error).upper() for error in errors)


def first_graphql_error(errors: list[Any]) -> str:
    """Return a sanitized summary of the first GraphQL error."""

    first = errors[0] if errors else {}
    if isinstance(first, dict):
        return str(first.get("message") or "Shopify GraphQL error")
    return "Shopify GraphQL error"


def extract_faqs_from_text(text: str) -> list[FAQ]:
    """Parse common FAQ page text patterns into question and answer entries."""

    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text).strip()
    question_matches = list(re.finditer(r"([^?.!]{8,120}\?)", normalized))
    faqs: list[FAQ] = []
    for index, match in enumerate(question_matches):
        question = match.group(1).strip()
        answer_start = match.end()
        answer_end = question_matches[index + 1].start() if index + 1 < len(question_matches) else len(normalized)
        answer = normalized[answer_start:answer_end].strip(" :-")
        faqs.append(FAQ(question=question, answer=answer or None))
    return faqs
