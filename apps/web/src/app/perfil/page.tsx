import Link from "next/link";

import { ProfileForm } from "@/components/profile-form";
import { ApiUnavailable } from "@/components/ui";
import { apiGet, getSessionToken, requireUser } from "@/lib/api";
import type { Profile, Taxonomy } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Mi perfil y disponibilidad",
  description:
    "Ajusta intereses, modalidad, ubicación y tiempo disponible para que el ranking de Oportuna explique mejor sus recomendaciones.",
};

export default async function ProfilePage() {
  const user = await requireUser("/perfil");
  const token = await getSessionToken();

  let profile: Profile;
  let taxonomy: Taxonomy;
  try {
    const [profilePayload, taxonomyPayload] = await Promise.all([
      apiGet<{ profile: Profile }>("/profile", token),
      apiGet<Taxonomy>("/taxonomy", token),
    ]);
    profile = profilePayload.profile;
    taxonomy = taxonomyPayload;
  } catch (error) {
    return <ApiUnavailable detail={error instanceof Error ? error.message : undefined} />;
  }

  return (
    <div className="shell py-10 lg:py-14">
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-line pb-7">
        <div>
          <p className="eyebrow mb-3">Tu radar · {user.email}</p>
          <h1 className="display max-w-3xl text-[44px] leading-[0.98] tracking-[-0.03em] sm:text-[56px]">
            Un radar a la medida
            <br />
            <span className="italic text-signal-deep">de tu tiempo real.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[13px] leading-relaxed text-muted">
            Dos personas interesadas en IA no necesitan lo mismo. Cuéntanos qué te interesa, cuándo
            puedes participar y cuánto tiempo tienes. Puedes cambiar todo cuando quieras.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/calendario" className="btn btn-outline !py-2.5">
            Mi calendario
          </Link>
          <Link href="/oportunidades" className="btn btn-primary !py-2.5">
            Explorar catálogo
          </Link>
        </div>
      </header>

      <div className="mt-8">
        <ProfileForm
          initialProfile={profile}
          taxonomy={taxonomy}
          userName={user.display_name || user.email}
        />
      </div>
    </div>
  );
}
