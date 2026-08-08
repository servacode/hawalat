"use client";

/**
 * زر تبديل الثيم (فاتح/داكن): يضبط data-theme على <html> ويحفظ الاختيار
 * في localStorage — سكربت الإقلاع في layout يطبّقه قبل الرسم (بلا وميض).
 */

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export const THEME_KEY = "hawalat.theme";

function effectiveDark(): boolean {
  const explicit = document.documentElement.dataset.theme;
  if (explicit) return explicit === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(effectiveDark());
  }, []);

  function toggle() {
    const next = !effectiveDark();
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    setDark(next);
  }

  if (dark === null) return <div className="size-9" aria-hidden="true" />;
  return (
    <button
      onClick={toggle}
      aria-label={dark ? "التبديل للوضع الفاتح" : "التبديل للوضع الداكن"}
      title={dark ? "الوضع الفاتح" : "الوضع الداكن"}
      className="flex size-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-brand"
    >
      {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </button>
  );
}
