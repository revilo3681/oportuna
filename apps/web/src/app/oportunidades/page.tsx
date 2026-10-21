import { CatalogExplorer } from "@/components/catalog-explorer";
import { ApiUnavailable } from "@/components/ui";
import { apiGet, getSessionToken, getSessionUser } from "@/lib/api";
import { filtersFromSearchParams, filtersToParams } from "@/lib/catalog-filters";
import type { CatalogResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Catálogo de oportunidades",
  description:
    "Busca y filtra hackathons, eventos, becas y programas por categoría, tecnología, país, modalidad, coste y fecha límite.",
};

type SearchParams = Record<string, string | string[] | undefined>;

export default async function CatalogPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(sp)) {
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, item));
    } else if (value) {
      params.set(key, value);
    }
  }

  const initialFilters = filtersFromSearchParams(params);
  const pageRaw = params.get("page") ?? "1";
  const page = /^\d+$/.test(pageRaw) ? Math.max(1, Number(pageRaw)) : 1;
  const query = filtersToParams(initialFilters, page);
  query.set("page_size", "24");

  const [token, user] = await Promise.all([getSessionToken(), getSessionUser()]);

  let data: CatalogResponse;
  try {
    data = await apiGet<CatalogResponse>(`/opportunities?${query.toString()}`, token);
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  let savedSlugs: string[] = [];
  if (token) {
    try {
      const payload = await apiGet<{ items: { slug: string }[] }>("/saved", token);
      savedSlugs = payload.items.map((item) => item.slug);
    } catch {
      savedSlugs = [];
    }
  }

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
            Escribe o marca filtros y los resultados se actualizan en vivo. Solo aparecen registros
            que han superado la validación de publicación; las cerradas se conservan como historial.
          </p>
        </div>
        <div className="border-l border-line pl-5">
          <p className="font-display text-[26px] leading-none text-ink">En vivo</p>
          <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
            búsqueda y filtros instantáneos
          </p>
        </div>
      </header>

      <div className="mt-8">
        <CatalogExplorer
          facets={data.facets}
          initialFilters={initialFilters}
          initialData={data}
          savedSlugs={savedSlugs}
          authenticated={Boolean(user)}
        />
      </div>
    </div>
  );
}
