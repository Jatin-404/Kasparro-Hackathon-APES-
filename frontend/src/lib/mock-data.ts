export const STORE_URL = "hackathon-store.myshopify.com";

export const SCORE_BEFORE = 38;
export const SCORE_AFTER = 71;
export const SCORE_POTENTIAL = 85;

export type DimensionKey = "product" | "policy" | "trust" | "faq";
export interface Dimension {
  key: DimensionKey;
  name: string;
  before: number;
  after: number;
  explanation: string;
  delta: number;
}
export const DIMENSIONS: Dimension[] = [
  { key: "product", name: "Product Clarity",     before: 48, after: 78, delta: 30, explanation: "Vague specs on 14 of 25 products. Titles claim features missing in descriptions." },
  { key: "policy",  name: "Policy Completeness", before: 20, after: 82, delta: 62, explanation: "No return, shipping, or refund policies found across the storefront." },
  { key: "trust",   name: "Trust Signals",       before: 25, after: 64, delta: 39, explanation: "Zero reviews surfaced. Missing warranty, contact, and brand provenance." },
  { key: "faq",     name: "FAQ Coverage",        before: 15, after: 60, delta: 45, explanation: "0 published FAQs. Top shopper questions go unanswered in store data." },
];

export type Classification = "REFUSED" | "VAGUE" | "HALLUCINATED" | "CONFIDENT";
export type Severity = "HIGH" | "MEDIUM" | "LOW";
export type Persona = "Budget Buyer" | "Gift Buyer" | "Researcher" | "Impulse Buyer" | "Skeptic";

export interface Failure {
  id: string;
  persona: Persona;
  query: string;
  response: string;
  fixedResponse: string;
  classification: Classification;
  rootCause: string;
  severity: Severity;
  affects: string;
  scoreDelta: number;
  effort: "LOW" | "MEDIUM" | "HIGH";
  fixTitle: string;
  before: string;
  after: string;
}

export const FAILURES: Failure[] = [
  {
    id: "f1", persona: "Gift Buyer",
    query: "Will this arrive before Christmas?",
    response: "I'm not certain about delivery timelines for this store as no shipping information is available on the product page or anywhere in the store policies.",
    fixedResponse: "Standard shipping arrives in 3–5 business days; expedited options ship same-day if ordered before 2pm ET. Orders placed by Dec 19 arrive before Christmas.",
    classification: "VAGUE", severity: "HIGH",
    rootCause: "Missing shipping policy — no delivery timeline anywhere in store data.",
    affects: "Policy Completeness", scoreDelta: 12, effort: "LOW",
    fixTitle: "Shipping Policy",
    before: "Shipping: Calculated at checkout.",
    after: "Shipping & Delivery: Standard (3–5 business days, free over $50). Expedited (1–2 business days). Orders placed by 2pm ET ship same day. Holiday cutoff: Dec 19 for delivery before Dec 25.",
  },
  {
    id: "f2", persona: "Researcher",
    query: "What's the return window if I buy the wrong size?",
    response: "I cannot find return policy information for this store. I'd recommend contacting the merchant directly before purchasing.",
    fixedResponse: "Returns are accepted within 30 days of delivery for unused items in original packaging. Refunds are issued within 5 business days of receipt.",
    classification: "REFUSED", severity: "HIGH",
    rootCause: "No return policy page exists on the storefront.",
    affects: "Policy Completeness", scoreDelta: 9, effort: "LOW",
    fixTitle: "Return Policy",
    before: "(no return policy published)",
    after: "Returns & Refunds: 30-day window from delivery. Items must be unused in original packaging. Free return label included. Refunds processed within 5 business days.",
  },
  {
    id: "f3", persona: "Skeptic",
    query: "Does the ProSound X1 have active noise cancellation?",
    response: "Yes, the ProSound X1 features active noise cancellation as indicated in the product title.",
    fixedResponse: "The ProSound X1 does not include active noise cancellation. It offers passive isolation via memory-foam tips. For ANC, see the ProSound X1 Pro.",
    classification: "HALLUCINATED", severity: "HIGH",
    rootCause: "Title implies ANC; description and specs do not list it. Agent guessed.",
    affects: "Product Clarity", scoreDelta: 8, effort: "MEDIUM",
    fixTitle: "ProSound X1 — Spec Reconciliation",
    before: "ProSound X1 ANC Wireless Earbuds — premium audio, long battery.",
    after: "ProSound X1 Wireless Earbuds — passive isolation (memory-foam tips), 8h battery, Bluetooth 5.3. Note: ANC is available on the X1 Pro model.",
  },
  {
    id: "f4", persona: "Budget Buyer",
    query: "What's the battery life on the EliteWatch S3?",
    response: "I don't have specific battery life information for the EliteWatch S3 in this store's product data.",
    fixedResponse: "EliteWatch S3 lasts up to 7 days on a single charge with typical use, or 36 hours with continuous GPS tracking enabled.",
    classification: "REFUSED", severity: "MEDIUM",
    rootCause: "Battery specification absent from product description and metafields.",
    affects: "Product Clarity", scoreDelta: 6, effort: "LOW",
    fixTitle: "EliteWatch S3 — Battery Spec",
    before: "EliteWatch S3 — sleek smartwatch with health tracking.",
    after: "EliteWatch S3 — 7-day battery (typical), 36h with always-on GPS. Fast charge: 0–80% in 45 minutes. Health tracking, AMOLED display, 5ATM water resistance.",
  },
  {
    id: "f5", persona: "Impulse Buyer",
    query: "Are there any customer reviews for this?",
    response: "I don't see any customer reviews currently available on the product page.",
    fixedResponse: "This product has 142 verified reviews averaging 4.6/5. Top mentions: sound quality, comfort, fast shipping.",
    classification: "VAGUE", severity: "MEDIUM",
    rootCause: "No review widget installed; zero reviews indexed across all products.",
    affects: "Trust Signals", scoreDelta: 7, effort: "MEDIUM",
    fixTitle: "Enable Verified Reviews",
    before: "(no reviews surfaced)",
    after: "★ 4.6 / 5 — 142 verified reviews. Highlights: \"crystal-clear sound\", \"comfortable for hours\", \"shipped next day\".",
  },
  {
    id: "f6", persona: "Researcher",
    query: "What's the warranty on the AirCore Speaker?",
    response: "I don't have warranty details for this product.",
    fixedResponse: "AirCore Speaker includes a 2-year limited manufacturer warranty covering defects and battery degradation.",
    classification: "REFUSED", severity: "MEDIUM",
    rootCause: "No warranty information in product data or store policies.",
    affects: "Trust Signals", scoreDelta: 5, effort: "LOW",
    fixTitle: "Add Warranty Information",
    before: "(no warranty info)",
    after: "Warranty: 2-year limited manufacturer warranty covers defects and >20% battery degradation. Register at /warranty within 30 days of purchase.",
  },
  {
    id: "f7", persona: "Gift Buyer",
    query: "Do you offer gift wrapping?",
    response: "I cannot confirm whether gift wrapping is available.",
    fixedResponse: "Yes — premium gift wrap is available at checkout for $4.99, with an optional handwritten note.",
    classification: "VAGUE", severity: "LOW",
    rootCause: "Gift options not documented in FAQ or checkout description.",
    affects: "FAQ Coverage", scoreDelta: 3, effort: "LOW",
    fixTitle: "FAQ — Gift Options",
    before: "(no gift wrap info)",
    after: "Gift Options: Premium gift wrap available at checkout ($4.99). Add a free handwritten note. Recipients never see prices.",
  },
  {
    id: "f8", persona: "Budget Buyer",
    query: "Do you offer student or first-time buyer discounts?",
    response: "I don't see any active discount programs mentioned on this store.",
    fixedResponse: "First-time buyers get 10% off with code WELCOME10. Verified students get an additional 15% via SheerID.",
    classification: "REFUSED", severity: "LOW",
    rootCause: "No promotions surfaced in storefront content.",
    affects: "Trust Signals", scoreDelta: 3, effort: "MEDIUM",
    fixTitle: "Surface Active Promotions",
    before: "(no discount info)",
    after: "New customers: 10% off with WELCOME10. Students: 15% off via SheerID verification. Stack savings on first order.",
  },
  {
    id: "f9", persona: "Skeptic",
    query: "Where are these products made and who is the brand?",
    response: "I cannot find brand origin or manufacturer information for the products in this store.",
    fixedResponse: "All products are designed in Brooklyn, NY and manufactured in audited facilities in Vietnam and South Korea. The store is operated by Apex Audio LLC since 2019.",
    classification: "VAGUE", severity: "MEDIUM",
    rootCause: "No brand story or about page indexed.",
    affects: "Trust Signals", scoreDelta: 5, effort: "LOW",
    fixTitle: "About / Brand Page",
    before: "(no brand info)",
    after: "About Apex Audio: Founded 2019 in Brooklyn, NY. Products designed in-house, manufactured in audited facilities in Vietnam and South Korea. SOC2-compliant supply chain.",
  },
  {
    id: "f10", persona: "Impulse Buyer",
    query: "Can I pay with Klarna or Afterpay?",
    response: "I don't have information on the payment methods available at this store.",
    fixedResponse: "We accept Visa, Mastercard, Amex, Apple Pay, Google Pay, Shop Pay, and 4-installment plans via Shop Pay Installments.",
    classification: "REFUSED", severity: "LOW",
    rootCause: "Payment options not documented in FAQ.",
    affects: "FAQ Coverage", scoreDelta: 3, effort: "LOW",
    fixTitle: "Payment Methods FAQ",
    before: "(no payment info)",
    after: "Payment Methods: Visa, Mastercard, Amex, Apple Pay, Google Pay, Shop Pay. Pay over time with Shop Pay Installments (4 interest-free payments).",
  },
  {
    id: "f11", persona: "Researcher",
    query: "Is the LiteBeam Lamp dimmable and what's the color temperature?",
    response: "Specifications for the LiteBeam Lamp are not detailed in the product page.",
    fixedResponse: "LiteBeam Lamp is fully dimmable (1–100%) with adjustable color temperature from 2700K (warm) to 6500K (cool daylight).",
    classification: "VAGUE", severity: "MEDIUM",
    rootCause: "Detailed specs missing from product description.",
    affects: "Product Clarity", scoreDelta: 4, effort: "LOW",
    fixTitle: "LiteBeam — Detailed Specs",
    before: "LiteBeam Lamp — modern desk lighting.",
    after: "LiteBeam Lamp — fully dimmable (1–100%), tunable white 2700K–6500K, 800-lumen max, USB-C powered, 5-year warranty.",
  },
  {
    id: "f12", persona: "Skeptic",
    query: "Has anyone had issues with delivery?",
    response: "There is no review or complaint information available for this store's delivery experience.",
    fixedResponse: "Across 142 verified reviews, 96% rated shipping 4★ or higher. Common feedback: \"arrived faster than expected\".",
    classification: "VAGUE", severity: "LOW",
    rootCause: "No reviews aggregated, no shipping satisfaction signal.",
    affects: "Trust Signals", scoreDelta: 3, effort: "MEDIUM",
    fixTitle: "Shipping Satisfaction Signal",
    before: "(no shipping reviews)",
    after: "Shipping satisfaction: 96% of 142 reviewers rated delivery 4★+. Average delivery: 3.2 business days.",
  },
  {
    id: "f13", persona: "Budget Buyer",
    query: "Do you price match?",
    response: "I do not have any price-matching policy listed for this store.",
    fixedResponse: "Yes — we price-match identical SKUs from authorized retailers within 14 days of purchase. Submit via /pricematch.",
    classification: "REFUSED", severity: "LOW",
    rootCause: "Price-match policy not published.",
    affects: "Policy Completeness", scoreDelta: 3, effort: "LOW",
    fixTitle: "Price Match Policy",
    before: "(no price-match policy)",
    after: "Price Match: We match identical SKUs from authorized retailers within 14 days of your purchase. Submit your request at /pricematch.",
  },
];

export const ACTION_PLAN = [
  { rank: 1, priority: "P1", impact: "HIGH IMPACT",  title: "Publish Return, Refund & Shipping Policies", why: "AI agents refused 4 policy questions. No policy = AI skips recommending your store.", effort: "LOW",    delta: 18, affects: "Policy Completeness, Trust Signals", fixIds: ["f1","f2","f13"] },
  { rank: 2, priority: "P1", impact: "HIGH IMPACT",  title: "Reconcile Product Titles with Descriptions", why: "AI hallucinated features (ANC) when titles claimed specs the description didn't confirm.", effort: "MEDIUM", delta: 12, affects: "Product Clarity", fixIds: ["f3"] },
  { rank: 3, priority: "P2", impact: "MEDIUM IMPACT",title: "Add Battery, Dimming & Detailed Specs",      why: "Two REFUSALs and two VAGUE responses traced to missing spec metafields.", effort: "LOW",    delta: 10, affects: "Product Clarity", fixIds: ["f4","f11"] },
  { rank: 4, priority: "P2", impact: "MEDIUM IMPACT",title: "Enable Verified Customer Reviews",            why: "Zero reviews indexed. AI cannot cite social proof; downgrades store trust.", effort: "MEDIUM", delta: 8,  affects: "Trust Signals", fixIds: ["f5","f12"] },
  { rank: 5, priority: "P3", impact: "MEDIUM IMPACT",title: "Add Brand Story, Warranty & Support Pages",   why: "Skeptic persona refused recommendation due to missing brand provenance.", effort: "LOW",    delta: 6,  affects: "Trust Signals", fixIds: ["f6","f9"] },
  { rank: 6, priority: "P3", impact: "LOW IMPACT",   title: "Publish FAQ — Gifts, Payments, Discounts",    why: "Multiple LOW severity gaps compound into shopper friction.", effort: "LOW",    delta: 4,  affects: "FAQ Coverage", fixIds: ["f7","f8","f10"] },
];

export const PROGRESS_STEPS = [38, 41, 53, 65, 75, 81, 85];
