"use client";

/** إعدادات المنصة: مفتاح الوضع المجاني/المدفوع + مفتاح التسجيل الذاتي. */

import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle, Skeleton } from "@/components/ui";
import { authedApi } from "@/lib/authedApi";

interface Settings {
  free_mode: boolean;
  self_registration_enabled: boolean;
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

  useEffect(() => {
    authedApi<Settings>("/api/admin/settings/").then(setSettings).catch(() => {});
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
      {saved && <p className="text-sm text-success">تم الحفظ ✓</p>}
    </div>
  );
}
