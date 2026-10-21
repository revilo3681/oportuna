"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/format";

export type NavItem = { href: string; label: string };

export function NavLinks({ items, className }: { items: NavItem[]; className?: string }) {
  const pathname = usePathname();

  return (
    <nav className={cn("items-center gap-0.5", className)} aria-label="Navegación principal">
      {items.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "relative rounded-full px-3 py-2 text-[13px] transition-colors",
              active ? "text-ink" : "text-muted hover:text-ink",
            )}
            aria-current={active ? "page" : undefined}
          >
            {item.label}
            <span
              className={cn(
                "absolute inset-x-3 -bottom-0.5 h-px bg-signal transition-opacity",
                active ? "opacity-100" : "opacity-0",
              )}
            />
          </Link>
        );
      })}
    </nav>
  );
}
