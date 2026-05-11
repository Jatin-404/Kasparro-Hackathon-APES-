"""Orchestrates APES modules from store input through final score."""

from __future__ import annotations

import logging
import uuid

from backend.app.models import AuditResult, FailureReplay, FailureVerification, FixProposal, ForensicFinding, SimulationResult, StoreContext
from backend.app.services.agent_simulator import AgentSimulator
from backend.app.services.failure_detector import FailureDetector
from backend.app.services.fix_generator import FixGenerator
from backend.app.services.forensics_engine import ForensicsEngine
from backend.app.services.perception_engine import PerceptionEngine
from backend.app.services.persona_engine import PersonaEngine
from backend.app.services.resimulation_runner import ResimulationRunner
from backend.app.services.score_engine import ScoreEngine
from backend.app.services.store_crawler import StoreCrawler

logger = logging.getLogger(__name__)


class AuditPipeline:
    """Run all seven APES modules while keeping AI and deterministic stages separate."""

    def __init__(
        self,
        crawler: StoreCrawler | None = None,
        personas: PersonaEngine | None = None,
        simulator: AgentSimulator | None = None,
        detector: FailureDetector | None = None,
        forensics: ForensicsEngine | None = None,
        fixes: FixGenerator | None = None,
        perception: PerceptionEngine | None = None,
        runner: ResimulationRunner | None = None,
        scorer: ScoreEngine | None = None,
    ) -> None:
        """Wire service dependencies so tests can replace any module independently."""

        self.crawler = crawler or StoreCrawler()
        self.personas = personas or PersonaEngine()
        self.simulator = simulator or AgentSimulator()
        self.detector = detector or FailureDetector()
        self.forensics = forensics or ForensicsEngine()
        self.fixes = fixes or FixGenerator()
        self.perception = perception or PerceptionEngine()
        self.runner = runner or ResimulationRunner()
        self.scorer = scorer or ScoreEngine()

    async def run(self, store_url: str, demo_mode: bool = True) -> AuditResult:
        """Execute crawl, query generation, simulation, detection, fixes, and scoring."""

        store_context = await self.crawler.fetch_store_context(store_url, demo_mode=demo_mode)
        return await self.run_with_context(store_url, store_context, demo_mode=demo_mode)

    async def run_with_context(self, store_url: str, store_context: StoreContext, demo_mode: bool = False) -> AuditResult:
        """Execute downstream modules from an already-crawled Module 1 StoreContext."""

        queries = await self.personas.generate_queries(store_context, demo_mode=demo_mode)
        simulations = await self.simulator.simulate_many(store_context, queries, demo_mode=demo_mode)
        verifications = await self.detector.classify_many(store_context, simulations, demo_mode=demo_mode)
        findings = await self.forensics.analyze_many(store_context, simulations, verifications, demo_mode=demo_mode)
        current_perception = await self.perception.generate(
            store_context,
            simulations,
            verifications,
            findings,
            demo_mode=demo_mode,
        )
        fixes = await self.fixes.generate_many(store_context, findings, queries, demo_mode=demo_mode)
        fixed_context = self.runner.apply_fixes(store_context, fixes)
        failed_query_ids = {verification.query_id for verification in verifications if verification.classification != "CONFIDENT_CORRECT"}
        failed_queries = [query for query in queries if query.id in failed_query_ids]
        after_simulations = await self.simulator.simulate_many(
            fixed_context,
            failed_queries,
            demo_mode=demo_mode,
            fixed_context=True,
        )
        after_verifications = await self.detector.classify_many(fixed_context, after_simulations, demo_mode=demo_mode)
        after_verification_ids = {verification.query_id for verification in after_verifications}
        combined_after_verifications = [
            verification for verification in verifications if verification.query_id not in after_verification_ids
        ]
        combined_after_verifications.extend(after_verifications)
        score = self.scorer.calculate(queries, verifications, combined_after_verifications, store_context, fixed_context)
        score.current_perception = current_perception
        failures = build_failure_replays(simulations, verifications, findings, fixes, after_simulations, after_verifications)
        failed_queries = sum(1 for verification in verifications if verification.classification != "CONFIDENT_CORRECT")
        return AuditResult(
            audit_id=audit_id_for(store_url),
            store_context=store_context,
            queries=queries,
            simulations=simulations,
            verifications=verifications,
            findings=findings,
            fixes=fixes,
            score=score,
            failures=failures,
            total_queries=len(queries),
            failed_queries=failed_queries,
            high_impact_fixes=sum(1 for finding in findings if finding.severity == "high"),
            action_plan=[
                "Publish the generated shipping policy with holiday cutoffs.",
                "Add warranty and refund timing details for electronics.",
                "Collect verified reviews for products with no social proof.",
                "Add three FAQ answers to reach 85+ AI readiness.",
            ],
        )


def audit_id_for(store_url: str) -> str:
    """Create a short public id for one audit run."""

    return uuid.uuid4().hex[:12]


def build_failure_replays(
    simulations: list[SimulationResult],
    verifications: list[FailureVerification],
    findings: list[ForensicFinding],
    fixes: list[FixProposal],
    after_simulations: list[SimulationResult],
    after_verifications: list[FailureVerification],
) -> list[FailureReplay]:
    """Join pipeline outputs into story cards for the failure replay UI."""

    verification_by_id = {item.query_id: item for item in verifications}
    finding_by_id = {item.query_id: item for item in findings}
    fix_by_id = {item.query_id: item for item in fixes}
    after_simulation_by_id = {item.query_id: item for item in after_simulations}
    after_verification_by_id = {item.query_id: item for item in after_verifications}
    replay: list[FailureReplay] = []
    for simulation in simulations:
        verification = verification_by_id[simulation.query_id]
        if verification.classification == "CONFIDENT_CORRECT":
            continue
        finding = finding_by_id[simulation.query_id]
        replay.append(
            FailureReplay(
                query_id=simulation.query_id,
                persona=simulation.query.persona,
                query=simulation.query.query,
                response=simulation.response,
                classification=verification.classification,
                severity=finding.severity,
                root_cause=finding.specific_issue,
                location=finding.location,
                dimension=simulation.query.dimension,
                fix=fix_by_id.get(simulation.query_id),
                after_response=after_simulation_by_id.get(simulation.query_id).response
                if after_simulation_by_id.get(simulation.query_id)
                else None,
                after_classification=after_verification_by_id.get(simulation.query_id).classification
                if after_verification_by_id.get(simulation.query_id)
                else None,
            )
        )
    return replay
