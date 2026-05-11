import { useEffect, useRef, useState } from "react";

export function CountUp({
  to,
  duration = 1400,
  className,
  suffix = "",
  trigger = 0,
}: { to: number; duration?: number; className?: string; suffix?: string; trigger?: number | string }) {
  const [val, setVal] = useState(0);
  const startRef = useRef<number | null>(null);
  const fromRef = useRef(0);

  useEffect(() => {
    fromRef.current = val;
    startRef.current = null;
    let raf = 0;
    const tick = (t: number) => {
      if (startRef.current === null) startRef.current = t;
      const p = Math.min(1, (t - startRef.current) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(fromRef.current + (to - fromRef.current) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [to, trigger]);

  return <span className={className}>{val}{suffix}</span>;
}
