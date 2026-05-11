# APES Decisions

## Simulation Over Checklist

APES evaluates whether agents can answer realistic shopping questions, not just whether fields exist. This better matches agentic commerce, where buyer intent and context determine whether data is usable.

## Deterministic Score Engine

The score is deterministic so merchants can trust before/after movement. AI can generate and verify language, but it does not directly assign the final score.

## Demo Fallbacks

The backend and frontend both include deterministic demo paths. This protects the hackathon demo from credential, network, or provider availability issues while preserving the production integration shape.

## Failure Replay As The Centerpiece

The most important screen is the failure replay. It turns a score into a story: customer asks, agent fails, APES explains why, fix proves improvement.
