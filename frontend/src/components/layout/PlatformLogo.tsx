"use client";

/** لوغو المنصة المركزي: يرفعه الأدمن من لوحته — وإلا يظهر شعار «ح» الافتراضي. */

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

let cached: string | null | undefined;

export function PlatformLogo({ className }: { className?: string }) {
  const [logo, setLogo] = useState<string | null>(cached ?? null);

  useEffect(() => {
    if (cached !== undefined) {
      setLogo(cached);
      return;
    }
    api<{ logo: string }>("/api/platform/branding/")
      .then((d) => {
        cached = d.logo || null;
        setLogo(cached);
      })
      .catch(() => {
        cached = null;
      });
  }, []);

  if (logo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- data URL محلي
      <img
        src={logo}
        alt="لوغو المنصة"
        className={cn("size-10 rounded-xl object-contain", className)}
      />
    );
  }
  return (
    <div
      className={cn(
        "flex size-10 items-center justify-center rounded-xl bg-brand text-lg font-bold text-white shadow-sm",
        className,
      )}
    >
      ح
    </div>
  );
}

/** يمسح الكاش بعد رفع الأدمن لوغو جديداً حتى يظهر فوراً. */
export function invalidatePlatformLogo() {
  cached = undefined;
}
