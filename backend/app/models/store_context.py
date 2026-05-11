"""Canonical StoreContext model for APES.

Every downstream module should import StoreContext from this file. The model
matches the Module 1 crawler response while allowing a small amount of
backward-compatible input normalization during the migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductImage(BaseModel):
    """Product image visible to agents, with null alt text preserved as a gap."""

    model_config = ConfigDict(populate_by_name=True)

    src: Optional[str] = Field(default=None, validation_alias=AliasChoices("src", "url"))
    alt: Optional[str] = Field(default=None, validation_alias=AliasChoices("alt", "alt_text"))


class ProductVariant(BaseModel):
    """Variant data exposed to downstream simulations."""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    price: Optional[str] = None
    sku: Optional[str] = None
    weight: Optional[float] = None
    available: Optional[bool] = Field(default=None, validation_alias=AliasChoices("available", "available_for_sale"))
    inventory_quantity: Optional[int] = None
    options: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value: Any) -> list[dict[str, Any]]:
        """Convert older dict options into the canonical list shape."""

        if isinstance(value, dict):
            return [{"name": key, "value": option_value} for key, option_value in value.items()]
        return value or []


class ProductMetafield(BaseModel):
    """Metafield value from Shopify Admin GraphQL."""

    namespace: str
    key: str
    value: str | None = None
    type: str | None = None


class Product(BaseModel):
    """Canonical product shape consumed by APES modules."""

    id: str
    title: str
    description: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    status: Optional[str] = None
    price_min: Optional[str] = None
    price_max: Optional[str] = None
    compare_at_price: Optional[str] = None
    images: list[ProductImage] = Field(default_factory=list)
    variants: list[ProductVariant] = Field(default_factory=list)
    metafields: list[ProductMetafield] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    reviews_count: Optional[int] = None
    average_rating: Optional[float] = None
    publicly_visible: bool = True
    reviews: list[Any] = Field(default_factory=list, exclude=True)

    @field_validator("metafields", mode="before")
    @classmethod
    def normalize_metafields(cls, value: Any) -> list[dict[str, Any]]:
        """Convert older metafield dicts into the canonical list shape."""

        if isinstance(value, dict):
            normalized = []
            for full_key, metafield_value in value.items():
                namespace, _, key = str(full_key).partition(".")
                normalized.append(
                    {
                        "namespace": namespace or "custom",
                        "key": key or namespace,
                        "value": metafield_value,
                        "type": "string",
                    }
                )
            return normalized
        return value or []

    @model_validator(mode="after")
    def summarize_reviews(self) -> "Product":
        """Summarize older review fixtures into canonical review count/rating fields."""

        if self.reviews and self.reviews_count is None:
            self.reviews_count = len(self.reviews)
        if self.reviews and self.average_rating is None:
            ratings = [getattr(review, "rating", None) for review in self.reviews]
            ratings = [rating for rating in ratings if rating is not None]
            if ratings:
                self.average_rating = sum(ratings) / len(ratings)
        return self


class Policy(BaseModel):
    """Policy content from Shopify REST policies endpoint."""

    title: str
    body: str
    url: Optional[str] = None


class Policies(BaseModel):
    """Policy slots where null represents a critical merchant gap."""

    model_config = ConfigDict(populate_by_name=True)

    return_policy: Optional[Policy] = Field(
        default=None,
        validation_alias=AliasChoices("return", "return_policy"),
        serialization_alias="return",
    )
    shipping: Optional[Policy] = None
    refund: Optional[Policy] = None
    privacy: Optional[Policy] = None
    warranty: Optional[Policy] = Field(default=None, exclude=True)

    @field_validator("return_policy", "shipping", "refund", "privacy", "warranty", mode="before")
    @classmethod
    def normalize_policy(cls, value: Any) -> Any:
        """Convert older plain-string policies into Policy objects."""

        if isinstance(value, str):
            return {"title": "Policy", "body": value, "url": None}
        return value


class FAQ(BaseModel):
    """FAQ pair extracted from Online Store pages."""

    question: str
    answer: Optional[str] = None
    source_page: Optional[str] = None


class Review(BaseModel):
    """Backward-compatible review fixture for demo data imports."""

    author: str | None = None
    rating: float | None = None
    body: str | None = None


class Collection(BaseModel):
    """Collection summary used for categories and product grouping."""

    id: str | None = None
    title: str = Field(default="", validation_alias=AliasChoices("title", "name"))
    description: Optional[str] = None
    products_count: int = 0
    products: list[str] = Field(default_factory=list, exclude=True)

    @model_validator(mode="after")
    def fill_collection_id(self) -> "Collection":
        """Use title as a stable fallback id for older collection fixtures."""

        if self.id is None:
            self.id = self.title
        if self.products and not self.products_count:
            self.products_count = len(self.products)
        return self


class NavigationItem(BaseModel):
    """Single menu item from Shopify navigation."""

    title: str
    url: str
    type: Optional[str] = None


class Navigation(BaseModel):
    """Navigation menu from Shopify Admin GraphQL."""

    menu_title: str
    items: list[NavigationItem] = Field(default_factory=list)


class Gap(BaseModel):
    """Structural crawler gap computed before AI analysis."""

    type: str
    description: str
    affected_count: int


class CrawlCoverage(BaseModel):
    """Coverage flags for independent crawler sections."""

    products: bool = False
    policies: bool = False
    pages: bool = False
    collections: bool = False
    navigation: bool = False
    storefront: bool = False


class StoreGap(Gap):
    """Backward-compatible gap model for older service fixtures."""

    location: str | None = None
    field: str | None = None
    message: str | None = None
    severity: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_old_gap(cls, value: Any) -> Any:
        """Convert older location/field/message gaps into structural gaps."""

        if isinstance(value, dict) and "type" not in value:
            return {
                **value,
                "type": value.get("field") or "missing_specs",
                "description": value.get("message") or value.get("field") or "Store gap",
                "affected_count": 1,
            }
        return value


class StorePage(BaseModel):
    """Backward-compatible page model retained for older crawler helpers."""

    id: str
    title: str
    handle: str | None = None
    body: str | None = None
    source: str = "admin"


class StoreContext(BaseModel):
    """Single canonical source of truth all APES modules consume."""

    model_config = ConfigDict(populate_by_name=True)

    store_name: Optional[str] = None
    store_url: str
    currency: Optional[str] = None
    crawled_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    crawl_coverage: CrawlCoverage = Field(default_factory=CrawlCoverage)
    products: list[Product] = Field(default_factory=list)
    collections: list[Collection] = Field(default_factory=list)
    policies: Policies = Field(default_factory=Policies)
    faqs: list[FAQ] = Field(default_factory=list)
    navigation: list[Navigation] = Field(default_factory=list)
    gaps_detected: list[Gap] = Field(default_factory=list)
    pages: list[StorePage] = Field(default_factory=list, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_old_context(cls, value: Any) -> Any:
        """Map older StoreContext fields into the canonical shape."""

        if not isinstance(value, dict):
            return value
        if "gaps" in value and "gaps_detected" not in value:
            value = {**value, "gaps_detected": value.get("gaps") or []}
        return value

    @model_validator(mode="after")
    def infer_legacy_coverage(self) -> "StoreContext":
        """Mark coverage for older fixtures that predate crawl_coverage flags."""

        flags = self.crawl_coverage
        if any([flags.products, flags.policies, flags.pages, flags.collections, flags.navigation, flags.storefront]):
            return self
        flags.products = bool(self.products)
        flags.policies = True
        flags.pages = bool(self.faqs or self.pages)
        flags.collections = bool(self.collections)
        flags.navigation = bool(self.navigation)
        flags.storefront = False
        return self

    @property
    def gaps(self) -> list[Gap]:
        """Return structural gaps for older helpers that still access context.gaps."""

        return self.gaps_detected

    def __getitem__(self, key: str) -> Any:
        """Allow older tests to read StoreContext like the endpoint JSON dict."""

        return self.model_dump(by_alias=True, exclude_none=False)[key]
