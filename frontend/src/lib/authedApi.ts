/**
 * حوالات — نداء API موثّق بالجلسة (مركزي)
 * يضيف التوكن تلقائياً؛ 401 → تنظيف الجلسة والعودة للدخول.
 */

import { api, ApiError } from "./api";
import { clearSession, getSession, refreshSession } from "./auth";

export async function authedApi<T>(
  path: string,
  options: Omit<Parameters<typeof api>[1] & object, "token"> = {},
): Promise<T> {
  const session = getSession();
  if (!session) {
    window.location.href = "/login";
    throw new ApiError(401, "لا توجد جلسة");
  }
  try {
    return await api<T>(path, { ...options, token: session.access });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      // تجديد تلقائي ثم إعادة محاولة واحدة — وإلا خروج نظيف
      const renewed = await refreshSession();
      if (renewed) {
        return api<T>(path, { ...options, token: renewed.access });
      }
      clearSession();
      window.location.href = "/login";
    }
    throw err;
  }
}

/** تنزيل ملف (Excel/PDF) بجلسة موثّقة عبر blob — window.open لا يحمل التوكن. */
export async function authedDownload(path: string, filename: string) {
  const session = getSession();
  if (!session) return;
  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${session.access}` },
  });
  if (!res.ok) throw new ApiError(res.status, "فشل التنزيل");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
