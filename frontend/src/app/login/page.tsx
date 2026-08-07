"use client";

/** حوالات — بوابة الدخول الموحّدة (المشهد 6): دور واحد لكل مستخدم يحدد وجهته. */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, CardBody, Input, Modal } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { roleHome, saveSession, type Session } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const session = await api<Session>("/api/auth/login/", {
        method: "POST",
        body: { username, password, remember },
      });
      saveSession(session, remember);
      router.replace(roleHome(session.user.role));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "بيانات الدخول غير صحيحة، أو الحساب موقوف."
          : "تعذر الاتصال بالخادم — حاول مجدداً.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-brand text-2xl font-bold text-white shadow-md">
            ح
          </div>
          <h1 className="text-2xl font-bold">حوالات</h1>
          <p className="text-muted">سجّل دخولك للمتابعة</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={onSubmit} className="flex flex-col gap-4">
              <Input
                label="اسم المستخدم"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
              <Input
                label="كلمة المرور"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />

              <div className="flex items-center justify-between">
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="size-4 accent-(--brand-600)"
                  />
                  تذكّرني
                </label>
                <button
                  type="button"
                  onClick={() => setForgotOpen(true)}
                  className="text-sm text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-brand"
                >
                  نسيت كلمة المرور؟
                </button>
              </div>

              {error && (
                <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
                  {error}
                </p>
              )}

              <Button type="submit" size="lg" disabled={loading}>
                {loading ? "جارٍ الدخول…" : "دخول"}
              </Button>
            </form>
          </CardBody>
        </Card>

        <p className="mt-6 text-center text-sm text-muted">
          لا تملك حساباً؟ فتح الحسابات يتم عبر مكتبك أو إدارة المنصة.
        </p>
      </div>

      <Modal
        open={forgotOpen}
        onClose={() => setForgotOpen(false)}
        title="استعادة كلمة المرور"
        footer={<Button onClick={() => setForgotOpen(false)}>فهمت</Button>}
      >
        <p className="text-muted">
          استعادة كلمة المرور تتم بشكل هرمي حفاظاً على الأمان:
        </p>
        <ul className="mt-3 flex list-inside list-disc flex-col gap-1.5 text-muted">
          <li>
            <span className="font-medium text-ink">مكتب صغير؟</span> تواصل مع
            مكتبك الكبير ليعيد تعيينها فوراً.
          </li>
          <li>
            <span className="font-medium text-ink">مكتب كبير؟</span> تواصل مع
            إدارة المنصة.
          </li>
        </ul>
      </Modal>
    </main>
  );
}
