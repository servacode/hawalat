"use client";

/**
 * إعدادات المكتب الصغير: معلومات المكتب للقراءة (الاسم + الكود) +
 * صورة بروفايل (تظهر بالتوب بار) + تغيير كلمة المرور.
 */

import { Camera, IdCard, KeyRound, Mail, Save, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Input,
  PasswordInput,
  Skeleton,
} from "@/components/ui";
import { authedApi } from "@/lib/authedApi";
import { updateSessionUser } from "@/lib/auth";

interface Me {
  username: string;
  first_name: string;
  office_code: string;
  tenant_name: string | null;
  avatar: string;
  email: string;
}

/** يصغّر الصورة إلى 256px ويعيدها data URL مضغوطة — تناسب حد الخادم. */
async function fileToAvatar(file: File): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = url;
    });
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    // قص مربع من المنتصف ثم تصغير
    const side = Math.min(img.width, img.height);
    ctx.drawImage(
      img,
      (img.width - side) / 2,
      (img.height - side) / 2,
      side,
      side,
      0,
      0,
      size,
      size,
    );
    return canvas.toDataURL("image/jpeg", 0.85);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function SmallSettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwBusy, setPwBusy] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [email, setEmail] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailMsg, setEmailMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    authedApi<Me>("/api/auth/me/").then((d) => {
      setMe(d);
      setEmail(d.email);
    }).catch(() => {});
  }, []);

  async function saveEmail(e: React.FormEvent) {
    e.preventDefault();
    setEmailMsg(null);
    setEmailBusy(true);
    try {
      const next = await authedApi<Me>("/api/auth/me/", { method: "PATCH", body: { email } });
      setMe(next);
      setEmail(next.email);
      setEmailMsg({ ok: true, text: "حُفظ البريد الإلكتروني." });
    } catch (err) {
      const detail = (err as { data?: { email?: string } })?.data?.email;
      setEmailMsg({ ok: false, text: detail ?? "تعذر الحفظ — تأكد من صيغة البريد." });
    } finally {
      setEmailBusy(false);
    }
  }

  async function saveAvatar(avatar: string) {
    setAvatarBusy(true);
    try {
      const next = await authedApi<Me>("/api/auth/me/", {
        method: "PATCH",
        body: { avatar },
      });
      setMe(next);
      updateSessionUser({ avatar: next.avatar });
    } finally {
      setAvatarBusy(false);
    }
  }

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    await saveAvatar(await fileToAvatar(file));
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwMsg(null);
    if (pw.next !== pw.confirm) {
      setPwMsg({ ok: false, text: "تأكيد كلمة المرور لا يطابقها." });
      return;
    }
    setPwBusy(true);
    try {
      await authedApi("/api/auth/change-password/", {
        method: "POST",
        body: { current_password: pw.current, new_password: pw.next },
      });
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ ok: true, text: "تم تغيير كلمة المرور بنجاح." });
    } catch {
      setPwMsg({
        ok: false,
        text: "تعذر التغيير — تأكد من كلمة المرور الحالية وأن الجديدة 8+ أحرف غير شائعة.",
      });
    } finally {
      setPwBusy(false);
    }
  }

  if (!me) return <Skeleton className="h-72" />;

  const name = me.first_name || me.username;
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      {/* صورة البروفايل */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="size-5 text-brand" /> صورة البروفايل
          </CardTitle>
        </CardHeader>
        <CardBody className="flex flex-wrap items-center gap-5">
          {me.avatar ? (
            // eslint-disable-next-line @next/next/no-img-element -- data URL محلي
            <img
              src={me.avatar}
              alt={name}
              className="size-20 rounded-full border border-border object-cover shadow-sm"
            />
          ) : (
            <div className="flex size-20 items-center justify-center rounded-full bg-brand/15 text-3xl font-bold text-brand-700">
              {name.trim().charAt(0)}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button disabled={avatarBusy} onClick={() => fileRef.current?.click()}>
              <Camera className="size-4" /> {me.avatar ? "تغيير الصورة" : "رفع صورة"}
            </Button>
            {me.avatar && (
              <Button variant="ghost" disabled={avatarBusy} onClick={() => saveAvatar("")}>
                <Trash2 className="size-4" /> إزالة
              </Button>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPickFile} />
          <p className="w-full text-sm text-muted">تظهر الصورة في الشريط العلوي — تُقصّ مربعة وتُصغّر تلقائياً.</p>
        </CardBody>
      </Card>

      {/* معلومات المكتب — للقراءة فقط */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <IdCard className="size-5 text-brand" /> معلومات المكتب
          </CardTitle>
        </CardHeader>
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Input label="اسم المكتب" value={name} disabled readOnly />
          <Input label="كود المكتب" value={me.office_code} disabled readOnly dir="ltr" className="tnum" />
          <Input label="اسم المستخدم" value={me.username} disabled readOnly dir="ltr" />
          <Input label="المكتب التابع له" value={me.tenant_name ?? "—"} disabled readOnly />
          <p className="text-sm text-muted sm:col-span-2">
            {`هذه البيانات يديرها مكتب ${me.tenant_name ?? "—"} — تواصل معه لأي تعديل.`}
          </p>
        </CardBody>
      </Card>

      {/* البريد الإلكتروني */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="size-5 text-brand" /> البريد الإلكتروني
          </CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={saveEmail} className="flex flex-col gap-3">
            <Input
              label="بريدك الإلكتروني"
              type="email"
              icon={Mail}
              dir="ltr"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {emailMsg && (
              <p
                className={
                  emailMsg.ok
                    ? "rounded-md bg-success/10 px-3 py-2 text-sm text-success"
                    : "rounded-md bg-danger/10 px-3 py-2 text-sm text-danger"
                }
              >
                {emailMsg.text}
              </p>
            )}
            <div>
              <Button type="submit" disabled={emailBusy || email === me.email}>
                <Save className="size-4" /> {emailBusy ? "جارٍ الحفظ…" : "حفظ البريد"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {/* تغيير كلمة المرور */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-5 text-brand" /> تغيير كلمة المرور
          </CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={changePassword} className="flex flex-col gap-4">
            <PasswordInput
              label="كلمة المرور الحالية"
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
              autoComplete="current-password"
              required
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <PasswordInput
                label="كلمة المرور الجديدة"
                hint="8 أحرف على الأقل وغير شائعة"
                value={pw.next}
                onChange={(e) => setPw({ ...pw, next: e.target.value })}
                autoComplete="new-password"
                required
              />
              <PasswordInput
                label="تأكيد كلمة المرور الجديدة"
                value={pw.confirm}
                onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
                autoComplete="new-password"
                required
              />
            </div>
            {pwMsg && (
              <p
                className={
                  pwMsg.ok
                    ? "rounded-md bg-success/10 px-3 py-2 text-sm text-success"
                    : "rounded-md bg-danger/10 px-3 py-2 text-sm text-danger"
                }
              >
                {pwMsg.text}
              </p>
            )}
            <div>
              <Button type="submit" disabled={pwBusy || !pw.current || !pw.next || !pw.confirm}>
                <Save className="size-4" /> {pwBusy ? "جارٍ الحفظ…" : "حفظ كلمة المرور"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
