"""Deterministic AI Readiness scoring for APES."""

from __future__ import annotations

from backend.app.models import Dimension, DimensionScore, FailureVerification, PersonaQuery, ScoreReport, StoreContext


WEIGHTS: dict[Dimension, float] = {
    "product_clarity": 0.30,
    "policy_completeness": 0.25,
    "trust_signals": 0.25,
    "faq_coverage": 0.20,
}

LABELS: dict[Dimension, str] = {
    "product_clarity": "Product Clarity",
    "policy_completeness": "Policy Completeness",
    "trust_signals": "Trust Signals",
    "faq_coverage": "FAQ Coverage",
}


class ScoreEngine:
    """Calculate weighted readiness scores from confident-correct rates."""

    def calculate(
        self,
        queries: list[PersonaQuery],
        before: list[FailureVerification],
        after: list[FailureVerification],
        context: StoreContext | None = None,
        after_context: StoreContext | None = None,
    ) -> ScoreReport:
        """Return before/after weighted score details for the dashboard."""

        before_dimensions = self._dimension_scores(queries, before, context)
        after_dimensions = self._dimension_scores(queries, after, after_context or context)
        before_score = weighted_total(before_dimensions)
        after_score = weighted_total(after_dimensions)
        return ScoreReport(
            before_score=before_score,
            after_score=after_score,
            delta=after_score - before_score,
            before_dimensions=before_dimensions,
            after_dimensions=after_dimensions,
        )

    def _dimension_scores(
        self,
        queries: list[PersonaQuery],
        verifications: list[FailureVerification],
        context: StoreContext | None = None,
    ) -> list[DimensionScore]:
        """Calculate the confident-correct rate for each score dimension."""

        verification_by_id = {verification.query_id: verification for verification in verifications}
        scores: list[DimensionScore] = []
        for dimension, weight in WEIGHTS.items():
            dimension_queries = [query for query in queries if query.dimension == dimension]
            correct = sum(
                1
                for query in dimension_queries
                if verification_by_id.get(query.id) and verification_by_id[query.id].classification == "CONFIDENT_CORRECT"
            )
            total = len(dimension_queries)
            score = round((correct / total) * 100) if total else 0
            score = apply_store_context_penalties(dimension, score, context)
            scores.append(
                DimensionScore(
                    dimension=dimension,
                    label=LABELS[dimension],
                    weight=weight,
                    total_queries=total,
                    confident_correct=correct,
                    score=score,
                )
            )
        return scores


def weighted_total(dimensions: list[DimensionScore]) -> int:
    """Convert per-dimension rates into the final 0-100 readiness score."""

    return round(sum(item.score * item.weight for item in dimensions))


def apply_store_context_penalties(dimension: Dimension, score: int, context: StoreContext | None) -> int:
    """Penalize dimensions when Module 1 proves key store surfaces are absent."""

    if context is None:
        return score
    coverage = context.crawl_coverage
    if not coverage.products and dimension == "product_clarity":
        score = min(score, 10)
    if not coverage.policies and dimension == "policy_completeness":
        score = min(score, 10)
    if not coverage.pages and dimension == "faq_coverage":
        score = min(score, 20)
    if dimension == "policy_completeness":
        if not context.policies.return_policy:
            score = min(score, 30)
        if not context.policies.shipping:
            score = min(score, 40)
    if dimension == "faq_coverage" and not context.faqs:
        score = min(score, 20)
    if dimension == "trust_signals" and context.products:
        reviewed = [product for product in context.products if product.reviews_count]
        if not reviewed:
            score = min(score, 25)
    return score
