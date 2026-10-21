import Link from "next/link";

import { AlertTriangle, Check, ExternalLink, Info, RadarMark, ShieldCheck } from "@/components/icons";
import { ApiUnavailable } from "@/components/ui";
import { apiGet } from "@/lib/api";
import { formatDateTime, formatRelative } from "@/lib/format";
import type { Methodology, PublicSource } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Metodología y fuentes",
  description:
    "Cómo descubre, verifica, deduplica y publica Oportuna. Fuentes activas, política de acceso y límites del sistema.",
};

const WEIGHT_LABELS: Record<string, { label: string; description: string }> = {
  affinity: {
    label: "Afinidad con tus intereses",
    description: "Coincidencia entre tus temas, objetivos y nivel con la oportunidad.",
  },
  availability: {
    label: "Horario, plazos y presupuesto",
    description: "Si cabe en tu semana, si la modalidad te sirve y si el coste es asumible.",
  },
  eligibility: {
    label: "Elegibilidad real",
    description: "Contraste de requisitos publicados. Sin datos, se muestra como por confirmar.",
  },
  reliability: {
    label: "Fiabilidad de la información",
    description: "Confianza explicable basada en señales observables, no en popularidad.",
  },
  value: {
    label: "Valor de aprendizaje o premios",
    description: "Lo que puedes conseguir, sin prometer resultados no publicados.",
  },
};

const PRODUCT_RULES = [
  "No inventar eventos, fechas, premios ni enlaces.",
  "No presentar datos de demostración como oportunidades reales.",
  "Mostrar la fuente original y la fecha de última comprobación.",
  "Separar claramente lo confirmado de lo pendiente.",
  "Respetar las condiciones de acceso de las plataformas.",
  "Permitir que el usuario ajuste o elimine sus datos de perfil.",
  "No confundir popularidad con calidad ni cantidad con cobertura.",
  "No automatizar inscripciones, pagos o compromisos sin autorización expresa.",
  "Conservar un historial de cambios para explicar por qué algo pasó de abierto a cerrado.",
  "Usar el feedback del usuario para mejorar el ranking.",
];

const STATE_DESCRIPTIONS: Record<string, string> = {
  verified: "La página oficial o plataforma de referencia respalda los datos principales y la comprobación es reciente.",
  pending: "Se encontró una oportunidad plausible, pero faltan datos esenciales o confirmación oficial.",
  conflict: "Dos fuentes difieren en fechas, precio, elegibilidad o estado. Se muestra el conflicto.",
  closed: "Cerrada, cancelada o finalizada. Se conserva el historial y deja de aparecer como abierta.",
};

export default async function MethodologyPage() {
  let methodology: Methodology;
  let sources: PublicSource[];
  try {
    const [methodologyPayload, sourcesPayload] = await Promise.all([
      apiGet<Methodology>("/methodology"),
      apiGet<{ sources: PublicSource[] }>("/sources"),
    ]);
    methodology = methodologyPayload;
    sources = sourcesPayload.sources;
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  const enabledSources = sources.filter((source) => source.enabled);
  const lastRun = sources
    .map((source) => source.last_run_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1) ?? null;

  return (
    <div>
      <section className="border-b border-line bg-paper-raised/40">
        <div className="shell grid gap-10 py-12 lg:grid-cols-[1.1fr_0.9fr] lg:py-16">
          <div>
            <p className="eyebrow mb-4">Método · transparencia radical</p>
            <h1 className="display max-w-2xl text-[44px] leading-[0.98] tracking-[-0.03em] sm:text-[60px]">
              La confianza no se
              <br />
              declara.
              <br />
              <span className="italic text-signal-deep">Se demuestra.</span>
            </h1>
            <p className="mt-6 max-w-xl text-[14px] leading-relaxed text-ink-soft">
              Oportuna no pide que confíes en una etiqueta. Cada ficha muestra su fuente, la fecha de
              comprobación, las señales que sostienen la confianza y lo que todavía no está confirmado.
            </p>
            <div className="mt-7 flex flex-wrap gap-2">
              <Link href="/oportunidades" className="btn btn-primary">
                Ver el catálogo
              </Link>
              <Link href="/fuentes" className="btn btn-outline">
                Fuentes y acceso
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-px self-start overflow-hidden border border-line bg-line">
            {[
              { label: "Publicadas", value: methodology.totals.published, note: "con validación superada" },
              { label: "Verificadas", value: methodology.totals.verified, note: "confirmadas o de plataforma de referencia" },
              { label: "En revisión", value: methodology.totals.pending_review, note: "visibles solo para administración" },
              { label: "Fuentes", value: methodology.totals.sources, note: "registradas en el sistema" },
            ].map((stat) => (
              <div key={stat.label} className="bg-paper-raised p-5">
                <p className="eyebrow">{stat.label}</p>
                <p className="mono mt-2 text-3xl text-ink">{stat.value}</p>
                <p className="mt-1 text-[10px] leading-snug text-muted">{stat.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="shell">
        <section className="py-12">
          <div className="flex items-end justify-between gap-4 border-b border-line pb-4">
            <div>
              <p className="eyebrow mb-2">Estados de verificación</p>
              <h2 className="display text-[34px] leading-tight">Cuatro estados, ninguna ambigüedad</h2>
            </div>
            <ShieldCheck size={28} className="hidden text-fern sm:block" />
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {Object.entries(methodology.verification_states).map(([key, label]) => (
              <div key={key} className="border border-line bg-paper-raised p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-display text-[24px] leading-tight">{label}</p>
                  <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">{key}</span>
                </div>
                <p className="mt-2 text-[12px] leading-relaxed text-muted">
                  {STATE_DESCRIPTIONS[key] ?? "Estado del registro."}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-10 py-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow mb-2">Confianza explicable</p>
            <h2 className="font-display text-[34px] leading-tight">Señales observables, no una caja negra</h2>
            <p className="mt-3 text-[13px] leading-relaxed text-muted">
              La puntuación no mide popularidad. Combina autoridad de la fuente, confirmación oficial,
              recencia, coherencia, enlace de registro y contradicciones. La IA no etiqueta un dato como
              “100 % confiable” por leer una página.
            </p>
            <ul className="mt-5 space-y-2">
              {methodology.confidence_signals.map((signal) => (
                <li key={signal} className="flex items-start gap-2 border-b border-line py-2 text-[13px] text-ink-soft">
                  <Check size={14} className="mt-0.5 shrink-0 text-fern" />
                  {signal}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="eyebrow mb-2">Publicación automática</p>
            <h2 className="font-display text-[34px] leading-tight">Estricta por defecto</h2>
            <p className="mt-3 text-[13px] leading-relaxed text-muted">
              {methodology.publication_policy.summary} Un registro dudoso no llega al catálogo público:
              espera en la cola de revisión con su motivo.
            </p>
            <ul className="mt-5 space-y-2">
              {methodology.publication_policy.gates.map((gate) => (
                <li key={gate} className="flex items-start gap-2 border-b border-line py-2 text-[13px] text-ink-soft">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-signal" />
                  {gate}
                </li>
              ))}
            </ul>
            <div className="mt-5 flex gap-3 border border-amber/30 bg-amber-soft/60 p-4 text-[11px] leading-relaxed text-ink-soft">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber" />
              <p>
                Umbral actual de publicación automática:{" "}
                <span className="mono">{Math.round(methodology.publication_policy.min_confidence * 100)}%</span>{" "}
                de confianza y comprobación en los últimos{" "}
                {methodology.publication_policy.max_age_days} días. Todo lo demás pasa a revisión.
              </p>
            </div>
          </div>
        </section>

        <section className="py-10">
          <div className="border-b border-line pb-4">
            <p className="eyebrow mb-2">Ranking</p>
            <h2 className="font-display text-[34px] leading-tight">Por qué aparece primero</h2>
            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-muted">
              Pesos iniciales ajustables mediante pruebas. La confianza actúa como filtro de publicación,
              no solo como criterio de orden. La diversidad evita que veinte hackathons de IA ocupen
              todo el panel.
            </p>
          </div>
          <div className="mt-6 space-y-4">
            {Object.entries(methodology.weights).map(([key, weight]) => {
              const meta = WEIGHT_LABELS[key] ?? { label: key, description: "" };
              return (
                <div key={key} className="grid gap-2 sm:grid-cols-[220px_1fr_60px] sm:items-center">
                  <div>
                    <p className="text-[13px] text-ink">{meta.label}</p>
                    <p className="text-[10px] text-muted">{meta.description}</p>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-paper-deep">
                    <div
                      className="h-full rounded-full bg-signal"
                      style={{ width: `${Math.round(weight * 100)}%` }}
                    />
                  </div>
                  <span className="mono text-right text-[14px] text-ink">{Math.round(weight * 100)}%</span>
                </div>
              );
            })}
          </div>
        </section>

        <section id="fuentes" className="scroll-mt-24 py-10">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
            <div>
              <p className="eyebrow mb-2">Fuentes y acceso</p>
              <h2 className="font-display text-[34px] leading-tight">De dónde sale la información</h2>
            </div>
            <p className="mono text-[10px] uppercase tracking-[0.1em] text-muted">
              {enabledSources.length} activas / {sources.length} registradas
            </p>
          </div>

          <p className="mt-4 max-w-3xl text-[12px] leading-relaxed text-muted">
            Solo se consultan endpoints públicos configurados, con allowlist de dominio, límites de
            frecuencia, User-Agent identificable y respeto de robots.txt. No se eluden protecciones
            anti-bots ni se accede a áreas privadas.
          </p>

          <div className="mt-6 overflow-x-auto border border-line">
            <table className="w-full min-w-[780px] text-left">
              <thead>
                <tr className="border-b border-line bg-paper-deep/40">
                  {["Fuente", "Tipo", "Región", "Autoridad", "Última ejecución", "Estado", "Publicadas"].map((label) => (
                    <th key={label} className="px-3 py-2.5 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.id} className="border-b border-line last:border-b-0">
                    <td className="px-3 py-3">
                      <a
                        href={source.homepage_url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex items-center gap-1 text-[12px] text-ink hover:text-signal-deep"
                      >
                        {source.name}
                        <ExternalLink size={10} />
                      </a>
                      {source.terms_url && (
                        <a
                          href={source.terms_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="mt-0.5 block font-mono text-[9px] uppercase tracking-wider text-muted hover:text-ink"
                        >
                          condiciones
                        </a>
                      )}
                    </td>
                    <td className="px-3 py-3 font-mono text-[10px] uppercase tracking-wider text-muted">{source.kind}</td>
                    <td className="px-3 py-3 text-[11px] text-ink-soft">{source.region}</td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <span className="mono text-[11px]">{source.authority}</span>
                        <span className="h-1 w-12 overflow-hidden rounded-full bg-paper-deep">
                          <span className="block h-full bg-moss" style={{ width: `${source.authority}%` }} />
                        </span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-[10px] text-muted">
                      {source.last_run_at ? formatRelative(source.last_run_at) : "Sin ejecutar"}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex rounded-full border px-2 py-1 font-mono text-[8px] uppercase tracking-wider ${
                          !source.enabled
                            ? "border-line bg-paper-deep text-muted"
                            : source.last_status === "error"
                              ? "border-brick/30 bg-brick-soft text-brick"
                              : "border-fern/30 bg-fern-soft text-fern"
                        }`}
                      >
                        {!source.enabled ? "Deshabilitada" : source.last_status === "error" ? "Error" : "Activa"}
                      </span>
                    </td>
                    <td className="px-3 py-3 mono text-[11px] text-ink-soft">{source.published_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {sources
              .filter((source) => source.access_notes)
              .map((source) => (
                <div key={source.id} className="border border-line bg-paper-raised p-4">
                  <p className="text-[12px] font-medium text-ink">{source.name}</p>
                  <p className="mt-1 text-[10px] leading-relaxed text-muted">{source.access_notes}</p>
                  {source.last_error && (
                    <p className="mt-2 font-mono text-[9px] leading-relaxed text-brick">{source.last_error}</p>
                  )}
                </div>
              ))}
          </div>
        </section>

        <section className="grid gap-10 py-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow mb-2">Política de actualización</p>
            <h2 className="font-display text-[32px] leading-tight">Frecuencia diferenciada</h2>
            <ul className="mt-5 space-y-3">
              {methodology.update_policy.map((item) => (
                <li key={item} className="flex gap-2 border-b border-line pb-3 text-[13px] leading-relaxed text-ink-soft">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-signal" />
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-[11px] leading-relaxed text-muted">
              “Sin cambios detectados” no es lo mismo que “confirmado que sigue abierto”. La ficha
              distingue última comprobación, última verificación y estado de inscripción.
            </p>
          </div>

          <div id="reglas" className="scroll-mt-24">
            <p className="eyebrow mb-2">Reglas del producto</p>
            <h2 className="font-display text-[32px] leading-tight">Diez límites que no cruzamos</h2>
            <ol className="mt-5 space-y-3">
              {PRODUCT_RULES.map((rule, index) => (
                <li key={rule} className="flex gap-3 border-b border-line pb-2.5 text-[12px] leading-relaxed text-ink-soft">
                  <span className="mono w-5 shrink-0 text-[10px] text-muted">{String(index + 1).padStart(2, "0")}</span>
                  {rule}
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="my-8 grid gap-6 border border-line bg-paper-raised p-6 sm:p-8 lg:grid-cols-[1fr_1fr]">
          <div>
            <div className="flex items-center gap-2">
              <Info size={16} className="text-muted" />
              <p className="eyebrow">Reportar un error</p>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
              Si una ficha está mal, la fuente original siempre prevalece. Puedes escribirnos con el
              enlace y el dato a corregir; el cambio queda registrado en el historial.
            </p>
            <a
              href="mailto:hello@oportuna.dev?subject=Correcci%C3%B3n%20de%20datos%20en%20Oportuna"
              className="btn btn-outline mt-4"
            >
              Escribir al equipo
            </a>
          </div>
          <div className="border-l border-line pl-6">
            <div className="flex items-center gap-2">
              <RadarMark size={16} className="text-signal" />
              <p className="eyebrow">Última comprobación global</p>
            </div>
            <p className="mt-2 font-display text-[24px] leading-tight text-ink">
              {methodology.totals.published > 0 ? "Datos reales en el catálogo" : "Catálogo en preparación"}
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              {methodology.totals.sources} fuentes registradas · {methodology.totals.verified} registros
              verificados · {formatDateTime(lastRun)}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
