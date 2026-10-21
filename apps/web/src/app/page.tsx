import Link from "next/link";

import {
  ArrowRight,
  ArrowUpRight,
  Calendar,
  Check,
  RadarMark,
  ShieldCheck,
  Sparkle,
} from "@/components/icons";
import { OpportunityCard, OpportunityRow } from "@/components/opportunity-card";
import { RadarVisual } from "@/components/radar-visual";
import { ApiUnavailable, EmptyState, Metric, SectionHeading } from "@/components/ui";
import { apiGet, getSessionToken, getSessionUser } from "@/lib/api";
import { formatDate, formatRelative } from "@/lib/format";
import type { DashboardData } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Panel diario de oportunidades tecnológicas",
  description:
    "Hackathons, eventos, becas y programas verificados: qué está abierto, cuánto tiempo queda y qué encaja contigo.",
};

async function loadSaved(token: string | null): Promise<Set<string>> {
  if (!token) return new Set();
  try {
    const payload = await apiGet<{ items: { slug: string }[] }>("/saved", token);
    return new Set(payload.items.map((item) => item.slug));
  } catch {
    return new Set();
  }
}

export default async function HomePage() {
  const [token, user] = await Promise.all([getSessionToken(), getSessionUser()]);

  let data: DashboardData;
  try {
    data = await apiGet<DashboardData>("/dashboard", token);
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }
  const saved = await loadSaved(token);

  const today = new Intl.DateTimeFormat("es-PE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());

  const profileHref = user ? "/perfil" : "/registro?next=%2Fperfil";

  return (
    <div>
      {/* Hero */}
      <section className="border-b border-line">
        <div className="shell grid items-center gap-10 py-12 lg:grid-cols-[1.08fr_0.92fr] lg:gap-16 lg:py-20">
          <div className="fade-up">
            <div className="mb-7 flex items-center gap-3">
              <span className="h-px w-8 bg-signal" />
              <span className="eyebrow text-ink-soft">Inteligencia de oportunidades · datos verificados</span>
            </div>
            <h1 className="display text-[52px] leading-[0.95] tracking-[-0.03em] text-ink sm:text-[68px] lg:text-[76px]">
              Tu próxima
              <br />
              oportunidad,
              <br />
              <span className="italic text-signal-deep">ya verificada.</span>
            </h1>
            <p className="mt-7 max-w-xl text-[15px] leading-relaxed text-ink-soft">
              Hackathons, eventos, becas y programas de todo el mundo. Cada ficha conserva su fuente
              original, la última comprobación y el motivo por el que aparece en tu radar.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/oportunidades" className="btn btn-primary group">
                Explorar oportunidades
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              {data.personalized ? (
                <Link href="#panel" className="btn btn-outline">
                  Ver mi panel
                </Link>
              ) : (
                <Link href={profileHref} className="btn btn-outline">
                  Activar mi radar
                </Link>
              )}
            </div>

            <ul className="mt-10 grid gap-3 border-t border-line pt-6 text-[11px] text-muted sm:grid-cols-3 sm:gap-6">
              <li className="flex items-start gap-2">
                <ShieldCheck size={14} className="mt-0.5 shrink-0 text-fern" />
                Fuente y última comprobación en cada ficha
              </li>
              <li className="flex items-start gap-2">
                <Check size={14} className="mt-0.5 shrink-0 text-fern" />
                Sin fechas inferidas como confirmadas
              </li>
              <li className="flex items-start gap-2">
                <RadarMark size={14} className="mt-0.5 shrink-0 text-ink-soft" />
                {data.summary.active_sources} fuentes activas · cobertura global
              </li>
            </ul>
          </div>

          <div className="relative">
            <RadarVisual
              openTotal={data.summary.open_total}
              sources={data.summary.active_sources}
              closing={data.summary.upcoming}
              className="mx-auto aspect-square w-full max-w-[480px] shadow-[0_30px_60px_-30px_rgba(17,19,16,0.45)]"
            />
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
              <span className="inline-flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-fern" />
                Última pasada {formatRelative(data.freshness.last_checked_at)}
              </span>
              <span>{data.summary.published_total} fichas verificables</span>
            </div>
          </div>
        </div>
      </section>

      {/* Daily summary */}
      <section className="border-b border-line bg-paper-raised/60">
        <div className="shell py-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow">Tu resumen diario</p>
              <p className="mt-1 font-display text-[26px] first-letter:uppercase text-ink">{today}</p>
            </div>
            <p className="max-w-md text-[12px] leading-relaxed text-muted">{data.note}</p>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-8 sm:grid-cols-3 lg:max-w-3xl lg:gap-10">
            <Metric
              label="Nuevas oportunidades"
              value={data.summary.new}
              note="Detectadas en los últimos 7 días"
            />
            <Metric
              label="Próximas fechas límite"
              value={data.summary.upcoming}
              note="Cierran en los próximos 7 días"
              accent={data.summary.upcoming > 0}
            />
            <Metric
              label={data.summary.priority_label}
              value={data.summary.priority}
              note={
                data.personalized
                  ? "Según tus intereses, tiempo y elegibilidad"
                  : "Ordenadas por afinidad y confianza"
              }
            />
          </div>
        </div>
      </section>

      <div className="shell">
        {/* Personalization prompt */}
        {!data.personalized && (
          <section className="mt-10 flex flex-col gap-5 border border-line bg-paper-raised p-6 sm:flex-row sm:items-center sm:justify-between sm:p-7">
            <div className="flex gap-4">
              <span className="mt-1 grid size-10 shrink-0 place-items-center rounded-full border border-signal/25 bg-signal-soft text-signal-deep">
                <Sparkle size={18} />
              </span>
              <div>
                <p className="eyebrow text-signal-deep">Radar personal</p>
                <h2 className="mt-1 font-display text-[25px] leading-tight">
                  El tiempo disponible importa tanto como los intereses
                </h2>
                <p className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-muted">
                  Dos personas interesadas en IA no necesitan lo mismo. Cuéntanos qué días tienes
                  libres, cuánto tiempo puedes dedicar y en qué modalidad. Se tarda menos de 2 minutos.
                </p>
              </div>
            </div>
            <Link href={profileHref} className="btn btn-signal shrink-0">
              Completar mi perfil
              <ArrowUpRight size={14} />
            </Link>
          </section>
        )}

        {/* Priority */}
        <section id="panel" className="scroll-mt-24 py-12">
          <SectionHeading
            eyebrow={data.personalized ? "Seleccionado para ti" : "Señal principal"}
            title={data.personalized ? "Lo que más encaja contigo" : "Las oportunidades más sólidas ahora"}
            description={
              data.personalized
                ? "Ordenadas por afinidad, compatibilidad de horario, elegibilidad comprobable, fiabilidad y valor. Cada tarjeta explica su motivo."
                : "Un orden explicable por calidad de la información, plazos y valor. Completa tu perfil para añadir tus intereses y disponibilidad."
            }
            action={{ href: "/oportunidades", label: "Ver todo el catálogo" }}
          />

          {data.priority.length === 0 ? (
            <div className="mt-8">
              <EmptyState
                title="El radar aún no tiene señal publicada"
                body="No mostraremos datos de demostración como si fueran reales. La ingesta inicial puede tardar unos minutos; mientras tanto puedes revisar el método y las fuentes."
                action={{ href: "/metodologia", label: "Ver método y fuentes" }}
              />
            </div>
          ) : (
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {data.priority.slice(0, 4).map((item) => (
                <OpportunityCard
                  key={item.id}
                  item={item}
                  saved={saved.has(item.slug)}
                  authenticated={Boolean(user)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Categories */}
        <section className="py-4">
          <SectionHeading
            eyebrow="Explorar por tipo"
            title="Cuatro puertas de entrada"
            description="Competiciones, comunidad, formación y emprendimiento. Cada categoría con sus subcategorías y etiquetas tecnológicas."
            action={{ href: "/oportunidades", label: "Abrir catálogo" }}
          />
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data.categories.map((category, index) => (
              <Link
                key={category.key}
                href={`/oportunidades?category=${category.key}`}
                className="group relative flex min-h-[188px] flex-col justify-between overflow-hidden rounded-[4px] border border-line bg-paper-raised p-5 transition-colors hover:border-ink/40"
              >
                <span className="absolute right-4 top-4 font-mono text-[10px] text-line-strong">
                  0{index + 1}
                </span>
                <div>
                  <h3 className="font-display text-[26px] leading-tight text-ink group-hover:text-signal-deep">
                    {category.label}
                  </h3>
                  <p className="mt-1.5 text-[12px] leading-snug text-muted">{category.tagline}</p>
                </div>
                <div className="mt-5 flex items-end justify-between">
                  <div>
                    <p className="mono text-3xl leading-none text-ink">{category.count}</p>
                    <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                      oportunidades
                    </p>
                  </div>
                  <ArrowUpRight
                    size={16}
                    className="text-line-strong transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-signal"
                  />
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Deadlines + new */}
        <section className="grid gap-10 py-12 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <SectionHeading
              eyebrow="No lo dejes pasar"
              title="Cierra pronto"
              description="Fechas límite publicadas por la fuente. Si no hay fecha, lo decimos: no la estimamos."
              action={{ href: "/oportunidades?days=7", label: "Ver plazos" }}
            />
            <div className="mt-2">
              {data.upcoming.length === 0 ? (
                <p className="border-b border-line py-8 text-[13px] text-muted">
                  Ninguna convocatoria publicada cierra en los próximos 7 días.
                </p>
              ) : (
                data.upcoming.map((item) => (
                  <OpportunityRow
                    key={item.id}
                    item={item}
                    saved={saved.has(item.slug)}
                    authenticated={Boolean(user)}
                  />
                ))
              )}
            </div>
          </div>

          <div>
            <SectionHeading
              eyebrow="Recién detectadas"
              title="Nuevas en el radar"
              action={{ href: "/oportunidades?sort=newest", label: "Ver nuevas" }}
            />
            <div className="mt-2">
              {data.new.length === 0 ? (
                <p className="border-b border-line py-8 text-[13px] text-muted">
                  Todavía no hay oportunidades nuevas esta semana.
                </p>
              ) : (
                <ul className="divide-y divide-line">
                  {data.new.map((item) => (
                    <li key={item.id} className="py-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                            {item.category.label} · {item.modality.label}
                          </p>
                          <h3 className="mt-1 font-display text-[20px] leading-tight">
                            <Link href={`/oportunidades/${item.slug}`} className="hover:text-signal-deep">
                              {item.title}
                            </Link>
                          </h3>
                          <p className="mt-1 text-[11px] text-muted">
                            {item.deadline.label} · {item.source?.name ?? "fuente original"}
                          </p>
                        </div>
                        <span className="mono shrink-0 text-[10px] text-muted">
                          {item.first_seen_at ? formatDate(item.first_seen_at, { year: undefined }) : ""}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>

        {/* Trust band */}
        <section className="my-8 overflow-hidden rounded-[4px] bg-ink text-paper-raised">
          <div className="grid gap-10 p-7 sm:p-10 lg:grid-cols-[0.95fr_1.05fr] lg:p-12">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-signal">
                La capa de confianza
              </p>
              <h2 className="mt-4 font-display text-[36px] leading-[1.02] sm:text-[44px]">
                No es un directorio.
                <br />
                <span className="italic text-paper-raised/70">Es una decisión informada.</span>
              </h2>
              <p className="mt-5 max-w-md text-[13px] leading-relaxed text-paper-raised/60">
                Cada oportunidad declara qué está confirmado, qué falta y de dónde sale cada dato.
                Una fecha sin confirmar nunca se presenta como segura. Un enlace que abre no
                significa que la inscripción siga abierta.
              </p>
              <Link
                href="/metodologia"
                className="mt-7 inline-flex items-center gap-2 border-b border-signal/50 pb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-paper-raised hover:border-signal"
              >
                Cómo verificamos <ArrowUpRight size={13} />
              </Link>
            </div>
            <div className="grid gap-px overflow-hidden rounded-[3px] border border-paper-raised/10 bg-paper-raised/10 sm:grid-cols-2">
              {[
                { title: "Verificado", body: "Datos principales respaldados por la fuente oficial." },
                { title: "Pendiente", body: "Plausible, pero faltan datos o confirmación oficial." },
                { title: "Contradicción", body: "Dos fuentes difieren; se muestra y no se oculta." },
                { title: "Cerrado", body: "Historial conservado, fuera de la lista de abiertas." },
              ].map((state) => (
                <div key={state.title} className="bg-ink p-5">
                  <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-signal/80">
                    Estado
                  </p>
                  <p className="mt-2 font-display text-[22px] text-paper-raised">{state.title}</p>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-paper-raised/50">{state.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="flex flex-col items-start justify-between gap-6 border-y border-line py-10 sm:flex-row sm:items-center">
          <div className="flex items-start gap-4">
            <Calendar size={22} className="mt-1 text-signal" />
            <div>
              <h2 className="font-display text-[28px] leading-tight">
                {data.personalized ? "Tu calendario ya puede trabajar por ti" : "Convierte el radar en tu agenda"}
              </h2>
              <p className="mt-1 max-w-xl text-[13px] text-muted">
                Guarda oportunidades, sigue tus postulaciones y exporta fechas límite a tu calendario.
                Sin inscripciones automáticas: siempre decides tú.
              </p>
            </div>
          </div>
          <Link href={user ? "/calendario" : "/registro?next=%2Fperfil"} className="btn btn-primary shrink-0">
            {user ? "Abrir calendario" : "Crear cuenta gratis"}
          </Link>
        </section>
      </div>
    </div>
  );
}
