"""Deterministic demo fixtures for the APES hackathon walkthrough."""

from __future__ import annotations

from backend.app.models import (
    Collection,
    FAQ,
    ForensicFinding,
    PersonaQuery,
    Policies,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    StoreContext,
    StoreGap,
    StorePage,
)


def build_demo_store_context(store_url: str = "hackathon-store.myshopify.com") -> StoreContext:
    """Create a seeded electronics store with intentional gaps for the demo path."""

    products = [
        Product(
            id="gid://shopify/Product/1001",
            title="NovaSound Pro Headphones",
            description=(
                "Wireless over-ear headphones with active noise cancellation, "
                "40-hour battery life, USB-C charging, and Bluetooth 5.3."
            ),
            variants=[
                ProductVariant(
                    id="gid://shopify/ProductVariant/1001-1",
                    title="Matte Black",
                    price="149.00",
                    currency="USD",
                    sku="NSP-BLK",
                    inventory_quantity=18,
                    available_for_sale=True,
                    options={"Color": "Matte Black"},
                )
            ],
            images=[
                ProductImage(
                    url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
                    alt_text="Black wireless headphones on a desk",
                )
            ],
            metafields={
                "battery_life": "40 hours",
                "connectivity": "Bluetooth 5.3",
                "noise_cancellation": "Hybrid ANC",
            },
            reviews=[
                Review(author="Maya", rating=4.8, body="Clear calls and strong battery life."),
                Review(author="Dev", rating=4.7, body="Great noise cancellation for commuting."),
            ],
            tags=["audio", "headphones", "giftable"],
        ),
        Product(
            id="gid://shopify/Product/1002",
            title="ChargeStack 3-in-1 Dock",
            description="Compact wireless charging dock for phone, earbuds, and watch.",
            variants=[
                ProductVariant(
                    id="gid://shopify/ProductVariant/1002-1",
                    title="White",
                    price="79.00",
                    currency="USD",
                    sku="CSD-WHT",
                    inventory_quantity=22,
                    available_for_sale=True,
                    options={"Color": "White"},
                )
            ],
            images=[
                ProductImage(
                    url="https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5",
                    alt_text=None,
                )
            ],
            metafields={"compatibility": None, "wattage": "15W phone charging"},
            reviews=[],
            tags=["charging", "desk", "giftable"],
        ),
        Product(
            id="gid://shopify/Product/1003",
            title="PixelBeam Mini Projector",
            description=None,
            variants=[
                ProductVariant(
                    id="gid://shopify/ProductVariant/1003-1",
                    title="Standard",
                    price="229.00",
                    currency="USD",
                    sku="PBM-STD",
                    inventory_quantity=6,
                    available_for_sale=True,
                    options={"Resolution": None},
                )
            ],
            images=[],
            metafields={"lumens": None, "throw_distance": None, "warranty": None},
            reviews=[],
            tags=["projector", "home theater"],
        ),
        Product(
            id="gid://shopify/Product/1004",
            title="HomeHub Mesh Router Duo",
            description="Two-pack Wi-Fi mesh system for apartments and small homes.",
            variants=[
                ProductVariant(
                    id="gid://shopify/ProductVariant/1004-1",
                    title="Two Pack",
                    price="189.00",
                    currency="USD",
                    sku="HHM-2PK",
                    inventory_quantity=11,
                    available_for_sale=True,
                    options={"Pack": "2"},
                )
            ],
            metafields={"coverage": "Up to 4,000 sq ft", "speed": None, "security": None},
            reviews=[Review(author="Ari", rating=4.5, body="Simple setup for a two-bedroom flat.")],
            tags=["networking", "router"],
        ),
        Product(
            id="gid://shopify/Product/1005",
            title="DeskGlow Monitor Light Bar",
            description="USB-powered monitor light bar with dimming and warm/cool controls.",
            variants=[
                ProductVariant(
                    id="gid://shopify/ProductVariant/1005-1",
                    title="Graphite",
                    price="59.00",
                    currency="USD",
                    sku="DGL-GRF",
                    inventory_quantity=30,
                    available_for_sale=True,
                    options={"Color": "Graphite"},
                )
            ],
            metafields={"desk_compatibility": "Fits monitors 0.4 to 1.2 inches thick"},
            reviews=[Review(author="Nina", rating=4.6, body="Reduced glare during late work.")],
            tags=["lighting", "office"],
        ),
    ]
    gaps = [
        StoreGap(
            location="policy:shipping",
            field="delivery_timeline",
            message="Shipping policy does not state cutoff dates or delivery windows.",
            severity="high",
        ),
        StoreGap(
            location="product:gid://shopify/Product/1003",
            field="description",
            message="Projector description is missing.",
            severity="high",
        ),
        StoreGap(
            location="product:gid://shopify/Product/1002",
            field="reviews",
            message="Charging dock has no reviews.",
            severity="medium",
        ),
        StoreGap(
            location="faq",
            field="holiday_delivery",
            message="FAQ does not answer holiday delivery questions.",
            severity="high",
        ),
    ]
    return StoreContext(
        store_name="APES Hackathon Electronics",
        store_url=store_url,
        products=products,
        policies=Policies(
            return_policy="Returns are accepted on eligible electronics.",
            shipping="We ship orders as quickly as possible. Delivery timing can vary by destination.",
            refund="Refunds are processed after returned items are inspected.",
            warranty=None,
        ),
        faqs=[
            FAQ(question="Do you ship internationally?", answer="We currently ship within the United States."),
            FAQ(question="Can I return opened electronics?", answer="Opened items may be returned if complete."),
            FAQ(question="Are chargers included?", answer=None),
        ],
        pages=[
            StorePage(
                id="demo-page-faq",
                title="FAQ",
                handle="faq",
                body="Do you ship internationally? We currently ship within the United States.\nCan I return opened electronics? Opened items may be returned if complete.\nAre chargers included?",
                source="demo",
            )
        ],
        collections=[
            Collection(
                name="Giftable Electronics",
                products=["gid://shopify/Product/1001", "gid://shopify/Product/1002", "gid://shopify/Product/1005"],
            ),
            Collection(
                name="Home Office",
                products=["gid://shopify/Product/1004", "gid://shopify/Product/1005"],
            ),
        ],
        gaps=gaps,
    )


def build_demo_queries() -> list[PersonaQuery]:
    """Return 20 tagged persona queries arranged for the target demo score math."""

    raw_queries = [
        (
            "q01",
            "Budget Buyer",
            "Will the NovaSound Pro give me enough battery life for a full week of commuting?",
            "product_specs",
            "product_clarity",
            "CONFIDENT_CORRECT",
        ),
        (
            "q02",
            "Researcher",
            "How bright is the PixelBeam Mini Projector, and what resolution does it support?",
            "product_specs",
            "product_clarity",
            "REFUSED",
        ),
        (
            "q03",
            "Skeptic",
            "Does the mesh router include any security features or only basic Wi-Fi?",
            "product_specs",
            "product_clarity",
            "VAGUE",
        ),
        (
            "q04",
            "Gift Buyer",
            "Which charging dock color and compatibility details should I know before buying it as a gift?",
            "product_specs",
            "product_clarity",
            "VAGUE",
        ),
        (
            "q05",
            "Impulse Buyer",
            "Can the DeskGlow light bar fit a normal monitor without extra accessories?",
            "product_specs",
            "product_clarity",
            "HALLUCINATED",
        ),
        (
            "q06",
            "Gift Buyer",
            "Will this arrive before Christmas?",
            "delivery",
            "policy_completeness",
            "VAGUE",
        ),
        (
            "q07",
            "Budget Buyer",
            "If I return opened headphones, how long does the refund take?",
            "returns",
            "policy_completeness",
            "VAGUE",
        ),
        (
            "q08",
            "Skeptic",
            "Is there a warranty for the projector if it fails after a month?",
            "warranty",
            "policy_completeness",
            "REFUSED",
        ),
        (
            "q09",
            "Researcher",
            "Do you ship outside the United States?",
            "shipping",
            "policy_completeness",
            "CONFIDENT_CORRECT",
        ),
        (
            "q10",
            "Impulse Buyer",
            "Can I get expedited shipping if I order today?",
            "delivery",
            "policy_completeness",
            "HALLUCINATED",
        ),
        (
            "q11",
            "Skeptic",
            "Do real buyers say the headphones are good for calls?",
            "reviews",
            "trust_signals",
            "CONFIDENT_CORRECT",
        ),
        (
            "q12",
            "Researcher",
            "Are there reviews proving the ChargeStack dock works reliably?",
            "reviews",
            "trust_signals",
            "VAGUE",
        ),
        (
            "q13",
            "Gift Buyer",
            "Which item has the strongest social proof for a holiday gift?",
            "comparison",
            "trust_signals",
            "CONFIDENT_CORRECT",
        ),
        (
            "q14",
            "Budget Buyer",
            "Can I trust the projector quality without any reviews?",
            "reviews",
            "trust_signals",
            "REFUSED",
        ),
        (
            "q15",
            "Impulse Buyer",
            "Does anyone mention the monitor light reducing glare?",
            "reviews",
            "trust_signals",
            "CONFIDENT_CORRECT",
        ),
        (
            "q16",
            "Budget Buyer",
            "Are chargers included with every product?",
            "faq",
            "faq_coverage",
            "VAGUE",
        ),
        (
            "q17",
            "Gift Buyer",
            "What should I know before gifting electronics to someone in another state?",
            "faq",
            "faq_coverage",
            "CONFIDENT_CORRECT",
        ),
        (
            "q18",
            "Researcher",
            "Do you have a clear FAQ on holiday delivery cutoffs?",
            "faq",
            "faq_coverage",
            "REFUSED",
        ),
        (
            "q19",
            "Skeptic",
            "Is there a FAQ explaining return condition requirements?",
            "faq",
            "faq_coverage",
            "CONFIDENT_CORRECT",
        ),
        (
            "q20",
            "Impulse Buyer",
            "Can I quickly compare the headphones and charger from the FAQ?",
            "comparison",
            "faq_coverage",
            "CONFIDENT_CORRECT",
        ),
    ]
    return [
        PersonaQuery(
            id=query_id,
            persona=persona,
            category="electronics",
            query=query,
            intent=intent,
            expected_answer_type="specific_store_answer",
            difficulty="medium" if index < 15 else "hard",
            dimension=dimension,  # type: ignore[arg-type]
        )
        for index, (query_id, persona, query, intent, dimension, _classification) in enumerate(raw_queries)
    ]


def demo_expected_classification(query_id: str, fixed_context: bool = False) -> str:
    """Return the scripted classification used to guarantee the hackathon demo arc."""

    before = {
        "q01": "CONFIDENT_CORRECT",
        "q02": "REFUSED",
        "q03": "VAGUE",
        "q04": "VAGUE",
        "q05": "HALLUCINATED",
        "q06": "VAGUE",
        "q07": "VAGUE",
        "q08": "REFUSED",
        "q09": "CONFIDENT_CORRECT",
        "q10": "HALLUCINATED",
        "q11": "CONFIDENT_CORRECT",
        "q12": "VAGUE",
        "q13": "CONFIDENT_CORRECT",
        "q14": "REFUSED",
        "q15": "CONFIDENT_CORRECT",
        "q16": "VAGUE",
        "q17": "CONFIDENT_CORRECT",
        "q18": "REFUSED",
        "q19": "CONFIDENT_CORRECT",
        "q20": "CONFIDENT_CORRECT",
    }
    after = {
        **before,
        "q06": "CONFIDENT_CORRECT",
        "q07": "CONFIDENT_CORRECT",
        "q08": "CONFIDENT_CORRECT",
        "q12": "CONFIDENT_CORRECT",
        "q14": "CONFIDENT_CORRECT",
        "q16": "CONFIDENT_CORRECT",
        "q18": "CONFIDENT_CORRECT",
    }
    return after[query_id] if fixed_context else before[query_id]


def demo_response_for_query(query: PersonaQuery, fixed_context: bool = False) -> str:
    """Produce a human-readable agent response that matches the scripted classification."""

    classification = demo_expected_classification(query.id, fixed_context)
    if fixed_context and query.id == "q06":
        return (
            "Yes. The updated shipping policy states that orders placed by December 18 "
            "ship within 1 business day and are expected to arrive before Christmas "
            "for continental U.S. addresses using standard shipping."
        )
    if classification == "CONFIDENT_CORRECT":
        return _confident_demo_response(query.id)
    if classification == "REFUSED":
        return "I don't know from the store data provided. I can't find enough information to answer that confidently."
    if classification == "VAGUE":
        return "I'm not certain from this store data; it might be possible, but the store does not give a specific enough answer."
    return "Yes, this store offers a confirmed answer with exact details, even though that detail is not present in the store data."


def _confident_demo_response(query_id: str) -> str:
    """Map successful demo queries to specific answers grounded in the store context."""

    responses = {
        "q01": "Yes. NovaSound Pro lists 40-hour battery life, which should cover a typical week of commuting.",
        "q09": "The FAQ says the store currently ships within the United States.",
        "q11": "Yes. A review mentions clear calls and strong battery life for the NovaSound Pro headphones.",
        "q13": "NovaSound Pro has the strongest social proof here, with two positive reviews and giftable tags.",
        "q15": "Yes. A DeskGlow review says it reduced glare during late work.",
        "q17": "The store ships within the United States, so gifting to another U.S. state is supported by the FAQ.",
        "q19": "Yes. The FAQ says opened items may be returned if complete.",
        "q20": "The FAQ does not compare them directly, but product data covers headphones and charger basics.",
    }
    return responses.get(query_id, "The store data provides enough detail to answer this confidently.")


def demo_forensic_finding(query: PersonaQuery) -> ForensicFinding:
    """Create a specific root cause for a failed demo query."""

    issue_map = {
        "q02": (
            "missing_field",
            "Projector lumens, resolution, and description are missing.",
            "product:gid://shopify/Product/1003",
            "high",
        ),
        "q03": ("missing_field", "Router security and speed details are incomplete.", "product:gid://shopify/Product/1004", "medium"),
        "q04": ("ambiguous_content", "Charging dock compatibility is not specific enough for gift confidence.", "product:gid://shopify/Product/1002", "medium"),
        "q05": ("ambiguous_content", "Desk compatibility exists but accessory requirements are not explicit.", "product:gid://shopify/Product/1005", "low"),
        "q06": ("policy_gap", "No shipping cutoff date or delivery window exists for Christmas delivery.", "policy:shipping", "high"),
        "q07": ("policy_gap", "Refund timing after return inspection is not stated.", "policy:refund", "medium"),
        "q08": ("policy_gap", "Warranty terms are missing for electronics.", "policy:warranty", "high"),
        "q10": ("policy_gap", "Expedited shipping availability is not stated.", "policy:shipping", "medium"),
        "q12": ("no_reviews", "ChargeStack has no reviews or reliability proof.", "product:gid://shopify/Product/1002", "medium"),
        "q14": ("no_reviews", "PixelBeam projector has no reviews to establish trust.", "product:gid://shopify/Product/1003", "medium"),
        "q16": ("missing_field", "FAQ answer about included chargers is blank.", "faq", "medium"),
        "q18": ("policy_gap", "FAQ does not cover holiday shipping cutoffs.", "faq", "high"),
    }
    gap_type, issue, location, severity = issue_map[query.id]
    return ForensicFinding(
        query_id=query.id,
        gap_type=gap_type,  # type: ignore[arg-type]
        specific_issue=issue,
        location=location,
        severity=severity,  # type: ignore[arg-type]
        impact_on_conversion="The agent cannot give a confident buying answer, so a motivated shopper may leave.",
    )
