"""Full deterministic Shopify crawler for Module 1.

This module returns the exact StoreContext JSON shape used by APES crawler
evaluation. It does not call AI. Missing data is preserved as null and also
summarized in deterministic structural gaps.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from html import unescape
from typing import Any, Awaitable, Callable

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.app.models import StoreContext

logger = logging.getLogger(__name__)

API_VERSION = "2024-01"
MAX_PRODUCTS = 100

PRODUCTS_QUERY = """
query GetProducts($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        description
        descriptionHtml
        vendor
        productType
        tags
        status
        createdAt
        updatedAt
        images(first: 5) {
          edges {
            node {
              src: url
              altText
            }
          }
        }
        variants(first: 10) {
          edges {
            node {
              id
              title
              price
              compareAtPrice
              sku
              availableForSale
              inventoryQuantity
              selectedOptions {
                name
                value
              }
            }
          }
        }
        metafields(first: 20) {
          edges {
            node {
              namespace
              key
              value
              type
            }
          }
        }
        collections(first: 5) {
          edges {
            node {
              title
            }
          }
        }
      }
    }
  }
}
"""

COLLECTIONS_QUERY = """
query GetCollections {
  collections(first: 20) {
    edges {
      node {
        id
        title
        description
        productsCount {
          count
        }
      }
    }
  }
}
"""

PAGES_QUERY = """
query GetPages {
  pages(first: 20) {
    edges {
      node {
        id
        title
        body
        bodySummary
        handle
      }
    }
  }
}
"""

MENUS_QUERY = """
query GetMenus {
  menus(first: 5) {
    edges {
      node {
        title
        handle
        items {
          title
          url
          type
        }
      }
    }
  }
}
"""

STOREFRONT_PRODUCTS_QUERY = """
query StorefrontProducts {
  products(first: 20) {
    edges {
      node {
        id
        title
        description
        availableForSale
        priceRange {
          minVariantPrice {
            amount
            currencyCode
          }
        }
        variants(first: 5) {
          edges {
            node {
              title
              availableForSale
              price {
                amount
              }
            }
          }
        }
      }
    }
  }
}
"""


class RetryableShopifyError(RuntimeError):
    """Raised for Shopify responses that should be retried."""


class FullStoreCrawler:
    """Fetch products, policies, pages, navigation, and storefront data deterministically."""

    def __init__(
        self,
        shop_url: str,
        access_token: str,
        storefront_token: str | None = None,
        api_version: str = API_VERSION,
    ) -> None:
        """Store normalized endpoints and tokens for one crawl."""

        self.shop = normalize_shop_domain(shop_url)
        self.access_token = access_token
        self.storefront_token = storefront_token
        self.api_version = api_version
        self.admin_graphql_url = f"https://{self.shop}/admin/api/{api_version}/graphql.json"
        self.admin_rest_url = f"https://{self.shop}/admin/api/{api_version}"
        self.storefront_url = f"https://{self.shop}/api/{api_version}/graphql.json"
        self.steps: list[dict[str, Any]] = []

    async def crawl(self) -> StoreContext:
        """Run independent crawl sections and assemble the exact StoreContext JSON."""

        async with httpx.AsyncClient(timeout=25.0) as client:
            shop_info = await self.safe_fetch(lambda: self.fetch_shop_info(client), "shop")
            products = await self.safe_fetch(lambda: self.fetch_products(client), "products")
            collections = await self.safe_fetch(lambda: self.fetch_collections(client), "collections")
            pages = await self.safe_fetch(lambda: self.fetch_pages(client), "pages")
            policies = await self.safe_fetch(lambda: self.fetch_policies(client), "policies")
            navigation = await self.safe_fetch(lambda: self.fetch_navigation(client), "navigation")
            storefront = await self.safe_fetch(lambda: self.fetch_storefront_products(client), "storefront")

        normalized_products = normalize_products(products or [])
        storefront_inconsistencies = compare_storefront_visibility(normalized_products, storefront or [])
        faqs = extract_faqs_from_pages(pages or [])
        context = {
            "store_name": (shop_info or {}).get("name"),
            "store_url": self.shop,
            "currency": (shop_info or {}).get("currency"),
            "crawled_at": datetime.now(UTC).isoformat(),
            "crawl_coverage": {
                "products": products is not None,
                "policies": policies is not None,
                "pages": pages is not None,
                "collections": collections is not None,
                "navigation": navigation is not None,
                "storefront": storefront is not None,
            },
            "products": normalized_products,
            "collections": normalize_collections(collections or []),
            "policies": normalize_policies(policies or []),
            "faqs": faqs,
            "navigation": normalize_navigation(navigation or []),
            "gaps_detected": [],
        }
        context["gaps_detected"] = detect_structural_gaps(context, storefront_inconsistencies)
        return StoreContext.model_validate(context)

    async def safe_fetch(self, fetch_fn: Callable[[], Awaitable[Any]], section_name: str) -> Any | None:
        """Run one section independently so partial crawl failures become coverage gaps."""

        try:
            value = await fetch_fn()
            self.steps.append({"section": section_name, "status": "ok"})
            return value
        except Exception as exc:
            logger.warning("Partial crawl failure: %s - %s", section_name, exc)
            self.steps.append({"section": section_name, "status": "failed", "reason": str(exc)})
            return None

    async def fetch_shop_info(self, client: httpx.AsyncClient) -> dict[str, Any]:
        """Fetch shop name, email, domain, locale, currency, and timezone through REST."""

        payload = await self.execute_rest(client, f"{self.admin_rest_url}/shop.json")
        shop = payload.get("shop") or {}
        return {
            "name": shop.get("name"),
            "email": shop.get("email"),
            "domain": shop.get("domain") or shop.get("myshopify_domain"),
            "primary_locale": shop.get("primary_locale"),
            "currency": shop.get("currency"),
            "timezone": shop.get("iana_timezone") or shop.get("timezone"),
        }

    async def fetch_products(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch up to 100 products from Admin GraphQL using cursor pagination."""

        products: list[dict[str, Any]] = []
        cursor: str | None = None
        while len(products) < MAX_PRODUCTS:
            payload = await self.execute_graphql(client, PRODUCTS_QUERY, {"cursor": cursor})
            connection = payload.get("products") or {}
            for edge in connection.get("edges", []):
                products.append(edge.get("node") or {})
                if len(products) >= MAX_PRODUCTS:
                    break
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        return products

    async def fetch_collections(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch collection metadata from Admin GraphQL."""

        payload = await self.execute_graphql(client, COLLECTIONS_QUERY)
        return [edge.get("node") or {} for edge in (payload.get("collections") or {}).get("edges", [])]

    async def fetch_pages(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch Online Store pages where FAQ content often lives."""

        payload = await self.execute_graphql(client, PAGES_QUERY)
        return [edge.get("node") or {} for edge in (payload.get("pages") or {}).get("edges", [])]

    async def fetch_policies(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch policies through REST because Shopify policies are not reliable in GraphQL."""

        payload = await self.execute_rest(client, f"{self.admin_rest_url}/policies.json")
        return payload.get("policies") or []

    async def fetch_navigation(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch Online Store menus to understand category and navigation structure."""

        payload = await self.execute_graphql(client, MENUS_QUERY)
        return [edge.get("node") or {} for edge in (payload.get("menus") or {}).get("edges", [])]

    async def fetch_storefront_products(self, client: httpx.AsyncClient) -> list[dict[str, Any]] | None:
        """Fetch public Storefront API products for visibility and content mismatch checks."""

        if not self.storefront_token:
            return None
        payload = await self.execute_storefront_graphql(client, STOREFRONT_PRODUCTS_QUERY)
        return [edge.get("node") or {} for edge in (payload.get("products") or {}).get("edges", [])]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RetryableShopifyError),
        reraise=True,
    )
    async def execute_graphql(
        self,
        client: httpx.AsyncClient,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Admin GraphQL with retries and cost-based throttle sleeping."""

        return await self._execute_graphql(
            client,
            self.admin_graphql_url,
            query,
            variables,
            "X-Shopify-Access-Token",
            self.access_token,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RetryableShopifyError),
        reraise=True,
    )
    async def execute_storefront_graphql(
        self,
        client: httpx.AsyncClient,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Storefront GraphQL with the same retry path as Admin GraphQL."""

        return await self._execute_graphql(
            client,
            self.storefront_url,
            query,
            variables,
            "X-Shopify-Storefront-Access-Token",
            self.storefront_token or "",
        )

    async def _execute_graphql(
        self,
        client: httpx.AsyncClient,
        url: str,
        query: str,
        variables: dict[str, Any] | None,
        token_header: str,
        token: str,
    ) -> dict[str, Any]:
        """Execute a GraphQL call and handle 429, 5xx, and Shopify cost throttling."""

        response = await client.post(
            url,
            json={"query": query, "variables": variables or {}},
            headers={token_header: token, "Content-Type": "application/json"},
        )
        if response.status_code == 429:
            await asyncio.sleep(2.0)
            raise RetryableShopifyError("Shopify rate limited the GraphQL request")
        if response.status_code >= 500:
            raise RetryableShopifyError(f"Shopify GraphQL returned {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors") or []
        if has_throttle_error(errors):
            await asyncio.sleep(2.0)
            raise RetryableShopifyError("Shopify GraphQL throttle error")
        if errors:
            raise RuntimeError(first_graphql_error(errors))
        await maybe_sleep_for_graphql_cost(payload)
        return payload.get("data") or {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RetryableShopifyError),
        reraise=True,
    )
    async def execute_rest(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        """Execute REST calls for shop and policies with retryable 429/5xx handling."""

        response = await client.get(url, headers={"X-Shopify-Access-Token": self.access_token})
        if response.status_code == 429:
            await asyncio.sleep(2.0)
            raise RetryableShopifyError("Shopify rate limited the REST request")
        if response.status_code >= 500:
            raise RetryableShopifyError(f"Shopify REST returned {response.status_code}")
        response.raise_for_status()
        await maybe_sleep_for_rest_limit(response)
        return response.json()


def normalize_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize raw Admin GraphQL products to the exact StoreContext product schema."""

    normalized: list[dict[str, Any]] = []
    for product in products:
        variants = [normalize_variant(edge.get("node") or {}) for edge in (product.get("variants") or {}).get("edges", [])]
        prices = [variant["price"] for variant in variants if variant.get("price") is not None]
        compare_at_prices = [
            str((edge.get("node") or {}).get("compareAtPrice"))
            for edge in (product.get("variants") or {}).get("edges", [])
            if (edge.get("node") or {}).get("compareAtPrice") is not None
        ]
        description = product.get("description") or html_to_text(product.get("descriptionHtml"))
        normalized.append(
            {
                "id": product.get("id"),
                "title": product.get("title") or "",
                "description": description or None,
                "vendor": product.get("vendor"),
                "product_type": product.get("productType"),
                "tags": product.get("tags") or [],
                "status": str(product.get("status") or "").lower() or None,
                "price_min": min(prices, key=decimal_string_key) if prices else None,
                "price_max": max(prices, key=decimal_string_key) if prices else None,
                "compare_at_price": compare_at_prices[0] if compare_at_prices else None,
                "images": [
                    {
                        "src": (edge.get("node") or {}).get("src"),
                        "alt": (edge.get("node") or {}).get("altText"),
                    }
                    for edge in (product.get("images") or {}).get("edges", [])
                ],
                "variants": variants,
                "metafields": [
                    {
                        "namespace": (edge.get("node") or {}).get("namespace"),
                        "key": (edge.get("node") or {}).get("key"),
                        "value": (edge.get("node") or {}).get("value"),
                        "type": (edge.get("node") or {}).get("type"),
                    }
                    for edge in (product.get("metafields") or {}).get("edges", [])
                ],
                "collections": [
                    (edge.get("node") or {}).get("title")
                    for edge in (product.get("collections") or {}).get("edges", [])
                    if (edge.get("node") or {}).get("title")
                ],
                "reviews_count": None,
                "average_rating": None,
                "publicly_visible": False,
            }
        )
    return normalized


def normalize_variant(variant: dict[str, Any]) -> dict[str, Any]:
    """Normalize a variant while preserving null SKU, weight, and inventory fields."""

    return {
        "title": variant.get("title"),
        "price": str(variant.get("price")) if variant.get("price") is not None else None,
        "sku": variant.get("sku"),
        "weight": variant.get("weight"),
        "available": variant.get("availableForSale"),
        "inventory_quantity": variant.get("inventoryQuantity"),
        "options": [
            {"name": option.get("name"), "value": option.get("value")}
            for option in variant.get("selectedOptions", [])
        ],
    }


def normalize_collections(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize collection metadata for category-level diagnostics."""

    return [
        {
            "id": collection.get("id"),
            "title": collection.get("title"),
            "description": collection.get("description") or None,
            "products_count": ((collection.get("productsCount") or {}).get("count")) or 0,
        }
        for collection in collections
    ]


def normalize_policies(policies: list[dict[str, Any]]) -> dict[str, Any]:
    """Map REST policy records to return, shipping, refund, and privacy slots."""

    mapped: dict[str, Any] = {"return": None, "shipping": None, "refund": None, "privacy": None}
    for policy in policies:
        title = str(policy.get("title") or "").lower()
        policy_value = {
            "title": policy.get("title"),
            "body": html_to_text(policy.get("body")) or "",
            "url": policy.get("url"),
        }
        if "shipping" in title:
            mapped["shipping"] = policy_value
        elif "refund" in title:
            mapped["refund"] = policy_value
        elif "return" in title:
            mapped["return"] = policy_value
        elif "privacy" in title:
            mapped["privacy"] = policy_value
    return mapped


def normalize_navigation(menus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Shopify menus to a compact navigation schema."""

    return [
        {
            "menu_title": menu.get("title"),
            "items": [
                {"title": item.get("title"), "url": item.get("url"), "type": item.get("type")}
                for item in menu.get("items", [])
            ],
        }
        for menu in menus
    ]


def extract_faqs_from_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract Q&A pairs from FAQ-like page bodies."""

    faqs: list[dict[str, Any]] = []
    for page in pages:
        title = str(page.get("title") or "")
        handle = str(page.get("handle") or "")
        if not is_faq_page(title, handle):
            continue
        body = html_to_text(page.get("body")) or html_to_text(page.get("bodySummary")) or ""
        for question, answer in parse_faq_pairs(body):
            faqs.append({"question": question, "answer": answer, "source_page": title or handle})
    return faqs


def is_faq_page(title: str, handle: str) -> bool:
    """Return true when page metadata looks like FAQ/help content."""

    text = f"{title} {handle}".lower()
    return any(token in text for token in ["faq", "questions", "help"])


def parse_faq_pairs(text: str) -> list[tuple[str, str | None]]:
    """Parse common FAQ patterns: Q:/A:, numbered questions, and plain question marks."""

    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text).strip()
    qa_matches = list(re.finditer(r"(?:Q:|Question:)\s*(.*?\?)\s*(?:A:|Answer:)\s*(.*?)(?=(?:Q:|Question:)\s*.*?\?|$)", normalized, re.IGNORECASE))
    if qa_matches:
        return [(match.group(1).strip(), match.group(2).strip() or None) for match in qa_matches]
    question_matches = list(re.finditer(r"(?:\d+\.\s*)?([^?.!]{8,160}\?)", normalized))
    pairs: list[tuple[str, str | None]] = []
    for index, match in enumerate(question_matches):
        answer_start = match.end()
        answer_end = question_matches[index + 1].start() if index + 1 < len(question_matches) else len(normalized)
        answer = normalized[answer_start:answer_end].strip(" :-")
        pairs.append((match.group(1).strip(), answer or None))
    return pairs


def compare_storefront_visibility(products: list[dict[str, Any]], storefront_products: list[dict[str, Any]]) -> int:
    """Mark Admin products as publicly visible and flag Storefront description mismatches."""

    storefront_by_title = {str(product.get("title") or "").lower(): product for product in storefront_products}
    inconsistencies = 0
    for product in products:
        storefront = storefront_by_title.get(str(product.get("title") or "").lower())
        product["publicly_visible"] = storefront is not None
        if storefront and (storefront.get("description") or "") != (product.get("description") or ""):
            inconsistencies += 1
    return inconsistencies


def detect_structural_gaps(context: dict[str, Any], storefront_inconsistencies: int = 0) -> list[dict[str, Any]]:
    """Pre-compute crawler-level structural gaps before any AI analysis runs."""

    gaps: list[dict[str, Any]] = []
    for policy_type in ["return", "shipping", "refund"]:
        if context["policies"].get(policy_type) is None:
            gaps.append(
                {
                    "type": "missing_policy",
                    "description": f"No {policy_type} policy found",
                    "affected_count": 1,
                }
            )
    no_desc = [
        product
        for product in context["products"]
        if not product.get("description") or len(product.get("description") or "") < 50
    ]
    if no_desc:
        gaps.append(
            {
                "type": "no_product_descriptions",
                "description": f"{len(no_desc)} products have missing or very short descriptions",
                "affected_count": len(no_desc),
            }
        )
    no_reviews = [
        product
        for product in context["products"]
        if product.get("reviews_count") is None or product.get("reviews_count") == 0
    ]
    if no_reviews:
        gaps.append(
            {
                "type": "no_reviews",
                "description": f"{len(no_reviews)} products have no customer reviews",
                "affected_count": len(no_reviews),
            }
        )
    if len(context["faqs"]) == 0:
        gaps.append(
            {
                "type": "missing_faq",
                "description": "Store has no FAQ page or FAQ content",
                "affected_count": 1,
            }
        )
    not_public = [product for product in context["products"] if product.get("publicly_visible") is False]
    if context["crawl_coverage"].get("storefront") and not_public:
        gaps.append(
            {
                "type": "missing_specs",
                "description": f"{len(not_public)} admin products are not visible in Storefront API results",
                "affected_count": len(not_public),
            }
        )
    if context["crawl_coverage"].get("storefront") and storefront_inconsistencies:
        gaps.append(
            {
                "type": "missing_specs",
                "description": f"{storefront_inconsistencies} products have different Admin and Storefront descriptions",
                "affected_count": storefront_inconsistencies,
            }
        )
    return gaps


def build_demo_store_context() -> StoreContext:
    """Return a fast demo StoreContext with 25 electronics products and known gaps."""

    products = []
    for index in range(25):
        product_number = index + 1
        products.append(
            {
                "id": f"gid://shopify/Product/demo-{product_number}",
                "title": f"Demo Electronics Product {product_number}",
                "description": None if product_number % 4 == 0 else "Compact electronics accessory with basic store data for APES demo diagnostics.",
                "vendor": "APES Demo",
                "product_type": "Electronics",
                "tags": ["electronics", "demo"],
                "status": "active",
                "price_min": "49.00",
                "price_max": "99.00",
                "compare_at_price": None,
                "images": [{"src": None, "alt": None}] if product_number % 5 == 0 else [],
                "variants": [
                    {
                        "title": "Default",
                        "price": "49.00",
                        "sku": None if product_number % 3 == 0 else f"DEMO-{product_number}",
                        "weight": None,
                        "available": True,
                        "inventory_quantity": None,
                        "options": [{"name": "Title", "value": "Default"}],
                    }
                ],
                "metafields": [],
                "collections": ["Demo Electronics"],
                "reviews_count": None,
                "average_rating": None,
                "publicly_visible": product_number <= 20,
            }
        )
    context = {
        "store_name": "APES Hackathon Electronics",
        "store_url": "hackathon-store.myshopify.com",
        "currency": "USD",
        "crawled_at": datetime.now(UTC).isoformat(),
        "crawl_coverage": {
            "products": True,
            "policies": True,
            "pages": True,
            "collections": True,
            "navigation": True,
            "storefront": True,
        },
        "products": products,
        "collections": [{"id": "demo-collection", "title": "Demo Electronics", "description": None, "products_count": 25}],
        "policies": {"return": None, "shipping": None, "refund": None, "privacy": None},
        "faqs": [],
        "navigation": [{"menu_title": "Main menu", "handle": "main-menu", "items": [{"title": "Catalog", "url": "/collections/all", "type": "COLLECTION"}]}],
        "gaps_detected": [],
    }
    context["gaps_detected"] = detect_structural_gaps(context)
    return StoreContext.model_validate(context)


def normalize_shop_domain(shop_url: str) -> str:
    """Normalize pasted Shopify input into a myshopify host."""

    value = shop_url.strip().replace("https://", "").replace("http://", "").strip("/")
    if "/" in value:
        value = value.split("/")[0]
    if "." not in value:
        value = f"{value}.myshopify.com"
    return value


def html_to_text(value: str | None) -> str | None:
    """Strip HTML to plain text while preserving null as a valid gap."""

    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text or None


def decimal_string_key(value: str) -> float:
    """Convert price-like strings to floats for min/max sorting."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


async def maybe_sleep_for_graphql_cost(payload: dict[str, Any]) -> None:
    """Sleep when Shopify GraphQL cost bucket gets low."""

    cost = (payload.get("extensions") or {}).get("cost") or {}
    throttle = cost.get("throttleStatus") or {}
    if throttle.get("currentlyAvailable", 1000) < 200:
        await asyncio.sleep(1.0)


async def maybe_sleep_for_rest_limit(response: httpx.Response) -> None:
    """Sleep when REST call-limit header is near the bucket ceiling."""

    header = response.headers.get("X-Shopify-Shop-Api-Call-Limit")
    if not header or "/" not in header:
        return
    used, total = header.split("/", 1)
    try:
        if int(used) / int(total) > 0.8:
            await asyncio.sleep(1.0)
    except ValueError:
        return


def has_throttle_error(errors: list[Any]) -> bool:
    """Detect Shopify GraphQL throttle errors."""

    return any("THROTTLED" in str(error).upper() or "THROTTLE" in str(error).upper() for error in errors)


def first_graphql_error(errors: list[Any]) -> str:
    """Return a sanitized first GraphQL error message."""

    first = errors[0] if errors else {}
    if isinstance(first, dict):
        return str(first.get("message") or "Shopify GraphQL error")
    return "Shopify GraphQL error"
