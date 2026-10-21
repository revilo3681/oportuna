"use client";

import Link from "next/link";

import { AlertTriangle, Refresh } from "@/components/icons";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="shell flex min-h-[60vh] flex-col items-center justify-center py-20 text-center">
      <AlertTriangle size={36} className="text-amber" />
      <p className="eyebrow mt-6">Algo falló al leer la señal</p>
      <h1 className="display mt-4 text-[44px] leading-none sm:text-[56px]">No pudimos completar la carga.</h1>
      <p className="mt-4 max-w-md text-[13px] leading-relaxed text-muted">
        Puede ser un problema temporal de la API o de la red. No mostraremos datos de demostración como
        si fueran oportunidades reales.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        <button type="button" onClick={reset} className="btn btn-primary">
          <Refresh size={14} />
          Reintentar
        </button>
        <Link href="/" className="btn btn-outline">
          Ir al panel
        </Link>
      </div>
      {error.digest && <p className="mono mt-6 text-[10px] text-muted">referencia: {error.digest}</p>}
    </div>
  );
}
