"""AI-powered persona and query generation with deterministic fallback."""

from __future__ import annotations

import logging
import os

from backend.app.models import PersonaQuery, StoreContext
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.demo_data import build_demo_queries
from backend.app.services.json_utils import extract_json_array
from backend.app.services.store_context_adapter import extract_categories

logger = logging.getLogger(__name__)


PERSONAS = ["Budget Buyer", "Gift Buyer", "Researcher", "Impulse Buyer", "Skeptic"]


class PersonaEngine:
    """Generate realistic customer queries that probe agent-visible store gaps."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        """Accept a Claude client so the service can be replaced in tests."""

        self.claude = claude or ClaudeClient()

    async def generate_queries(self, store_context: StoreContext, demo_mode: bool = False) -> list[PersonaQuery]:
        """Generate 20 persona-tagged queries or fall back to demo queries on failure."""

        if demo_mode:
            return build_demo_queries()
        should_use_ollama = (
            self.claude.is_ollama and os.getenv("OLLAMA_GENERATE_PERSONAS", "false").lower() == "true"
        )
        if not self.claude.is_configured or (self.claude.is_ollama and not should_use_ollama):
            return build_store_fallback_queries(store_context)
        categories = extract_categories(store_context)
        store_name = store_context.store_name or "this store"
        prompt = (
            "Generate 20 realistic customer queries for the personas Budget Buyer, Gift Buyer, "
            f"Researcher, Impulse Buyer, and Skeptic shopping in {store_name}. "
            f"Use these product categories when relevant: {', '.join(categories)}. Queries "
            "should be natural, varied, and specifically designed to probe: product specs, "
            "policies, delivery, comparisons, and trust signals. Return JSON array only, no preamble. "
            "Each item must include persona, query, intent, expected_answer_type, difficulty, and dimension "
            "where dimension is one of product_clarity, policy_completeness, trust_signals, faq_coverage."
        )
        try:
            text = await self.claude.complete_json("Return strict JSON only.", prompt, max_tokens=900)
            items = extract_json_array(text)
            queries = [
                PersonaQuery(
                    id=f"q{index + 1:02d}",
                    persona=str(item.get("persona", PERSONAS[index % len(PERSONAS)])),
                    category=str(item.get("category", categories[index % len(categories)])),
                    query=str(item.get("query", "")),
                    intent=str(item.get("intent", "shopping_question")),
                    expected_answer_type=str(item.get("expected_answer_type", "specific_store_answer")),
                    difficulty=item.get("difficulty", "medium"),
                    dimension=item.get("dimension", "product_clarity"),
                )
                for index, item in enumerate(items[:20])
                if item.get("query")
            ]
            if len(queries) == 20:
                return queries
        except Exception as exc:
            logger.warning("Persona generation fell back to deterministic store queries: %s", exc)
        return build_store_fallback_queries(store_context)


def build_store_fallback_queries(store_context: StoreContext) -> list[PersonaQuery]:
    """Generate deterministic real-store queries when no AI model is available."""

    products = store_context.products[:10]
    categories = extract_categories(store_context)
    first = products[0].title if products else "this product"
    second = products[1].title if len(products) > 1 else first
    third = products[2].title if len(products) > 2 else first
    fourth = products[3].title if len(products) > 3 else first
    fifth = products[4].title if len(products) > 4 else first
    raw_queries = [
        ("Budget Buyer", first, f"Is {first} good value for the price?", "comparison", "product_clarity", "medium"),
        ("Researcher", third, f"What exact specs are listed for {third}?", "product_specs", "product_clarity", "medium"),
        ("Skeptic", fourth, f"What important details are missing for {fourth}?", "product_specs", "product_clarity", "hard"),
        ("Gift Buyer", second, f"Is {second} clear enough to buy as a gift?", "gift_confidence", "product_clarity", "medium"),
        ("Impulse Buyer", fifth, f"Can I quickly tell whether {fifth} works with my devices?", "compatibility", "product_clarity", "medium"),
        ("Gift Buyer", first, "Will this arrive before Christmas?", "delivery", "policy_completeness", "hard"),
        ("Budget Buyer", second, "If I return an opened item, how long does the refund take?", "returns", "policy_completeness", "hard"),
        ("Skeptic", third, f"Is there a warranty for {third} if it fails after a month?", "warranty", "policy_completeness", "hard"),
        ("Researcher", first, "Do you ship outside the United States?", "shipping", "policy_completeness", "medium"),
        ("Impulse Buyer", first, "Can I get expedited shipping if I order today?", "delivery", "policy_completeness", "hard"),
        ("Skeptic", first, f"Do real buyers say {first} is reliable?", "reviews", "trust_signals", "medium"),
        ("Researcher", second, f"Are there reviews proving {second} works reliably?", "reviews", "trust_signals", "medium"),
        ("Gift Buyer", first, "Which product has the strongest social proof for a gift?", "comparison", "trust_signals", "medium"),
        ("Budget Buyer", third, f"Can I trust {third} without any reviews?", "reviews", "trust_signals", "hard"),
        ("Impulse Buyer", fourth, f"Does anyone mention whether {fourth} works well in real life?", "reviews", "trust_signals", "medium"),
        ("Budget Buyer", first, "Are chargers or required accessories included with every product?", "faq", "faq_coverage", "hard"),
        ("Gift Buyer", first, "What should I know before gifting electronics to someone in another state?", "faq", "faq_coverage", "medium"),
        ("Researcher", first, "Do you have a clear FAQ on holiday delivery cutoffs?", "faq", "faq_coverage", "hard"),
        ("Skeptic", first, "Is there a FAQ explaining return condition requirements?", "faq", "faq_coverage", "medium"),
        ("Impulse Buyer", first, f"Can I quickly compare {first} and {second} from the FAQ?", "comparison", "faq_coverage", "medium"),
    ]
    return [
        PersonaQuery(
            id=f"q{index + 1:02d}",
            persona=persona,
            category=categories[index % len(categories)],
            query=query,
            intent=intent,
            expected_answer_type="specific_store_answer",
            difficulty=difficulty,  # type: ignore[arg-type]
            dimension=dimension,  # type: ignore[arg-type]
        )
        for index, (persona, _product, query, intent, dimension, difficulty) in enumerate(raw_queries)
    ]
