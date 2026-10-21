import Link from "next/link";

import { Calendar, Download, ArrowLeft, ArrowRight } from "@/components/icons";
import { ApiUnavailable, EmptyState } from "@/components/ui";
import { apiGet, getSessionToken, requireUser } from "@/lib/api";
import { cn, formatDate } from "@/lib/format";
import type { CalendarItem, CalendarResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Mi calendario de oportunidades",
  description: "Fechas límite y eventos de las oportunidades que has guardado, con exportación iCalendar.",
};

const DAY_MS = 86_400_000;
const DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

function startOfUtcDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function addDays(date: Date, days: number): Date {
  return new Date(date.getTime() + days * DAY_MS);
}

function addMonths(date: Date, months: number): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + months, 1));
}

function parseDate(value: string | undefined): Date {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const digits = value.split("-").map(Number);
    return new Date(Date.UTC(digits[0], digits[1] - 1, digits[2]));
  }
  return startOfUtcDay(new Date());
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function monthLabel(date: Date): string {
  return new Intl.DateTimeFormat("es-PE", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function dayLabel(date: Date): string {
  return new Intl.DateTimeFormat("es-PE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function shortRange(start: Date, end: Date): string {
  const fmt = new Intl.DateTimeFormat("es-PE", { day: "numeric", month: "short", timeZone: "UTC" });
  return `${fmt.format(start)} – ${fmt.format(addDays(end, -1))}`;
}

type View = "month" | "week" | "day" | "agenda";

export default async function CalendarPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const user = await requireUser("/calendario");
  const token = await getSessionToken();
  const sp = await searchParams;
  const rawView = Array.isArray(sp.view) ? sp.view[0] : sp.view;
  const view: View = rawView === "week" || rawView === "day" || rawView === "agenda" ? rawView : "month";
  const anchor = parseDate(Array.isArray(sp.date) ? sp.date[0] : sp.date);

  const today = startOfUtcDay(new Date());
  let rangeStart: Date;
  let rangeEnd: Date;

  if (view === "week") {
    const offset = (anchor.getUTCDay() + 6) % 7;
    rangeStart = addDays(anchor, -offset);
    rangeEnd = addDays(rangeStart, 7);
  } else if (view === "day") {
    rangeStart = anchor;
    rangeEnd = addDays(anchor, 1);
  } else if (view === "agenda") {
    rangeStart = today;
    rangeEnd = addDays(today, 90);
  } else {
    const first = new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth(), 1));
    const offset = (first.getUTCDay() + 6) % 7;
    rangeStart = addDays(first, -offset);
    rangeEnd = addDays(rangeStart, 42);
  }

  let data: CalendarResponse;
  try {
    data = await apiGet<CalendarResponse>(
      `/calendar?start=${rangeStart.toISOString()}&end=${rangeEnd.toISOString()}`,
      token,
    );
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  const itemsByDay = new Map<string, CalendarItem[]>();
  for (const item of data.items) {
    const day = item.date.slice(0, 10);
    const list = itemsByDay.get(day) ?? [];
    list.push(item);
    itemsByDay.set(day, list);
  }

  const deadlineCount = data.items.filter((item) => item.kind === "deadline").length;
  const eventCount = data.items.filter((item) => item.kind === "event").length;
  const nextDeadline = data.items
    .filter((item) => item.kind === "deadline")
    .sort((a, b) => a.date.localeCompare(b.date))[0];

  const navBase = `/calendario?view=${view}`;
  const prevAnchor =
    view === "month"
      ? addMonths(anchor, -1)
      : view === "week"
        ? addDays(anchor, -7)
        : addDays(anchor, -1);
  const nextAnchor =
    view === "month"
      ? addMonths(anchor, 1)
      : view === "week"
        ? addDays(anchor, 7)
        : addDays(anchor, 1);

  const gridStart = new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth(), 1));
  const gridOffset = (gridStart.getUTCDay() + 6) % 7;
  const calendarDays = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index - gridOffset));

  const dayItems = itemsByDay.get(isoDate(anchor)) ?? [];
  const weekStart = addDays(anchor, -((anchor.getUTCDay() + 6) % 7));
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  const agendaDays = Array.from({ length: 90 }, (_, index) => addDays(today, index)).filter(
    (day) => (itemsByDay.get(isoDate(day)) ?? []).length > 0,
  );

  const title =
    view === "month"
      ? monthLabel(anchor)
      : view === "week"
        ? `Semana del ${monthLabel(addDays(weekStart, 3))}`
        : view === "day"
          ? dayLabel(anchor)
          : "Próximos 90 días";

  return (
    <div className="shell py-10 lg:py-14">
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-line pb-6">
        <div>
          <p className="eyebrow mb-3">Calendario personal · {user.display_name || user.email}</p>
          <h1 className="display text-[44px] leading-[0.98] tracking-[-0.03em] sm:text-[56px]">
            Tus plazos,
            <br />
            <span className="italic text-signal-deep">en orden.</span>
          </h1>
          <p className="mt-3 max-w-2xl text-[13px] leading-relaxed text-muted">
            Solo aparece lo que has guardado. Las fechas límite y los eventos se muestran por separado;
            exporta el calendario cuando quieras.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={`/api/calendar.ics?start=${rangeStart.toISOString()}&end=${rangeEnd.toISOString()}`}
            className="btn btn-outline !py-2.5"
          >
            <Download size={14} />
            Exportar .ics
          </a>
          <Link href="/oportunidades" className="btn btn-primary !py-2.5">
            Buscar más oportunidades
          </Link>
        </div>
      </header>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-1 rounded-full border border-line bg-paper-raised p-1">
          {(["month", "week", "day", "agenda"] as View[]).map((option) => (
            <Link
              key={option}
              href={`/calendario?view=${option}&date=${isoDate(anchor)}`}
              className={cn(
                "rounded-full px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.06em] transition-colors",
                view === option ? "bg-ink text-paper-raised" : "text-muted hover:text-ink",
              )}
            >
              {option === "month" ? "Mes" : option === "week" ? "Semana" : option === "day" ? "Día" : "Agenda"}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          {view !== "agenda" && (
            <>
              <Link
                href={`${navBase}&date=${isoDate(prevAnchor)}`}
                className="grid size-9 place-items-center rounded-full border border-line text-muted hover:text-ink"
                aria-label="Anterior"
              >
                <ArrowLeft size={15} />
              </Link>
              <Link href={`/calendario?view=${view}`} className="btn btn-outline !px-3 !py-2">
                Hoy
              </Link>
              <Link
                href={`${navBase}&date=${isoDate(nextAnchor)}`}
                className="grid size-9 place-items-center rounded-full border border-line text-muted hover:text-ink"
                aria-label="Siguiente"
              >
                <ArrowRight size={15} />
              </Link>
            </>
          )}
          <span className="ml-2 font-mono text-[12px] first-letter:uppercase text-ink">{title}</span>
        </div>
      </div>

      <div className="mt-6 grid gap-4 border-y border-line py-4 sm:grid-cols-3">
        <div>
          <p className="eyebrow">Fechas límite</p>
          <p className="mono mt-1 text-2xl text-signal-deep">{deadlineCount}</p>
        </div>
        <div>
          <p className="eyebrow">Eventos guardados</p>
          <p className="mono mt-1 text-2xl text-ink">{eventCount}</p>
        </div>
        <div>
          <p className="eyebrow">Próximo cierre</p>
          <p className="mt-1 truncate text-[13px] text-ink-soft">
            {nextDeadline ? `${nextDeadline.title} · ${formatDate(nextDeadline.date)}` : "Sin cierres en este rango"}
          </p>
        </div>
      </div>

      {data.items.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Tu calendario está vacío en este rango"
            body="Guarda oportunidades y sus fechas límite aparecerán aquí. No rellenamos huecos con eventos que no hayas elegido."
            action={{ href: "/oportunidades", label: "Explorar el catálogo" }}
            icon={<Calendar size={20} />}
          />
        </div>
      ) : (
        <>
          {(view === "month" || view === "week") && (
          <div className="mt-8 hidden overflow-hidden border border-line bg-paper-raised md:block">
            <div className="grid grid-cols-7 border-b border-line bg-paper-deep/40">
              {DAY_NAMES.map((day) => (
                <div key={day} className="border-r border-line px-3 py-2 last:border-r-0">
                  <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">{day}</span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {(view === "week" ? weekDays : calendarDays).map((day, index) => {
                const key = isoDate(day);
                const items = itemsByDay.get(key) ?? [];
                const isToday = key === isoDate(today);
                const inMonth = day.getUTCMonth() === anchor.getUTCMonth();
                const dimmed = view === "month" && !inMonth;
                return (
                  <div
                    key={key}
                    className={cn(
                      "min-h-[136px] border-b border-r border-line p-2 last:border-r-0",
                      dimmed && "bg-paper/50",
                      isToday && "bg-signal-soft/30",
                      index >= 35 && view === "month" && "border-b-0",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          "mono text-[11px]",
                          isToday ? "grid size-5 place-items-center rounded-full bg-signal text-white" : dimmed ? "text-line-strong" : "text-ink-soft",
                        )}
                      >
                        {day.getUTCDate()}
                      </span>
                      {items.length > 0 && (
                        <span className="font-mono text-[8px] uppercase tracking-wider text-muted">
                          {items.length}
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5 space-y-1">
                      {items.slice(0, 2).map((item) => (
                        <Link
                          key={`${item.uid}-${item.kind}`}
                          href={`/oportunidades/${item.slug}`}
                          className={cn(
                            "block truncate rounded-sm border-l-2 px-1.5 py-1 text-[10px] leading-tight hover:bg-paper-deep/60",
                            item.kind === "deadline"
                              ? "border-signal bg-signal-soft/40 text-signal-deep"
                              : "border-moss bg-paper text-ink-soft",
                          )}
                          title={item.title}
                        >
                          {item.title}
                        </Link>
                      ))}
                      {items.length > 2 && (
                        <span className="block px-1.5 font-mono text-[9px] text-muted">
                          +{items.length - 2} más
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          )}

          {view === "week" && (
            <div className="mt-4 grid gap-3 md:hidden">
              {weekDays.map((day) => {
                const key = isoDate(day);
                const items = itemsByDay.get(key) ?? [];
                return (
                  <div key={key} className="border border-line bg-paper-raised p-4">
                    <p className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">{dayLabel(day)}</p>
                    <div className="mt-2 space-y-2">
                      {items.length === 0 ? (
                        <p className="text-[11px] text-muted">Sin elementos.</p>
                      ) : (
                        items.map((item) => <CalendarEntry key={`${item.uid}-${item.kind}`} item={item} />)
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {view === "day" && (
            <div className="mt-4 border border-line bg-paper-raised p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">{dayLabel(anchor)}</p>
              <div className="mt-3 space-y-2">
                {dayItems.length === 0 ? (
                  <p className="text-[12px] text-muted">No hay fechas límite ni eventos guardados este día.</p>
                ) : (
                  dayItems.map((item) => <CalendarEntry key={`${item.uid}-${item.kind}`} item={item} />)
                )}
              </div>
            </div>
          )}

          {view === "agenda" && (
            <div className="mt-8 space-y-8">
              {agendaDays.length === 0 ? (
                <p className="text-[13px] text-muted">Sin elementos en los próximos 90 días.</p>
              ) : (
                agendaDays.map((day) => {
                  const key = isoDate(day);
                  const items = itemsByDay.get(key) ?? [];
                  return (
                    <div key={key} className="grid gap-3 border-b border-line pb-5 sm:grid-cols-[160px_1fr]">
                      <div>
                        <p className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                          {new Intl.DateTimeFormat("es-PE", { weekday: "short", timeZone: "UTC" }).format(day)}
                        </p>
                        <p className="font-display text-[24px] leading-none">{formatDate(day.toISOString())}</p>
                      </div>
                      <div className="space-y-2">
                        {items.map((item) => (
                          <CalendarEntry key={`${item.uid}-${item.kind}`} item={item} />
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-4 text-[10px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-signal" /> Fecha límite
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-moss" /> Evento
        </span>
        <span>Las integraciones externas de calendario requieren autorización; el .ics es la vía directa.</span>
      </div>
    </div>
  );
}

function CalendarEntry({ item }: { item: CalendarItem }) {
  return (
    <Link
      href={`/oportunidades/${item.slug}`}
      className="flex items-start justify-between gap-3 rounded-sm border border-line bg-paper p-3 transition-colors hover:border-ink/30"
    >
      <div className="min-w-0">
        <p className={cn("font-mono text-[9px] uppercase tracking-[0.1em]", item.kind === "deadline" ? "text-signal-deep" : "text-moss")}>
          {item.kind === "deadline" ? "Cierre" : "Evento"} · {item.label}
        </p>
        <p className="mt-1 truncate text-[12px] text-ink">{item.title}</p>
      </div>
      <span className="mono shrink-0 text-[10px] text-muted">{formatDate(item.date)}</span>
    </Link>
  );
}
