# APES Product Document

## 1. Problem Statement

Merchants are entering a shift where shoppers increasingly ask AI agents what to buy instead of browsing every storefront themselves. Shopify's Agentic Plan describes a future where merchants can surface real-time product data to AI channels such as ChatGPT, Google AI Mode and Gemini, Copilot, Perplexity, and the Shop app, and where brand knowledge can answer questions about returns, shipping, and products in AI conversations. Source: https://www.shopify.com/agentic-plan

That means merchant representation quality becomes the new SEO. A store can have good products and still be invisible or misrepresented if agents cannot confidently answer basic purchase questions. Missing shipping timelines, vague warranties, thin descriptions, absent reviews, and blank FAQs all become conversion blockers because the agent either refuses, hedges, or invents.

APES is built for that moment. It shows merchants not just what data is missing, but how the missing data changes agent behavior and revenue confidence.

## 2. Our Insight

Most audits treat AI readiness as a checklist:

- Description present.
- Policy present.
- Reviews present.
- FAQ present.

That is useful but incomplete. AI agents fail in context. A short product description might be enough for an impulse buyer but not for a researcher comparing specs. A shipping policy might exist but still fail a Gift Buyer asking if an item will arrive before Christmas.

APES uses simulation instead of static validation. We generate customer personas, run realistic queries, classify agent behavior, trace failures to exact content gaps, generate fixes, and re-run the failed queries to prove improvement. The core product promise is proof, not guesswork.

## 3. What We Considered and Rejected

Simple field validator: rejected because it only answers whether fields exist, not whether agents can use them.

Generic SEO audit: rejected because search crawlers and shopping agents fail differently. SEO optimizes pages for ranking; APES optimizes store context for agent answers.

Basic FAQ checker: rejected because FAQs are only one agent input. Products, variants, policies, reviews, collections, and metafields all affect representation.

Merchant chatbot: rejected because the hackathon track is representation optimization, not another chat surface.

Manual content recommendations only: rejected because it does not prove that the agent's answer changes after the fix.

## 4. Core User Journey

1. Merchant enters a Shopify store URL or runs demo mode.
2. APES crawls Shopify Admin data and normalizes it into StoreContext JSON.
3. APES generates persona-led shopping queries across product specs, policies, delivery, comparisons, trust signals, and FAQs.
4. Claude simulates an AI shopping agent using only StoreContext.
5. APES classifies failures as REFUSED, VAGUE, HALLUCINATED, or CONFIDENT_CORRECT.
6. APES explains the exact root cause for each failure.
7. APES generates merchant-ready fixes.
8. APES re-simulates failed queries against fixed content.
9. Merchant sees AI Readiness Score improve from before to after.

The demo journey is optimized around the Christmas delivery failure:

1. Paste `hackathon-store.myshopify.com`.
2. Watch live audit progress.
3. See score `38/100`.
4. Open Failure Replay.
5. See Gift Buyer ask, "Will this arrive before Christmas?"
6. See the agent hedge because shipping timelines are vague.
7. Apply the shipping policy fix.
8. Re-simulate and see the agent answer correctly.
9. Score improves to `71/100`.

## 5. Scope Decisions and Tradeoffs

We prioritized one complete diagnostic loop over breadth. The product must show crawl, simulation, failure, fix, re-simulation, and score movement in one coherent flow.

We used deterministic fallbacks for the demo so the project remains presentable without live Shopify or Claude credentials. The production architecture still has explicit Shopify and Claude integrations.

We kept Supabase out of the first vertical slice because persistence is less important than proving the representation loop. The API models are shaped so audit persistence can be added cleanly.

We made the Failure Replay the most expressive view because judges and merchants need to feel the problem. A score alone is abstract; a failed customer question is concrete.

We intentionally separated deterministic and AI-powered responsibilities in code and docs. This lets merchants trust that scoring is repeatable while still benefiting from AI where language judgment is required.

## 6. What's Next If We Had 30 More Days

Shopify write-back workflow: convert approved fixes into draft product, policy, page, or metaobject updates through Shopify Admin APIs.

Supabase audit history: store every crawl, simulation, fix, and score delta so merchants can track readiness over time.

Competitor and category baselines: show how a merchant compares to similar stores.

Multi-agent simulation: add agent styles for ChatGPT, Perplexity-like research behavior, bargain-hunter agents, and voice-shopping agents.

Merchant approval queue: let teams approve, edit, reject, and assign generated fixes.

Revenue-weighted scoring: weight failures by product margin, inventory, seasonality, and traffic.

Continuous monitoring: re-run APES after catalog changes, policy edits, theme changes, or new review batches.
