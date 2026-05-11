import { DIMENSIONS, FAILURES, SCORE_AFTER, SCORE_BEFORE, type Classification, type Dimension } from "@/lib/mock-data";

export interface AuditResult {
  audit_id: string;
  store_context: {
    store_name: string | null;
    store_url: string;
    products: unknown[];
    faqs: unknown[];
    gaps_detected: Array<{ type: string; description: string; affected_count: number }>;
  };
  score: {
    before_score: number;
    after_score: number;
    delta: number;
    before_dimensions: Array<ApiDimension>;
    after_dimensions: Array<ApiDimension>;
    current_perception?: CurrentPerception | null;
    brand_input?: BrandGapRequest | null;
    gap_analysis?: BrandGapAnalysis | null;
    gap_score?: number | null;
  };
  failures: Array<ApiFailure>;
  failed_queries: number;
  total_queries: number;
  high_impact_fixes: number;
  action_plan: string[];
}

export interface CurrentPerception {
  perception_summary: string;
  perceived_as: string;
  confidence_level: "very low" | "low" | "medium" | "high";
  confidence_reason: string;
  biggest_perception_problems: string[];
}

export interface BrandGapRequest {
  brand_positioning: string;
  brand_adjectives: string[];
  target_customer: string;
  must_get_right: string;
  must_never_say: string;
}

export interface BrandGapAnalysis {
  gap_score: number;
  gap_summary: string;
  aligned_areas: string[];
  misaligned_areas: Array<{
    desired: string;
    current: string;
    caused_by: string;
    fix_priority: "high" | "medium" | "low";
  }>;
  must_never_say_risk: {
    at_risk: boolean;
    reason: string;
  };
  perception_blockers: Array<{
    blocker: string;
    data_needed: string;
    estimated_gap_reduction: number;
  }>;
  if_all_fixed: {
    projected_perception: string;
    projected_gap_score: number;
  };
}

export interface AuditSummary {
  audit_id: string;
  shop_url: string;
  store_name: string | null;
  status: "pending" | "running" | "complete" | "failed" | string;
  before_score: number | null;
  after_score: number | null;
  score_delta: number | null;
  failed_queries: number | null;
  high_impact_fixes: number | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface AuditCompareResult {
  audit_a: AuditCompareSide;
  audit_b: AuditCompareSide;
  delta: {
    score_change: number;
    direction: "improved" | "declined" | "unchanged";
    failed_queries_change: number | null;
    high_findings_change: number | null;
  };
}

export interface AuditCompareSide {
  audit_id: string;
  created_at: string | null;
  before_score: number | null;
  after_score: number | null;
  failed_queries: number | null;
  high_findings: number;
  dimensions: Array<ApiDimension>;
}

export interface ClearTestAuditsResult {
  shop_url: string;
  deleted_count: number;
  kept_audit_id: string | null;
}

export interface AuditProgressEvent {
  type: "progress" | "result" | "error";
  stage?: "crawl" | "personas" | "simulations" | "verification" | "forensics" | "perception" | "fixes" | "resimulation" | "scoring";
  status?: "started" | "running" | "complete";
  message?: string;
  current?: number;
  total?: number;
  result?: AuditResult;
}

export interface ApiDimension {
  dimension: "product_clarity" | "policy_completeness" | "trust_signals" | "faq_coverage";
  label: string;
  score: number;
}

interface ApiFailure {
  query_id: string;
  persona: string;
  query: string;
  response: string;
  classification: string;
  severity: string;
  root_cause: string;
  location: string;
  dimension: ApiDimension["dimension"];
  after_response: string | null;
  after_classification: string | null;
  fix: {
    content_type: string;
    original_content: string | null;
    improved_content: string;
    confidence_improvement_reason: string;
    impact_points: number;
  } | null;
}

const STORAGE_KEY = "apes:lastAudit";
const API_BASE = import.meta.env.VITE_APES_API_BASE_URL || "http://127.0.0.1:8000";

export async function runAudit(storeUrl: string, demoMode: boolean): Promise<AuditResult> {
  const endpoint = demoMode ? `${API_BASE}/audit/demo` : `${API_BASE}/audit`;
  let response: Response;
  try {
    response = demoMode
      ? await fetch(endpoint, { method: "POST" })
      : await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ store_url: storeUrl, demo_mode: false }),
        });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "network request failed";
    throw new Error(`Could not reach APES backend at ${endpoint}: ${reason}`);
  }
  if (!response.ok) {
    throw new Error(`Audit failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function runAuditStream(
  storeUrl: string,
  demoMode: boolean,
  onEvent: (event: AuditProgressEvent) => void,
): Promise<AuditResult> {
  const endpoint = `${API_BASE}/audit/stream`;
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ store_url: storeUrl, demo_mode: demoMode }),
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "network request failed";
    throw new Error(`Could not reach APES backend at ${endpoint}: ${reason}`);
  }
  if (!response.ok) {
    throw new Error(`Streaming audit failed with HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Streaming audit response did not include a readable body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: AuditResult | null = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as AuditProgressEvent;
      onEvent(event);
      if (event.type === "error") {
        throw new Error(event.message || "Streaming audit failed");
      }
      if (event.type === "result" && event.result) {
        finalResult = event.result;
      }
    }

    if (done) break;
  }

  if (!finalResult) {
    throw new Error("Streaming audit ended before returning a final report");
  }
  return finalResult;
}

export async function analyzeBrandGap(auditId: string, payload: BrandGapRequest): Promise<BrandGapAnalysis> {
  const endpoint = `${API_BASE}/api/audit/${auditId}/brand-gap`;
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "network request failed";
    throw new Error(`Could not reach APES backend at ${endpoint}: ${reason}`);
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Brand gap analysis failed with HTTP ${response.status}: ${detail}`);
  }
  return response.json();
}

export async function fetchAuditsByStore(shopUrl: string): Promise<AuditSummary[]> {
  return fetchJson(`${API_BASE}/api/audits?shop_url=${encodeURIComponent(shopUrl)}`, "Audit history");
}

export async function fetchRecentAudits(limit = 20): Promise<AuditSummary[]> {
  return fetchJson(`${API_BASE}/api/audits/recent?limit=${limit}`, "Recent audits");
}

export async function compareAudits(auditA: string, auditB: string): Promise<AuditCompareResult> {
  return fetchJson(
    `${API_BASE}/api/audits/compare?audit_a=${encodeURIComponent(auditA)}&audit_b=${encodeURIComponent(auditB)}`,
    "Audit comparison",
  );
}

export async function fetchSavedAudit(auditId: string): Promise<AuditResult> {
  const saved = await fetchJson<SavedAuditResponse>(`${API_BASE}/api/audit/${encodeURIComponent(auditId)}`, "Saved audit");
  return savedAuditToResult(saved);
}

export async function clearTestAudits(shopUrl: string): Promise<ClearTestAuditsResult> {
  return fetchJson(`${API_BASE}/api/audits/clear-test?shop_url=${encodeURIComponent(shopUrl)}`, "Clear test audits", {
    method: "DELETE",
  });
}

export function saveAudit(result: AuditResult) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
}

export function loadAudit(): AuditResult | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuditResult;
  } catch {
    return null;
  }
}

export function getScores(result: AuditResult | null) {
  if (!result) return { before: SCORE_BEFORE, after: SCORE_AFTER, failedBefore: 13, failedAfter: 4, total: 20 };
  const failedAfter = result.failures.filter((failure) => failure.after_classification !== "CONFIDENT_CORRECT").length;
  return {
    before: result.score.before_score,
    after: result.score.after_score,
    failedBefore: result.failed_queries,
    failedAfter,
    total: result.total_queries,
  };
}

export function getDimensions(result: AuditResult | null): Dimension[] {
  if (!result) return DIMENSIONS;
  return result.score.before_dimensions.map((before) => {
    const after = result.score.after_dimensions.find((item) => item.dimension === before.dimension);
    return {
      key: dimensionKey(before.dimension),
      name: before.label,
      before: before.score,
      after: after?.score ?? before.score,
      delta: (after?.score ?? before.score) - before.score,
      explanation: explanationFor(before.dimension, result),
    };
  });
}

export function getFailures(result: AuditResult | null) {
  if (!result) return FAILURES;
  return result.failures.map((failure, index) => ({
    id: failure.query_id || `f${index + 1}`,
    persona: failure.persona as any,
    query: failure.query,
    response: failure.response,
    fixedResponse: failure.after_response || "Re-simulation has not produced a confident answer yet.",
    classification: normalizeClassification(failure.classification),
    rootCause: failure.root_cause,
    severity: normalizeSeverity(failure.severity),
    affects: labelFor(failure.dimension),
    scoreDelta: failure.fix?.impact_points ?? 0,
    effort: "LOW" as const,
    fixTitle: titleFor(failure),
    before: failure.fix?.original_content || "(missing or unclear content)",
    after: failure.fix?.improved_content || "Merchant input needed.",
  }));
}

function normalizeClassification(value: string): Classification {
  return value === "CONFIDENT_CORRECT" ? "CONFIDENT" : (value as Classification);
}

function normalizeSeverity(value: string) {
  const upper = value.toUpperCase();
  return upper === "HIGH" || upper === "MEDIUM" || upper === "LOW" ? upper : "MEDIUM";
}

function dimensionKey(value: ApiDimension["dimension"]): Dimension["key"] {
  return {
    product_clarity: "product",
    policy_completeness: "policy",
    trust_signals: "trust",
    faq_coverage: "faq",
  }[value] as Dimension["key"];
}

function labelFor(value: ApiDimension["dimension"]) {
  return {
    product_clarity: "Product Clarity",
    policy_completeness: "Policy Completeness",
    trust_signals: "Trust Signals",
    faq_coverage: "FAQ Coverage",
  }[value];
}

function explanationFor(value: ApiDimension["dimension"], result: AuditResult) {
  const gaps = result.store_context.gaps_detected.map((gap) => gap.description).join(" ");
  if (value === "policy_completeness") return "Missing or vague policy content blocks delivery, return, refund, and warranty answers.";
  if (value === "trust_signals") return "Review and rating gaps prevent agents from citing social proof.";
  if (value === "faq_coverage") return result.store_context.faqs.length ? "FAQ coverage exists but still misses key shopper questions." : "No FAQ content was found in the store crawl.";
  return gaps || "Product descriptions and public visibility determine whether agents can answer confidently.";
}

function titleFor(failure: ApiFailure) {
  if (failure.fix?.content_type) return failure.fix.content_type.replace(/\b\w/g, (char) => char.toUpperCase());
  return failure.location.replace("product:", "Product: ").replace("policy:", "Policy: ");
}

async function fetchJson<T>(endpoint: string, label: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint, init);
  } catch (error) {
    const reason = error instanceof Error ? error.message : "network request failed";
    throw new Error(`${label} request failed at ${endpoint}: ${reason}`);
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${label} failed with HTTP ${response.status}: ${detail}`);
  }
  return response.json();
}

interface SavedAuditResponse {
  audit_id: string;
  shop_url: string;
  store_name: string | null;
  status: string;
  failed_queries: number | null;
  total_queries: number | null;
  high_impact_fixes: number | null;
  store_context: {
    store_data?: AuditResult["store_context"];
    gaps_detected?: AuditResult["store_context"]["gaps_detected"];
  } | null;
  simulations: Array<Record<string, any>>;
  findings: Array<Record<string, any>>;
  fixes: Array<Record<string, any>>;
  score: AuditResult["score"] & { action_plan?: string[] };
  action_plan?: string[];
}

function savedAuditToResult(saved: SavedAuditResponse): AuditResult {
  const storeData = saved.store_context?.store_data;
  const findingsByQuery = new Map(saved.findings.map((finding) => [finding.query_id, finding]));
  const fixesByQuery = new Map(saved.fixes.map((fix) => [fix.query_id, fix]));
  const failures = saved.simulations
    .filter((simulation) => simulation.classification && simulation.classification !== "CONFIDENT_CORRECT")
    .map((simulation, index) => {
      const finding = findingsByQuery.get(simulation.query_id) || {};
      const fix = fixesByQuery.get(simulation.query_id);
      return {
        query_id: simulation.query_id || `q${index + 1}`,
        persona: simulation.persona || "Shopper",
        query: simulation.query || "",
        response: simulation.response || "",
        classification: simulation.classification || "VAGUE",
        severity: finding.severity || simulation.severity || "medium",
        root_cause: finding.specific_issue || "Saved audit issue",
        location: finding.location || "store",
        dimension: simulation.dimension || "product_clarity",
        after_response: simulation.after_response || null,
        after_classification: simulation.after_classification || null,
        fix: fix
          ? {
              content_type: fix.content_type || "content",
              original_content: fix.original_content || null,
              improved_content: fix.improved_content || "Merchant input needed.",
              confidence_improvement_reason: fix.confidence_improvement_reason || "",
              impact_points: fix.impact_points || 0,
            }
          : null,
      } as ApiFailure;
    });
  return {
    audit_id: saved.audit_id,
    store_context: {
      store_name: storeData?.store_name ?? saved.store_name,
      store_url: storeData?.store_url ?? saved.shop_url,
      products: storeData?.products ?? [],
      faqs: storeData?.faqs ?? [],
      gaps_detected: storeData?.gaps_detected ?? saved.store_context?.gaps_detected ?? [],
    },
    score: saved.score,
    failures,
    failed_queries: saved.failed_queries ?? failures.length,
    total_queries: saved.total_queries ?? saved.simulations.length,
    high_impact_fixes: saved.high_impact_fixes ?? saved.fixes.length,
    action_plan: saved.action_plan ?? saved.score?.action_plan ?? [],
  };
}
