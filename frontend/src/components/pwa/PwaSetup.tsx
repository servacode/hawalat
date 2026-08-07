"use client";

/** تسجيل الـ Service Worker + التقاط طلب التثبيت (PWA — المرحلة 10). */

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;

export function PwaSetup() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    const onPrompt = (e: Event) => {
      e.preventDefault();
      deferredPrompt = e as BeforeInstallPromptEvent;
      window.dispatchEvent(new Event("hawalat:installable"));
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);
  return null;
}

/** زر تثبيت التطبيق — يظهر فقط عندما يسمح المتصفح. */
export function InstallButton({ className }: { className?: string }) {
  const [installable, setInstallable] = useState(false);

  useEffect(() => {
    if (deferredPrompt) setInstallable(true);
    const show = () => setInstallable(true);
    window.addEventListener("hawalat:installable", show);
    return () => window.removeEventListener("hawalat:installable", show);
  }, []);

  if (!installable) return null;
  return (
    <button
      onClick={async () => {
        if (!deferredPrompt) return;
        await deferredPrompt.prompt();
        const choice = await deferredPrompt.userChoice;
        if (choice.outcome === "accepted") setInstallable(false);
      }}
      className={
        className ??
        "rounded-md border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:border-brand hover:text-brand-700"
      }
    >
      📲 تثبيت التطبيق
    </button>
  );
}
