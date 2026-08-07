"use client";

import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/admin", label: "الرئيسية", icon: "📊" },
  { href: "/admin/offices", label: "المكاتب الكبيرة", icon: "🏢" },
  { href: "/admin/packages", label: "الباقات", icon: "📦" },
  { href: "/admin/subscriptions", label: "الاشتراكات", icon: "🧾" },
  { href: "/admin/broadcasts", label: "التنبيهات", icon: "📢" },
  { href: "/admin/settings", label: "إعدادات المنصة", icon: "⚙️" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="admin">
      {() => (
        <Shell title="إدارة المنصة" subtitle="أدمن — إداري بحت" nav={NAV}>
          {children}
        </Shell>
      )}
    </RoleGuard>
  );
}
