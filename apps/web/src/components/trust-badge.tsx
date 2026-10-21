import { AlertTriangle, Check, Info, ShieldCheck } from "@/components/icons";
import { cn, verificationClasses } from "@/lib/format";
import type { Verification } from "@/lib/types";

export function TrustBadge({
  verification,
  showConfidence = true,
  className,
}: {
  verification: Verification;
  showConfidence?: boolean;
  className?: string;
}) {
  const state = verification.state;
  const Icon = state === "verified" ? ShieldCheck : state === "conflict" ? AlertTriangle : state === "closed" ? Info : Info;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-[5px] font-mono text-[9px] uppercase leading-none tracking-[0.08em]",
        verificationClasses(state),
        className,
      )}
      title={verification.review_reason ?? verification.label}
    >
      <Icon size={11} />
      {verification.label}
      {showConfidence && (
        <span className="opacity-60">· {verification.confidence_pct}%</span>
      )}
    </span>
  );
}

export function ConfidenceMeter({ verification }: { verification: Verification }) {
  const pct = Math.max(4, Math.min(100, verification.confidence_pct));
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <span className="eyebrow">Confianza de los datos</span>
        <span className="mono text-[13px] text-ink">{verification.confidence_pct}%</span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-paper-deep" role="img" aria-label={`Confianza ${verification.confidence_pct}%`}>
        <div
          className={cn(
            "h-full rounded-full",
            verification.state === "verified"
              ? "bg-fern"
              : verification.state === "conflict"
                ? "bg-brick"
                : "bg-amber",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <ul className="mt-4 space-y-2">
        {verification.reasons.slice(0, 6).map((reason) => (
          <li key={reason.code} className="flex items-start gap-2 text-[12px] leading-snug text-ink-soft">
            <span
              className={cn(
                "mt-[3px] grid size-4 shrink-0 place-items-center rounded-full border",
                reason.impact === "positive"
                  ? "border-fern/30 bg-fern-soft text-fern"
                  : reason.impact === "negative"
                    ? "border-brick/30 bg-brick-soft text-brick"
                    : "border-line bg-paper text-muted",
              )}
            >
              {reason.impact === "positive" ? <Check size={9} /> : <span className="block size-1 rounded-full bg-current" />}
            </span>
            <span>{reason.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
