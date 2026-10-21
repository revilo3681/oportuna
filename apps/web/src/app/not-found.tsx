import Link from "next/link";

import { RadarMark } from "@/components/icons";

export default function NotFound() {
  return (
    <div className="shell flex min-h-[60vh] flex-col items-center justify-center py-20 text-center">
      <RadarMark size={40} className="text-line-strong" />
      <p className="eyebrow mt-6">Error 404 · fuera de cobertura</p>
      <h1 className="display mt-4 text-[48px] leading-none sm:text-[64px]">Esta señal no existe.</h1>
      <p className="mt-4 max-w-md text-[13px] leading-relaxed text-muted">
        La oportunidad pudo cerrarse, cambiar de enlace o no haber sido publicada. No mostraremos una
        ficha inventada para llenar el hueco.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        <Link href="/oportunidades" className="btn btn-primary">
          Volver al catálogo
        </Link>
        <Link href="/" className="btn btn-outline">
          Ir al panel
        </Link>
      </div>
    </div>
  );
}
