# Contribution Note

Solo build contribution split:

- 45% product thinking: problem framing, Shopify agentic commerce positioning, simulation-over-checklist insight, prompt design, scoring model, demo narrative, documentation.
- 55% engineering: FastAPI pipeline, Shopify crawler contract, Claude service wrappers, deterministic fallbacks, failure detector, score engine, Next.js UI, test coverage, setup docs.

All architecture decisions intentionally preserve the AI/deterministic boundary so APES can be trusted as a diagnostic tool rather than a generic chatbot.
