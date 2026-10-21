import { ShieldCheck } from "@/components/icons";
import { formatDate, formatDateTime } from "@/lib/format";
import type { OpportunityChange, ProvenanceRow } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  title: "Título",
  summary: "Resumen",
  description: "Descripción",
  category: "Categoría",
  tech_tags: "Etiquetas tecnológicas",
  modality: "Modalidad",
  country: "País",
  city: "Ciudad",
  language: "Idioma",
  organizer: "Organizador",
  official_url: "Enlace oficial",
  registration_url: "Enlace de registro",
  event_start: "Inicio del evento",
  event_end: "Fin del evento",
  registration_deadline: "Fecha límite de inscripción",
  submission_deadline: "Fecha límite de entregas",
  cost: "Coste",
  prizes: "Premios",
  eligibility: "Requisitos",
  duration: "Duración",
};

const FIELD_ORDER = [
  "title",
  "official_url",
  "registration_url",
  "category",
  "modality",
  "country",
  "city",
  "organizer",
  "event_start",
  "event_end",
  "registration_deadline",
  "submission_deadline",
  "cost",
  "prizes",
  "eligibility",
  "duration",
  "tech_tags",
  "language",
  "summary",
  "description",
];

function isIsoDate(value: unknown): boolean {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value);
}

function renderValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "Por confirmar";
  if (isIsoDate(value)) {
    return field.includes("deadline") ? `${formatDate(value as string)} · fin del día` : formatDate(value as string);
  }
  if (Array.isArray(value)) {
    if (!value.length) return "Por confirmar";
    return value
      .map((item) => {
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          return String(record.label ?? record.description ?? JSON.stringify(record));
        }
        return String(item);
      })
      .join(" · ");
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if ("type" in record || "amount" in record) {
      return [
        record.type === "free" ? "Gratis" : record.type === "paid" ? "De pago" : "Por confirmar",
        typeof record.amount === "number" ? `${record.amount} ${record.currency ?? ""}`.trim() : "",
      ]
        .filter(Boolean)
        .join(" · ");
    }
    if ("label" in record) return String(record.label);
    return Object.entries(record)
      .filter(([, item]) => item !== null && item !== undefined && item !== "")
      .map(([key, item]) => `${key}: ${typeof item === "object" ? JSON.stringify(item) : String(item)}`)
      .join(" · ");
  }
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}

export function ProvenanceTable({ rows }: { rows: ProvenanceRow[] }) {
  const latest = new Map<string, ProvenanceRow>();
  for (const row of rows) {
    if (!latest.has(row.field)) latest.set(row.field, row);
  }
  const sorted = [...latest.values()].sort((a, b) => {
    const ai = FIELD_ORDER.indexOf(a.field);
    const bi = FIELD_ORDER.indexOf(b.field);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  if (sorted.length === 0) {
    return (
      <p className="border border-dashed border-line-strong p-6 text-[13px] text-muted">
        Esta ficha no tiene procedencia registrada por campo. Es una señal de que no debería
        publicarse; revisa el estado de verificación.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border border-line">
      <table className="w-full min-w-[680px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-paper-deep/40">
            {["Campo", "Valor", "Fuente", "Comprobado"].map((label) => (
              <th
                key={label}
                className="px-3 py-2.5 font-mono text-[9px] uppercase tracking-[0.1em] text-muted"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={`${row.field}-${row.source?.slug ?? "unknown"}`} className="border-b border-line last:border-b-0">
              <td className="px-3 py-3 align-top text-[11px] font-medium text-ink-soft">
                {FIELD_LABELS[row.field] ?? row.field}
              </td>
              <td className="max-w-[320px] px-3 py-3 align-top text-[11px] leading-relaxed text-ink">
                <span className="line-clamp-3">{renderValue(row.field, row.value)}</span>
                {row.note && <span className="mt-1 block text-[10px] text-muted">{row.note}</span>}
              </td>
              <td className="px-3 py-3 align-top">
                <span className="block text-[11px] text-ink-soft">{row.source?.name ?? "Sin fuente"}</span>
                <span className="mono mt-0.5 block text-[9px] uppercase tracking-wider text-muted">
                  {row.method} · autoridad {row.source?.authority ?? "—"}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-3 align-top">
                <span className="mono block text-[10px] text-ink-soft">
                  {row.observed_at ? formatDateTime(row.observed_at) : "Sin fecha"}
                </span>
                <span className="mt-1 inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-wider text-muted">
                  {row.is_official && <ShieldCheck size={10} className="text-fern" />}
                  {row.is_official ? "oficial" : "no oficial"} · {Math.round(row.confidence * 100)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChangeTimeline({ changes }: { changes: OpportunityChange[] }) {
  if (changes.length === 0) {
    return (
      <p className="border border-dashed border-line-strong p-6 text-[13px] text-muted">
        Sin cambios registrados desde la primera detección. No significa que siga abierta: significa
        que aún no hemos detectado una modificación.
      </p>
    );
  }
  return (
    <ol className="border-l border-line">
      {changes.slice(0, 12).map((change, index) => (
        <li key={`${change.field}-${change.created_at}-${index}`} className="relative pb-5 pl-5 last:pb-0">
          <span className="absolute -left-[3px] top-1.5 size-1.5 rounded-full bg-line-strong" />
          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
            {change.field} · {change.actor} · {change.created_at ? formatDate(change.created_at) : "sin fecha"}
          </p>
          <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">
            {change.old_value !== null && change.old_value !== undefined && (
              <span className="text-muted line-through">{renderValue(change.field, change.old_value)}</span>
            )}
            {change.old_value !== null && change.old_value !== undefined && " → "}
            <span className="text-ink">{renderValue(change.field, change.new_value)}</span>
          </p>
          {change.reason && <p className="mt-0.5 text-[10px] text-muted">{change.reason}</p>}
        </li>
      ))}
    </ol>
  );
}
