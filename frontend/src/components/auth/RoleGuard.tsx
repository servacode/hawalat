"use client";

/**
 * حارس الأدوار المركزي: يمنع الوصول بلا جلسة، ويعيد كل دور لواجهته.
 * (حماية الواجهة فقط — الحماية الفعلية للبيانات في الـ API بالصلاحيات والعزل.)
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
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

export function LogoutButton({ compact = false }: { compact?: boolean }) {
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
      className={
        compact
          ? "flex size-9 items-center justify-center rounded-full text-danger transition-colors hover:bg-danger hover:text-white focus-visible:outline-2 focus-visible:outline-danger"
          : "flex items-center justify-center gap-2 rounded-lg bg-danger px-3 py-2 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-danger"
      }
      aria-label="تسجيل الخروج"
    >
      <LogOut className="size-4" aria-hidden="true" />
      {!compact && "تسجيل الخروج"}
    </button>
  );
}
