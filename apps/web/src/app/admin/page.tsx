import { AdminConsole } from "@/components/admin-console";
import { requireAdmin } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Consola interna",
  robots: { index: false, follow: false },
};

export default async function AdminPage() {
  const user = await requireAdmin();

  return (
    <div className="min-h-[calc(100vh-70px)] bg-paper-deep/25">
      <AdminConsole adminName={user.display_name || user.email} />
    </div>
  );
}
