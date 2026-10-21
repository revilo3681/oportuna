import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthLayout } from "@/components/auth-layout";
import { getSessionUser } from "@/lib/api";
import { safeNextPath } from "@/lib/navigation";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Crear cuenta",
  description: "Activa tu radar personal de oportunidades tecnológicas en menos de un minuto.",
};

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const nextPath = safeNextPath(sp.next);
  const user = await getSessionUser();
  if (user) redirect(nextPath);

  return (
    <AuthLayout
      eyebrow="Crear cuenta · gratis"
      title="Activa tu radar."
      description="Empieza con intereses, modalidad y disponibilidad. El resto se completa cuando tú quieras, sin bloquear el catálogo."
      sideTitle={
        <>
          Dos personas,
          <br />
          dos radares
          <br />
          <span className="italic text-signal">distintos.</span>
        </>
      }
      sideBody="La misma oportunidad puede ser perfecta para quien tiene el sábado libre y descartable para quien dispone de veinte minutos. Tu disponibilidad es parte del filtro."
    >
      <AuthForm mode="register" nextPath={nextPath} />
    </AuthLayout>
  );
}
