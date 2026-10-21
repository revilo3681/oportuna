"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Bookmark, Check, ExternalLink } from "@/components/icons";
import { cn } from "@/lib/format";

const STATES = [
  { value: "saved", label: "Guardada" },
  { value: "following", label: "Siguiendo" },
  { value: "applied", label: "Me postulé" },
  { value: "accepted", label: "Aceptada" },
  { value: "attended", label: "Asistí" },
  { value: "dismissed", label: "Descartada" },
];

export function DetailActions({
  slug,
  initialState,
  authenticated,
}: {
  slug: string;
  initialState: string | null;
  authenticated: boolean;
}) {
  const router = useRouter();
  const [state, setState] = useState<string | null>(initialState);
  const [useful, setUseful] = useState<boolean | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saved = state !== null;

  function requireAuth(): boolean {
    if (authenticated) return true;
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/entrar?next=${next}`;
    return false;
  }

  async function save() {
    if (!requireAuth()) return;
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/saved/${slug}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ state: "saved" }),
      });
      if (!response.ok) throw new Error("No se pudo guardar");
      setState("saved");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function update(nextState: string | null) {
    if (!requireAuth()) return;
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/saved/${slug}`, {
        method: nextState ? "PATCH" : "DELETE",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: nextState ? JSON.stringify({ state: nextState, useful }) : undefined,
      });
      if (!response.ok) throw new Error("No se pudo actualizar");
      setState(nextState);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-3">
      {!saved ? (
        <button type="button" onClick={save} disabled={pending} className="btn btn-primary w-full">
          <Bookmark size={15} />
          {pending ? "Guardando…" : "Guardar en mi radar"}
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={() => update(null)}
            disabled={pending}
            className="btn btn-outline w-full"
          >
            <Check size={15} />
            En tu radar
          </button>
          <label className="label !mb-1" htmlFor="tracking-state">
            Seguimiento
          </label>
          <select
            id="tracking-state"
            className="field"
            value={state ?? "saved"}
            onChange={(event) => update(event.target.value)}
            disabled={pending}
          >
            {STATES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-[11px] text-muted">
            <input
              type="checkbox"
              className="size-3.5 accent-signal"
              checked={useful === true}
              onChange={(event) => {
                const next = event.target.checked;
                setUseful(next);
                void update(state ?? "saved");
              }}
            />
            Esta oportunidad me resultó útil
          </label>
          <p className="text-[10px] leading-relaxed text-muted">
            Tu feedback se usa para mejorar el ranking. No inscribimos por ti.
          </p>
        </>
      )}
      {error && <p className="text-[11px] text-brick">{error}</p>}
      <a
        href="#fuente"
        className={cn("flex items-center justify-center gap-1.5 pt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted hover:text-ink")}
      >
        Ver procedencia <ExternalLink size={11} />
      </a>
    </div>
  );
}
