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
      onClick={async () => {
        const session = getSession();
        if (session) {
          // إبطال refresh نهائياً على الخادم (blacklist) — لا ننتظر النتيجة طويلاً
          const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
          fetch(`${API_URL}/api/auth/logout/`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${session.access}`,
            },
            body: JSON.stringify({ refresh: session.refresh }),
          }).catch(() => {});
        }
        clearSession();
        router.replace("/login");
      }}
      className="text-sm text-muted transition-colors hover:text-danger focus-visible:outline-2 focus-visible:outline-brand"
    >
      تسجيل الخروج
    </button>
  );
}
