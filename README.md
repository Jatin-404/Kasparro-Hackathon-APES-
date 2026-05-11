# APES

Agent Perception Evaluation System for Kasparro's AI Commerce Hackathon, Track 5: AI Representation Optimizer.

APES is a merchant-facing diagnostic tool that simulates how AI shopping agents perceive a Shopify store, identifies where and why they fail, generates fixes, and proves the fixes work through re-simulation.

## Demo Target

1. Paste `hackathon-store.myshopify.com`.
2. Watch audit progress.
3. See AI Readiness Score `38/100`.
4. Open Failure Replay and inspect the Christmas delivery failure.
5. Apply the generated shipping policy fix.
6. Re-simulate.
7. See projected score improve to `71/100`.
8. Show ranked action plan: `3 more fixes to reach 85+`.

Demo video link: TBD

## Repo Structure

```text
/
├── backend/          # FastAPI audit pipeline
├── frontend/         # Next.js 14 App Router UI
├── docs/
│   ├── product.md
│   ├── technical.md
│   └── decisions.md
├── screenshots/
├── README.md
└── CONTRIBUTION.md
```

## Backend Setup

Run these from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy backend\.env.example backend\.env
uvicorn backend.app.main:app --reload --port 8000
```

Environment variables:

```text
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6
SHOPIFY_ADMIN_ACCESS_TOKEN=
SHOPIFY_STOREFRONT_ACCESS_TOKEN=
APES_DEMO_LOCK=true
```

The API can run without credentials in demo mode. Live Shopify crawling uses:

```text
https://{store}.myshopify.com/admin/api/2024-01/graphql.json
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

Optional frontend environment:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

If the API is unavailable, the frontend uses a local demo audit result so the flow remains presentable.

## Tests

```powershell
python -m pytest backend\tests -q
```

## Store Crawler Probe

Demo crawler, no Shopify API call:

```powershell
python backend\scripts\crawl_probe.py --demo
```

Live crawler against the hackathon store:

```powershell
python backend\scripts\crawl_probe.py --shop hackathon-store.myshopify.com --out crawl-output.json
```

Required in `backend\.env` for live mode:

```text
SHOPIFY_ADMIN_ACCESS_TOKEN=...
SHOPIFY_STOREFRONT_ACCESS_TOKEN=...
```

## Boundary Summary

Deterministic:

- Store Crawler
- Rule pre-classifier
- Re-simulation orchestration
- Score Engine

AI-powered:

- Persona Engine
- Agent Simulator
- Failure verification
- Forensics Engine
- Fix Generator

See [docs/technical.md](docs/technical.md) for the full architecture and prompt decisions.
