import { AssistantPanel } from "@/components/assistant-panel";
import { apiGet, getSessionUser } from "@/lib/api";
import type { AssistantStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Asistente de oportunidades",
  description:
    "Pregunta por hackathons, becas o eventos según modalidad, presupuesto, país y fechas. Respuestas basadas en el catálogo verificado y con fuentes citadas.",
};

export default async function AssistantPage() {
  const user = await getSessionUser();
  let aiStatus: AssistantStatus | null = null;
  try {
    aiStatus = await apiGet<AssistantStatus>("/assistant/status");
  } catch {
    aiStatus = null;
  }

  return (
    <div className="shell py-10 lg:py-14">
      <header className="max-w-3xl">
        <p className="eyebrow mb-3">Asistente · IA local sobre catálogo verificado</p>
        <h1 className="display text-[44px] leading-[0.98] tracking-[-0.03em] sm:text-[58px]">
          Pregunta como
          <br />
          <span className="italic text-signal-deep">le preguntarías a alguien</span>
          <br />
          que ya revisó las fuentes.
        </h1>
        <p className="mt-5 max-w-2xl text-[14px] leading-relaxed text-muted">
          Sin ruido, sin enlaces muertos y sin eventos inventados. Tu IA local traduce la pregunta a filtros, consulta el catálogo publicado y cita de dónde sale cada respuesta. Nada se envía a la nube.
        </p>
      </header>

      <div className="mt-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_290px]">
        <AssistantPanel userName={user ? user.display_name || user.email : null} initialStatus={aiStatus} />

        <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <div className="border border-line bg-paper-raised p-5">
            <p className="eyebrow">Qué entiende</p>
            <ul className="mt-3 space-y-2 text-[12px] leading-relaxed text-ink-soft">
              <li>· Categoría: hackathon, beca, evento, startup.</li>
              <li>· Tecnología: IA, datos, ciberseguridad, robótica.</li>
              <li>· Modalidad: online, presencial o híbrida.</li>
              <li>· Precio: gratis o con coste.</li>
              <li>· Tiempo: hoy, esta semana, este mes.</li>
              <li>· País o región cuando el catálogo lo declara.</li>
            </ul>
          </div>

          <div className="border border-line bg-paper-raised p-5">
            <p className="eyebrow">Qué no hace</p>
            <ul className="mt-3 space-y-2 text-[12px] leading-relaxed text-muted">
              <li>· No inventa convocatorias ni fechas.</li>
              <li>· No inscribe ni paga por ti.</li>
              <li>· No afirma que cumples requisitos sin datos.</li>
              <li>· No usa oportunidades no publicadas.</li>
            </ul>
          </div>

          <div className="border border-line bg-ink p-5 text-paper-raised">
            <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-signal">
              Modo de respuesta
            </p>
            <p className="mt-2 font-display text-[22px] leading-tight">
              Reglas explícitas sobre datos verificados, no una caja negra.
            </p>
            <p className="mt-2 text-[11px] leading-relaxed text-paper-raised/55">
              El motor no genera texto libre sobre el catálogo: filtra, ordena y explica. Si no hay
              coincidencias, lo verás.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
