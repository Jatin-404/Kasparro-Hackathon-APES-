"""Analyze mismatch between current AI perception and desired brand representation."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.models import BrandGapAnalysis, BrandGapRequest, CurrentPerception
from backend.app.services.claude_client import ClaudeClient
from backend.app.services.json_utils import extract_json_object

logger = logging.getLogger(__name__)

BRAND_GAP_SYSTEM_PROMPT = """You analyze Shopify brand representation gaps for merchants.
Compare the current AI-agent perception against the merchant's desired representation.
Use only the supplied evidence. Return strict JSON only."""


class BrandGapEngine:
    """Generate structured brand gap analysis."""

    def __init__(self, claude: ClaudeClient | None = None) -> None:
        self.claude = claude or ClaudeClient()

    async def analyze(
        self,
        current_perception: CurrentPerception,
        request: BrandGapRequest,
        gaps_detected: list[dict[str, Any]],
    ) -> BrandGapAnalysis:
        """Compare desired representation with current AI perception."""

        if self.claude.is_configured:
            try:
                text = await self.claude.complete_json(
                    BRAND_GAP_SYSTEM_PROMPT,
                    build_brand_gap_prompt(current_perception, request, gaps_detected),
                    max_tokens=1100,
                )
                analysis = normalize_brand_gap(extract_json_object(text))
                return calibrate_brand_gap(analysis, current_perception, request, gaps_detected)
            except Exception as exc:
                logger.warning("Brand gap analysis fell back to deterministic analysis: %s", exc)
        return deterministic_brand_gap(current_perception, request, gaps_detected)


def build_brand_gap_prompt(
    current_perception: CurrentPerception,
    request: BrandGapRequest,
    gaps_detected: list[dict[str, Any]],
) -> str:
    gaps_text = "\n".join(format_gap(gap) for gap in gaps_detected[:12]) or "- No structured gaps were found."
    return f"""CURRENT AI PERCEPTION:
{current_perception.perception_summary}
Confidence level: {current_perception.confidence_level}
Biggest problems: {", ".join(current_perception.biggest_perception_problems)}

MERCHANT'S DESIRED REPRESENTATION:
Positioning: {request.brand_positioning}
Brand adjectives: {", ".join(request.brand_adjectives)}
Target customer: {request.target_customer}
Must always get right: {request.must_get_right}
Must never say: {request.must_never_say}

Known data gaps causing failures:
{gaps_text}

Analyze the gap between current and desired perception. Be specific about which exact data gaps are causing the mismatch.
IMPORTANT gap_score scale:
- 1-2: Store already matches the desired perception.
- 3-4: Minor gaps, mostly aligned.
- 5-6: Moderate mismatch, several fixes needed.
- 7-8: Major mismatch, significant gaps.
- 9-10: Completely opposite to desired perception.

Higher gap_score means WORSE alignment. Lower gap_score means BETTER alignment.
If the merchant wants premium, reliable, trustworthy, or expert representation, but current AI perception says
the store has incomplete information, low confidence, no policies, no reviews, or vague product details, return
gap_score as 8 or 9 because the merchant's desired perception is almost completely opposite to how the store is
currently perceived.

For this store pattern, return gap_score as 8 or 9 when the merchant's desired perception (premium, reliable,
trustworthy, expert) is almost completely opposite to how the store is currently perceived (incomplete, low
confidence, no policies).

if_all_fixed.projected_gap_score must be LOWER than gap_score because fixes close the gap.

Return JSON only:
{{
  "gap_score": 8,
  "gap_summary": "string",
  "aligned_areas": ["string"],
  "misaligned_areas": [
    {{
      "desired": "string",
      "current": "string",
      "caused_by": "string",
      "fix_priority": "high"
    }}
  ],
  "must_never_say_risk": {{
    "at_risk": true,
    "reason": "string"
  }},
  "perception_blockers": [
    {{
      "blocker": "string",
      "data_needed": "string",
      "estimated_gap_reduction": 2
    }}
  ],
  "if_all_fixed": {{
    "projected_perception": "string",
    "projected_gap_score": 2
  }}
}}"""


def deterministic_brand_gap(
    current_perception: CurrentPerception,
    request: BrandGapRequest,
    gaps_detected: list[dict[str, Any]],
) -> BrandGapAnalysis:
    """Local fallback that still returns useful product output."""

    gap_score = score_for_confidence(current_perception.confidence_level, len(gaps_detected))
    top_gaps = gaps_detected[:3]
    blockers = [
        {
            "blocker": gap.get("description") or gap.get("message") or "Missing AI-readable store evidence",
            "data_needed": data_needed_for_gap(gap),
            "estimated_gap_reduction": max(1, min(3, 4 - index)),
        }
        for index, gap in enumerate(top_gaps, start=1)
    ]
    if not blockers:
        blockers = [
            {
                "blocker": "Desired positioning is not explicitly stated in store content.",
                "data_needed": "Add homepage, FAQ, and product copy that states the desired brand positioning.",
                "estimated_gap_reduction": 2,
            }
        ]
    must_risk = bool(request.must_never_say) and any(
        keyword in current_perception.perception_summary.lower()
        for keyword in ["uncertain", "incomplete", "missing", "low confidence", "unclear"]
    )
    misaligned = [
        {
            "desired": request.brand_positioning,
            "current": current_perception.perceived_as,
            "caused_by": blockers[0]["blocker"],
            "fix_priority": "high" if gap_score >= 7 else "medium",
        },
        {
            "desired": f"AI should see the brand as {', '.join(request.brand_adjectives[:5])}.",
            "current": current_perception.confidence_reason,
            "caused_by": blockers[min(1, len(blockers) - 1)]["blocker"],
            "fix_priority": "medium",
        },
    ]
    if request.must_get_right:
        misaligned.append(
            {
                "desired": request.must_get_right,
                "current": "Current store evidence may not make this claim explicit enough for AI agents.",
                "caused_by": blockers[min(2, len(blockers) - 1)]["blocker"],
                "fix_priority": "high",
            }
        )
    projected_gap = max(1, gap_score - sum(item["estimated_gap_reduction"] for item in blockers))
    analysis = normalize_brand_gap(
        {
            "gap_score": gap_score,
            "gap_summary": (
                f"The store wants to be represented as {request.brand_positioning}, but AI agents currently see it as "
                f"{current_perception.perceived_as} with {current_perception.confidence_level} confidence. The gap is "
                "mainly caused by missing or ambiguous data that prevents agents from proving the desired positioning."
            ),
            "aligned_areas": [
                f"The catalog can support the target customer segment: {request.target_customer}.",
                "The audit has enough product and policy evidence to identify concrete fixes.",
            ],
            "misaligned_areas": misaligned,
            "must_never_say_risk": {
                "at_risk": must_risk,
                "reason": (
                    "The current perception already contains uncertainty or incomplete-data language that overlaps with the merchant's feared perception."
                    if must_risk
                    else "The feared perception is not directly present, but missing evidence could still let agents imply it."
                ),
            },
            "perception_blockers": blockers,
            "if_all_fixed": {
                "projected_perception": (
                    f"AI agents would be more likely to describe the store as {request.brand_positioning}, "
                    f"especially for {request.target_customer.lower()}."
                ),
                "projected_gap_score": projected_gap,
            },
        }
    )
    return calibrate_brand_gap(analysis, current_perception, request, gaps_detected)


def normalize_brand_gap(value: dict[str, Any]) -> BrandGapAnalysis:
    """Coerce model JSON into the exact API schema."""

    value["gap_score"] = clamp_int(value.get("gap_score"), 1, 10, 7)
    value["gap_summary"] = str(value.get("gap_summary") or "Current and desired perception are misaligned.")
    value["aligned_areas"] = normalize_string_list(value.get("aligned_areas"), ["Some catalog evidence supports the desired positioning."])
    value["misaligned_areas"] = [
        {
            "desired": str(item.get("desired") or "Desired brand positioning"),
            "current": str(item.get("current") or "Current AI perception is less confident."),
            "caused_by": str(item.get("caused_by") or "Missing or ambiguous store data."),
            "fix_priority": normalize_priority(item.get("fix_priority")),
        }
        for item in normalize_dict_list(value.get("misaligned_areas"))
    ] or [
        {
            "desired": "Desired brand positioning",
            "current": "Current AI perception is incomplete.",
            "caused_by": "Missing or ambiguous store data.",
            "fix_priority": "high",
        }
    ]
    risk = value.get("must_never_say_risk") if isinstance(value.get("must_never_say_risk"), dict) else {}
    value["must_never_say_risk"] = {
        "at_risk": bool(risk.get("at_risk", False)),
        "reason": str(risk.get("reason") or "Risk depends on whether missing evidence is fixed."),
    }
    value["perception_blockers"] = [
        {
            "blocker": str(item.get("blocker") or "Missing AI-readable evidence"),
            "data_needed": str(item.get("data_needed") or "Add clear product, policy, FAQ, or trust-signal data."),
            "estimated_gap_reduction": clamp_int(item.get("estimated_gap_reduction"), 1, 10, 1),
        }
        for item in normalize_dict_list(value.get("perception_blockers"))
    ] or [
        {
            "blocker": "Missing AI-readable evidence",
            "data_needed": "Add clear product, policy, FAQ, or trust-signal data.",
            "estimated_gap_reduction": 1,
        }
    ]
    projected = value.get("if_all_fixed") if isinstance(value.get("if_all_fixed"), dict) else {}
    value["if_all_fixed"] = {
        "projected_perception": str(projected.get("projected_perception") or "AI agents would describe the store more confidently after fixes."),
        "projected_gap_score": clamp_int(projected.get("projected_gap_score"), 1, 10, max(1, value["gap_score"] - 3)),
    }
    if value["if_all_fixed"]["projected_gap_score"] >= value["gap_score"]:
        value["if_all_fixed"]["projected_gap_score"] = max(1, value["gap_score"] - 5)
    return BrandGapAnalysis.model_validate(value)


def calibrate_brand_gap(
    analysis: BrandGapAnalysis,
    current_perception: CurrentPerception,
    request: BrandGapRequest,
    gaps_detected: list[dict[str, Any]],
) -> BrandGapAnalysis:
    """Correct inverted model scores and enforce that fixes reduce the gap."""

    data = analysis.model_dump(mode="json")
    minimum_score = minimum_gap_score(current_perception, request, gaps_detected)
    data["gap_score"] = max(data["gap_score"], minimum_score)
    if data["if_all_fixed"]["projected_gap_score"] >= data["gap_score"]:
        data["if_all_fixed"]["projected_gap_score"] = max(1, data["gap_score"] - 5)
    return BrandGapAnalysis.model_validate(data)


def minimum_gap_score(
    current_perception: CurrentPerception,
    request: BrandGapRequest,
    gaps_detected: list[dict[str, Any]],
) -> int:
    """Infer a score floor from concrete evidence so the scale cannot invert."""

    desired_text = " ".join(
        [
            request.brand_positioning,
            " ".join(request.brand_adjectives),
            request.must_get_right,
            request.must_never_say,
        ]
    ).lower()
    current_text = " ".join(
        [
            current_perception.perception_summary,
            current_perception.perceived_as,
            current_perception.confidence_level,
            current_perception.confidence_reason,
            " ".join(current_perception.biggest_perception_problems),
            " ".join(format_gap(gap) for gap in gaps_detected),
        ]
    ).lower()
    desired_strength = sum(
        token in desired_text
        for token in [
            "premium",
            "reliable",
            "trustworthy",
            "expert",
            "fast shipping",
            "return",
            "support",
            "transparent",
        ]
    )
    evidence_gaps = sum(
        token in current_text
        for token in [
            "no return",
            "missing_policy",
            "no shipping",
            "no refund",
            "no reviews",
            "zero reviews",
            "vague",
            "incomplete",
            "low confidence",
            "very low",
        ]
    )
    if desired_strength >= 4 and evidence_gaps >= 4:
        return 9
    if desired_strength >= 3 and evidence_gaps >= 3:
        return 8
    if desired_strength >= 2 and evidence_gaps >= 2:
        return 7
    return 1


def format_gap(gap: dict[str, Any]) -> str:
    return f"- {gap.get('type') or gap.get('field') or gap.get('location')}: {gap.get('description') or gap.get('message') or gap}"


def data_needed_for_gap(gap: dict[str, Any]) -> str:
    gap_type = str(gap.get("type") or gap.get("field") or "").lower()
    if "policy" in gap_type or "shipping" in gap_type or "refund" in gap_type:
        return "Publish precise shipping, refund, return, or warranty policy language."
    if "review" in gap_type:
        return "Collect and expose verified reviews or ratings."
    if "faq" in gap_type:
        return "Add FAQ answers covering the buyer questions agents failed on."
    return "Add specific product specs, compatibility, images, or structured details."


def score_for_confidence(confidence: str, gap_count: int) -> int:
    base = {"very low": 9, "low": 7, "medium": 5, "high": 3}.get(confidence, 7)
    return max(1, min(10, base + min(2, gap_count // 4)))


def clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        return max(minimum, min(maximum, int(round(float(value)))))
    except (TypeError, ValueError):
        return fallback


def normalize_priority(value: Any) -> str:
    text = str(value or "").lower()
    return text if text in {"high", "medium", "low"} else "medium"


def normalize_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or fallback
    return fallback


def normalize_dict_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []
