"""AI-powered shopping agent simulator."""

from __future__ import annotations

import logging
import asyncio

from backend.app.models import PersonaQuery, SimulationResult, StoreContext
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.demo_data import demo_response_for_query
from backend.app.services.store_context_adapter import build_store_summary

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an AI shopping agent helping a customer.
You ONLY know what is in the store data below.
Do not make up specs, prices, or policies not mentioned.
If you are unsure about anything, say so explicitly.
Never hallucinate. Answer as if helping a real customer."""

HEDGING_TERMS = ["probably", "i think", "might be", "should be", "approximately", "not certain", "unsure"]
REFUSAL_TERMS = ["i don't know", "not sure", "can't find", "no information", "cannot find"]


class AgentSimulator:
    """Run Claude as a constrained shopping agent against only StoreContext."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        """Accept a Claude client so simulation can fail closed when unavailable."""

        self.claude = claude or ClaudeClient()

    async def simulate_many(
        self,
        store_context: StoreContext,
        queries: list[PersonaQuery],
        demo_mode: bool = False,
        fixed_context: bool = False,
    ) -> list[SimulationResult]:
        """Run every persona query and store response metadata for later classification."""

        if self.claude.is_ollama:
            results: list[SimulationResult] = []
            for query in queries:
                results.append(
                    await self.simulate(store_context, query, demo_mode=demo_mode, fixed_context=fixed_context)
                )
            return results
        return await asyncio.gather(
            *[
                self.simulate(store_context, query, demo_mode=demo_mode, fixed_context=fixed_context)
                for query in queries
            ]
        )

    async def simulate(
        self,
        store_context: StoreContext,
        query: PersonaQuery,
        demo_mode: bool = False,
        fixed_context: bool = False,
    ) -> SimulationResult:
        """Run one simulated shopping answer with graceful fallback text."""

        if demo_mode or not self.claude.is_configured:
            response = demo_response_for_query(query, fixed_context=fixed_context)
        else:
            store_summary = build_store_summary(store_context)
            user_prompt = f"Store data:\n{store_summary}\n\nCustomer query: {query.query}"
            try:
                response = await self.claude.complete_text(AGENT_SYSTEM_PROMPT, user_prompt, max_tokens=260)
            except Exception as exc:
                logger.warning("Agent simulation fell back to uncertainty response: %s", exc)
                response = "I don't know from the store data provided. I can't find enough information to answer confidently."
        return SimulationResult(
            query_id=query.id,
            query=query,
            response=response,
            response_length=len(response),
            hedging_language_detected=contains_any(response, HEDGING_TERMS),
            refusal_detected=contains_any(response, REFUSAL_TERMS),
            fixed_context=fixed_context,
        )


def contains_any(text: str, terms: list[str]) -> bool:
    """Check a response for classification trigger phrases."""

    lowered = text.lower()
    return any(term in lowered for term in terms)


def compact_store_context(store_context: StoreContext) -> str:
    """Serialize store context in a stable way for prompts and debugging."""

    return build_store_summary(store_context)
