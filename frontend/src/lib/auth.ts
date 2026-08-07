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

export function clearSession(): void {
  localStorage.removeItem(KEY);
  sessionStorage.removeItem(KEY);
}

/** الوجهة الرئيسية لكل دور — التوجيه الموحّد بعد الدخول */
export function roleHome(role: Role): string {
  switch (role) {
    case "admin":
      return "/admin";
    case "big_office":
      return "/office";
    case "small_office":
      return "/small";
  }
}
