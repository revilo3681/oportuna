import Link from "next/link";

import { Search, Sliders } from "@/components/icons";
import type { CatalogResponse } from "@/lib/types";

type Applied = CatalogResponse["applied"];

function CheckboxRow({
  name,
  value,
  label,
  count,
  checked,
}: {
  name: string;
  value: string;
  label: string;
  count?: number;
  checked: boolean;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-2 py-[5px] text-[12px] text-ink-soft">
      <span className="flex min-w-0 items-center gap-2">
        <input
          type="checkbox"
          name={name}
          value={value}
          defaultChecked={checked}
          className="size-3.5 shrink-0 accent-signal"
        />
        <span className="truncate">{label}</span>
      </span>
      {typeof count === "number" && <span className="mono text-[9px] text-muted">{count}</span>}
    </label>
  );
}

function FilterFields({ data }: { data: CatalogResponse }) {
  const { facets, applied } = data;
  return (
    <div className="space-y-6">
      <div>
        <label className="label" htmlFor="q">
          Buscar
        </label>
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            id="q"
            name="q"
            type="search"
            defaultValue={applied.q}
            placeholder="IA, hackathon, beca…"
            className="field !pl-9"
          />
        </div>
      </div>

      <fieldset>
        <legend className="label">Categoría</legend>
        <div className="border-t border-line pt-1.5">
          {facets.category.map((facet) => (
            <CheckboxRow
              key={facet.key}
              name="category"
              value={facet.key}
              label={facet.label ?? facet.key}
              count={facet.count}
              checked={applied.category.includes(facet.key)}
            />
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="label">Tecnología</legend>
        <div className="max-h-52 overflow-y-auto border-t border-line pt-1.5 pr-1">
          {facets.tech.slice(0, 12).map((facet) => (
            <CheckboxRow
              key={facet.key}
              name="tech"
              value={facet.key}
              label={facet.label ?? facet.key}
              count={facet.count}
              checked={applied.tech.includes(facet.key)}
            />
          ))}
        </div>
      </fieldset>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="modality">
            Modalidad
          </label>
          <select id="modality" name="modality" defaultValue={applied.modality ?? ""} className="field">
            <option value="">Todas</option>
            {facets.modality
              .filter((facet) => facet.key !== "unknown")
              .map((facet) => (
                <option key={facet.key} value={facet.key}>
                  {facet.label}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="cost">
            Coste
          </label>
          <select id="cost" name="cost" defaultValue={applied.cost ?? ""} className="field">
            <option value="">Cualquiera</option>
            <option value="free">Gratis</option>
            <option value="paid">De pago</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="days">
            Cierra en
          </label>
          <select id="days" name="days" defaultValue={applied.days ?? ""} className="field">
            <option value="">Cualquier fecha</option>
            <option value="7">7 días</option>
            <option value="30">30 días</option>
            <option value="90">90 días</option>
          </select>
        </div>
        <div>
          <label className="label" htmlFor="language">
            Idioma
          </label>
          <select id="language" name="language" defaultValue={applied.language ?? ""} className="field">
            <option value="">Todos</option>
            {facets.language.map((facet) => (
              <option key={facet.key} value={facet.key}>
                {facet.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="country">
          País
        </label>
        <select id="country" name="country" defaultValue={applied.country ?? ""} className="field">
          <option value="">Todos los países</option>
          {facets.country.map((facet) => (
            <option key={facet.key} value={facet.key}>
              {facet.label} ({facet.count})
            </option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 text-[11px] text-muted">
        <input
          type="checkbox"
          name="include_closed"
          value="true"
          defaultChecked={applied.include_closed}
          className="size-3.5 accent-signal"
        />
        Incluir convocatorias cerradas (historial)
      </label>

      <div className="flex items-center gap-2 border-t border-line pt-5">
        <button type="submit" className="btn btn-primary flex-1 !py-2.5">
          Aplicar filtros
        </button>
        <Link href="/oportunidades" className="btn btn-ghost !px-3 !py-2.5 text-[12px]">
          Limpiar
        </Link>
      </div>
    </div>
  );
}

export function CatalogFilters({ data }: { data: CatalogResponse }) {
  return (
    <>
      <aside className="hidden lg:block" aria-label="Filtros del catálogo">
        <form method="get" action="/oportunidades" className="sticky top-24">
          <div className="mb-4 flex items-center justify-between border-b border-line pb-3">
            <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink">
              <Sliders size={14} className="text-signal" /> Filtros
            </span>
            <span className="mono text-[10px] text-muted">{data.total}</span>
          </div>
          <FilterFields data={data} />
        </form>
      </aside>

      <div className="lg:hidden">
        <details className="group border border-line bg-paper-raised">
          <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-[13px]">
            <span className="flex items-center gap-2">
              <Sliders size={15} className="text-signal" /> Filtros y búsqueda
            </span>
            <span className="mono text-[10px] text-muted">{data.total} resultados</span>
          </summary>
          <form method="get" action="/oportunidades" className="border-t border-line p-4">
            <FilterFields data={data} />
          </form>
        </details>
      </div>
    </>
  );
}
