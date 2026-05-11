import { CountUp } from "./CountUp";
import { scoreBarColor, scoreLabel, scorePillClass } from "@/lib/score";

interface Props {
  title: string;
  score: number;
  delta?: number;
  explanation: string;
  trigger?: number | string;
  delay?: number;
}
export function ScoreCard({ title, score, delta = 0, explanation, trigger, delay = 0 }: Props) {
  return (
    <div
      className="surface-card group relative overflow-hidden p-5 animate-fade-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="label-tiny">{title}</div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <CountUp to={score} trigger={trigger} className="font-mono text-4xl font-semibold tracking-tight" />
            <span className="font-mono text-xs text-muted-foreground">/100</span>
          </div>
        </div>
        <span className={scorePillClass(score)}>{scoreLabel(score)}</span>
      </div>

      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          key={`${trigger}-${score}`}
          className="h-full animate-bar rounded-full"
          style={{ width: `${score}%`, background: scoreBarColor(score) }}
        />
      </div>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{explanation}</p>

      {delta > 0 && (
        <div className="mt-3 hidden text-xs font-medium text-success group-hover:block">
          +{delta} points available with fixes
        </div>
      )}
    </div>
  );
}
