"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Bookmark } from "@/components/icons";
import { cn } from "@/lib/format";

export function SaveButton({
  slug,
  initiallySaved,
  authenticated,
  variant = "icon",
  className,
}: {
  slug: string;
  initiallySaved: boolean;
  authenticated: boolean;
  variant?: "icon" | "full";
  className?: string;
}) {
  const router = useRouter();
  const [saved, setSaved] = useState(initiallySaved);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (!authenticated) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/entrar?next=${next}`;
      return;
    }
    setError(null);
    const nextSaved = !saved;
    setSaved(nextSaved);
    try {
      const response = await fetch(`/api/saved/${slug}`, {
        method: nextSaved ? "PUT" : "DELETE",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: nextSaved ? JSON.stringify({ state: "saved" }) : undefined,
      });
      if (!response.ok) {
        throw new Error(response.status === 401 ? "Inicia sesión de nuevo" : "No se pudo guardar");
      }
      startTransition(() => router.refresh());
    } catch (err) {
      setSaved(!nextSaved);
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <button
        type="button"
        onClick={toggle}
        disabled={pending}
        aria-pressed={saved}
        aria-label={saved ? "Quitar de guardadas" : "Guardar oportunidad"}
        title={saved ? "Guardada" : "Guardar"}
        className={cn(
          "inline-flex items-center gap-2 rounded-full border transition-colors disabled:opacity-60",
          variant === "icon" ? "size-8 justify-center" : "px-3 py-2 text-[12px]",
          saved
            ? "border-signal/30 bg-signal-soft text-signal-deep"
            : "border-line bg-paper-raised text-muted hover:border-ink/40 hover:text-ink",
        )}
      >
        <Bookmark size={14} className={saved ? "fill-current" : undefined} />
        {variant === "full" && <span>{saved ? "Guardada" : "Guardar"}</span>}
      </button>
      {error && <span className="text-[11px] text-brick">{error}</span>}
    </div>
  );
}
