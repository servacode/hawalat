"use client";

/**
 * حارس الأدوار المركزي: يمنع الوصول بلا جلسة، ويعيد كل دور لواجهته.
 * (حماية الواجهة فقط — الحماية الفعلية للبيانات في الـ API بالصلاحيات والعزل.)
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getSession, roleHome, type Role, type Session } from "@/lib/auth";

export function RoleGuard({
  role,
  children,
}: {
  role: Role;
  children: (session: Session) => React.ReactNode;
}) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const s = getSession();
    if (!s) {
      router.replace("/login");
      return;
    }
    if (s.user.role !== role) {
      router.replace(roleHome(s.user.role));
      return;
    }
    setSession(s);
    setChecked(true);
  }, [role, router]);

  if (!checked || !session) return null;
  return <>{children(session)}</>;
}

export function LogoutButton() {
  const router = useRouter();
  return (
    <button
      onClick={() => {
        clearSession();
        router.replace("/login");
      }}
      className="text-sm text-muted transition-colors hover:text-danger focus-visible:outline-2 focus-visible:outline-brand"
    >
      تسجيل الخروج
    </button>
  );
}
