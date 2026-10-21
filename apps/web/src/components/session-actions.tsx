"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Close, LogOut, Menu, RadarMark } from "@/components/icons";
import { NavLinks } from "@/components/nav-links";
import { cn, initals } from "@/lib/format";
import type { SessionUser } from "@/lib/types";

export function SessionActions({
  user,
  compact = false,
}: {
  user: SessionUser | null;
  compact?: boolean;
}) {
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } finally {
      window.location.href = "/";
    }
  }

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link href="/entrar" className="hidden text-[13px] text-ink-soft hover:text-signal sm:block">
          Entrar
        </Link>
        <Link href="/registro" className="btn btn-primary !px-4 !py-2.5">
          Crear cuenta
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <Link
        href="/perfil"
        className="group flex items-center gap-2 rounded-full border border-line bg-paper-raised py-1 pl-1 pr-3 transition-colors hover:border-ink/40"
        title="Tu perfil y disponibilidad"
      >
        <span className="grid size-7 place-items-center rounded-full bg-ink text-[10px] font-medium text-paper-raised">
          {initals(user.display_name || user.email)}
        </span>
        {!compact && (
          <span className="hidden max-w-[120px] truncate text-[12px] text-ink-soft md:block">
            {user.display_name || user.email}
          </span>
        )}
      </Link>
      {user.role === "admin" && (
        <Link
          href="/admin"
          className="hidden rounded-full border border-signal/30 bg-signal-soft px-3 py-2 font-mono text-[10px] uppercase tracking-[0.1em] text-signal-deep md:block"
        >
          Admin
        </Link>
      )}
      <button
        type="button"
        onClick={logout}
        disabled={pending}
        className="grid size-9 place-items-center rounded-full text-muted transition-colors hover:bg-paper-deep hover:text-ink"
        aria-label="Cerrar sesión"
        title="Cerrar sesión"
      >
        <LogOut size={16} />
      </button>
    </div>
  );
}

export function MobileNav({ user, items }: { user: SessionUser | null; items: { href: string; label: string }[] }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="grid size-9 place-items-center rounded-full border border-line text-ink"
        aria-expanded={open}
        aria-label={open ? "Cerrar menú" : "Abrir menú"}
      >
        {open ? <Close size={18} /> : <Menu size={18} />}
      </button>

      {open && (
        <div className="fixed inset-x-0 top-[70px] z-40 max-h-[calc(100vh-70px)] overflow-y-auto border-b border-line bg-paper px-5 pb-8 pt-6 shadow-[0_20px_40px_rgba(17,19,16,0.08)]">
          <div className="mb-6 flex items-center gap-2 text-muted">
            <RadarMark size={16} className="text-signal" />
            <span className="eyebrow">Navegación</span>
          </div>
          <NavLinks items={items} className="flex flex-col items-start gap-1" />
          <div className="mt-6 border-t border-line pt-6">
            {user ? (
              <div className="flex flex-col gap-3">
                <Link href="/perfil" className="btn btn-outline w-full justify-between">
                  Mi perfil
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    {Math.round(user.profile.completeness)}%
                  </span>
                </Link>
                {user.role === "admin" && (
                  <Link href="/admin" className="btn btn-outline w-full justify-start">
                    Consola de administración
                  </Link>
                )}
                <SessionActions user={user} compact />
              </div>
            ) : (
              <div className="grid gap-2">
                <Link href="/entrar" className="btn btn-outline w-full">
                  Entrar
                </Link>
                <Link href="/registro" className="btn btn-primary w-full">
                  Crear cuenta
                </Link>
              </div>
            )}
          </div>
          <p className={cn("eyebrow mt-8 leading-relaxed")}>
            Datos verificables · Fuente original visible · Sin inscripciones automáticas
          </p>
        </div>
      )}
    </div>
  );
}
