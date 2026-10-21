"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Check, Info, Trash } from "@/components/icons";
import { DAY_LABELS, SLOT_LABELS, cn } from "@/lib/format";
import type { Profile, Taxonomy } from "@/lib/types";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SLOTS = ["morning", "afternoon", "evening"];
const TEAM_OPTIONS = [
  { value: "unknown", label: "Me da igual" },
  { value: "team", label: "Prefiero equipo" },
  { value: "solo", label: "Prefiero individual" },
];

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] transition-colors",
        active
          ? "border-ink bg-ink text-paper-raised"
          : "border-line bg-paper-raised text-ink-soft hover:border-ink/40",
      )}
    >
      {active && <Check size={11} />}
      {children}
    </button>
  );
}

function Section({
  number,
  title,
  description,
  children,
  tone,
}: {
  number: string;
  title: string;
  description: string;
  children: React.ReactNode;
  tone?: "core" | "advanced";
}) {
  return (
    <section className="border border-line bg-paper-raised">
      <header className="flex items-start gap-4 border-b border-line p-5">
        <span className="mono mt-0.5 text-[11px] text-signal">{number}</span>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-[24px] leading-tight">{title}</h2>
            {tone === "core" && (
              <span className="rounded-full bg-signal-soft px-2 py-0.5 font-mono text-[8px] uppercase tracking-wider text-signal-deep">
                Esencial
              </span>
            )}
          </div>
          <p className="mt-1 text-[12px] leading-relaxed text-muted">{description}</p>
        </div>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function ProfileForm({
  initialProfile,
  taxonomy,
  userName,
}: {
  initialProfile: Profile;
  taxonomy: Taxonomy;
  userName: string;
}) {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dangerOpen, setDangerOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const completeness = profile.completeness;
  const selectedDays = profile.availability?.days ?? [];
  const selectedSlots = profile.availability?.slots ?? [];

  const groupedInterests = useMemo(
    () => [
      { label: "Categorías", items: taxonomy.categories.map((item) => ({ key: item.key, label: item.label })) },
      { label: "Tecnologías", items: taxonomy.tech },
    ],
    [taxonomy],
  );

  function update<K extends keyof Profile>(key: K, value: Profile[K]) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function toggleList(key: "interests" | "modalities" | "goals" | "languages" | "time_preferences", value: string) {
    const current = profile[key] ?? [];
    update(key, current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }

  function toggleAvailability(kind: "days" | "slots", value: string) {
    const availability = profile.availability ?? {};
    const current = availability[kind] ?? [];
    const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    update("availability", { ...availability, [kind]: next });
  }

  async function save(event?: React.FormEvent) {
    event?.preventDefault();
    setPending(true);
    setMessage(null);
    setError(null);
    try {
      const payload = {
        interests: profile.interests,
        level: profile.level,
        goals: profile.goals,
        country: profile.country,
        city: profile.city || null,
        travel_radius_km: profile.travel_radius_km,
        modalities: profile.modalities,
        languages: profile.languages,
        availability: profile.availability,
        time_preferences: profile.time_preferences,
        budget: profile.budget,
        eligibility: {
          ...(typeof profile.eligibility?.age === "number" ? { age: profile.eligibility.age } : {}),
          ...(typeof profile.eligibility?.is_student === "boolean"
            ? { is_student: profile.eligibility.is_student }
            : {}),
        },
        preferences: {
          ...profile.preferences,
          team:
            profile.preferences?.team === "team"
              ? true
              : profile.preferences?.team === "solo"
                ? false
                : null,
        },
      };
      const response = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("No se pudo guardar el perfil");
      const data = (await response.json()) as { profile: Profile };
      setProfile(data.profile);
      setMessage("Perfil guardado. Tu panel se recalcula con estos datos.");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setPending(false);
    }
  }

  async function resetProfile() {
    if (!window.confirm("¿Vaciar todos los datos de tu perfil? Esta acción no se puede deshacer.")) return;
    setPending(true);
    try {
      const response = await fetch("/api/profile", { method: "DELETE", credentials: "include" });
      if (!response.ok) throw new Error("No se pudo borrar el perfil");
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
      setPending(false);
    }
  }

  async function deleteAccount() {
    if (confirmText !== "eliminar") return;
    setPending(true);
    try {
      const response = await fetch("/api/account?confirm=eliminar", {
        method: "DELETE",
        credentials: "include",
      });
      if (!response.ok) throw new Error("No se pudo eliminar la cuenta");
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
      setPending(false);
    }
  }

  const coreReady =
    profile.interests.length > 0 && profile.modalities.length > 0 && selectedDays.length > 0;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
      <form id="profile-form" onSubmit={save} className="space-y-4">
        {!coreReady && (
          <div className="flex gap-3 border border-amber/30 bg-amber-soft/60 p-4 text-[12px] leading-relaxed text-ink-soft">
            <Info size={16} className="mt-0.5 shrink-0 text-amber" />
            <p>
              Para personalizar el ranking necesitamos al menos un interés, una modalidad y un día
              disponible. Todo lo demás es opcional y puedes cambiarlo cuando quieras.
            </p>
          </div>
        )}

        <Section
          number="01"
          title="Qué te interesa"
          description="Elige categorías y tecnologías. No es un examen: puedes marcar varias y ajustarlo después."
          tone="core"
        >
          <div className="space-y-5">
            {groupedInterests.map((group) => (
              <div key={group.label}>
                <p className="label">{group.label}</p>
                <div className="flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <Chip
                      key={item.key}
                      active={profile.interests.includes(item.key)}
                      onClick={() => toggleList("interests", item.key)}
                    >
                      {item.label}
                    </Chip>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section
          number="02"
          title="Cómo quieres participar"
          description="Filtramos por la modalidad que realmente puedes asumir."
          tone="core"
        >
          <div className="grid gap-2 sm:grid-cols-3">
            {Object.entries(taxonomy.modalities)
              .filter(([key]) => key !== "unknown")
              .map(([key, label]) => {
                const active = profile.modalities.includes(key);
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleList("modalities", key)}
                    aria-pressed={active}
                    className={cn(
                      "flex items-center justify-between border px-4 py-3 text-left text-[13px] transition-colors",
                      active
                        ? "border-ink bg-ink text-paper-raised"
                        : "border-line bg-paper text-ink-soft hover:border-ink/40",
                    )}
                  >
                    {label}
                    {active ? <Check size={14} /> : <span className="size-3.5 rounded-full border border-line-strong" />}
                  </button>
                );
              })}
          </div>
        </Section>

        <Section
          number="03"
          title="Dónde estás"
          description="País y ciudad permiten comprobar elegibilidad y cercanía. Puedes omitir la ciudad si prefieres."
          tone="core"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="country">
                País
              </label>
              <select
                id="country"
                className="field"
                value={profile.country ?? ""}
                onChange={(event) => update("country", event.target.value || null)}
              >
                <option value="">Prefiero no decirlo</option>
                {taxonomy.countries_all.map((country) => (
                  <option key={country.code} value={country.code}>
                    {country.name ?? country.code}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="city">
                Ciudad (opcional)
              </label>
              <input
                id="city"
                className="field"
                value={profile.city ?? ""}
                onChange={(event) => update("city", event.target.value || null)}
                placeholder="Lima"
                maxLength={120}
              />
            </div>
            <div>
              <label className="label" htmlFor="radius">
                Radio de desplazamiento (km)
              </label>
              <input
                id="radius"
                type="number"
                min={0}
                max={20000}
                className="field"
                value={profile.travel_radius_km ?? ""}
                onChange={(event) =>
                  update("travel_radius_km", event.target.value ? Number(event.target.value) : null)
                }
                placeholder="Opcional"
              />
            </div>
          </div>
        </Section>

        <Section
          number="04"
          title="Tu tiempo real"
          description="Distinguimos tiempo para asistir y tiempo de preparación. El ranking no te propondrá un hackathon de 24 h si solo tienes 45 minutos."
          tone="core"
        >
          <div className="space-y-5">
            <div>
              <p className="label">Días disponibles</p>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((day) => (
                  <Chip
                    key={day}
                    active={selectedDays.includes(day)}
                    onClick={() => toggleAvailability("days", day)}
                  >
                    {DAY_LABELS[day]}
                  </Chip>
                ))}
              </div>
            </div>
            <div>
              <p className="label">Franjas</p>
              <div className="flex flex-wrap gap-2">
                {SLOTS.map((slot) => (
                  <Chip
                    key={slot}
                    active={selectedSlots.includes(slot)}
                    onClick={() => toggleAvailability("slots", slot)}
                  >
                    {SLOT_LABELS[slot]}
                  </Chip>
                ))}
              </div>
            </div>
            <div>
              <p className="label">Bloques que puedes dedicar</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(taxonomy.time_buckets).map(([key, label]) => (
                  <Chip
                    key={key}
                    active={profile.time_preferences.includes(key)}
                    onClick={() => toggleList("time_preferences", key)}
                  >
                    {label}
                  </Chip>
                ))}
              </div>
            </div>
          </div>
        </Section>

        <details open={completeness > 35} className="group">
          <summary className="flex cursor-pointer items-center justify-between border border-line bg-paper-raised px-5 py-4">
            <div>
              <p className="eyebrow">Opcional</p>
              <h2 className="mt-1 font-display text-[24px] leading-tight">Afina el radar</h2>
              <p className="mt-1 text-[12px] text-muted">
                Nivel, objetivos, idiomas, presupuesto y preferencias de formato. Mejora la
                explicación del ranking, no bloquea el uso.
              </p>
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted group-open:hidden">
              Abrir
            </span>
            <span className="hidden font-mono text-[10px] uppercase tracking-wider text-muted group-open:block">
              Cerrar
            </span>
          </summary>

          <div className="mt-4 space-y-4">
            <Section number="05" title="Nivel y objetivos" description="No cambia tu acceso a las oportunidades; cambia el orden y el motivo mostrado.">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="level">
                    Nivel
                  </label>
                  <select
                    id="level"
                    className="field"
                    value={profile.level ?? ""}
                    onChange={(event) => update("level", event.target.value || null)}
                  >
                    <option value="">Prefiero no decirlo</option>
                    {Object.entries(taxonomy.levels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <p className="label">Objetivos</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(taxonomy.goals).map(([key, label]) => (
                      <Chip
                        key={key}
                        active={profile.goals.includes(key)}
                        onClick={() => toggleList("goals", key)}
                      >
                        {label}
                      </Chip>
                    ))}
                  </div>
                </div>
              </div>
            </Section>

            <Section number="06" title="Idiomas y presupuesto" description="Filtramos eventos en idiomas que puedes usar y costes que puedes asumir.">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="label">Idiomas</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(taxonomy.languages)
                      .slice(0, 10)
                      .map(([key, label]) => (
                        <Chip
                          key={key}
                          active={profile.languages.includes(key)}
                          onClick={() => toggleList("languages", key)}
                        >
                          {label}
                        </Chip>
                      ))}
                  </div>
                </div>
                <div>
                  <label className="label" htmlFor="budget">
                    Presupuesto
                  </label>
                  <select
                    id="budget"
                    className="field"
                    value={profile.budget ?? ""}
                    onChange={(event) => update("budget", event.target.value || null)}
                  >
                    <option value="">Prefiero no decirlo</option>
                    {Object.entries(taxonomy.budgets).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Section>

            <Section number="07" title="Elegibilidad y formato" description="Solo lo usamos para avisarte si algo no encaja. Nunca afirmamos que cumplas requisitos sin datos.">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="age">
                    Edad
                  </label>
                  <input
                    id="age"
                    type="number"
                    min={13}
                    max={120}
                    className="field"
                    value={typeof profile.eligibility?.age === "number" ? profile.eligibility.age : ""}
                    onChange={(event) =>
                      update("eligibility", {
                        ...profile.eligibility,
                        age: event.target.value ? Number(event.target.value) : null,
                      })
                    }
                    placeholder="Opcional"
                  />
                </div>
                <div>
                  <label className="label" htmlFor="student">
                    Estatus de estudiante
                  </label>
                  <select
                    id="student"
                    className="field"
                    value={
                      profile.eligibility?.is_student === true
                        ? "yes"
                        : profile.eligibility?.is_student === false
                          ? "no"
                          : ""
                    }
                    onChange={(event) =>
                      update("eligibility", {
                        ...profile.eligibility,
                        is_student:
                          event.target.value === "yes"
                            ? true
                            : event.target.value === "no"
                              ? false
                              : null,
                      })
                    }
                  >
                    <option value="">Prefiero no decirlo</option>
                    <option value="yes">Sí, soy estudiante</option>
                    <option value="no">No soy estudiante</option>
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="team">
                    Formato preferido
                  </label>
                  <select
                    id="team"
                    className="field"
                    value={
                      profile.preferences?.team === true
                        ? "team"
                        : profile.preferences?.team === false
                          ? "solo"
                          : "unknown"
                    }
                    onChange={(event) =>
                      update("preferences", { ...profile.preferences, team: event.target.value })
                    }
                  >
                    {TEAM_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col justify-end gap-2">
                  <label className="flex items-center gap-2 text-[12px] text-ink-soft">
                    <input
                      type="checkbox"
                      className="size-3.5 accent-signal"
                      checked={profile.preferences?.certificate === true}
                      onChange={(event) =>
                        update("preferences", {
                          ...profile.preferences,
                          certificate: event.target.checked,
                        })
                      }
                    />
                    Me interesan certificados
                  </label>
                  <label className="flex items-center gap-2 text-[12px] text-ink-soft">
                    <input
                      type="checkbox"
                      className="size-3.5 accent-signal"
                      checked={profile.preferences?.prizes === true}
                      onChange={(event) =>
                        update("preferences", { ...profile.preferences, prizes: event.target.checked })
                      }
                    />
                    Me interesan premios
                  </label>
                </div>
              </div>
            </Section>
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-3 border-t border-line pt-5">
          <button type="submit" disabled={pending} className="btn btn-primary">
            {pending ? "Guardando…" : "Guardar cambios"}
          </button>
          {message && <span className="text-[12px] text-fern">{message}</span>}
          {error && <span className="text-[12px] text-brick">{error}</span>}
        </div>

        <div className="border border-line bg-paper p-5">
          <p className="eyebrow">Tus datos</p>
          <p className="mt-2 text-[12px] leading-relaxed text-muted">
            Puedes vaciar tu perfil sin borrar la cuenta, o eliminar la cuenta por completo. El
            catálogo seguirá siendo accesible aunque no tengas perfil.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={resetProfile} disabled={pending} className="btn btn-outline !py-2 text-[12px]">
              <Trash size={13} />
              Vaciar perfil
            </button>
            <button
              type="button"
              onClick={() => setDangerOpen((value) => !value)}
              className="btn btn-ghost !py-2 text-[12px] text-brick"
            >
              Eliminar cuenta
            </button>
          </div>
          {dangerOpen && (
            <div className="mt-4 border border-brick/30 bg-brick-soft/60 p-4">
              <p className="text-[11px] leading-relaxed text-ink-soft">
                Escribe <span className="mono">eliminar</span> para confirmar. Se borran tu perfil,
                guardadas y alertas. Esta acción es irreversible.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  className="field !w-40"
                  value={confirmText}
                  onChange={(event) => setConfirmText(event.target.value)}
                  placeholder="eliminar"
                  aria-label="Confirmación"
                />
                <button
                  type="button"
                  onClick={deleteAccount}
                  disabled={confirmText !== "eliminar" || pending}
                  className="btn bg-brick text-white disabled:opacity-40"
                >
                  Confirmar eliminación
                </button>
              </div>
            </div>
          )}
        </div>
      </form>

      <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
        <div className="border border-line bg-paper-raised p-5">
          <div className="flex items-baseline justify-between">
            <p className="eyebrow">Perfil completo</p>
            <span className="mono text-2xl text-ink">{completeness}%</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-paper-deep">
            <div className="h-full rounded-full bg-signal" style={{ width: `${Math.max(completeness, 2)}%` }} />
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-muted">
            La parte esencial basta para personalizar. Lo opcional mejora la precisión del motivo y la
            comprobación de elegibilidad.
          </p>
          <button type="submit" form="profile-form" disabled={pending} className="btn btn-primary mt-4 w-full !py-2.5">
            {pending ? "Guardando…" : "Guardar cambios"}
          </button>
        </div>

        <div className="border border-line bg-paper-raised p-5">
          <p className="eyebrow">Cómo se usa</p>
          <ul className="mt-3 space-y-3 text-[11px] leading-relaxed text-muted">
            <li>
              <strong className="font-medium text-ink-soft">Intereses y objetivos</strong> pesan en la
              afinidad del ranking.
            </li>
            <li>
              <strong className="font-medium text-ink-soft">Disponibilidad y tiempo</strong> filtran
              oportunidades que no caben en tu semana.
            </li>
            <li>
              <strong className="font-medium text-ink-soft">País y elegibilidad</strong> evitan
              recomendaciones que no puedes aprovechar.
            </li>
            <li>
              Tu elegibilidad nunca se afirma sin contrastar requisitos publicados: se muestra como
              “posiblemente elegible” o “por confirmar”.
            </li>
          </ul>
        </div>

        <div className="border border-line bg-paper-deep/40 p-5">
          <p className="eyebrow">Hola, {userName.split(" ")[0] || "explorador"}</p>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">
            Puedes cambiar o eliminar estos datos en cualquier momento. No vendemos perfiles ni los
            compartimos con terceros.
          </p>
        </div>
      </aside>
    </div>
  );
}
