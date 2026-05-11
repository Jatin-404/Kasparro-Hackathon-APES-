"""FastAPI entrypoint for APES."""

from __future__ import annotations

import logging
import os
import json
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.models import AuditRequest, AuditResult, CrawlRequest, ErrorResponse
from backend.app.services.audit_pipeline import AuditPipeline, audit_id_for, build_failure_replays
from backend.app.services.full_store_crawler import FullStoreCrawler, build_demo_store_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv("backend/.env")

app = FastAPI(
    title="APES API",
    description="Agent Perception Evaluation System backend for Shopify AI readiness audits.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = AuditPipeline()

try:
    from backend.app.db.engine import db_enabled, db_required, get_db, init_db
    from backend.app.db import repository as repo
    from backend.app.db.persistence import persist_audit_result

    DB_AVAILABLE = True
    DB_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised when optional DB deps are absent
    DB_AVAILABLE = False
    DB_IMPORT_ERROR = exc

    def db_enabled() -> bool:
        return False

    def db_required() -> bool:
        return os.environ.get("APES_DB_REQUIRED", "false").lower() in {"1", "true", "yes", "on"}

    async def persist_audit_result(result: AuditResult, shop_url: str) -> None:
        return None

    async def init_db() -> None:
        raise RuntimeError(f"Database dependencies are unavailable: {DB_IMPORT_ERROR}") from DB_IMPORT_ERROR

    async def get_db() -> AsyncIterator[Any]:
        raise HTTPException(status_code=503, detail="Database persistence is not installed")

    repo = None


@app.on_event("startup")
async def startup() -> None:
    """Verify optional DB tables on startup when persistence is enabled."""

    if not db_enabled():
        logger.info("Database persistence disabled; set APES_ENABLE_DB=true to enable it")
        return
    try:
        await init_db()
        logger.info("APES database persistence enabled")
    except Exception:
        logger.exception("Database startup failed")
        if db_required():
            raise


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a small health signal for local setup and demo checks."""

    return {"status": "ok", "service": "apes-api"}


@app.post("/audit", response_model=AuditResult, responses={500: {"model": ErrorResponse}})
async def run_audit(request: AuditRequest) -> AuditResult:
    """Run the full APES audit and return sanitized, UI-ready results."""

    try:
        if request.demo_mode:
            result = await pipeline.run(request.store_url, demo_mode=True)
            await persist_audit_result(result, request.store_url)
            return result
        load_dotenv("backend/.env", override=True)
        access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        storefront_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN")
        if not access_token:
            result = await pipeline.run(request.store_url, demo_mode=True)
            await persist_audit_result(result, request.store_url)
            return result
        crawler = FullStoreCrawler(
            shop_url=request.store_url,
            access_token=access_token,
            storefront_token=storefront_token,
        )
        store_context = await crawler.crawl()
        result = await pipeline.run_with_context(request.store_url, store_context, demo_mode=False)
        await persist_audit_result(result, request.store_url)
        return result
    except Exception as exc:
        logger.exception("Audit failed")
        raise HTTPException(
            status_code=500,
            detail={"message": "APES could not complete the audit. Please retry in demo mode.", "recoverable": True},
        ) from exc


@app.post("/audit/stream", responses={500: {"model": ErrorResponse}})
async def stream_audit(request: AuditRequest) -> StreamingResponse:
    """Run an audit while streaming real backend progress as NDJSON events."""

    return StreamingResponse(
        audit_event_stream(request),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/audit/demo", response_model=AuditResult, responses={500: {"model": ErrorResponse}})
async def run_demo_audit() -> AuditResult:
    """Run the deterministic hackathon demo audit for hackathon-store.myshopify.com."""

    try:
        result = await pipeline.run("hackathon-store.myshopify.com", demo_mode=True)
        await persist_audit_result(result, "hackathon-store.myshopify.com")
        return result
    except Exception as exc:
        logger.exception("Demo audit failed")
        raise HTTPException(
            status_code=500,
            detail={"message": "Demo audit could not complete locally.", "recoverable": True},
        ) from exc


@app.post("/api/crawl", responses={500: {"model": ErrorResponse}})
async def crawl_store(request: CrawlRequest) -> dict:
    """Run deterministic Module 1 crawler and return exact StoreContext JSON."""

    load_dotenv("backend/.env", override=True)
    access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
    storefront_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail={"message": "Shopify Admin access token is required for /api/crawl.", "recoverable": True},
        )
    try:
        crawler = FullStoreCrawler(
            shop_url=request.shop_url,
            access_token=access_token,
            storefront_token=storefront_token,
        )
        context = await crawler.crawl()
        return context.model_dump(by_alias=True, exclude_none=False)
    except Exception as exc:
        logger.exception("Crawler failed")
        raise HTTPException(
            status_code=500,
            detail={"message": "Store crawl failed. Try /api/crawl/demo for fallback demo data.", "recoverable": True},
        ) from exc


@app.get("/api/crawl/demo")
async def crawl_demo_store() -> dict:
    """Return a pre-built 25-product StoreContext without hitting Shopify."""

    return build_demo_store_context().model_dump(by_alias=True, exclude_none=False)


@app.get("/api/audits/recent")
async def recent_audits(db: Any = Depends(get_db)) -> list[dict[str, Any]]:
    """List the ten most recent persisted audits."""

    if repo is None:
        raise HTTPException(status_code=503, detail="Database persistence is not installed")
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Database persistence is disabled")
    audits = await repo.get_recent_audits(db)
    return [
        {
            "audit_id": audit.audit_id,
            "shop_url": audit.shop_url,
            "store_name": audit.store_name,
            "status": audit.status,
            "before_score": audit.before_score,
            "after_score": audit.after_score,
            "score_delta": audit.after_score - audit.before_score
            if audit.before_score is not None and audit.after_score is not None
            else None,
            "created_at": audit.created_at.isoformat() if audit.created_at else None,
            "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
        }
        for audit in audits
    ]


@app.get("/api/audit/{audit_id}")
async def get_saved_audit(audit_id: str, db: Any = Depends(get_db)) -> dict[str, Any]:
    """Load a persisted audit by id."""

    if repo is None:
        raise HTTPException(status_code=503, detail="Database persistence is not installed")
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Database persistence is disabled")
    audit = await repo.get_audit_by_id(db, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    simulations = await repo.get_simulations(db, audit_id)
    findings = await repo.get_findings(db, audit_id)
    fixes = await repo.get_fixes(db, audit_id)
    score = await repo.get_score_report(db, audit_id)
    return {
        "audit_id": audit.audit_id,
        "shop_url": audit.shop_url,
        "store_name": audit.store_name,
        "status": audit.status,
        "before_score": audit.before_score,
        "after_score": audit.after_score,
        "score_delta": audit.after_score - audit.before_score
        if audit.before_score is not None and audit.after_score is not None
        else None,
        "failed_queries": audit.failed_queries,
        "high_impact_fixes": audit.high_impact_fixes,
        "simulations": [row_to_dict(row) for row in simulations],
        "findings": [row_to_dict(row) for row in findings],
        "fixes": [row_to_dict(row) for row in fixes],
        "score": row_to_dict(score) if score else None,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }


@app.post("/api/audit/{audit_id}/fix/{query_id}/apply")
async def apply_saved_fix(audit_id: str, query_id: str, db: Any = Depends(get_db)) -> dict[str, str]:
    """Mark a persisted fix as applied."""

    if repo is None:
        raise HTTPException(status_code=503, detail="Database persistence is not installed")
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Database persistence is disabled")
    audit = await repo.get_audit_by_id(db, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    await repo.mark_fix_applied(db, audit_id, query_id)
    return {"status": "applied", "audit_id": audit_id, "query_id": query_id}


def stream_event(event_type: str, **payload: object) -> str:
    """Serialize one frontend progress event as a newline-delimited JSON row."""

    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


def row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy row object to a JSON-safe dict."""

    data = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            value = str(value)
        data[column.name] = value
    return data


async def audit_event_stream(request: AuditRequest) -> AsyncIterator[str]:
    """Execute the audit pipeline with progress messages between real backend stages."""

    try:
        yield stream_event("progress", stage="crawl", status="started", message="Starting Shopify store crawl")
        load_dotenv("backend/.env", override=True)
        access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        storefront_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN")
        demo_mode = request.demo_mode or not access_token
        if demo_mode:
            store_context = build_demo_store_context()
        else:
            crawler = FullStoreCrawler(
                shop_url=request.store_url,
                access_token=access_token,
                storefront_token=storefront_token,
            )
            store_context = await crawler.crawl()
        yield stream_event(
            "progress",
            stage="crawl",
            status="complete",
            message=(
                f"Crawl complete: {len(store_context.products)} products, "
                f"{len(store_context.collections)} collections, {len(store_context.faqs)} FAQs"
            ),
        )

        yield stream_event("progress", stage="personas", status="started", message="Generating customer personas and queries")
        queries = await pipeline.personas.generate_queries(store_context, demo_mode=demo_mode)
        yield stream_event(
            "progress",
            stage="personas",
            status="complete",
            message=f"Generated {len(queries)} persona queries",
            current=len(queries),
            total=len(queries),
        )

        simulations = []
        yield stream_event("progress", stage="simulations", status="started", message="Running agent simulations", current=0, total=len(queries))
        for index, query in enumerate(queries, start=1):
            simulation = await pipeline.simulator.simulate(store_context, query, demo_mode=demo_mode)
            simulations.append(simulation)
            yield stream_event(
                "progress",
                stage="simulations",
                status="running",
                message=f"Simulated query {index} of {len(queries)}: {query.query}",
                current=index,
                total=len(queries),
            )
        yield stream_event("progress", stage="simulations", status="complete", message="Agent simulations complete", current=len(queries), total=len(queries))

        yield stream_event("progress", stage="verification", status="started", message="Classifying simulated responses")
        verifications = await pipeline.detector.classify_many(store_context, simulations, demo_mode=demo_mode)
        failed_query_ids = {verification.query_id for verification in verifications if verification.classification != "CONFIDENT_CORRECT"}
        yield stream_event(
            "progress",
            stage="verification",
            status="complete",
            message=f"Classified {len(verifications)} responses: {len(failed_query_ids)} failures found",
            current=len(verifications),
            total=len(verifications),
        )

        yield stream_event("progress", stage="forensics", status="started", message="Tracing failures to store content gaps")
        findings = await pipeline.forensics.analyze_many(store_context, simulations, verifications, demo_mode=demo_mode)
        yield stream_event("progress", stage="forensics", status="complete", message=f"Generated {len(findings)} forensic findings")

        yield stream_event("progress", stage="fixes", status="started", message="Generating fix proposals")
        fixes = await pipeline.fixes.generate_many(store_context, findings, queries, demo_mode=demo_mode)
        yield stream_event("progress", stage="fixes", status="complete", message=f"Generated {len(fixes)} fix proposals")

        fixed_context = pipeline.runner.apply_fixes(store_context, fixes)
        failed_queries = [query for query in queries if query.id in failed_query_ids]
        after_simulations = []
        yield stream_event("progress", stage="resimulation", status="started", message="Re-simulating failed queries after fixes", current=0, total=len(failed_queries))
        for index, query in enumerate(failed_queries, start=1):
            simulation = await pipeline.simulator.simulate(fixed_context, query, demo_mode=demo_mode, fixed_context=True)
            after_simulations.append(simulation)
            yield stream_event(
                "progress",
                stage="resimulation",
                status="running",
                message=f"Re-simulated failed query {index} of {len(failed_queries)}",
                current=index,
                total=len(failed_queries),
            )
        after_verifications = await pipeline.detector.classify_many(fixed_context, after_simulations, demo_mode=demo_mode)
        yield stream_event("progress", stage="resimulation", status="complete", message="Re-simulation complete", current=len(failed_queries), total=len(failed_queries))

        yield stream_event("progress", stage="scoring", status="started", message="Calculating AI readiness score")
        after_verification_ids = {verification.query_id for verification in after_verifications}
        combined_after_verifications = [
            verification for verification in verifications if verification.query_id not in after_verification_ids
        ]
        combined_after_verifications.extend(after_verifications)
        score = pipeline.scorer.calculate(queries, verifications, combined_after_verifications, store_context, fixed_context)
        failures = build_failure_replays(simulations, verifications, findings, fixes, after_simulations, after_verifications)
        result = AuditResult(
            audit_id=audit_id_for(request.store_url),
            store_context=store_context,
            queries=queries,
            simulations=simulations,
            verifications=verifications,
            findings=findings,
            fixes=fixes,
            score=score,
            failures=failures,
            total_queries=len(queries),
            failed_queries=len(failed_query_ids),
            high_impact_fixes=sum(1 for finding in findings if finding.severity == "high"),
            action_plan=[
                "Publish the generated shipping policy with holiday cutoffs.",
                "Add warranty and refund timing details for electronics.",
                "Collect verified reviews for products with no social proof.",
                "Add three FAQ answers to reach 85+ AI readiness.",
            ],
        )
        yield stream_event("progress", stage="scoring", status="complete", message=f"Score ready: {score.before_score}/100 -> {score.after_score}/100")
        await persist_audit_result(result, request.store_url)
        yield stream_event("result", result=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("Streaming audit failed")
        yield stream_event("error", message=str(exc) or "APES could not complete the streaming audit")
