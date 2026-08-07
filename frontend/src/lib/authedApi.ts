/**
 * حوالات — نداء API موثّق بالجلسة (مركزي)
 * يضيف التوكن تلقائياً؛ 401 → تنظيف الجلسة والعودة للدخول.
 */

import { api, ApiError } from "./api";
import { clearSession, getSession } from "./auth";

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
      clearSession();
      window.location.href = "/login";
    }
    throw err;
  }
}
