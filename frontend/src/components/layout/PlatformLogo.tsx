"use client";

/**
 * لوغو المنصة المركزي: يرفعه الأدمن من لوحته.
 * الصورة تُعرض على طبيعتها — بلا قص ولا حواف ولا دوائر (ملاحظة 24).
 * الافتراضي (لا لوغو): شعار «ح» بمربع الهوية.
 */

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

let cached: string | null | undefined;

const IMG_SIZES = { md: "h-10", lg: "h-16", xl: "h-20" } as const;
const BOX_SIZES = {
  md: "size-10 rounded-xl text-lg",
  lg: "size-16 rounded-2xl text-3xl",
  xl: "size-20 rounded-2xl text-4xl",
} as const;

export function PlatformLogo({
  size = "md",
  className,
}: {
  size?: keyof typeof IMG_SIZES;
  className?: string;
}) {
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
        className={cn("w-auto object-contain", IMG_SIZES[size], className)}
      />
    );
  }
  return (
    <div
      className={cn(
        "flex items-center justify-center bg-brand font-bold text-white shadow-sm",
        BOX_SIZES[size],
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
