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
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-e border-border bg-surface md:flex">
        <div className="flex items-center gap-3 border-b border-border px-5 py-4">
          <div className="flex size-9 items-center justify-center rounded-lg bg-brand text-lg font-bold text-white">
            ح
          </div>
          <div className="leading-tight">
            <p className="font-bold">حوالات</p>
            {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {nav.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-base transition-colors",
                  active
                    ? "bg-brand/10 font-bold text-brand-700"
                    : "text-muted hover:bg-surface-2 hover:text-ink",
                )}
              >
                <Icon className="size-5 shrink-0" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex flex-col gap-2 border-t border-border p-4">
          <InstallButton />
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-5 py-4 md:px-8">
          <h1 className="text-xl font-bold">{title}</h1>
          <div className="flex items-center gap-2">
            <NotificationBell />
            <div className="md:hidden">
              <LogoutButton />
            </div>
          </div>
        </header>
        <main className="flex-1 px-5 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
