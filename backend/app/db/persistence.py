"""Helpers that map APES Pydantic audit results into repository rows."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.engine import AsyncSessionLocal, db_enabled
from backend.app.db import repository as repo
from backend.app.models import AuditResult

logger = logging.getLogger(__name__)


async def persist_audit_result(result: AuditResult, shop_url: str) -> None:
    """Persist a completed audit when APES_ENABLE_DB is enabled."""

    if not db_enabled():
        return
    async with AsyncSessionLocal() as db:
        try:
            await repo.create_audit(
                db,
                shop_url=shop_url,
                store_name=result.store_context.store_name,
                audit_id=result.audit_id,
            )
            store_data = result.store_context.model_dump(mode="json", by_alias=True, exclude_none=False)
            await repo.save_store_context(
                db,
                audit_id=result.audit_id,
                store_data=store_data,
                gaps_detected=[gap.model_dump(mode="json") for gap in result.store_context.gaps_detected],
                crawl_coverage=result.store_context.crawl_coverage.model_dump(mode="json"),
                product_count=len(result.store_context.products),
                has_policies=has_any_policy(store_data.get("policies", {})),
                has_faqs=len(result.store_context.faqs) > 0,
            )
            await repo.save_queries(
                db,
                result.audit_id,
                [query.model_dump(mode="json") for query in result.queries],
            )
            await repo.save_simulations(db, result.audit_id, simulation_rows(result))
            await repo.save_findings(
                db,
                result.audit_id,
                [finding.model_dump(mode="json") for finding in result.findings],
            )
            await repo.save_fixes(
                db,
                result.audit_id,
                [fix.model_dump(mode="json") for fix in result.fixes],
            )
            await repo.save_score_report(
                db,
                result.audit_id,
                result.score.model_dump(mode="json"),
                result.action_plan,
            )
            await repo.complete_audit(
                db,
                audit_id=result.audit_id,
                before_score=result.score.before_score,
                after_score=result.score.after_score,
                failed_queries=result.failed_queries,
                high_impact_fixes=result.high_impact_fixes,
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to persist audit %s", result.audit_id)
        except Exception:
            await db.rollback()
            logger.exception("Unexpected persistence failure for audit %s", result.audit_id)


def simulation_rows(result: AuditResult) -> list[dict[str, Any]]:
    """Combine simulations, verifications, findings, and replays into DB-ready rows."""

    verification_by_id = {item.query_id: item for item in result.verifications}
    finding_by_id = {item.query_id: item for item in result.findings}
    replay_by_id = {item.query_id: item for item in result.failures}
    rows = []
    for simulation in result.simulations:
        row = simulation.model_dump(mode="json")
        verification = verification_by_id.get(simulation.query_id)
        finding = finding_by_id.get(simulation.query_id)
        replay = replay_by_id.get(simulation.query_id)
        if verification:
            row["classification"] = verification.classification
            row["confidence"] = verification.confidence
            row["grounding"] = verification.grounding or {}
        if finding:
            row["severity"] = finding.severity
        if replay:
            row["after_response"] = replay.after_response
            row["after_classification"] = replay.after_classification
        rows.append(row)
    return rows


def has_any_policy(policies: dict[str, Any]) -> bool:
    """Return true if the crawled policy object has any filled policy body."""

    return any(bool(value) for key, value in policies.items() if key != "model_config")
