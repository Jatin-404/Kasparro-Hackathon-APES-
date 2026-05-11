export function scoreColor(score: number) {
  if (score < 40) return "danger";
  if (score < 70) return "warning";
  return "success";
}
export function scoreLabel(score: number) {
  if (score < 40) return "CRITICAL";
  if (score < 70) return "NEEDS WORK";
  return "STRONG";
}
export function scorePillClass(score: number) {
  const c = scoreColor(score);
  return `pill pill-${c}`;
}
export function scoreBarColor(score: number) {
  if (score < 40) return "var(--danger)";
  if (score < 70) return "var(--warning)";
  return "var(--success)";
}
