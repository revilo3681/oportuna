import Link from "next/link";
import type { ReactNode } from "react";

import { ArrowRight, RadarMark } from "@/components/icons";
import { cn } from "@/lib/format";

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: { href: string; label: string };
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4", className)}>
      <div>
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h2 className="font-display text-[28px] leading-tight text-ink sm:text-[34px]">{title}</h2>
        {description && <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-muted">{description}</p>}
      </div>
      {action && (
        <Link
          href={action.href}
          className="group inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft transition-colors hover:text-signal-deep"
        >
          {action.label}
          <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
        </Link>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
  icon,
}: {
  title: string;
  body: string;
  action?: { href: string; label: string };
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[4px] border border-dashed border-line-strong bg-paper-raised/50 px-6 py-16 text-center">
      <span className="grid size-11 place-items-center rounded-full border border-line bg-paper text-muted">
        {icon ?? <RadarMark size={20} />}
      </span>
      <h3 className="mt-5 font-display text-2xl text-ink">{title}</h3>
      <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted">{body}</p>
      {action && (
        <Link href={action.href} className="btn btn-outline mt-6">
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function ApiUnavailable({ detail }: { detail?: string }) {
  return (
    <div className="shell py-20">
      <div className="mx-auto max-w-xl rounded-[4px] border border-amber/30 bg-amber-soft/60 p-8">
        <p className="eyebrow text-amber">Servicio temporalmente no disponible</p>
        <h1 className="mt-3 font-display text-3xl">No pudimos leer el catálogo</h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          La API de Oportuna no respondió. No mostraremos datos de ejemplo como si fueran oportunidades
          reales. Vuelve a intentarlo en unos segundos.
        </p>
        {detail && (
          <pre className="mt-4 overflow-auto rounded bg-ink/5 p-3 font-mono text-[10px] text-ink-soft">
            {detail}
          </pre>
        )}
        <div className="mt-6 flex flex-wrap gap-2">
          <Link href="/" className="btn btn-primary">
            Reintentar
          </Link>
          <Link href="/metodologia" className="btn btn-outline">
            Ver el método
          </Link>
        </div>
      </div>
    </div>
  );
}

export function Metric({
  label,
  value,
  note,
  accent,
}: {
  label: string;
  value: string | number;
  note?: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col border-l border-line pl-4 first:border-l-0 first:pl-0 sm:pl-6 sm:first:pl-0">
      <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className={cn("mono mt-2 text-4xl leading-none tracking-tight sm:text-[44px]", accent ? "text-signal" : "text-ink")}>
        {value}
      </p>
      {note && <p className="mt-2 text-[11px] leading-snug text-muted">{note}</p>}
    </div>
  );
}
