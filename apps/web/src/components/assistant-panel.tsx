"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ArrowUpRight, Check, Search, Sparkle } from "@/components/icons";
import { TrustBadge } from "@/components/trust-badge";
import { cn } from "@/lib/format";
import type { AssistantAnswer, AssistantStatus } from "@/lib/types";

const SUGGESTIONS = [
  "¿Qué hackathons de IA online gratis puedo hacer este mes?",
  "Becas y fellowships abiertas con presupuesto cero",
  "Eventos de ciberseguridad en las próximas 4 semanas",
  "Programas de startups en Latinoamérica",
];

export function AssistantPanel({
  userName,
  initialStatus,
}: {
  userName: string | null;
  initialStatus: AssistantStatus | null;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [status, setStatus] = useState<AssistantStatus | null>(initialStatus);
  const [useAI, setUseAI] = useState(Boolean(initialStatus?.available));
  const [pending, setPending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialStatus) return;
    let alive = true;
    fetch("/api/assistant/status", { credentials: "include" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload: AssistantStatus | null) => {
        if (!alive || !payload) return;
        setStatus(payload);
        setUseAI(Boolean(payload.available));
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [initialStatus]);

  useEffect(() => {
    if (!pending) return;
    const started = Date.now();
    setElapsed(0);
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 500);
    return () => window.clearInterval(timer);
  }, [pending]);

  async function ask(value: string) {
    const text = value.trim();
    if (text.length < 3) return;
    setPending(true);
    setError(null);
    setAnswer(null);
    try {
      const response = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question: text, use_ai: useAI && Boolean(status?.available) }),
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

  const modeLabel = answer
    ? answer.grounding.uses_llm
      ? "IA local"
      : answer.grounding.mode.includes("fallback")
        ? "Fallback por reglas"
        : "Reglas del catálogo"
    : null;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 border border-line bg-[var(--color-paper-raised)] px-4 py-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "size-2 rounded-full",
              status?.available ? "bg-fern" : "bg-amber",
            )}
          />
          <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
            {status?.available
              ? `IA local · ${status.model ?? "modelo listo"}`
              : status?.enabled
                ? "IA local no disponible · modo reglas"
                : "IA local desactivada · modo reglas"}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-[11px] text-muted">
            <input
              type="checkbox"
              className="size-3.5 accent-signal"
              checked={useAI}
              disabled={!status?.available}
              onChange={(event) => setUseAI(event.target.checked)}
            />
            Usar IA local
          </label>
          <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-muted">
            Ollama · sin nube
          </span>
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
        className="mt-3 border border-line bg-[var(--color-paper-raised)] p-4 sm:p-5"
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
            {pending ? "Pensando…" : "Preguntar"}
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
        <p className="mt-3 flex items-center gap-1.5 text-[10px] text-muted">
          <Check size={11} className="text-fern" />
          Tu pregunta se procesa en este equipo con Ollama. No se envía a una API externa.
        </p>
      </form>

      {error && (
        <p className="mt-4 border border-brick/30 bg-brick-soft p-3 text-[12px] text-brick" role="alert">
          {error}
        </p>
      )}

      <div ref={resultRef} className="mt-6 scroll-mt-24">
        {pending && (
          <div className="border border-line bg-[var(--color-paper-raised)] p-6">
            <div className="flex items-center gap-3">
              <span className="relative grid size-9 place-items-center rounded-full border border-signal/30 bg-signal-soft">
                <Sparkle size={16} className="text-signal-deep" />
                <span className="absolute inset-0 animate-ping rounded-full border border-signal/30" />
              </span>
              <div>
                <p className="text-[13px] text-ink">
                  {elapsed < 2 ? "Consultando el catálogo verificado…" : `Razonando con ${status?.model ?? "el modelo local"}…`}
                </p>
                <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                  {elapsed}s · la primera respuesta suele tardar 20–60 s en local
                </p>
              </div>
            </div>
            <div className="mt-5 space-y-2">
              <div className="h-2.5 w-3/4 animate-pulse rounded bg-paper-deep" />
              <div className="h-2.5 w-1/2 animate-pulse rounded bg-paper-deep" />
              <div className="h-2.5 w-2/3 animate-pulse rounded bg-paper-deep" />
            </div>
            <div className="mt-5 flex gap-2 text-[10px] text-muted">
              <span className="rounded-full border border-line px-2 py-1">catálogo</span>
              <span className="rounded-full border border-line px-2 py-1">embeddings</span>
              <span className="rounded-full border border-line px-2 py-1">citas</span>
            </div>
          </div>
        )}

        {answer && !pending && (
          <div className="border border-line bg-[var(--color-paper-raised)]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
                  <Sparkle size={12} className="text-signal" />
                  {modeLabel}
                </span>
                {answer.grounding.model && (
                  <span className="chip">{answer.grounding.model}</span>
                )}
                {typeof answer.grounding.latency_ms === "number" && answer.grounding.uses_llm && (
                  <span className="chip">{(answer.grounding.latency_ms / 1000).toFixed(1)} s</span>
                )}
                {answer.grounding.semantic_search && (
                  <span className="chip">búsqueda semántica</span>
                )}
              </div>
              <span
                className={cn(
                  "rounded-full border px-2 py-1 font-mono text-[8px] uppercase tracking-wider",
                  answer.grounding.uses_llm
                    ? "border-fern/30 bg-fern-soft text-fern"
                    : "border-amber/30 bg-amber-soft text-amber",
                )}
              >
                {answer.grounding.uses_llm ? "IA local activa" : "sin IA · determinista"}
              </span>
            </div>

            <div className="p-5 sm:p-6">
              <p className="whitespace-pre-line text-[14px] leading-[1.8] text-ink-soft">{answer.answer}</p>

              {answer.items.length > 0 && (
                <div className="mt-6 space-y-2">
                  <p className="eyebrow">Oportunidades citadas</p>
                  {answer.items.map((item, index) => (
                    <Link
                      key={item.id}
                      href={`/oportunidades/${item.slug}`}
                      className="flex gap-3 border border-line bg-paper p-3 transition-colors hover:border-ink/30"
                    >
                      <span className="mono grid size-6 shrink-0 place-items-center rounded-full border border-line-strong bg-[var(--color-paper-raised)] text-[10px] text-ink">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                            {item.category.label} · {item.modality.label} · {item.deadline.label}
                          </p>
                          <TrustBadge verification={item.verification} showConfidence={false} />
                        </div>
                        <p className="mt-1 truncate text-[13px] text-ink">{item.title}</p>
                        <p className="mt-0.5 truncate text-[10px] text-muted">
                          {item.event_range} · {item.source?.name ?? "fuente original"}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}

              {answer.citations.length > 0 && (
                <div className="mt-5 border-t border-line pt-4">
                  <p className="eyebrow">Fuentes citadas</p>
                  <ul className="mt-2 space-y-1.5">
                    {answer.citations.map((citation, index) => (
                      <li key={citation.slug} className="flex items-start gap-2 text-[11px] text-muted">
                        <span className="mono shrink-0 text-ink-soft">[{index + 1}]</span>
                        <span>
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
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="mt-5 border-t border-line pt-3 text-[10px] leading-relaxed text-muted">
                {answer.grounding.note} No se afirma elegibilidad sin contrastar requisitos.
                {userName
                  ? ` Búsqueda personalizada para ${userName}.`
                  : " Inicia sesión para usar tu perfil y tu disponibilidad."}
              </p>
            </div>
          </div>
        )}
      </div>

      {!answer && !pending && (
        <div className="mt-6 border border-dashed border-line-strong p-6">
          <p className="font-display text-[22px] leading-snug text-ink">
            Pregunta en lenguaje natural y la IA local decide con el catálogo, no con su memoria.
          </p>
          <p className="mt-2 max-w-xl text-[12px] leading-relaxed text-muted">
            El modelo recibe solo oportunidades publicadas, numeradas y sin instrucciones ocultas.
            Devuelve una respuesta breve con citas. Si no hay datos, lo dice; si el modelo falla,
            respondemos con reglas y te lo indicamos.
          </p>
        </div>
      )}
    </div>
  );
}
