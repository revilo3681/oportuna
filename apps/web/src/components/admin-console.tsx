"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AlertTriangle, Check, Refresh, ShieldCheck, Trash } from "@/components/icons";
import { TrustBadge } from "@/components/trust-badge";
import { cn, formatDateTime, formatRelative } from "@/lib/format";
import type {
  AdminSource,
  AdminStats,
  DuplicatePair,
  OpportunityCard,
} from "@/lib/types";

type Tab = "overview" | "review" | "sources" | "duplicates" | "audit";

type ReviewItem = OpportunityCard & { review_reason?: string | null };

type AuditRow = {
  id: string;
  slug: string | null;
  field: string;
  old_value: unknown;
  new_value: unknown;
  actor: string;
  reason: string | null;
  created_at: string | null;
};

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Resumen" },
  { key: "review", label: "Cola de revisión" },
  { key: "sources", label: "Fuentes" },
  { key: "duplicates", label: "Duplicados" },
  { key: "audit", label: "Auditoría" },
];

const KIND_OPTIONS = ["ics", "rss", "jsonld", "devpost", "github"];

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

function StatCard({ label, value, note, tone }: { label: string; value: string | number; note?: string; tone?: "warn" | "good" }) {
  return (
    <div className="border border-line bg-paper-raised p-4">
      <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">{label}</p>
      <p
        className={cn(
          "mono mt-2 text-3xl leading-none",
          tone === "warn" ? "text-brick" : tone === "good" ? "text-fern" : "text-ink",
        )}
      >
        {value}
      </p>
      {note && <p className="mt-1 text-[10px] leading-snug text-muted">{note}</p>}
    </div>
  );
}

export function AdminConsole({ adminName }: { adminName: string }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [review, setReview] = useState<ReviewItem[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicatePair[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showSourceForm, setShowSourceForm] = useState(false);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, sourceData, reviewData, duplicateData, auditData] = await Promise.all([
        request<AdminStats>("/api/admin/stats"),
        request<{ sources: AdminSource[] }>("/api/admin/sources"),
        request<{ items: ReviewItem[] }>("/api/admin/review"),
        request<{ items: DuplicatePair[] }>("/api/admin/duplicates"),
        request<{ items: AuditRow[] }>("/api/admin/audit"),
      ]);
      setStats(statsData);
      setSources(sourceData.sources);
      setReview(reviewData.items);
      setDuplicates(duplicateData.items);
      setAudit(auditData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la consola");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  function flash(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(null), 4000);
  }

  async function reviewAction(id: string, action: "approve" | "hide") {
    const note = window.prompt(
      action === "approve" ? "Nota de aprobación (opcional)" : "Motivo para ocultar (opcional)",
    );
    if (note === null) return;
    try {
      await request(`/api/admin/opportunities/${id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ note: note || null }),
      });
      flash(action === "approve" ? "Oportunidad aprobada." : "Oportunidad ocultada.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function runSource(id: string) {
    try {
      await request(`/api/admin/sources/${id}/run`, { method: "POST", body: JSON.stringify({}) });
      flash("Ejecución encolada. Revisa las métricas en unos segundos.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function toggleSource(source: AdminSource) {
    try {
      await request(`/api/admin/sources/${source.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !source.enabled }),
      });
      flash(source.enabled ? "Fuente deshabilitada." : "Fuente habilitada.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function correctOpportunity(id: string, event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: Record<string, unknown> = {
      modality: String(form.get("modality") ?? "unknown"),
      cost_type: String(form.get("cost_type") ?? "unknown"),
    };
    const title = String(form.get("title") ?? "").trim();
    const officialUrl = String(form.get("official_url") ?? "").trim();
    const deadline = String(form.get("registration_deadline") ?? "").trim();
    if (title) payload.title = title;
    if (officialUrl) payload.official_url = officialUrl;
    payload.registration_deadline = deadline ? new Date(`${deadline}T23:59:59Z`).toISOString() : null;
    try {
      await request(`/api/admin/opportunities/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      flash("Corrección guardada y registrada en la auditoría.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function resolveDuplicate(id: string, action: "merge" | "reject") {
    try {
      await request(`/api/admin/duplicates/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      flash(action === "merge" ? "Registros fusionados y auditados." : "Marcados como distintos.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function createSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await request("/api/admin/sources", {
        method: "POST",
        body: JSON.stringify({
          slug: String(form.get("slug") ?? "").trim(),
          name: String(form.get("name") ?? "").trim(),
          kind: String(form.get("kind") ?? "ics"),
          homepage_url: String(form.get("homepage_url") ?? "").trim(),
          endpoint: String(form.get("endpoint") ?? "").trim(),
          region: String(form.get("region") ?? "global"),
          authority: Number(form.get("authority") ?? 60),
          frequency_minutes: Number(form.get("frequency_minutes") ?? 720),
          enabled: false,
          access_notes: String(form.get("access_notes") ?? "").trim(),
          config: {},
          languages: [],
        }),
      });
      flash("Fuente registrada como deshabilitada. Revísala antes de activarla.");
      setShowSourceForm(false);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="shell py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Consola interna · {adminName}</p>
          <h1 className="display mt-2 text-[38px] leading-tight">Calidad, no volumen.</h1>
          <p className="mt-1 text-[12px] text-muted">
            Cada aprobación, corrección y fusión queda registrada. Ninguna IA publica sin controles.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void loadAll()} className="btn btn-outline !py-2.5">
            <Refresh size={14} />
            Actualizar
          </button>
          <Link href="/" className="btn btn-primary !py-2.5">
            Ver sitio público
          </Link>
        </div>
      </div>

      {error && (
        <div className="mt-5 flex items-start gap-3 border border-brick/30 bg-brick-soft/60 p-3 text-[12px] text-brick">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <p className="flex-1">{error}</p>
          <button type="button" onClick={() => setError(null)} className="underline">
            cerrar
          </button>
        </div>
      )}
      {notice && (
        <div className="mt-5 flex items-center gap-2 border border-fern/30 bg-fern-soft p-3 text-[12px] text-fern">
          <Check size={15} />
          {notice}
        </div>
      )}

      <nav className="mt-7 flex flex-wrap gap-1 border-b border-line" aria-label="Secciones de administración">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={cn(
              "relative px-3 py-2.5 text-[12px] transition-colors",
              tab === item.key ? "text-ink" : "text-muted hover:text-ink",
            )}
            aria-current={tab === item.key ? "page" : undefined}
          >
            {item.label}
            {item.key === "review" && review.length > 0 && (
              <span className="ml-1.5 rounded-full bg-signal px-1.5 py-0.5 font-mono text-[8px] text-white">
                {review.length}
              </span>
            )}
            {item.key === "duplicates" && duplicates.length > 0 && (
              <span className="ml-1.5 rounded-full bg-amber px-1.5 py-0.5 font-mono text-[8px] text-white">
                {duplicates.length}
              </span>
            )}
            {tab === item.key && <span className="absolute inset-x-2 -bottom-px h-0.5 bg-signal" />}
          </button>
        ))}
      </nav>

      {loading && (
        <div className="mt-8 grid gap-3 sm:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="h-24 animate-pulse border border-line bg-paper-deep/40" />
          ))}
        </div>
      )}

      {!loading && tab === "overview" && stats && (
        <div className="mt-7 space-y-8">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Publicadas" value={stats.totals.published} note={`${stats.totals.opportunities} registros totales`} tone="good" />
            <StatCard label="Cola de revisión" value={stats.totals.review_queue} note="pendientes de decisión humana" tone={stats.totals.review_queue > 0 ? "warn" : undefined} />
            <StatCard label="Conflictos" value={stats.totals.conflicts} note="fuentes que no coinciden" tone={stats.totals.conflicts > 0 ? "warn" : undefined} />
            <StatCard label="Duplicados abiertos" value={stats.totals.open_duplicates} note="pares por resolver" tone={stats.totals.open_duplicates > 0 ? "warn" : undefined} />
            <StatCard label="Fuentes activas" value={`${stats.totals.sources_enabled}/${stats.totals.sources}`} note={`${stats.totals.sources_failing} con fallos`} />
            <StatCard label="Confianza media" value={`${Math.round(stats.totals.avg_confidence * 100)}%`} note="solo publicadas" />
            <StatCard
              label="Frescura"
              value={stats.totals.freshness_hours !== null ? `${stats.totals.freshness_hours} h` : "—"}
              note={stats.totals.last_checked_at ? `última: ${formatDateTime(stats.totals.last_checked_at)}` : "sin comprobaciones"}
              tone={stats.totals.freshness_hours !== null && stats.totals.freshness_hours > 48 ? "warn" : "good"}
            />
            <StatCard label="Publicadas obsoletas" value={stats.totals.stale_published} note="requieren re-comprobación" tone={stats.totals.stale_published > 0 ? "warn" : undefined} />
          </div>

          <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="border border-line bg-paper-raised">
              <div className="flex items-center justify-between border-b border-line px-4 py-3">
                <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">Ingesta últimas 24 h</p>
                <span className="mono text-[10px] text-muted">{stats.ingestion_24h.runs} ejecuciones</span>
              </div>
              <div className="grid grid-cols-3 gap-px bg-line sm:grid-cols-6">
                {[
                  ["Encontradas", stats.ingestion_24h.found],
                  ["Creadas", stats.ingestion_24h.created],
                  ["Actualizadas", stats.ingestion_24h.updated],
                  ["Publicadas", stats.ingestion_24h.published],
                  ["Revisión", stats.ingestion_24h.review],
                  ["Errores", stats.ingestion_24h.errors],
                ].map(([label, value]) => (
                  <div key={String(label)} className="bg-paper-raised p-3 text-center">
                    <p className="mono text-xl text-ink">{value}</p>
                    <p className="mt-1 font-mono text-[8px] uppercase tracking-wider text-muted">{label}</p>
                  </div>
                ))}
              </div>
              <div className="px-4 py-3 text-[10px] text-muted">
                Coste registrado: <span className="mono">${stats.ingestion_24h.cost_usd.toFixed(4)}</span> ·
                La ingesta no gasta APIs de pago por defecto.
              </div>
            </div>

            <div className="border border-line bg-paper-raised p-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">Cobertura por región</p>
              <ul className="mt-3 space-y-2">
                {stats.coverage.region.map((region) => (
                  <li key={region.key} className="flex items-center justify-between gap-2 text-[11px]">
                    <span className="capitalize text-ink-soft">{region.key}</span>
                    <span className="mono text-ink">{region.count}</span>
                  </li>
                ))}
                {stats.coverage.region.length === 0 && <li className="text-[11px] text-muted">Sin datos.</li>}
              </ul>
              <p className="mt-4 border-t border-line pt-3 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
                Cobertura por idioma
              </p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {stats.coverage.language.map((language) => (
                  <li key={language.key} className="chip">
                    {language.key}: {language.count}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <h2 className="font-display text-[26px]">Últimas ejecuciones</h2>
              <Link href="/metodologia#fuentes" className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted underline">
                Política de fuentes
              </Link>
            </div>
            <div className="mt-3 overflow-x-auto border border-line">
              <table className="w-full min-w-[820px] text-left">
                <thead>
                  <tr className="border-b border-line bg-paper-deep/40">
                    {["Fuente", "Estado", "Inicio", "Encontradas", "Creadas", "Publicadas", "Revisión", "Errores", "Duración"].map((label) => (
                      <th key={label} className="px-3 py-2 font-mono text-[8px] uppercase tracking-[0.1em] text-muted">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_runs.map((run) => (
                    <tr key={run.id} className="border-b border-line last:border-b-0">
                      <td className="px-3 py-2.5 text-[11px] text-ink">{run.source}</td>
                      <td className="px-3 py-2.5">
                        <span className={cn("rounded-full px-2 py-1 font-mono text-[8px] uppercase", run.status === "ok" ? "bg-fern-soft text-fern" : "bg-brick-soft text-brick")}>
                          {run.status}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-[10px] text-muted">{formatRelative(run.started_at)}</td>
                      <td className="px-3 py-2.5 mono text-[11px]">{run.items_found}</td>
                      <td className="px-3 py-2.5 mono text-[11px]">{run.items_created}</td>
                      <td className="px-3 py-2.5 mono text-[11px]">{run.items_published}</td>
                      <td className="px-3 py-2.5 mono text-[11px]">{run.items_review}</td>
                      <td className={cn("px-3 py-2.5 mono text-[11px]", run.errors > 0 ? "text-brick" : "text-muted")}>{run.errors}</td>
                      <td className="px-3 py-2.5 mono text-[10px] text-muted">
                        {run.duration_ms !== null ? `${(run.duration_ms / 1000).toFixed(1)} s` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {stats.recent_runs.some((run) => run.error_detail) && (
              <div className="mt-3 border border-brick/20 bg-brick-soft/40 p-3">
                <p className="font-mono text-[8px] uppercase tracking-[0.1em] text-brick">Errores recientes</p>
                {stats.recent_runs
                  .filter((run) => run.error_detail)
                  .slice(0, 3)
                  .map((run) => (
                    <p key={run.id} className="mt-1 text-[10px] text-ink-soft">
                      <strong>{run.source}</strong>: {run.error_detail}
                    </p>
                  ))}
              </div>
            )}
          </section>
        </div>
      )}

      {!loading && tab === "review" && (
        <div className="mt-7">
          {review.length === 0 ? (
            <div className="border border-dashed border-line-strong p-10 text-center">
              <ShieldCheck size={24} className="mx-auto text-fern" />
              <p className="mt-3 font-display text-2xl">Cola vacía</p>
              <p className="mt-1 text-[12px] text-muted">
                No hay registros ambiguos esperando decisión humana.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {review.map((item) => (
                <article key={item.id} className="border border-line bg-paper-raised">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-4">
                    <div className="min-w-0">
                      <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                        {item.category.label} · {item.modality.label} · {item.deadline.label}
                      </p>
                      <h3 className="mt-1 font-display text-[22px] leading-tight">{item.title}</h3>
                      <p className="mt-1 max-w-2xl text-[11px] leading-relaxed text-muted">
                        {item.review_reason ?? "Sin motivo registrado"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <TrustBadge verification={item.verification} />
                      <Link
                        href={`/oportunidades/${item.slug}`}
                        className="btn btn-outline !px-3 !py-2 text-[11px]"
                      >
                        Revisar ficha
                      </Link>
                      <button type="button" onClick={() => reviewAction(item.id, "approve")} className="btn btn-primary !px-3 !py-2 text-[11px]">
                        Aprobar
                      </button>
                      <button type="button" onClick={() => reviewAction(item.id, "hide")} className="btn btn-outline !px-3 !py-2 text-[11px] text-brick">
                        Ocultar
                      </button>
                    </div>
                  </div>
                  <div className="grid gap-4 p-4 sm:grid-cols-2">
                    <div>
                      <p className="font-mono text-[8px] uppercase tracking-[0.1em] text-muted">Señales de confianza</p>
                      <ul className="mt-2 space-y-1">
                        {item.verification.reasons.slice(0, 5).map((reason) => (
                          <li key={reason.code} className="flex gap-2 text-[10px] text-ink-soft">
                            <span
                              className={cn(
                                "mt-1 size-1.5 shrink-0 rounded-full",
                                reason.impact === "positive" ? "bg-fern" : reason.impact === "negative" ? "bg-brick" : "bg-line-strong",
                              )}
                            />
                            {reason.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="text-[10px] text-muted">
                      <p>
                        Fuente: <span className="text-ink-soft">{item.source?.name ?? "sin registrar"}</span>
                      </p>
                      <p className="mt-1">
                        Oficial:{" "}
                        <a href={item.official_url} target="_blank" rel="noreferrer noopener" className="text-ink-soft underline">
                          abrir enlace
                        </a>
                      </p>
                      <p className="mt-1">Comprobado: {formatDateTime(item.last_checked_at)}</p>
                      <p className="mt-1">Publicada: {item.verification.published ? "sí" : "no"}</p>
                    </div>
                  </div>
                  <details className="border-t border-line bg-paper/40 px-4 py-3">
                    <summary className="cursor-pointer font-mono text-[9px] uppercase tracking-[0.1em] text-muted">
                      Corregir datos extraídos
                    </summary>
                    <form onSubmit={(event) => correctOpportunity(item.id, event)} className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <label className="label" htmlFor={`title-${item.id}`}>Título</label>
                        <input id={`title-${item.id}`} name="title" defaultValue={item.title} className="field" maxLength={400} />
                      </div>
                      <div className="sm:col-span-2">
                        <label className="label" htmlFor={`url-${item.id}`}>Enlace oficial</label>
                        <input id={`url-${item.id}`} name="official_url" defaultValue={item.official_url} className="field" />
                      </div>
                      <div>
                        <label className="label" htmlFor={`deadline-${item.id}`}>Fecha límite de inscripción</label>
                        <input
                          id={`deadline-${item.id}`}
                          name="registration_deadline"
                          type="date"
                          defaultValue={item.deadline.registration_deadline?.slice(0, 10) ?? ""}
                          className="field"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="label" htmlFor={`modality-${item.id}`}>Modalidad</label>
                          <select id={`modality-${item.id}`} name="modality" defaultValue={item.modality.key} className="field">
                            {["unknown", "online", "presencial", "hibrida"].map((value) => (
                              <option key={value} value={value}>{value}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="label" htmlFor={`cost-${item.id}`}>Coste</label>
                          <select id={`cost-${item.id}`} name="cost_type" defaultValue={item.cost.type} className="field">
                            {["unknown", "free", "paid"].map((value) => (
                              <option key={value} value={value}>{value}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 sm:col-span-2">
                        <button type="submit" className="btn btn-primary !py-2 text-[11px]">Guardar corrección</button>
                        <span className="text-[10px] text-muted">La corrección se audita con tu usuario; no cambia la fuente original.</span>
                      </div>
                    </form>
                  </details>
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && tab === "sources" && (
        <div className="mt-7 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[12px] text-muted">
              {sources.length} fuentes registradas. Añadir una fuente no requiere cambios de código:
              el adaptador se elige por tipo.
            </p>
            <button type="button" onClick={() => setShowSourceForm((value) => !value)} className="btn btn-primary !py-2">
              {showSourceForm ? "Cerrar formulario" : "Registrar fuente"}
            </button>
          </div>

          {showSourceForm && (
            <form onSubmit={createSource} className="border border-line bg-paper-raised p-5">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="label" htmlFor="slug">Slug</label>
                  <input id="slug" name="slug" required pattern="[a-z0-9][a-z0-9-]*" className="field" placeholder="mi-universidad-events" />
                </div>
                <div>
                  <label className="label" htmlFor="name">Nombre</label>
                  <input id="name" name="name" required className="field" placeholder="Mi Universidad Events" />
                </div>
                <div>
                  <label className="label" htmlFor="kind">Tipo</label>
                  <select id="kind" name="kind" className="field" defaultValue="ics">
                    {KIND_OPTIONS.map((kind) => (
                      <option key={kind} value={kind}>{kind}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="homepage_url">Sitio</label>
                  <input id="homepage_url" name="homepage_url" required className="field" placeholder="https://events.example.edu/" />
                </div>
                <div>
                  <label className="label" htmlFor="endpoint">Endpoint público</label>
                  <input id="endpoint" name="endpoint" required className="field" placeholder="https://events.example.edu/calendar.ics" />
                </div>
                <div>
                  <label className="label" htmlFor="region">Región</label>
                  <select id="region" name="region" className="field" defaultValue="global">
                    {["global", "latam", "europa", "norteamerica", "asia", "africa", "oceania"].map((region) => (
                      <option key={region} value={region}>{region}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="authority">Autoridad (0–100)</label>
                  <input id="authority" name="authority" type="number" min={0} max={100} defaultValue={60} className="field" />
                </div>
                <div>
                  <label className="label" htmlFor="frequency_minutes">Frecuencia (min)</label>
                  <input id="frequency_minutes" name="frequency_minutes" type="number" min={60} max={10080} defaultValue={720} className="field" />
                </div>
                <div className="sm:col-span-2 lg:col-span-3">
                  <label className="label" htmlFor="access_notes">Condiciones de acceso</label>
                  <textarea id="access_notes" name="access_notes" className="field min-h-20" placeholder="Qué se consulta, límites y condiciones de la fuente." />
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <button type="submit" className="btn btn-primary !py-2">Guardar fuente</button>
                <span className="self-center text-[10px] text-muted">Se crea deshabilitada hasta revisión.</span>
              </div>
            </form>
          )}

          <div className="space-y-2">
            {sources.map((source) => (
              <div key={source.id} className="border border-line bg-paper-raised">
                <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-[13px] font-medium text-ink">{source.name}</p>
                      <span className="chip">{source.kind}</span>
                      <span className="chip">{source.region}</span>
                      <span className="font-mono text-[9px] uppercase tracking-wider text-muted">autoridad {source.authority}</span>
                      {!source.enabled && <span className="rounded-full bg-paper-deep px-2 py-1 font-mono text-[8px] uppercase text-muted">deshabilitada</span>}
                      {source.last_status === "error" && <span className="rounded-full bg-brick-soft px-2 py-1 font-mono text-[8px] uppercase text-brick">fallo</span>}
                    </div>
                    <p className="mt-1 truncate font-mono text-[10px] text-muted">{source.endpoint}</p>
                    <p className="mt-1 text-[10px] text-muted">
                      Última ejecución: {formatRelative(source.last_run_at)} · Publicadas: {source.published_count} ·
                      Fallos consecutivos: {source.consecutive_failures}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setExpandedSource(expandedSource === source.id ? null : source.id)} className="btn btn-ghost !py-2 text-[11px]">
                      Detalles
                    </button>
                    <button type="button" onClick={() => toggleSource(source)} className="btn btn-outline !py-2 text-[11px]">
                      {source.enabled ? "Deshabilitar" : "Habilitar"}
                    </button>
                    <button type="button" onClick={() => runSource(source.id)} className="btn btn-primary !py-2 text-[11px]">
                      Ejecutar
                    </button>
                  </div>
                </div>
                {expandedSource === source.id && (
                  <div className="border-t border-line bg-paper p-4 text-[11px] leading-relaxed text-muted">
                    <p><span className="text-ink-soft">Condiciones:</span> {source.access_notes || "sin notas"}</p>
                    {source.terms_url && <p className="mt-1">Términos: <a href={source.terms_url} target="_blank" rel="noreferrer noopener" className="underline">{source.terms_url}</a></p>}
                    <p className="mt-1">Configuración: <span className="mono">{JSON.stringify(source.config)}</span></p>
                    {source.last_error && <p className="mt-1 text-brick">Último error: {source.last_error}</p>}
                    {source.disabled_reason && <p className="mt-1">Motivo de desactivación: {source.disabled_reason}</p>}
                    <p className="mt-1">Sitio: <a href={source.homepage_url} target="_blank" rel="noreferrer noopener" className="underline">{source.homepage_url}</a></p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && tab === "duplicates" && (
        <div className="mt-7">
          {duplicates.length === 0 ? (
            <div className="border border-dashed border-line-strong p-10 text-center">
              <Check size={24} className="mx-auto text-fern" />
              <p className="mt-3 font-display text-2xl">Sin duplicados abiertos</p>
              <p className="mt-1 text-[12px] text-muted">
                Las coincidencias exactas se fusionan automáticamente; las dudosas se revisan aquí.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {duplicates.map((pair) => (
                <div key={pair.id} className="border border-line bg-paper-raised p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                    <p className="font-mono text-[10px] uppercase tracking-[0.1em] text-amber">
                      Similitud {Math.round(pair.score * 100)}%
                    </p>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => resolveDuplicate(pair.id, "merge")} className="btn btn-primary !px-3 !py-2 text-[11px]">
                        Fusionar
                      </button>
                      <button type="button" onClick={() => resolveDuplicate(pair.id, "reject")} className="btn btn-outline !px-3 !py-2 text-[11px]">
                        Son distintas
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {[pair.left, pair.right].map((side) => (
                      <Link key={side.id} href={`/oportunidades/${side.slug}`} className="block border border-line bg-paper p-3 hover:border-ink/30">
                        <p className="font-mono text-[9px] uppercase tracking-wider text-muted">
                          {side.published ? "publicada" : "no publicada"} · {side.source_count} fuentes
                        </p>
                        <p className="mt-1 text-[13px] text-ink">{side.title}</p>
                        <p className="mt-1 text-[10px] text-muted">
                          {side.organizer ?? "sin organizador"} · {side.event_start ? formatDateTime(side.event_start) : "sin fecha"}
                        </p>
                      </Link>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {pair.reasons.map((reason) => (
                      <span key={reason.code} className="chip">
                        {reason.label}: {reason.value}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && tab === "audit" && (
        <div className="mt-7">
          <div className="overflow-x-auto border border-line">
            <table className="w-full min-w-[760px] text-left">
              <thead>
                <tr className="border-b border-line bg-paper-deep/40">
                  {["Cuándo", "Oportunidad", "Campo", "Antes", "Después", "Actor", "Motivo"].map((label) => (
                    <th key={label} className="px-3 py-2 font-mono text-[8px] uppercase tracking-[0.1em] text-muted">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {audit.map((row) => (
                  <tr key={row.id} className="border-b border-line last:border-b-0">
                    <td className="whitespace-nowrap px-3 py-2.5 text-[10px] text-muted">{formatDateTime(row.created_at)}</td>
                    <td className="px-3 py-2.5 text-[10px] text-ink-soft">
                      {row.slug ? <Link href={`/oportunidades/${row.slug}`} className="underline">{row.slug}</Link> : "—"}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[10px]">{row.field}</td>
                    <td className="max-w-[160px] truncate px-3 py-2.5 text-[10px] text-muted">{JSON.stringify(row.old_value)}</td>
                    <td className="max-w-[160px] truncate px-3 py-2.5 text-[10px] text-ink-soft">{JSON.stringify(row.new_value)}</td>
                    <td className="px-3 py-2.5">
                      <span className="rounded-full border border-line px-2 py-1 font-mono text-[8px] uppercase">{row.actor}</span>
                    </td>
                    <td className="px-3 py-2.5 text-[10px] text-muted">{row.reason ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {audit.length === 0 && <p className="mt-4 text-[12px] text-muted">Sin cambios registrados.</p>}
        </div>
      )}

      <p className="mt-10 flex items-center gap-2 border-t border-line pt-4 text-[10px] text-muted">
        <Trash size={12} />
        Los datos personales de usuarios no se muestran en esta consola. Las acciones quedan auditadas.
      </p>
    </div>
  );
}
