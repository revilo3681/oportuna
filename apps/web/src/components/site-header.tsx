import Link from "next/link";

import { RadarMark } from "@/components/icons";
import { NavLinks } from "@/components/nav-links";
import { MobileNav, SessionActions } from "@/components/session-actions";
import { getSessionUser } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Panel" },
  { href: "/oportunidades", label: "Catálogo" },
  { href: "/calendario", label: "Calendario" },
  { href: "/asistente", label: "Asistente IA" },
  { href: "/metodologia", label: "Metodología" },
];

export async function SiteHeader() {
  const user = await getSessionUser();

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/90 backdrop-blur-md">
      <div className="shell flex h-[70px] items-center justify-between gap-4">
        <Link href="/" className="group flex items-center gap-3" aria-label="Oportuna, inicio">
          <span className="relative grid size-9 place-items-center rounded-full border border-ink/15 bg-paper-raised">
            <RadarMark size={18} className="text-signal transition-transform duration-500 group-hover:rotate-45" />
            <span className="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-signal" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="display text-[27px] tracking-[-0.02em] text-ink">oportuna</span>
            <span className="mt-1 hidden font-mono text-[8px] uppercase tracking-[0.22em] text-muted sm:block">
              Global tech opportunity intelligence
            </span>
          </span>
        </Link>

        <NavLinks items={NAV_ITEMS} className="hidden lg:flex" />

        <div className="flex items-center gap-2">
          <div className="hidden md:block">
            <SessionActions user={user} compact />
          </div>
          <MobileNav user={user} items={NAV_ITEMS} />
        </div>
      </div>
    </header>
  );
}
