"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { ArrowUpRight, Search, Sparkle } from "@/components/icons";
import { TrustBadge } from "@/components/trust-badge";
import type { AssistantAnswer } from "@/lib/types";

const SUGGESTIONS = [
  "¿Qué hackathons online de IA puedo hacer este mes gratis?",
  "Becas y fellowships abiertas con presupuesto cero",
  "Eventos de ciberseguridad en las próximas 4 semanas",
  "Programas de startups en Latinoamérica",
];

export function AssistantPanel({ userName }: { userName: string | null }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  async function ask(value: string) {
    const text = value.trim();
    if (text.length < 3) return;
    setPending(true);
    setError(null);
    setAnswer(null);
    try {
      const response = await fetch("/api/assistant/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question: text }),
      });
      if (!response.ok) {
        let detail = "No se pudo responder.";
        try {
          const payload = await response.json();
          if (typeof payload.detail === "string") detail = payload.detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      setAnswer((await response.json()) as AssistantAnswer);
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
        className="border border-line bg-paper-raised p-4 sm:p-5"
      >
        <label className="label" htmlFor="assistant-question">
          Tu pregunta
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              id="assistant-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ej. hackathons de IA online este mes con presupuesto cero"
              className="field !py-3 !pl-9"
              maxLength={500}
            />
          </div>
          <button type="submit" disabled={pending || question.trim().length < 3} className="btn btn-primary !py-3">
            {pending ? "Buscando…" : "Preguntar"}
            {!pending && <ArrowUpRight size={15} />}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setQuestion(suggestion);
                void ask(suggestion);
              }}
              className="rounded-full border border-line bg-paper px-2.5 py-1 text-[10px] text-muted transition-colors hover:border-ink/40 hover:text-ink"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </form>

      {error && (
        <p className="mt-4 border border-brick/30 bg-brick-soft p-3 text-[12px] text-brick" role="alert">
          {error}
        </p>
      )}

      <div ref={resultRef} className="mt-6 scroll-mt-24">
        {pending && (
          <div className="space-y-3 border border-line bg-paper-raised p-6">
            <div className="h-3 w-2/3 animate-pulse rounded bg-paper-deep" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-paper-deep" />
            <div className="h-3 w-3/4 animate-pulse rounded bg-paper-deep" />
            <p className="pt-2 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
              Consultando el catálogo verificado…
            </p>
          </div>
        )}

        {answer && !pending && (
          <div className="border border-line bg-paper-raised">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
              <span className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
                <Sparkle size={12} className="text-signal" />
                Respuesta con datos del catálogo
              </span>
              <span className="rounded-full border border-fern/30 bg-fern-soft px-2 py-1 font-mono text-[8px] uppercase tracking-wider text-fern">
                {answer.grounding.uses_llm ? "LLM" : "Sin LLM · reglas"}
              </span>
            </div>
            <div className="p-5 sm:p-6">
              <p className="whitespace-pre-line text-[14px] leading-[1.75] text-ink-soft">{answer.answer}</p>

              {answer.items.length > 0 && (
                <div className="mt-6 space-y-2">
                  {answer.items.map((item) => (
                    <Link
                      key={item.id}
                      href={`/oportunidades/${item.slug}`}
                      className="flex flex-col gap-2 border border-line bg-paper p-3 transition-colors hover:border-ink/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0">
                        <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                          {item.category.label} · {item.modality.label} · {item.deadline.label}
                        </p>
                        <p className="mt-1 truncate text-[13px] text-ink">{item.title}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <TrustBadge verification={item.verification} showConfidence={false} />
                        <span className="mono text-[10px] text-muted">{item.event_range}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}

              {answer.citations.length > 0 && (
                <div className="mt-5 border-t border-line pt-4">
                  <p className="eyebrow">Fuentes citadas</p>
                  <ul className="mt-2 space-y-1.5">
                    {answer.citations.map((citation) => (
                      <li key={citation.slug} className="text-[11px] text-muted">
                        <Link href={citation.path} className="text-ink-soft underline decoration-line-strong underline-offset-2 hover:text-signal-deep">
                          {citation.title}
                        </Link>{" "}
                        · {citation.source ?? "fuente sin registrar"}{" "}
                        <a
                          href={citation.official_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex items-center gap-0.5 underline decoration-line-strong underline-offset-2 hover:text-signal-deep"
                        >
                          original <ArrowUpRight size={10} />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="mt-5 border-t border-line pt-3 text-[10px] leading-relaxed text-muted">
                {answer.grounding.note} No se afirma elegibilidad sin contrastar requisitos.
                {userName ? ` Búsqueda personalizada para ${userName}.` : " Inicia sesión para usar tu perfil y tu disponibilidad."}
              </p>
            </div>
          </div>
        )}
      </div>

      {!answer && !pending && (
        <div className="mt-6 border border-dashed border-line-strong p-6">
          <p className="font-display text-[22px] leading-snug text-ink">
            Haz una pregunta concreta y te devolveremos coincidencias reales, no una lista inventada.
          </p>
          <p className="mt-2 max-w-xl text-[12px] leading-relaxed text-muted">
            El asistente entiende categoría, tecnología, modalidad, precio, país y horizonte temporal.
            Cuando no hay datos, lo dice. No es un generador de eventos: es una consulta sobre el
            catálogo publicado.
          </p>
        </div>
      )}
    </div>
  );
}
