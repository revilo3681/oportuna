export type FilterOption = { value: string; label: string; count?: number };

export type CatalogFilterState = {
  q: string;
  category: string[];
  tech: string[];
  modality: string;
  country: string;
  language: string;
  cost: string;
  days: string;
  sort: string;
  includeClosed: boolean;
};

export const EMPTY_FILTERS: CatalogFilterState = {
  q: "",
  category: [],
  tech: [],
  modality: "",
  country: "",
  language: "",
  cost: "",
  days: "",
  sort: "relevance",
  includeClosed: false,
};

export const SORT_OPTIONS: FilterOption[] = [
  { value: "relevance", label: "Relevancia" },
  { value: "deadline", label: "Cierra antes" },
  { value: "newest", label: "Recién detectadas" },
  { value: "confidence", label: "Mayor confianza" },
];

export function filtersToParams(filters: CatalogFilterState, page = 1): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  filters.category.forEach((value) => params.append("category", value));
  filters.tech.forEach((value) => params.append("tech", value));
  if (filters.modality) params.set("modality", filters.modality);
  if (filters.country) params.set("country", filters.country);
  if (filters.language) params.set("language", filters.language);
  if (filters.cost) params.set("cost", filters.cost);
  if (filters.days) params.set("days", filters.days);
  if (filters.includeClosed) params.set("include_closed", "true");
  if (filters.sort !== "relevance") params.set("sort", filters.sort);
  if (page > 1) params.set("page", String(page));
  return params;
}

export function countActiveFilters(filters: CatalogFilterState): number {
  return (
    (filters.q.trim() ? 1 : 0) +
    filters.category.length +
    filters.tech.length +
    (filters.modality ? 1 : 0) +
    (filters.country ? 1 : 0) +
    (filters.language ? 1 : 0) +
    (filters.cost ? 1 : 0) +
    (filters.days ? 1 : 0) +
    (filters.includeClosed ? 1 : 0)
  );
}

export function filtersFromSearchParams(sp: URLSearchParams): CatalogFilterState {
  const list = (key: string) => sp.getAll(key).filter(Boolean);
  return {
    q: sp.get("q") ?? "",
    category: list("category"),
    tech: list("tech"),
    modality: sp.get("modality") ?? "",
    country: sp.get("country") ?? "",
    language: sp.get("language") ?? "",
    cost: sp.get("cost") ?? "",
    days: sp.get("days") ?? "",
    sort: sp.get("sort") ?? "relevance",
    includeClosed: sp.get("include_closed") === "true",
  };
}
