"""Repository layer for APES audit persistence."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Audit, Finding, Fix, PersonaQuery, ScoreReport, Simulation, StoreContext

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_audit_id() -> str:
    return uuid.uuid4().hex[:12]


async def create_audit(
    db: AsyncSession,
    shop_url: str,
    store_name: str | None = None,
    audit_id: str | None = None,
) -> str:
    """Insert an audit row and return the public audit id."""

    public_id = audit_id or new_audit_id()
    db.add(Audit(audit_id=public_id, shop_url=shop_url, store_name=store_name, status="running"))
    await db.flush()
    logger.info("Audit started: %s", public_id)
    return public_id


async def complete_audit(
    db: AsyncSession,
    audit_id: str,
    before_score: int,
    after_score: int,
    failed_queries: int,
    high_impact_fixes: int,
) -> None:
    await db.execute(
        update(Audit)
        .where(Audit.audit_id == audit_id)
        .values(
            status="complete",
            before_score=before_score,
            after_score=after_score,
            failed_queries=failed_queries,
            high_impact_fixes=high_impact_fixes,
            completed_at=_now(),
        )
    )


async def fail_audit(db: AsyncSession, audit_id: str, error: str) -> None:
    await db.execute(
        update(Audit)
        .where(Audit.audit_id == audit_id)
        .values(status="failed", error_message=error[:500], completed_at=_now())
    )


async def get_audit_by_id(db: AsyncSession, audit_id: str) -> Audit | None:
    result = await db.execute(select(Audit).where(Audit.audit_id == audit_id))
    return result.scalar_one_or_none()


async def get_recent_audits(db: AsyncSession, limit: int = 10) -> list[Audit]:
    result = await db.execute(select(Audit).order_by(desc(Audit.created_at)).limit(limit))
    return list(result.scalars().all())


async def save_store_context(
    db: AsyncSession,
    audit_id: str,
    store_data: dict[str, Any],
    gaps_detected: list[dict[str, Any]],
    crawl_coverage: dict[str, Any],
    product_count: int,
    has_policies: bool,
    has_faqs: bool,
) -> None:
    db.add(
        StoreContext(
            audit_id=audit_id,
            store_data=store_data,
            gaps_detected=gaps_detected,
            crawl_coverage=crawl_coverage,
            product_count=product_count,
            has_policies=has_policies,
            has_faqs=has_faqs,
        )
    )
    await db.flush()


async def save_queries(db: AsyncSession, audit_id: str, queries: list[dict[str, Any]]) -> None:
    db.add_all(
        [
            PersonaQuery(
                audit_id=audit_id,
                query_id=query["id"],
                persona=query["persona"],
                category=query.get("category"),
                query=query["query"],
                intent=query.get("intent"),
                dimension=query["dimension"],
                difficulty=query.get("difficulty"),
            )
            for query in queries
        ]
    )
    await db.flush()


async def save_simulations(db: AsyncSession, audit_id: str, simulations: list[dict[str, Any]]) -> None:
    rows = []
    for simulation in simulations:
        query = simulation.get("query", {})
        grounding = simulation.get("grounding") or {}
        rows.append(
            Simulation(
                audit_id=audit_id,
                query_id=simulation["query_id"],
                persona=query.get("persona") or simulation.get("persona") or "",
                query=query.get("query") or simulation.get("query") or "",
                dimension=query.get("dimension") or simulation.get("dimension") or "",
                response=simulation.get("response"),
                classification=simulation.get("classification"),
                confidence=simulation.get("confidence"),
                severity=simulation.get("severity"),
                hedging_detected=simulation.get("hedging_language_detected", False),
                refusal_detected=simulation.get("refusal_detected", False),
                is_grounded=grounding.get("is_grounded", True),
                ungrounded_claims=grounding.get("ungrounded_claims", []),
                fixed_context=simulation.get("fixed_context", False),
                after_response=simulation.get("after_response"),
                after_classification=simulation.get("after_classification"),
            )
        )
    db.add_all(rows)
    await db.flush()


async def get_simulations(db: AsyncSession, audit_id: str) -> list[Simulation]:
    result = await db.execute(select(Simulation).where(Simulation.audit_id == audit_id))
    return list(result.scalars().all())


async def save_findings(db: AsyncSession, audit_id: str, findings: list[dict[str, Any]]) -> None:
    db.add_all(
        [
            Finding(
                audit_id=audit_id,
                query_id=finding["query_id"],
                gap_type=finding["gap_type"],
                specific_issue=finding["specific_issue"],
                location=finding["location"],
                severity=finding["severity"],
                impact_on_conversion=finding.get("impact_on_conversion"),
            )
            for finding in findings
        ]
    )
    await db.flush()


async def get_findings(db: AsyncSession, audit_id: str) -> list[Finding]:
    result = await db.execute(select(Finding).where(Finding.audit_id == audit_id))
    return list(result.scalars().all())


async def save_fixes(db: AsyncSession, audit_id: str, fixes: list[dict[str, Any]]) -> None:
    db.add_all(
        [
            Fix(
                audit_id=audit_id,
                query_id=fix["query_id"],
                content_type=fix["content_type"],
                original_content=fix.get("original_content"),
                improved_content=fix.get("improved_content"),
                changes_made=fix.get("changes_made", []),
                confidence_improvement_reason=fix.get("confidence_improvement_reason"),
                impact_points=fix.get("impact_points", 0),
                applied=False,
            )
            for fix in fixes
        ]
    )
    await db.flush()


async def get_fixes(db: AsyncSession, audit_id: str) -> list[Fix]:
    result = await db.execute(select(Fix).where(Fix.audit_id == audit_id))
    return list(result.scalars().all())


async def mark_fix_applied(db: AsyncSession, audit_id: str, query_id: str) -> None:
    await db.execute(
        update(Fix)
        .where(Fix.audit_id == audit_id)
        .where(Fix.query_id == query_id)
        .values(applied=True, applied_at=_now())
    )


async def save_score_report(
    db: AsyncSession,
    audit_id: str,
    score: dict[str, Any],
    action_plan: list[str],
) -> None:
    db.add(
        ScoreReport(
            audit_id=audit_id,
            before_score=score["before_score"],
            after_score=score["after_score"],
            delta=score["delta"],
            before_dimensions=score["before_dimensions"],
            after_dimensions=score["after_dimensions"],
            action_plan=action_plan,
        )
    )
    await db.flush()


async def get_score_report(db: AsyncSession, audit_id: str) -> ScoreReport | None:
    result = await db.execute(select(ScoreReport).where(ScoreReport.audit_id == audit_id))
    return result.scalar_one_or_none()
