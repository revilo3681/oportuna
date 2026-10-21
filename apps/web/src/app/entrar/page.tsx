import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthLayout } from "@/components/auth-layout";
import { getSessionUser } from "@/lib/api";
import { safeNextPath } from "@/lib/navigation";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Entrar",
  description: "Accede a tu radar personal de oportunidades tecnológicas.",
};

export default async function LoginPage({
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
      eyebrow="Tu cuenta"
      title="Bienvenido de vuelta."
      description="Tu panel, tus guardadas y tus fechas límite siguen donde los dejaste."
      sideTitle={
        <>
          El radar sigue
          <br />
          <span className="italic text-paper-raised/65">trabajando por ti.</span>
        </>
      }
      sideBody="Mientras no estás, comprobamos fuentes, actualizamos plazos y buscamos señales nuevas. Al volver, encuentras lo importante ya ordenado."
    >
      <AuthForm mode="login" nextPath={nextPath} />
    </AuthLayout>
  );
}
