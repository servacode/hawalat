/**
 * حوالات — إدارة الجلسة المركزية (المرحلة 2)
 * «تذكّرني» → localStorage (يبقى بعد إغلاق المتصفح)
 * بدونها → sessionStorage (تنتهي بإغلاق التبويب)
 */

export type Role = "admin" | "big_office" | "small_office";

export interface SessionUser {
  id: number;
  username: string;
  first_name: string;
  role: Role;
  office_code: string;
  tenant_code: string | null;
  tenant_name: string | null;
  whatsapp_group_link?: string;
  whatsapp_group_name?: string;
  avatar?: string;
}

export interface Session {
  access: string;
  refresh: string;
  user: SessionUser;
}

const KEY = "hawalat.session";

function storage(remember: boolean): Storage {
  return remember ? localStorage : sessionStorage;
}

export function saveSession(session: Session, remember: boolean): void {
  clearSession();
  storage(remember).setItem(KEY, JSON.stringify(session));
}

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY) ?? sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

/** يحدّث بيانات مستخدم الجلسة المحفوظة (مثل الصورة) ويُعلم الواجهة. */
export function updateSessionUser(patch: Partial<SessionUser>): void {
  const session = getSession();
  if (!session) return;
  const next: Session = { ...session, user: { ...session.user, ...patch } };
  saveSession(next, sessionRemembered());
  window.dispatchEvent(new CustomEvent("hawalat:session"));
}

export function clearSession(): void {
  localStorage.removeItem(KEY);
  sessionStorage.removeItem(KEY);
}

/** أين حُفظت الجلسة الحالية؟ (للحفاظ على وضع «تذكّرني» عند التجديد) */
export function sessionRemembered(): boolean {
  return typeof window !== "undefined" && localStorage.getItem(KEY) !== null;
}

/** يجدّد access باستخدام refresh — يعيد الجلسة الجديدة أو null (انتهت). */
export async function refreshSession(): Promise<Session | null> {
  const session = getSession();
  if (!session) return null;
  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${API_URL}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: session.refresh }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { access: string; refresh?: string };
    const next: Session = {
      ...session,
      access: data.access,
      refresh: data.refresh ?? session.refresh, // التدوير يعيد refresh جديداً
    };
    saveSession(next, sessionRemembered());
    return next;
  } catch {
    return null;
  }
}

/** الوجهة الرئيسية لكل دور — التوجيه الموحّد بعد الدخول */
export function roleHome(role: Role): string {
  switch (role) {
    case "admin":
      return "/admin";
    case "big_office":
      return "/office";
    case "small_office":
      // رئيسية الصغير أُلغيت (ملاحظة 17) — يدخل مباشرة على إرسال حركة
      return "/small/send";
  }
}
