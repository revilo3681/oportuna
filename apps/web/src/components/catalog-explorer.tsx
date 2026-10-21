"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { OpportunityCard } from "@/components/opportunity-card";
import { Search, Sliders, Sparkle } from "@/components/icons";
import {
  CatalogFilterState,
  EMPTY_FILTERS,
  SORT_OPTIONS,
  countActiveFilters,
  filtersToParams,
} from "@/lib/catalog-filters";
import { cn } from "@/lib/format";
import type { CatalogResponse, Facet } from "@/lib/types";

type Facets = CatalogResponse["facets"];

function SearchField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="relative">
      <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
      <input
        id="catalog-search"
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="IA, hackathon, beca, Python…"
        className="field !py-3 !pl-10 !pr-20"
        aria-label="Buscar oportunidades"
        autoComplete="off"
      />
      <span className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-line px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-muted sm:block">
        en vivo
      </span>
    </div>
  );
}

function ToggleChip({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11.5px] transition-colors",
        active
          ? "border-ink bg-ink text-[var(--color-paper-raised)]"
          : "border-line bg-paper-raised text-ink-soft hover:border-ink/40 hover:text-ink",
      )}
    >
      {active ? <span className="text-[10px] leading-none">×</span> : null}
      {label}
      {typeof count === "number" && count > 0 && (
        <span className={cn("font-mono text-[9px]", active ? "opacity-60" : "text-muted")}>{count}</span>
      )}
    </button>
  );
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className="field">
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function CatalogExplorer({
  facets,
  initialFilters,
  initialData,
  savedSlugs = [],
  authenticated,
}: {
  facets: Facets;
  initialFilters: CatalogFilterState;
  initialData: CatalogResponse;
  savedSlugs?: string[];
  authenticated: boolean;
}) {
  const router = useRouter();
  const [filters, setFilters] = useState<CatalogFilterState>(initialFilters);
  const [data, setData] = useState<CatalogResponse>(initialData);
  const [page, setPage] = useState(initialData.page);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debouncedQ, setDebouncedQ] = useState(initialFilters.q);
  const [showFilters, setShowFilters] = useState(false);
  const savedSet = new Set(savedSlugs);
  const abortRef = useRef<AbortController | null>(null);
  const firstRun = useRef(true);
  const [, startTransition] = useTransition();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(filters.q), 350);
    return () => clearTimeout(timer);
  }, [filters.q]);

  const fetchPage = useCallback(
    async (nextFilters: CatalogFilterState, nextPage: number) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);
      try {
        const params = filtersToParams(nextFilters, nextPage);
        params.set("page_size", "24");
        const response = await fetch(`/api/opportunities?${params.toString()}`, {
          signal: controller.signal,
          credentials: "include",
        });
        if (!response.ok) throw new Error(`La búsqueda falló (${response.status})`);
        const payload = (await response.json()) as CatalogResponse;
        setData(payload);
        setPage(payload.page);
        const query = filtersToParams(nextFilters, payload.page).toString();
        window.history.replaceState(null, "", query ? `/oportunidades?${query}` : "/oportunidades");
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError(err instanceof Error ? err.message : "Error inesperado");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    const effective = { ...filters, q: debouncedQ };
    if (firstRun.current) {
      firstRun.current = false;
      const initialQuery = filtersToParams(initialFilters, initialData.page).toString();
      const loadedQuery = filtersToParams(effective, initialData.page).toString();
      if (initialQuery === loadedQuery) return;
    }
    void fetchPage(effective, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ, filters.category, filters.tech, filters.modality, filters.country, filters.language, filters.cost, filters.days, filters.sort, filters.includeClosed]);

  function update<K extends keyof CatalogFilterState>(key: K, value: CatalogFilterState[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function toggleList(key: "category" | "tech", value: string) {
    setFilters((current) => {
      const list = current[key];
      return {
        ...current,
        [key]: list.includes(value) ? list.filter((item) => item !== value) : [...list, value],
      };
    });
  }

  function clearAll() {
    setFilters({ ...EMPTY_FILTERS });
    setDebouncedQ("");
    startTransition(() => router.refresh());
  }

  function goToPage(target: number) {
    void fetchPage({ ...filters, q: debouncedQ }, target);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const active = countActiveFilters({ ...filters, q: debouncedQ });
  const labels = new Map<string, string>();
  facets.category.forEach((facet: Facet) => labels.set(`category:${facet.key}`, facet.label ?? facet.key));
  facets.tech.forEach((facet: Facet) => labels.set(`tech:${facet.key}`, facet.label ?? facet.key));
  facets.modality.forEach((facet: Facet) => labels.set(`modality:${facet.key}`, facet.label ?? facet.key));
  facets.country.forEach((facet: Facet) => labels.set(`country:${facet.key}`, facet.label ?? facet.key));
  facets.language.forEach((facet: Facet) => labels.set(`language:${facet.key}`, facet.label ?? facet.key));

  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (debouncedQ.trim()) {
    chips.push({ key: "q", label: `“${debouncedQ.trim()}”`, clear: () => { update("q", ""); setDebouncedQ(""); } });
  }
  filters.category.forEach((value) =>
    chips.push({ key: `category:${value}`, label: labels.get(`category:${value}`) ?? value, clear: () => toggleList("category", value) }),
  );
  filters.tech.forEach((value) =>
    chips.push({ key: `tech:${value}`, label: labels.get(`tech:${value}`) ?? value, clear: () => toggleList("tech", value) }),
  );
  if (filters.modality)
    chips.push({ key: "modality", label: labels.get(`modality:${filters.modality}`) ?? filters.modality, clear: () => update("modality", "") });
  if (filters.country)
    chips.push({ key: "country", label: labels.get(`country:${filters.country}`) ?? filters.country, clear: () => update("country", "") });
  if (filters.language)
    chips.push({ key: "language", label: labels.get(`language:${filters.language}`) ?? filters.language, clear: () => update("language", "") });
  if (filters.cost)
    chips.push({ key: "cost", label: filters.cost === "free" ? "Gratis" : "De pago", clear: () => update("cost", "") });
  if (filters.days)
    chips.push({ key: "days", label: `Cierra en ${filters.days} días`, clear: () => update("days", "") });
  if (filters.includeClosed)
    chips.push({ key: "closed", label: "Incluye cerradas", clear: () => update("includeClosed", false) });

  const start = data.total === 0 ? 0 : (page - 1) * data.page_size + 1;
  const end = Math.min(page * data.page_size, data.total);

  return (
    <div>
      <div className="sticky top-[70px] z-30 -mx-5 border-b border-line bg-[var(--color-paper)]/95 px-5 py-3 backdrop-blur-md md:-mx-8 md:px-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="flex-1">
            <SearchField value={filters.q} onChange={(value) => update("q", value)} />
          </div>
          <div className="flex items-center gap-2">
            <label className="sr-only" htmlFor="sort">
              Orden
            </label>
            <select
              id="sort"
              value={filters.sort}
              onChange={(event) => update("sort", event.target.value)}
              className="field !w-auto !py-3 text-[12px]"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Link
              href={authenticated ? "/perfil" : "/registro?next=%2Fperfil"}
              className="hidden items-center gap-1.5 rounded-full border border-signal/30 bg-signal-soft px-3 py-2.5 text-[11px] text-signal-deep hover:border-signal md:inline-flex"
              title="Personaliza el orden con tus intereses y disponibilidad"
            >
              <Sparkle size={12} />
              Para mí
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowFilters((value) => !value)}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper-raised px-3 py-1.5 text-[11px] text-ink-soft lg:hidden"
            aria-expanded={showFilters}
          >
            <Sliders size={13} />
            Filtros{active > 0 ? ` (${active})` : ""}
          </button>
          <span className="mono text-[11px] text-ink-soft" aria-live="polite">
            {loading ? "Buscando…" : data.total === 0 ? "Sin resultados" : `${start}–${end} de ${data.total}`}
          </span>
          {active > 0 && (
            <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
              {active} filtro{active === 1 ? "" : "s"} activo{active === 1 ? "" : "s"}
            </span>
          )}
          <span
            className={cn(
              "inline-flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.08em]",
              loading ? "text-signal" : "text-fern",
            )}
          >
            <span className={cn("size-1.5 rounded-full", loading ? "animate-pulse bg-signal" : "bg-fern")} />
            {loading ? "consultando catálogo" : "actualizado"}
          </span>
        </div>
        {active > 0 && (
          <button type="button" onClick={clearAll} className="text-[11px] text-muted underline decoration-line-strong underline-offset-2 hover:text-ink">
            Limpiar todo
          </button>
        )}
      </div>

      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={chip.clear}
              className="inline-flex items-center gap-1.5 rounded-full border border-ink/20 bg-paper-raised px-2.5 py-1 text-[11px] text-ink transition-colors hover:border-signal hover:text-signal-deep"
              title="Quitar filtro"
            >
              {chip.label}
              <span className="text-muted">×</span>
            </button>
          ))}
        </div>
      )}

      <div className="mt-5 grid gap-8 lg:grid-cols-[260px_1fr]">
        <aside className={cn("space-y-5", !showFilters && "hidden lg:block")} aria-label="Filtros">
          <div className="flex items-center gap-2 border-b border-line pb-2">
            <Sliders size={14} className="text-signal" />
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink">Filtros</span>
          </div>

          <div>
            <p className="label">Categoría</p>
            <div className="flex flex-wrap gap-1.5">
              {facets.category.map((facet) => (
                <ToggleChip
                  key={facet.key}
                  active={filters.category.includes(facet.key)}
                  label={facet.label ?? facet.key}
                  count={facet.count}
                  onClick={() => toggleList("category", facet.key)}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="label">Tecnología</p>
            <div className="flex flex-wrap gap-1.5">
              {facets.tech.slice(0, 12).map((facet) => (
                <ToggleChip
                  key={facet.key}
                  active={filters.tech.includes(facet.key)}
                  label={facet.label ?? facet.key}
                  count={facet.count}
                  onClick={() => toggleList("tech", facet.key)}
                />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <SelectField
              id="modality"
              label="Modalidad"
              value={filters.modality}
              placeholder="Todas"
              onChange={(value) => update("modality", value)}
              options={facets.modality.filter((facet) => facet.key !== "unknown").map((facet) => ({ value: facet.key, label: facet.label ?? facet.key }))}
            />
            <SelectField
              id="cost"
              label="Coste"
              value={filters.cost}
              placeholder="Cualquiera"
              onChange={(value) => update("cost", value)}
              options={[
                { value: "free", label: "Gratis" },
                { value: "paid", label: "De pago" },
              ]}
            />
            <SelectField
              id="days"
              label="Cierra en"
              value={filters.days}
              placeholder="Cualquier fecha"
              onChange={(value) => update("days", value)}
              options={[
                { value: "7", label: "7 días" },
                { value: "30", label: "30 días" },
                { value: "90", label: "90 días" },
              ]}
            />
            <SelectField
              id="language"
              label="Idioma"
              value={filters.language}
              placeholder="Todos"
              onChange={(value) => update("language", value)}
              options={facets.language.map((facet) => ({ value: facet.key, label: facet.label ?? facet.key }))}
            />
          </div>

          <SelectField
            id="country"
            label="País"
            value={filters.country}
            placeholder="Todos los países"
            onChange={(value) => update("country", value)}
            options={facets.country.map((facet) => ({ value: facet.key, label: `${facet.label ?? facet.key} (${facet.count})` }))}
          />

          <label className="flex items-center gap-2 text-[11px] text-muted">
            <input
              type="checkbox"
              checked={filters.includeClosed}
              onChange={(event) => update("includeClosed", event.target.checked)}
              className="size-3.5 accent-signal"
            />
            Incluir convocatorias cerradas
          </label>
        </aside>

        <section aria-label="Resultados" aria-busy={loading}>
          {error && (
            <div className="mb-4 border border-brick/30 bg-brick-soft/60 p-3 text-[12px] text-brick" role="alert">
              {error}
            </div>
          )}

          {data.items.length === 0 ? (
            <div className="border border-dashed border-line-strong bg-paper-raised/60 p-10 text-center">
              <p className="font-display text-2xl text-ink">Sin resultados con estos filtros</p>
              <p className="mx-auto mt-2 max-w-md text-[12px] leading-relaxed text-muted">
                Prueba a quitar un filtro o ampliar el plazo. Si algo no está en el catálogo, no lo
                inventamos: aparece cuando una fuente lo confirma.
              </p>
              <button type="button" onClick={clearAll} className="btn btn-outline mt-4 !py-2">
                Limpiar filtros
              </button>
            </div>
          ) : (
            <div className={cn("grid gap-3 md:grid-cols-2", loading && "opacity-60 transition-opacity")}>
              {data.items.map((item) => (
                <OpportunityCard key={item.id} item={item} saved={savedSet.has(item.slug)} authenticated={authenticated} />
              ))}
            </div>
          )}

          {data.pages > 1 && (
            <nav className="mt-8 flex items-center justify-between border-t border-line pt-4" aria-label="Paginación">
              <button
                type="button"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1 || loading}
                className="btn btn-outline !py-2 disabled:opacity-40"
              >
                ← Anterior
              </button>
              <span className="mono text-[11px] text-muted">
                Página {page} / {data.pages}
              </span>
              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={page >= data.pages || loading}
                className="btn btn-outline !py-2 disabled:opacity-40"
              >
                Siguiente →
              </button>
            </nav>
          )}
        </section>
      </div>
    </div>
  );
}

