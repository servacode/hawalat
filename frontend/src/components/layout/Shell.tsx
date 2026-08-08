"use client";

/** هيكل لوحة موحّد (Shell): شريط جانبي RTL بأيقونات Lucide + ترويسة — لكل الأدوار. */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { LogoutButton } from "@/components/auth/RoleGuard";
import { getSession, type SessionUser } from "@/lib/auth";
import { NotificationBell } from "./NotificationBell";
import { PlatformLogo } from "./PlatformLogo";
import { ThemeToggle } from "./ThemeToggle";
import { InstallButton } from "@/components/pwa/PwaSetup";

/** كود المكتب في التوب بار بجانب الاسم (ملاحظة 15). */
function OfficeCodeChip() {
  const [code, setCode] = useState<string>("");
  useEffect(() => {
    setCode(getSession()?.user.office_code ?? "");
  }, []);
  if (!code) return null;
  return (
    <p dir="ltr" className="tnum truncate text-xs font-medium text-muted" style={{ textAlign: "end" }}>
      {code}
    </p>
  );
}

/** صورة/حرف المستخدم في التوب بار — تتحدث فور رفع صورة جديدة (hawalat:session). */
function UserBadge() {
  const [user, setUser] = useState<SessionUser | null>(null);
  useEffect(() => {
    const read = () => setUser(getSession()?.user ?? null);
    read();
    window.addEventListener("hawalat:session", read);
    return () => window.removeEventListener("hawalat:session", read);
  }, []);
  if (!user) return null;
  const name = user.first_name || user.username;
  return (
    <div className="flex items-center gap-2.5">
      {user.avatar ? (
        // eslint-disable-next-line @next/next/no-img-element -- data URL محلي
        <img
          src={user.avatar}
          alt={name}
          className="size-9 rounded-full border border-border object-cover"
        />
      ) : (
        <div className="flex size-9 items-center justify-center rounded-full bg-brand/15 font-bold text-brand-700">
          {name.trim().charAt(0)}
        </div>
      )}
      <span className="hidden max-w-36 truncate text-sm font-medium sm:block">{name}</span>
    </div>
  );
}

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
  // قائمة الجوال (ملاحظة 26): السايدبار مخفي على الشاشات الصغيرة — القائمة من زر ☰
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);
  // النشط = أطول مسار مطابق فقط (وإلا تضيء «الرئيسية» مع كل قسم فرعي)
  const activeHref = nav
    .filter((i) => pathname === i.href || pathname.startsWith(i.href + "/"))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  function navLinks(onNavigate?: () => void) {
    return nav.map((item) => {
      const active = item.href === activeHref;
      const Icon = item.icon;
      return (
        <Link
          key={item.href}
          href={item.href}
          onClick={onNavigate}
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
    });
  }

  return (
    <div className="flex min-h-screen gap-4 bg-bg p-3 md:p-4">
      <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-64 shrink-0 flex-col overflow-y-auto rounded-2xl border border-border bg-surface shadow-sm md:flex">
        <div className="flex flex-col items-center gap-2 border-b border-border px-5 pb-5 pt-6">
          <PlatformLogo size="lg" />
          {subtitle && <p className="text-xs leading-tight text-muted">{subtitle}</p>}
        </div>
        <nav className="flex flex-1 flex-col gap-1.5 px-3 pt-2">{navLinks()}</nav>
        <div className="flex flex-col gap-2 p-3">
          <InstallButton />
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="sticky top-4 z-10 flex items-center justify-between gap-4 rounded-2xl border border-border bg-surface/95 px-5 py-3.5 shadow-sm backdrop-blur md:px-6">
          <div className="min-w-0 leading-tight">
            <h1 className="truncate text-xl font-bold">{title}</h1>
            <OfficeCodeChip />
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <NotificationBell />
            <UserBadge />
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-label="فتح القائمة"
              className="flex size-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink md:hidden"
            >
              <Menu className="size-5" />
            </button>
          </div>
        </header>
        <main className="flex-1 px-0.5 pb-2">{children}</main>
      </div>

      {/* قائمة الجوال المنسدلة (ملاحظة 26) */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 start-0 flex w-72 max-w-[85vw] flex-col overflow-y-auto bg-surface shadow-lg">
            <div className="flex items-center justify-between border-b border-border px-4 py-4">
              <PlatformLogo size="md" />
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                aria-label="إغلاق القائمة"
                className="flex size-9 items-center justify-center rounded-full text-muted hover:bg-surface-2 hover:text-ink"
              >
                <X className="size-5" />
              </button>
            </div>
            <nav className="flex flex-1 flex-col gap-1.5 p-3">
              {navLinks(() => setMenuOpen(false))}
            </nav>
            <div className="flex flex-col gap-2 border-t border-border p-3">
              <InstallButton />
              <LogoutButton />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
