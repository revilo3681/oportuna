export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

const DATE_LOCALE = "es-PE";

export function formatDate(value: string | null, options?: Intl.DateTimeFormatOptions): string {
  if (!value) return "Por confirmar";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Por confirmar";
  return new Intl.DateTimeFormat(DATE_LOCALE, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(date);
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Sin registrar";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin registrar";
  return new Intl.DateTimeFormat(DATE_LOCALE, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
}

export function formatRelative(value: string | null): string {
  if (!value) return "sin comprobar";
  const date = new Date(value).getTime();
  if (Number.isNaN(date)) return "sin comprobar";
  const diff = Date.now() - date;
  const hours = Math.round(diff / 3_600_000);
  if (hours < 1) return "hace minutos";
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "ayer";
  if (days < 30) return `hace ${days} días`;
  return `hace ${Math.round(days / 30)} meses`;
}

export function formatDuration(minutes: number | null): string {
  if (minutes === null || minutes === undefined) return "Duración por confirmar";
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 24 * 60) {
    const hours = Math.round((minutes / 60) * 10) / 10;
    return `${hours} h`;
  }
  const days = Math.round((minutes / (24 * 60)) * 10) / 10;
  return `${days} días`;
}

export function compactNumber(value: number): string {
  return new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function initals(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function urgencyClasses(urgency: string): { pill: string; dot: string; text: string } {
  switch (urgency) {
    case "imminent":
      return {
        pill: "border-brick/30 bg-brick-soft text-brick",
        dot: "bg-brick",
        text: "text-brick",
      };
    case "soon":
      return {
        pill: "border-signal/30 bg-signal-soft text-signal-deep",
        dot: "bg-signal",
        text: "text-signal-deep",
      };
    case "upcoming":
      return {
        pill: "border-line bg-paper-deep/60 text-ink-soft",
        dot: "bg-moss",
        text: "text-ink-soft",
      };
    case "unknown":
      return {
        pill: "border-dashed border-line bg-transparent text-muted",
        dot: "bg-line-strong",
        text: "text-muted",
      };
    case "expired":
      return {
        pill: "border-line bg-paper-deep text-muted",
        dot: "bg-line-strong",
        text: "text-muted",
      };
    default:
      return {
        pill: "border-fern/25 bg-fern-soft text-fern",
        dot: "bg-fern",
        text: "text-fern",
      };
  }
}

export function verificationClasses(state: string): string {
  switch (state) {
    case "verified":
      return "border-fern/30 bg-fern-soft text-fern";
    case "conflict":
      return "border-brick/30 bg-brick-soft text-brick";
    case "closed":
      return "border-line bg-paper-deep text-muted";
    default:
      return "border-amber/30 bg-amber-soft text-amber";
  }
}

export function confidenceTone(value: number): string {
  if (value >= 0.8) return "bg-fern";
  if (value >= 0.6) return "bg-moss";
  if (value >= 0.4) return "bg-amber";
  return "bg-brick";
}

export function booleanPreference(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  return null;
}

export const DAY_LABELS: Record<string, string> = {
  mon: "Lun",
  tue: "Mar",
  wed: "Mié",
  thu: "Jue",
  fri: "Vie",
  sat: "Sáb",
  sun: "Dom",
};

export const SLOT_LABELS: Record<string, string> = {
  morning: "Mañana",
  afternoon: "Tarde",
  evening: "Noche",
};

export function buildQuery(params: Record<string, string | string[] | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, item);
    } else {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
