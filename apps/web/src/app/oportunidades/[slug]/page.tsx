import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { DetailActions } from "@/components/detail-actions";
import {
  AlertTriangle,
  ArrowUpRight,
  Calendar,
  Clock,
  Download,
  ExternalLink,
  Globe,
  Info,
  MapPin,
  ShieldCheck,
  Sparkle,
} from "@/components/icons";
import { OpportunityCard } from "@/components/opportunity-card";
import { ChangeTimeline, ProvenanceTable } from "@/components/provenance-table";
import { ConfidenceMeter, TrustBadge } from "@/components/trust-badge";
import { ApiUnavailable } from "@/components/ui";
import { ApiError, apiGet, getSessionToken, getSessionUser } from "@/lib/api";
import {
  cn,
  formatDate,
  formatDateTime,
  formatDuration,
  urgencyClasses,
} from "@/lib/format";
import type { OpportunityDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

type Params = { slug: string };

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const item = await apiGet<OpportunityDetail>(`/opportunities/${slug}`);
    return {
      title: item.title,
      description: item.summary || `${item.category.label} · ${item.modality.label} · ${item.event_range}`,
      openGraph: { title: item.title, description: item.summary || item.event_range },
    };
  } catch {
    return { title: "Oportunidad" };
  }
}

export default async function OpportunityPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const [token, user] = await Promise.all([getSessionToken(), getSessionUser()]);

  let item: OpportunityDetail;
  try {
    item = await apiGet<OpportunityDetail>(`/opportunities/${slug}`, token);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  const isAdminPreview = !item.verification.published && user?.role === "admin";
  const urgency = urgencyClasses(item.deadline.urgency);
  const closed = ["closed", "finished", "cancelled"].includes(item.lifecycle.key);
  const registrationLabel =
    item.registration_state === "open"
      ? "Inscripción abierta"
      : item.registration_state === "closed"
        ? "Inscripción cerrada"
        : "Inscripción por confirmar";
  const registrationNote =
    item.registration_state === "unknown"
      ? "La fuente consultada no declara si el registro sigue abierto; no lo inferimos desde el enlace."
      : null;

  type DateEntry = {
    label: string;
    value: string | null;
    kind: "registration" | "submission" | "event" | "result";
    required?: boolean;
  };

  const dateEntries: DateEntry[] = [
    {
      label: "Apertura de inscripción",
      value: item.registration_open_at,
      kind: "registration" as const,
    },
    {
      label: "Fecha límite de inscripción",
      value: item.deadline.registration_deadline,
      kind: "registration" as const,
      required: true,
    },
    {
      label: "Fecha límite de entregas",
      value: item.deadline.submission_deadline,
      kind: "submission" as const,
    },
    { label: "Inicio del evento", value: item.event_start, kind: "event" as const, required: true },
    { label: "Fin del evento", value: item.event_end, kind: "event" as const },
    { label: "Resultados", value: item.results_at, kind: "result" as const },
  ].filter((entry) => entry.required || entry.value);

  const location =
    item.modality.key === "online"
      ? "Online"
      : [item.city, item.country?.name].filter(Boolean).join(", ") || item.modality.label;

  return (
    <div>
      <div className="border-b border-line bg-paper-raised/50">
        <div className="shell py-5">
          <nav className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.1em] text-muted" aria-label="Migas de pan">
            <Link href="/" className="hover:text-ink">
              Panel
            </Link>
            <span>/</span>
            <Link href="/oportunidades" className="hover:text-ink">
              Catálogo
            </Link>
            <span>/</span>
            <span className="truncate text-ink-soft">{item.category.label}</span>
          </nav>
        </div>
      </div>

      <div className="shell pt-8">
        {isAdminPreview && (
          <div className="mb-6 flex flex-wrap items-start gap-3 border border-amber/30 bg-amber-soft/70 p-4 text-[12px] leading-relaxed text-ink-soft">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber" />
            <div className="flex-1">
              <strong className="font-medium">Vista previa de administración.</strong> Esta ficha no está
              publicada ({item.verification.review_label.toLowerCase()}). Motivo:{" "}
              {item.verification.review_reason ?? "sin motivo registrado"}.
            </div>
            <Link href="/admin" className="font-mono text-[9px] uppercase tracking-[0.1em] underline">
              Ir a la consola
            </Link>
          </div>
        )}

        <header className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="chip !border-ink/20 !bg-paper-raised !text-ink">{item.category.label}</span>
            {item.tech_tags.slice(0, 4).map((tag) => (
              <span key={tag.key} className="chip">
                {tag.label}
              </span>
            ))}
            <TrustBadge verification={item.verification} />
          </div>

          <h1 className="display mt-5 text-[42px] leading-[0.98] tracking-[-0.03em] sm:text-[56px] lg:text-[64px]">
            {item.title}
          </h1>

          {item.summary ? (
            <p className="mt-5 max-w-3xl text-[16px] leading-relaxed text-ink-soft">{item.summary}</p>
          ) : (
            <p className="mt-5 max-w-3xl text-[14px] italic leading-relaxed text-muted">
              La fuente oficial no publica un resumen. Esta ficha no añade descripciones inventadas:
              revisa el enlace original para conocer el programa completo.
            </p>
          )}

          <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line pt-5 text-[12px] text-muted">
            <span className="inline-flex items-center gap-1.5">
              <Calendar size={14} />
              {item.event_range}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={14} />
              {location}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock size={14} />
              {item.duration_known ? formatDuration(item.duration_minutes) : "Duración por confirmar"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Globe size={14} />
              {item.language ? item.language.toUpperCase() : "Idioma por confirmar"}
            </span>
            {item.organizer && (
              <span>
                Organiza <strong className="font-medium text-ink-soft">{item.organizer}</strong>
              </span>
            )}
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            <a href={item.official_url} target="_blank" rel="noreferrer noopener" className="btn btn-primary">
              Ver en la fuente oficial
              <ExternalLink size={14} />
            </a>
            {item.registration_url && (
              <a
                href={item.registration_url}
                target="_blank"
                rel="noreferrer noopener"
                className="btn btn-signal"
              >
                Ir al registro o envío
                <ArrowUpRight size={14} />
              </a>
            )}
            {item.verification.published && (
              <a href={`/api/opportunities/${item.slug}/ics`} className="btn btn-outline">
                <Download size={14} />
                Añadir a mi calendario
              </a>
            )}
          </div>
        </header>

        <div className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-14">
          <div className="min-w-0">
            <section className="border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">La oportunidad</h2>
              {item.description ? (
                <div className="mt-4 whitespace-pre-line text-[14px] leading-[1.75] text-ink-soft">
                  {item.description}
                </div>
              ) : (
                <div className="mt-4 flex gap-3 border border-dashed border-line-strong p-5 text-[13px] leading-relaxed text-muted">
                  <Info size={16} className="mt-0.5 shrink-0" />
                  <p>
                    La fuente no ofrece una descripción estructurada. No la completamos con texto
                    generado: la ficha conserva solo los datos publicados y el enlace original.
                  </p>
                </div>
              )}

              <div className="mt-6 grid gap-px overflow-hidden border border-line bg-line sm:grid-cols-2">
                {[
                  {
                    label: "Modalidad",
                    value: item.modality.label,
                  },
                  {
                    label: "Coste",
                    value:
                      item.cost.type === "free"
                        ? "Gratis"
                        : item.cost.type === "paid"
                          ? `De pago${item.cost.amount ? ` · ${item.cost.amount} ${item.cost.currency ?? ""}` : ""}`
                          : "Por confirmar",
                  },
                  {
                    label: "Duración del evento",
                    value: item.duration_known ? formatDuration(item.duration_minutes) : "Desconocida",
                  },
                  {
                    label: "Preparación estimada",
                    value:
                      item.prep_time_minutes !== null
                        ? formatDuration(item.prep_time_minutes)
                        : "No publicada por la organización",
                  },
                  {
                    label: "Compromiso total",
                    value:
                      item.commitment_minutes !== null
                        ? formatDuration(item.commitment_minutes)
                        : "Sin estimación fiable",
                  },
                  {
                    label: "Equipo",
                    value:
                      item.team_min || item.team_max
                        ? `${item.team_min ?? "?"}–${item.team_max ?? "?"} personas`
                        : "Por confirmar",
                  },
                ].map((fact) => (
                  <div key={fact.label} className="bg-paper-raised p-4">
                    <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
                      {fact.label}
                    </p>
                    <p className="mt-1.5 text-[13px] text-ink">{fact.value}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="mt-10 border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">Fechas, sin ambigüedad</h2>
              <p className="mt-2 text-[12px] leading-relaxed text-muted">
                La fecha de inscripción y la del evento son campos distintos. Cuando la fuente no
                publica una fecha, aquí aparece como desconocida: nunca la inferimos.
              </p>
              <ol className="mt-6 space-y-0">
                {dateEntries.map((entry) => (
                  <li
                    key={`${entry.kind}-${entry.label}`}
                    className="grid grid-cols-[104px_1fr] gap-4 border-b border-line py-3 last:border-b-0 sm:grid-cols-[150px_1fr]"
                  >
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                        {entry.kind === "registration"
                          ? "Inscripción"
                          : entry.kind === "submission"
                            ? "Entregas"
                            : entry.kind === "result"
                              ? "Resultados"
                              : "Evento"}
                      </p>
                      <p className="mt-1 text-[12px] text-ink-soft">{entry.label}</p>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span
                        className={cn(
                          "text-[14px]",
                          entry.value ? "text-ink" : "italic text-muted",
                        )}
                      >
                        {entry.value ? formatDate(entry.value) : "Sin fecha publicada"}
                      </span>
                      {entry.label === "Fecha límite de inscripción" && (
                        <span className={cn("rounded-full border px-2 py-1 font-mono text-[9px] uppercase", urgency.pill)}>
                          {item.deadline.label}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
              {item.timezone && (
                <p className="mt-3 text-[11px] text-muted">
                  Zona horaria publicada por la fuente:{" "}
                  <span className="mono text-ink-soft">{item.timezone}</span>
                </p>
              )}
              {item.phases.length > 0 && (
                <div className="mt-4 border border-line p-4">
                  <p className="label">Fases publicadas</p>
                  <ul className="space-y-1 text-[12px] text-ink-soft">
                    {item.phases.map((phase, index) => (
                      <li key={index} className="flex flex-wrap items-baseline gap-2">
                        <span className="text-ink">{String(phase.label ?? `Fase ${index + 1}`)}</span>
                        {phase.start ? (
                          <span className="mono text-[10px] text-muted">
                            {formatDate(String(phase.start))}
                            {phase.end ? ` → ${formatDate(String(phase.end))}` : ""}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            <section className="mt-10 border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">Requisitos y elegibilidad</h2>
              {item.eligibility_summary.length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {item.eligibility_summary.map((requirement) => (
                    <li key={requirement} className="flex items-start gap-2 text-[13px] text-ink-soft">
                      <span className="mt-1.5 size-1 shrink-0 rounded-full bg-signal" />
                      {requirement}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 border border-dashed border-line-strong p-5 text-[13px] leading-relaxed text-muted">
                  La organización no ha publicado requisitos verificables en la fuente consultada.
                  No afirmamos que seas elegible: confirma edad, país, equipo y nivel antes de invertir
                  tiempo.
                </p>
              )}
              <div className="mt-5 flex gap-3 border-l-2 border-signal/60 bg-signal-soft/40 p-4 text-[11px] leading-relaxed text-ink-soft">
                <AlertTriangle size={15} className="mt-0.5 shrink-0 text-signal-deep" />
                <p>
                  Oportuna no inscribe, no paga y no se compromete en tu nombre. La elegibilidad final
                  la determina siempre el organizador en su web oficial.
                </p>
              </div>
            </section>

            <section className="mt-10 border-t border-line pt-7">
              <div className="grid gap-8 sm:grid-cols-2">
                <div>
                  <h2 className="font-display text-[26px] leading-tight">Premios</h2>
                  {item.prizes.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {item.prizes.map((prize, index) => (
                        <li key={index} className="border-l border-line pl-3 text-[13px] text-ink-soft">
                          {String(prize.label ?? prize.description ?? JSON.stringify(prize))}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-[13px] text-muted">
                      Premios por verificar. La ausencia de datos no significa que no existan.
                    </p>
                  )}
                </div>
                <div>
                  <h2 className="font-display text-[26px] leading-tight">Qué puedes conseguir</h2>
                  <ul className="mt-3 space-y-2 text-[13px] text-ink-soft">
                    <li className="flex items-start gap-2">
                      <Sparkle size={14} className="mt-0.5 shrink-0 text-signal" />
                      {item.category.key === "formacion"
                        ? "Aprendizaje estructurado, mentoría o financiación."
                        : item.category.key === "hackathons"
                          ? "Práctica real, portafolio y, si la fuente lo confirma, premios."
                          : "Conocimiento, comunidad y acceso a personas que construyen tecnología."}
                    </li>
                    {item.prizes_summary && <li className="text-[12px] text-muted">{item.prizes_summary}</li>}
                    <li className="text-[12px] text-muted">
                      La ficha no promete resultados ni premios no publicados.
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <section className="mt-10 border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">Qué deberías hacer después</h2>
              <ol className="mt-4 space-y-3">
                {item.next_steps.map((step, index) => (
                  <li key={`${step.kind}-${index}`} className="flex gap-4 border border-line bg-paper-raised p-4">
                    <span className="mono grid size-7 shrink-0 place-items-center rounded-full border border-line text-[10px] text-muted">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <p className="text-[13px] font-medium text-ink">{step.label}</p>
                      <p className="mt-1 text-[12px] leading-relaxed text-muted">{step.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>

            <section id="fuente" className="mt-10 scroll-mt-24 border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">Fuente y procedencia</h2>
              <p className="mt-2 max-w-2xl text-[12px] leading-relaxed text-muted">
                Cada campo conserva la fuente que lo respalda, el método de extracción y cuándo se
                comprobó. Si una fuente no confirma un dato, ese dato no se presenta como confirmado.
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {item.sources.map((source) => (
                  <div key={`${source.slug}-${source.source_url}`} className="border border-line bg-paper-raised p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[13px] font-medium text-ink">{source.name}</p>
                      <span className="mono text-[9px] uppercase tracking-wider text-muted">
                        autoridad {source.authority}/100
                      </span>
                    </div>
                    <a
                      href={source.source_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-2 inline-flex items-center gap-1 break-all font-mono text-[10px] text-ink-soft underline decoration-line-strong underline-offset-2 hover:text-signal-deep"
                    >
                      {source.source_url}
                      <ExternalLink size={10} className="shrink-0" />
                    </a>
                    <p className="mt-2 text-[10px] leading-relaxed text-muted">
                      Última lectura: {formatDateTime(source.retrieved_at)}
                      {source.external_id ? ` · id ${source.external_id}` : ""}
                    </p>
                    {source.notes && <p className="mt-1.5 text-[10px] leading-relaxed text-muted">{source.notes}</p>}
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <ProvenanceTable rows={item.provenance} />
              </div>
            </section>

            <section className="mt-10 border-t border-line pt-7">
              <h2 className="font-display text-[28px] leading-tight">Historial de cambios</h2>
              <p className="mt-2 text-[12px] text-muted">
                Para entender por qué una oportunidad pasó de abierta a cerrada, o qué dato cambió.
              </p>
              <div className="mt-5">
                <ChangeTimeline changes={item.changes} />
              </div>
            </section>

            {item.related.length > 0 && (
              <section className="mt-12 border-t border-line pt-7">
                <h2 className="font-display text-[28px] leading-tight">Oportunidades relacionadas</h2>
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  {item.related.slice(0, 2).map((related) => (
                    <OpportunityCard key={related.id} item={related} />
                  ))}
                </div>
              </section>
            )}
          </div>

          <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
            <div className={cn("border bg-paper-raised p-5", closed ? "border-line" : "border-ink/15")}>
              <div className="flex items-center justify-between gap-2">
                <span className="eyebrow">Estado de la convocatoria</span>
                <span className={cn("rounded-full border px-2 py-1 font-mono text-[9px] uppercase", urgency.pill)}>
                  {item.lifecycle.label}
                </span>
              </div>
              <p className={cn("mt-4 font-display text-[34px] leading-none", closed ? "text-muted" : "text-ink")}>
                {item.deadline.label}
              </p>
              <p className="mt-2 text-[11px] text-muted">
                {item.deadline.effective
                  ? `${item.deadline.kind === "submission" ? "Cierre de entregas" : "Cierre de inscripción"}: ${formatDate(item.deadline.effective)}`
                  : "Fecha límite no publicada por la fuente"}
              </p>
              <div className="mt-3 border-t border-line pt-3">
                <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                  Estado de inscripción
                </p>
                <p className="mt-1 text-[12px] text-ink-soft">{registrationLabel}</p>
                {registrationNote && (
                  <p className="mt-1 text-[10px] leading-relaxed text-muted">{registrationNote}</p>
                )}
              </div>
              {item.deadline.kind === "submission" && (
                <p className="mt-2 text-[10px] leading-relaxed text-muted">
                  Devpost publica este cierre como fin del periodo de envíos. No confirma por sí solo
                  que la inscripción siga abierta.
                </p>
              )}
            </div>

            <div className="border border-line bg-paper-raised p-5">
              <div className="flex items-center justify-between gap-2">
                <span className="eyebrow">Verificación</span>
                <TrustBadge verification={item.verification} showConfidence={false} />
              </div>
              <div className="mt-4">
                <ConfidenceMeter verification={item.verification} />
              </div>
              <dl className="mt-5 space-y-2 border-t border-line pt-4 text-[11px]">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Última comprobación</dt>
                  <dd className="text-right text-ink-soft">{formatDateTime(item.last_checked_at)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Última verificación</dt>
                  <dd className="text-right text-ink-soft">{formatDateTime(item.verification.last_verified_at)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Contradicciones</dt>
                  <dd className="text-right text-ink-soft">{item.verification.conflict_count}</dd>
                </div>
              </dl>
              {item.verification.review_reason && (
                <p className="mt-3 border-t border-line pt-3 text-[10px] leading-relaxed text-muted">
                  {item.verification.review_reason}
                </p>
              )}
            </div>

            <div className="border border-line bg-paper-raised p-5">
              <p className="eyebrow mb-3">Tu seguimiento</p>
              <DetailActions
                slug={item.slug}
                initialState={item.saved?.state ?? null}
                authenticated={Boolean(user)}
              />
            </div>

            <div className="border border-line bg-paper-deep/40 p-5">
              <p className="eyebrow">Nota de confianza</p>
              <p className="mt-2 text-[11px] leading-relaxed text-ink-soft">
                Un enlace que carga no demuestra que el formulario siga aceptando inscripciones.
                Confirma el estado en la fuente oficial antes de asumir un compromiso.
              </p>
              <Link
                href="/metodologia"
                className="mt-3 inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.1em] text-ink-soft underline decoration-line-strong underline-offset-2 hover:text-signal-deep"
              >
                Cómo calculamos la confianza <ShieldCheck size={11} />
              </Link>
            </div>
          </aside>
        </div>

        <p className="mt-16 border-t border-line pt-5 text-[10px] leading-relaxed text-muted">
          Oportuna es una capa de inteligencia sobre fuentes públicas. No está afiliada a las
          plataformas, universidades u organizaciones listadas. Si detectas un error, la fuente
          original siempre prevalece.
        </p>
      </div>
    </div>
  );
}
