"use client";

/** تسجيل الـ Service Worker + التقاط طلب التثبيت (PWA — المرحلة 10). */

import { MonitorDown } from "lucide-react";
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
        "flex items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-accent"
      }
    >
      <MonitorDown className="size-4" aria-hidden="true" />
      تثبيت التطبيق
    </button>
  );
}
