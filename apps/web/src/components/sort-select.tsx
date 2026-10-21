"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

const OPTIONS = [
  { value: "relevance", label: "Relevancia" },
  { value: "deadline", label: "Fecha límite" },
  { value: "newest", label: "Recién detectadas" },
  { value: "confidence", label: "Mayor confianza" },
];

export function SortSelect({ value }: { value: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  return (
    <label className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.08em] text-muted">
      Orden
      <select
        value={value}
        onChange={(event) => {
          const params = new URLSearchParams(searchParams.toString());
          if (event.target.value === "relevance") {
            params.delete("sort");
          } else {
            params.set("sort", event.target.value);
          }
          params.delete("page");
          const query = params.toString();
          router.push(query ? `${pathname}?${query}` : pathname);
        }}
        className="field !w-auto !py-1.5 !pl-2 !pr-7 text-[11px] text-ink"
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
