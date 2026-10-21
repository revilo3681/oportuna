import Link from "next/link";

import { Calendar, Clock, MapPin } from "@/components/icons";
import { SaveButton } from "@/components/save-button";
import { TrustBadge } from "@/components/trust-badge";
import { cn, formatDuration, formatRelative, urgencyClasses } from "@/lib/format";
import type { OpportunityCard as OpportunityCardData } from "@/lib/types";

const ACCENTS: Record<string, string> = {
  hackathons: "bg-signal",
  eventos: "bg-moss",
  formacion: "bg-fern",
  startups: "bg-amber",
};

function DeadlinePill({ item }: { item: OpportunityCardData }) {
  const tones = urgencyClasses(item.deadline.urgency);
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[9px] uppercase leading-none tracking-[0.04em]",
        tones.pill,
      )}
    >
      <span className={cn("size-1.5 rounded-full", tones.dot, item.deadline.urgency === "imminent" && "animate-pulse")} />
      {item.deadline.label}
    </span>
  );
}

function ReasonList({ reasons, limit = 2 }: { reasons: OpportunityCardData["reasons"]; limit?: number }) {
  if (!reasons.length) return null;
  return (
    <ul className="mt-3 flex flex-wrap gap-1.5">
      {reasons.slice(0, limit).map((reason) => (
        <li
          key={`${reason.kind}-${reason.label}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-2 py-1 text-[10px] text-ink-soft"
        >
          <span className="size-1 rounded-full bg-signal" />
          {reason.label}
        </li>
      ))}
    </ul>
  );
}

export function OpportunityCard({
  item,
  variant = "default",
  saved = false,
  authenticated = false,
}: {
  item: OpportunityCardData;
  variant?: "default" | "feature";
  saved?: boolean;
  authenticated?: boolean;
}) {
  const feature = variant === "feature";
  const closed = ["closed", "finished", "cancelled"].includes(item.lifecycle.key);
  const location =
    item.modality.key === "online"
      ? "Online"
      : item.city || item.country?.name || item.modality.label;

  return (
    <article
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-[4px] border bg-paper-raised transition-all duration-300",
        closed ? "border-line opacity-80" : "border-line hover:border-ink/40",
      )}
    >
      <span className={cn("absolute inset-x-0 top-0 h-[2px] opacity-80", ACCENTS[item.category.key] ?? "bg-line-strong")} />
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-ink-soft">
            {item.category.label}
          </span>
          {item.tech_tags.length > 0 && (
            <span className="hidden truncate font-mono text-[9px] uppercase tracking-[0.08em] text-muted sm:block">
              · {item.tech_tags.slice(0, 2).map((tag) => tag.label).join(" / ")}
            </span>
          )}
        </div>
        <DeadlinePill item={item} />
      </div>

      <div className={cn("flex flex-1 flex-col p-4 sm:p-5", feature && "sm:p-6")}>
        <div className="flex items-start justify-between gap-3">
          <h3
            className={cn(
              "font-display leading-[1.05] text-ink",
              feature ? "text-[27px] sm:text-[31px]" : "text-[22px] sm:text-[24px]",
            )}
          >
            <Link href={`/oportunidades/${item.slug}`} className="transition-colors hover:text-signal-deep">
              {item.title}
            </Link>
          </h3>
          {closed && (
            <span className="mt-1 shrink-0 rounded-full border border-line bg-paper-deep px-2 py-1 font-mono text-[8px] uppercase tracking-wider text-muted">
              Historial
            </span>
          )}
        </div>

        {item.summary ? (
          <p className="mt-2.5 line-clamp-3 text-[13px] leading-relaxed text-muted">{item.summary}</p>
        ) : (
          <p className="mt-2.5 line-clamp-2 text-[12px] italic leading-relaxed text-muted/80">
            La fuente oficial no publica un resumen. Revisa la ficha y el enlace original antes de
            decidir.
          </p>
        )}

        <ReasonList reasons={item.reasons} limit={feature ? 3 : 2} />

        <div className="mt-auto pt-5">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-muted">
            <span className="inline-flex items-center gap-1.5">
              <Calendar size={12} />
              {item.event_range}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={12} />
              {location}
            </span>
            {item.duration_known && item.duration_minutes !== null && (
              <span className="inline-flex items-center gap-1.5" title="Duración del evento; la preparación se muestra en la ficha">
                <Clock size={12} />
                {formatDuration(item.duration_minutes)}
              </span>
            )}
          </div>

          <div className="mt-3 flex items-center justify-between gap-3 border-t border-line pt-3">
            <div className="flex min-w-0 items-center gap-2">
              <TrustBadge verification={item.verification} showConfidence={false} />
              <span className="hidden truncate font-mono text-[9px] uppercase tracking-[0.06em] text-muted sm:block">
                {item.source
                  ? `${item.source.name} · ${formatRelative(item.last_checked_at)}`
                  : "Procedencia no registrada"}
              </span>
            </div>
            <SaveButton slug={item.slug} initiallySaved={saved} authenticated={authenticated} />
          </div>
        </div>
      </div>
    </article>
  );
}

export function OpportunityRow({
  item,
  saved = false,
  authenticated = false,
}: {
  item: OpportunityCardData;
  saved?: boolean;
  authenticated?: boolean;
}) {
  const date = item.deadline.effective ?? item.event_start;
  const tones = urgencyClasses(item.deadline.urgency);
  const parsed = date ? new Date(date) : null;
  const monthLabel = parsed
    ? new Intl.DateTimeFormat("es-PE", { month: "short", timeZone: "UTC" }).format(parsed)
    : "—";
  const dayLabel = parsed
    ? new Intl.DateTimeFormat("es-PE", { day: "2-digit", timeZone: "UTC" }).format(parsed)
    : "—";
  return (
    <article className="group grid grid-cols-[52px_1fr] gap-4 border-b border-line py-4 last:border-b-0 sm:grid-cols-[60px_1fr_auto] sm:items-center">
      <div className="flex flex-col items-start border-l-2 border-line pl-3">
        <span className="mono text-[10px] uppercase tracking-wider text-muted">{monthLabel}</span>
        <span className="mono text-xl leading-none text-ink">{dayLabel}</span>
      </div>

      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
            {item.category.label}
          </span>
          <span className={cn("size-1.5 rounded-full", tones.dot)} />
          <span className={cn("font-mono text-[9px] uppercase tracking-[0.06em]", tones.text)}>
            {item.deadline.label}
          </span>
        </div>
        <h3 className="mt-1 truncate font-display text-[19px] leading-tight sm:text-[21px]">
          <Link href={`/oportunidades/${item.slug}`} className="hover:text-signal-deep">
            {item.title}
          </Link>
        </h3>
        <p className="mt-1 truncate text-[11px] text-muted">
          {item.modality.label}
          {item.country?.name ? ` · ${item.country.name}` : ""}
          {item.organizer ? ` · ${item.organizer}` : ""}
        </p>
      </div>

      <div className="col-span-2 flex items-center justify-between gap-3 sm:col-span-1 sm:justify-end">
        <TrustBadge verification={item.verification} showConfidence={false} />
        <SaveButton slug={item.slug} initiallySaved={saved} authenticated={authenticated} />
      </div>
    </article>
  );
}
