"use client";

/** إعدادات المنصة: الوضع المجاني/المدفوع + التسجيل الذاتي + لوغو المنصة + خادم الواتساب. */

import { ImagePlus, MessageCircle, Save, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Card, CardBody, CardHeader, CardTitle, Input, PasswordInput, Skeleton } from "@/components/ui";
import { PlatformLogo, invalidatePlatformLogo } from "@/components/layout/PlatformLogo";
import { authedApi } from "@/lib/authedApi";

/** يصغّر اللوغو (أقصى بُعد 512px مع حفظ النسبة والشفافية) ويعيده data URL. */
async function fileToLogo(file: File): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = url;
    });
    const scale = Math.min(1, 512 / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}

interface Settings {
  free_mode: boolean;
  self_registration_enabled: boolean;
  logo: string;
  waha_url: string;
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-3">
      <span>
        <span className="block font-medium">{label}</span>
        <span className="block text-sm text-muted">{description}</span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-5 shrink-0 accent-(--brand-600)"
      />
    </label>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const logoRef = useRef<HTMLInputElement>(null);
  const [wahaUrl, setWahaUrl] = useState("");
  const [wahaKey, setWahaKey] = useState("");

  async function saveLogo(logo: string) {
    setLogoBusy(true);
    try {
      const next = await authedApi<Settings>("/api/admin/settings/", {
        method: "PATCH",
        body: { logo },
      });
      setSettings(next);
      invalidatePlatformLogo();
    } finally {
      setLogoBusy(false);
    }
  }

  async function onPickLogo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    await saveLogo(await fileToLogo(file));
  }

  useEffect(() => {
    authedApi<Settings>("/api/admin/settings/").then((d) => {
      setSettings(d);
      setWahaUrl(d.waha_url || "");
    }).catch(() => {});
  }, []);

  async function update(patch: Partial<Settings>) {
    const next = await authedApi<Settings>("/api/admin/settings/", {
      method: "PATCH",
      body: patch,
    });
    setSettings(next);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  if (!settings) return <Skeleton className="h-48" />;

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>وضع المنصة</CardTitle>
        </CardHeader>
        <CardBody className="divide-y divide-border">
          <Toggle
            label="الوضع المجاني"
            description="مفعّل: كل شيء مفتوح بلا باقات. معطّل: يلزم اشتراك مفعّل، وتسري الحدود على ما يُنشأ بعد التفعيل فقط (الترحيل)."
            checked={settings.free_mode}
            onChange={(v) => update({ free_mode: v })}
          />
          <Toggle
            label="التسجيل الذاتي للمكاتب الكبيرة"
            description="مفعّل: يظهر زر إنشاء حساب في صفحة الدخول، والطلبات تُنشأ موقوفة بانتظار تفعيلك."
            checked={settings.self_registration_enabled}
            onChange={(v) => update({ self_registration_enabled: v })}
          />
        </CardBody>
      </Card>
      {/* لوغو المنصة (ملاحظة 15): يظهر بالشعار الجانبي وشاشة الدخول لكل المستخدمين */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImagePlus className="size-5 text-brand" /> لوغو المنصة
          </CardTitle>
        </CardHeader>
        <CardBody className="flex flex-wrap items-center gap-5">
          {settings.logo ? (
            // eslint-disable-next-line @next/next/no-img-element -- data URL محلي
            <img src={settings.logo} alt="لوغو المنصة" className="max-h-20 max-w-40 rounded-xl border border-border object-contain p-1" />
          ) : (
            <PlatformLogo size="lg" />
          )}
          <div className="flex flex-wrap gap-2">
            <Button disabled={logoBusy} onClick={() => logoRef.current?.click()}>
              <ImagePlus className="size-4" /> {settings.logo ? "تغيير اللوغو" : "رفع لوغو"}
            </Button>
            {settings.logo && (
              <Button variant="ghost" disabled={logoBusy} onClick={() => saveLogo("")}>
                <Trash2 className="size-4" /> إزالة (العودة للافتراضي)
              </Button>
            )}
          </div>
          <input ref={logoRef} type="file" accept="image/*" hidden onChange={onPickLogo} />
          <p className="w-full text-sm text-muted">
            يظهر في الشعار الجانبي وشاشة الدخول لكل المكاتب — يُصغَّر تلقائياً مع حفظ الشفافية.
          </p>
        </CardBody>
      </Card>

      {/* خادم الواتساب (ملاحظة 44): WAHA واحد للمنصة — وكل مكتب كبير يربط رقمه بمسح QR */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="size-5 text-brand" /> خادم الواتساب (WAHA)
          </CardTitle>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <p className="text-sm text-muted">
            يُضبط مرة واحدة عند النشر — وبعدها كل مكتب كبير يربط رقمه بنفسه بمسح QR
            من إعداداته، فتُرسل المطابقات والحركات مباشرة من رقمه.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="عنوان الخادم" dir="ltr" placeholder="https://waha.example.com"
              value={wahaUrl} onChange={(e) => setWahaUrl(e.target.value)} />
            <PasswordInput label="مفتاح الخادم (API Key)" dir="ltr"
              value={wahaKey} onChange={(e) => setWahaKey(e.target.value)}
              placeholder="يبقى المحفوظ إن تُرك فارغاً" />
          </div>
          <div className="flex justify-end">
            <Button onClick={() => update({ waha_url: wahaUrl, ...(wahaKey ? { waha_key: wahaKey } : {}) } as Partial<Settings>)}>
              <Save className="size-4" /> حفظ
            </Button>
          </div>
        </CardBody>
      </Card>

      {saved && <p className="text-sm text-success">تم الحفظ ✓</p>}
    </div>
  );
}
