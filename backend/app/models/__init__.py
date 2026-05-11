"""APES model exports.

StoreContext is imported from backend.app.models.store_context and should not
be redefined elsewhere.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from backend.app.models.store_context import (
    Collection,
    CrawlCoverage,
    FAQ,
    Gap,
    Navigation,
    NavigationItem,
    Policies,
    Policy,
    Product,
    ProductImage,
    ProductMetafield,
    ProductVariant,
    Review,
    StoreContext,
    StoreGap,
    StorePage,
)

Classification = Literal["REFUSED", "VAGUE", "HALLUCINATED", "CONFIDENT_CORRECT"]
Dimension = Literal["product_clarity", "policy_completeness", "trust_signals", "faq_coverage"]
GapType = Literal["missing_field", "ambiguous_content", "contradictory_data", "no_reviews", "policy_gap"]
Severity = Literal["high", "medium", "low"]


class PersonaQuery(BaseModel):
    """Natural customer query tagged with persona and scoring dimension."""

    id: str
    persona: str
    category: str
    query: str
    intent: str
    expected_answer_type: str
    difficulty: Literal["easy", "medium", "hard"]
    dimension: Dimension


class SimulationResult(BaseModel):
    """Stored output from an agent simulation before any failure analysis."""

    query_id: str
    query: PersonaQuery
    response: str
    response_length: int
    hedging_language_detected: bool
    refusal_detected: bool
    fixed_context: bool = False
    classification: Classification | None = None
    dimension: Dimension | None = None


class FailureVerification(BaseModel):
    """Claude verification result or deterministic fallback for a classification."""

    query_id: str
    classification: Classification
    confidence: float
    reason: str
    rule_classification: Classification
    grounding: dict | None = None


class ForensicFinding(BaseModel):
    """Exact root cause that explains why a simulated shopping agent failed."""

    query_id: str
    gap_type: GapType
    specific_issue: str
    location: str
    severity: Severity
    impact_on_conversion: str


class FixProposal(BaseModel):
    """AI-generated content repair tied to one forensic finding."""

    query_id: str
    content_type: str
    original_content: str | None
    improved_content: str
    changes_made: list[str]
    confidence_improvement_reason: str
    impact_points: int


class DimensionScore(BaseModel):
    """Score detail for one weighted AI readiness dimension."""

    dimension: Dimension
    label: str
    weight: float
    total_queries: int
    confident_correct: int
    score: int


class ScoreReport(BaseModel):
    """Before/after score calculation with weighted dimension details."""

    before_score: int
    after_score: int
    delta: int
    before_dimensions: list[DimensionScore]
    after_dimensions: list[DimensionScore]
    current_perception: "CurrentPerception | None" = None


class CurrentPerception(BaseModel):
    """How AI shopping agents currently perceive the store from simulations."""

    perception_summary: str
    perceived_as: str
    confidence_level: Literal["very low", "low", "medium", "high"]
    confidence_reason: str
    biggest_perception_problems: list[str]


class FailureReplay(BaseModel):
    """UI-ready replay card combining query, response, classification, cause, and fix."""

    query_id: str
    persona: str
    query: str
    response: str
    classification: Classification
    severity: Severity
    root_cause: str
    location: str
    dimension: Dimension
    fix: FixProposal | None = None
    after_response: str | None = None
    after_classification: Classification | None = None


class AuditResult(BaseModel):
    """Complete APES audit response consumed by the frontend dashboard."""

    audit_id: str
    store_context: StoreContext
    queries: list[PersonaQuery]
    simulations: list[SimulationResult]
    verifications: list[FailureVerification]
    findings: list[ForensicFinding]
    fixes: list[FixProposal]
    score: ScoreReport
    failures: list[FailureReplay]
    total_queries: int
    failed_queries: int
    high_impact_fixes: int
    action_plan: list[str]


class AuditRequest(BaseModel):
    """Input accepted by the audit endpoint without exposing secret API details."""

    store_url: str = "hackathon-store.myshopify.com"
    demo_mode: bool = True


class BrandGapRequest(BaseModel):
    """Merchant-provided desired brand representation."""

    brand_positioning: str
    brand_adjectives: list[str]
    target_customer: str
    must_get_right: str = ""
    must_never_say: str = ""


class MisalignedArea(BaseModel):
    """One mismatch between desired representation and current perception."""

    desired: str
    current: str
    caused_by: str
    fix_priority: Literal["high", "medium", "low"]


class MustNeverSayRisk(BaseModel):
    """Whether AI agents are likely to say the merchant's feared perception."""

    at_risk: bool
    reason: str


class PerceptionBlocker(BaseModel):
    """A concrete data blocker preventing the desired perception."""

    blocker: str
    data_needed: str
    estimated_gap_reduction: int


class ProjectedPerception(BaseModel):
    """Projected perception after fixing all blockers."""

    projected_perception: str
    projected_gap_score: int


class BrandGapAnalysis(BaseModel):
    """AI comparison of current perception against desired merchant positioning."""

    gap_score: int
    gap_summary: str
    aligned_areas: list[str]
    misaligned_areas: list[MisalignedArea]
    must_never_say_risk: MustNeverSayRisk
    perception_blockers: list[PerceptionBlocker]
    if_all_fixed: ProjectedPerception


class CrawlRequest(BaseModel):
    """Input for deterministic Module 1 Shopify crawler endpoint."""

    shop_url: str = "hackathon-store.myshopify.com"


class ErrorResponse(BaseModel):
    """Sanitized API error shape for user-facing clients."""

    message: str
    recoverable: bool = True
