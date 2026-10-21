import Link from "next/link";

import { CatalogFilters } from "@/components/catalog-filters";
import { OpportunityCard } from "@/components/opportunity-card";
import { SortSelect } from "@/components/sort-select";
import { ApiUnavailable, EmptyState } from "@/components/ui";
import { apiGet, getSessionToken, getSessionUser } from "@/lib/api";
import type { CatalogResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Catálogo de oportunidades",
  description:
    "Busca y filtra hackathons, eventos, becas y programas por categoría, tecnología, país, modalidad, coste y fecha límite.",
};

type SearchParams = Record<string, string | string[] | undefined>;

function listOf(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function oneOf(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

const SORTS = new Set(["relevance", "deadline", "newest", "confidence"]);
const PAGE_SIZE = 24;

function buildParams(input: {
  q: string;
  categories: string[];
  tech: string[];
  modality: string | null;
  country: string | null;
  language: string | null;
  cost: string | null;
  days: number | null;
  includeClosed: boolean;
  sort: string;
  page: number;
}): URLSearchParams {
  const params = new URLSearchParams();
  if (input.q) params.set("q", input.q);
  input.categories.forEach((value) => params.append("category", value));
  input.tech.forEach((value) => params.append("tech", value));
  if (input.modality) params.set("modality", input.modality);
  if (input.country) params.set("country", input.country);
  if (input.language) params.set("language", input.language);
  if (input.cost) params.set("cost", input.cost);
  if (input.days) params.set("days", String(input.days));
  if (input.includeClosed) params.set("include_closed", "true");
  if (input.sort !== "relevance") params.set("sort", input.sort);
  if (input.page > 1) params.set("page", String(input.page));
  return params;
}

export default async function CatalogPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const categories = listOf(sp.category);
  const tech = listOf(sp.tech);
  const modality = oneOf(sp.modality);
  const country = oneOf(sp.country);
  const language = oneOf(sp.language);
  const cost = oneOf(sp.cost);
  const q = oneOf(sp.q) ?? "";
  const daysRaw = oneOf(sp.days);
  const days = daysRaw && /^\d+$/.test(daysRaw) ? Number(daysRaw) : null;
  const includeClosed = oneOf(sp.include_closed) === "true";
  const sortRaw = oneOf(sp.sort) ?? "relevance";
  const sort = SORTS.has(sortRaw) ? sortRaw : "relevance";
  const pageRaw = oneOf(sp.page) ?? "1";
  const page = /^\d+$/.test(pageRaw) ? Math.max(1, Number(pageRaw)) : 1;

  const params = buildParams({
    q,
    categories,
    tech,
    modality,
    country,
    language,
    cost,
    days,
    includeClosed,
    sort,
    page,
  });
  params.set("page_size", String(PAGE_SIZE));

  const [token, user] = await Promise.all([getSessionToken(), getSessionUser()]);

  let data: CatalogResponse;
  try {
    data = await apiGet<CatalogResponse>(`/opportunities?${params.toString()}`, token);
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  let saved = new Set<string>();
  if (token) {
    try {
      const payload = await apiGet<{ items: { slug: string }[] }>("/saved", token);
      saved = new Set(payload.items.map((item) => item.slug));
    } catch {
      saved = new Set();
    }
  }

  const applied = data.applied;
  const labels = new Map<string, string>();
  data.facets.category.forEach((facet) => labels.set(`category:${facet.key}`, facet.label ?? facet.key));
  data.facets.tech.forEach((facet) => labels.set(`tech:${facet.key}`, facet.label ?? facet.key));
  data.facets.modality.forEach((facet) => labels.set(`modality:${facet.key}`, facet.label ?? facet.key));
  data.facets.country.forEach((facet) => labels.set(`country:${facet.key}`, facet.label ?? facet.key));
  data.facets.language.forEach((facet) => labels.set(`language:${facet.key}`, facet.label ?? facet.key));

  function hrefFor(overrides: Partial<Parameters<typeof buildParams>[0]>): string {
    const next = buildParams({
      q: applied.q,
      categories: applied.category,
      tech: applied.tech,
      modality: applied.modality,
      country: applied.country,
      language: applied.language,
      cost: applied.cost,
      days: applied.days,
      includeClosed: applied.include_closed,
      sort: applied.sort,
      page: 1,
      ...overrides,
    });
    const query = next.toString();
    return query ? `/oportunidades?${query}` : "/oportunidades";
  }

  const chips: { key: string; label: string; href: string }[] = [];
  if (applied.q) chips.push({ key: "q", label: `“${applied.q}”`, href: hrefFor({ q: "" }) });
  applied.category.forEach((value) =>
    chips.push({
      key: `category:${value}`,
      label: labels.get(`category:${value}`) ?? value,
      href: hrefFor({ categories: applied.category.filter((item) => item !== value) }),
    }),
  );
  applied.tech.forEach((value) =>
    chips.push({
      key: `tech:${value}`,
      label: labels.get(`tech:${value}`) ?? value,
      href: hrefFor({ tech: applied.tech.filter((item) => item !== value) }),
    }),
  );
  if (applied.modality)
    chips.push({
      key: "modality",
      label: labels.get(`modality:${applied.modality}`) ?? applied.modality,
      href: hrefFor({ modality: null }),
    });
  if (applied.country)
    chips.push({
      key: "country",
      label: labels.get(`country:${applied.country}`) ?? applied.country,
      href: hrefFor({ country: null }),
    });
  if (applied.language)
    chips.push({
      key: "language",
      label: labels.get(`language:${applied.language}`) ?? applied.language,
      href: hrefFor({ language: null }),
    });
  if (applied.cost)
    chips.push({
      key: "cost",
      label: applied.cost === "free" ? "Gratis" : "De pago",
      href: hrefFor({ cost: null }),
    });
  if (applied.days)
    chips.push({
      key: "days",
      label: `Cierra en ${applied.days} días`,
      href: hrefFor({ days: null }),
    });
  if (applied.include_closed)
    chips.push({ key: "closed", label: "Incluye cerradas", href: hrefFor({ includeClosed: false }) });

  const pageHref = (target: number) => {
    const next = buildParams({
      q: applied.q,
      categories: applied.category,
      tech: applied.tech,
      modality: applied.modality,
      country: applied.country,
      language: applied.language,
      cost: applied.cost,
      days: applied.days,
      includeClosed: applied.include_closed,
      sort: applied.sort,
      page: target,
    });
    const query = next.toString();
    return query ? `/oportunidades?${query}` : "/oportunidades";
  };

  const start = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1;
  const end = Math.min(data.page * data.page_size, data.total);

  return (
    <div className="shell py-10 lg:py-14">
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-line pb-7">
        <div>
          <p className="eyebrow mb-3">Catálogo global · señal verificada</p>
          <h1 className="display max-w-3xl text-[44px] leading-[0.98] tracking-[-0.03em] sm:text-[58px]">
            Todas las oportunidades,
            <br />
            <span className="italic text-signal-deep">con su procedencia.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[13px] leading-relaxed text-muted">
            Busca por texto y combina filtros. Solo aparecen registros que han superado la validación
            de publicación; las convocatorias cerradas se conservan como historial y se etiquetan.
          </p>
        </div>
        <div className="border-l border-line pl-5">
          <p className="mono text-4xl leading-none text-ink">{data.total}</p>
          <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
            resultados publicados
          </p>
        </div>
      </header>

      <div className="mt-8 grid gap-10 lg:grid-cols-[248px_1fr]">
        <CatalogFilters data={data} />

        <section aria-label="Resultados">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="mono text-[11px] text-ink-soft">
                {data.total === 0 ? "Sin resultados" : `${start}–${end} de ${data.total}`}
              </span>
              {chips.length > 0 && (
                <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                  {chips.length} filtro{chips.length === 1 ? "" : "s"} activo{chips.length === 1 ? "" : "s"}
                </span>
              )}
            </div>
            <SortSelect value={applied.sort} />
          </div>

          {chips.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <Link
                  key={chip.key}
                  href={chip.href}
                  className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper-raised px-2.5 py-1 text-[11px] text-ink-soft transition-colors hover:border-ink/40"
                  title="Quitar filtro"
                >
                  {chip.label}
                  <span className="text-muted">×</span>
                </Link>
              ))}
              <Link
                href="/oportunidades"
                className="inline-flex items-center px-1 text-[11px] text-muted underline decoration-line-strong underline-offset-2 hover:text-ink"
              >
                Limpiar todo
              </Link>
            </div>
          )}

          {data.items.length === 0 ? (
            <div className="mt-8">
              <EmptyState
                title="Ninguna oportunidad cumple esos filtros"
                body="Amplía la búsqueda o elimina algún filtro. Si buscas algo que no está en el catálogo, no lo inventaremos: las fuentes nuevas se incorporan cuando se confirman."
                action={{ href: "/oportunidades", label: "Ver todo el catálogo" }}
              />
            </div>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {data.items.map((item) => (
                <OpportunityCard
                  key={item.id}
                  item={item}
                  saved={saved.has(item.slug)}
                  authenticated={Boolean(user)}
                />
              ))}
            </div>
          )}

          {data.pages > 1 && (
            <nav className="mt-10 flex items-center justify-between border-t border-line pt-5" aria-label="Paginación">
              <div>
                {data.page > 1 ? (
                  <Link href={pageHref(data.page - 1)} className="btn btn-outline !py-2">
                    ← Anterior
                  </Link>
                ) : (
                  <span className="btn btn-outline pointer-events-none !py-2 opacity-40">← Anterior</span>
                )}
              </div>
              <span className="mono text-[11px] text-muted">
                Página {data.page} / {data.pages}
              </span>
              <div>
                {data.page < data.pages ? (
                  <Link href={pageHref(data.page + 1)} className="btn btn-outline !py-2">
                    Siguiente →
                  </Link>
                ) : (
                  <span className="btn btn-outline pointer-events-none !py-2 opacity-40">Siguiente →</span>
                )}
              </div>
            </nav>
          )}
        </section>
      </div>
    </div>
  );
}
