import Link from "next/link";

import { ArrowUpRight, RadarMark } from "@/components/icons";

const COLUMNS = [
  {
    title: "Producto",
    links: [
      { href: "/", label: "Panel diario" },
      { href: "/oportunidades", label: "Catálogo" },
      { href: "/calendario", label: "Calendario" },
      { href: "/asistente", label: "Asistente" },
    ],
  },
  {
    title: "Confianza",
    links: [
      { href: "/metodologia", label: "Método de verificación" },
      { href: "/metodologia#fuentes", label: "Fuentes y acceso" },
      { href: "/metodologia#reglas", label: "Reglas del producto" },
    ],
  },
  {
    title: "Cuenta",
    links: [
      { href: "/perfil", label: "Perfil y disponibilidad" },
      { href: "/entrar", label: "Entrar" },
      { href: "/registro", label: "Crear cuenta" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 bg-ink text-paper-raised">
      <div className="shell grid gap-12 py-16 md:grid-cols-[1.4fr_2fr]">
        <div>
          <Link href="/" className="inline-flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-full border border-paper-raised/25">
              <RadarMark size={18} className="text-signal" />
            </span>
            <span className="display text-[30px] leading-none">oportuna</span>
          </Link>
          <p className="mt-6 max-w-sm font-display text-2xl leading-[1.15] text-paper-raised/90">
            Menos tiempo buscando.
            <br />
            <span className="italic text-signal">Mejores decisiones</span> sobre dónde invertir tu tiempo.
          </p>
          <p className="mt-6 max-w-sm text-[13px] leading-relaxed text-paper-raised/55">
            Inteligencia de oportunidades tecnológicas con procedencia visible. Sin eventos inventados,
            sin fechas inferidas presentadas como confirmadas.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          {COLUMNS.map((column) => (
            <div key={column.title}>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-paper-raised/40">
                {column.title}
              </p>
              <ul className="mt-4 space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[13px] text-paper-raised/70 transition-colors hover:text-signal"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-paper-raised/10">
        <div className="shell flex flex-col gap-3 py-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-paper-raised/40">
            Oportuna v0.1 · Datos con fuente y fecha de comprobación
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-paper-raised/45">
            <span>No afiliado a las plataformas listadas</span>
            <a
              href="https://github.com/oportuna"
              className="inline-flex items-center gap-1 hover:text-paper-raised"
              rel="noreferrer noopener"
              target="_blank"
            >
              Código y método <ArrowUpRight size={12} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
