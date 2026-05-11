"""Regression tests for the deterministic APES demo pipeline."""

from __future__ import annotations

import pytest

from backend.app.services.audit_pipeline import AuditPipeline
from backend.app.main import audit_event_stream
from backend.app.models import AuditRequest


@pytest.mark.asyncio
async def test_demo_pipeline_hits_target_scores() -> None:
    """Ensure the required demo arc remains 38/100 to 71/100."""

    result = await AuditPipeline().run("hackathon-store.myshopify.com", demo_mode=True)
    assert result.total_queries == 20
    assert result.failed_queries == 12
    assert result.score.before_score == 38
    assert result.score.after_score == 71
    assert any("Christmas" in failure.query for failure in result.failures)


@pytest.mark.asyncio
async def test_demo_failure_cards_have_fixes() -> None:
    """Verify each failed replay has a root cause and a proposed content fix."""

    result = await AuditPipeline().run("hackathon-store.myshopify.com", demo_mode=True)
    assert result.failures
    assert all(failure.root_cause for failure in result.failures)
    assert all(failure.fix for failure in result.failures)


@pytest.mark.asyncio
async def test_streaming_audit_emits_progress_and_result() -> None:
    """Ensure the frontend can receive real progress events before the final report."""

    chunks = [
        chunk
        async for chunk in audit_event_stream(
            AuditRequest(store_url="hackathon-store.myshopify.com", demo_mode=True)
        )
    ]
    payload = "".join(chunks)
    assert '"type": "progress"' in payload
    assert '"stage": "simulations"' in payload
    assert '"type": "result"' in payload
