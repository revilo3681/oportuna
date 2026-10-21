import type { ReactNode } from "react";

import { RadarMark } from "@/components/icons";

export function AuthLayout({
  eyebrow,
  title,
  description,
  sideTitle,
  sideBody,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  sideTitle: ReactNode;
  sideBody: string;
  children: ReactNode;
}) {
  return (
    <div className="grid min-h-[calc(100vh-70px)] lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden overflow-hidden bg-ink p-12 text-paper-raised lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          <div className="absolute left-1/2 top-1/2 size-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-paper-raised/10" />
          <div className="absolute left-1/2 top-1/2 size-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-paper-raised/10" />
          <div className="absolute left-1/2 top-1/2 size-[240px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-paper-raised/15" />
          <div className="absolute left-1/2 top-1/2 h-px w-full -translate-y-1/2 bg-paper-raised/10" />
          <div className="absolute left-1/2 top-1/2 h-full w-px -translate-x-1/2 bg-paper-raised/10" />
          <div className="absolute inset-0 grain opacity-[0.14]" />
        </div>

        <div className="relative flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-full border border-paper-raised/25">
            <RadarMark size={18} className="text-signal" />
          </span>
          <span className="display text-[30px] leading-none">oportuna</span>
        </div>

        <div className="relative max-w-md">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-signal">Radar personal</p>
          <h2 className="mt-4 font-display text-[44px] leading-[1.02]">{sideTitle}</h2>
          <p className="mt-5 text-[13px] leading-relaxed text-paper-raised/60">{sideBody}</p>
          <ul className="mt-8 space-y-3 border-t border-paper-raised/10 pt-6 text-[11px] text-paper-raised/60">
            <li className="flex gap-2.5">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-signal" />
              Tu perfil es opcional: el catálogo completo sigue abierto.
            </li>
            <li className="flex gap-2.5">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-signal" />
              Nunca inscribimos ni pagamos en tu nombre.
            </li>
            <li className="flex gap-2.5">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-signal" />
              Puedes exportar tu calendario y borrar tus datos.
            </li>
          </ul>
        </div>

        <p className="relative font-mono text-[9px] uppercase tracking-[0.14em] text-paper-raised/30">
          Global tech opportunity intelligence · v0.1
        </p>
      </div>

      <div className="flex items-center justify-center px-5 py-14 sm:px-8">
        <div className="w-full max-w-[420px]">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="display mt-3 text-[42px] leading-[0.98] text-ink sm:text-[50px]">{title}</h1>
          <p className="mt-3 text-[13px] leading-relaxed text-muted">{description}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
