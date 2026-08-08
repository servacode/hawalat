"use client";

/** هيكل لوحة موحّد (Shell): شريط جانبي RTL بأيقونات Lucide + ترويسة — لكل الأدوار. */

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { LogoutButton } from "@/components/auth/RoleGuard";
import { NotificationBell } from "./NotificationBell";
import { InstallButton } from "@/components/pwa/PwaSetup";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export function Shell({
  title,
  subtitle,
  nav,
  children,
}: {
  title: string;
  subtitle?: string;
  nav: NavItem[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen gap-4 bg-bg p-3 md:p-4">
      <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-64 shrink-0 flex-col overflow-y-auto rounded-2xl border border-border bg-surface shadow-sm md:flex">
        <div className="flex items-center gap-3 px-5 pb-4 pt-5">
          <div className="flex size-10 items-center justify-center rounded-xl bg-brand text-lg font-bold text-white shadow-sm">
            ح
          </div>
          <div className="leading-tight">
            <p className="text-lg font-bold">حوالات</p>
            {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1.5 px-3 pt-2">
          {nav.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-base transition-colors",
                  active
                    ? "bg-brand font-semibold text-white shadow-sm"
                    : "text-muted hover:bg-surface-2 hover:text-ink",
                )}
              >
                <Icon className="size-5 shrink-0" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="m-3 flex flex-col gap-2 rounded-xl bg-surface-2/60 p-3">
          <InstallButton />
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="sticky top-4 z-10 flex items-center justify-between gap-4 rounded-2xl border border-border bg-surface/95 px-5 py-3.5 shadow-sm backdrop-blur md:px-6">
          <h1 className="text-xl font-bold">{title}</h1>
          <div className="flex items-center gap-2">
            <NotificationBell />
            <div className="md:hidden">
              <LogoutButton />
            </div>
          </div>
        </header>
        <main className="flex-1 px-0.5 pb-2">{children}</main>
      </div>
    </div>
  );
}
