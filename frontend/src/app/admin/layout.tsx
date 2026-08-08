"use client";

import { Building2, LayoutDashboard, Megaphone, Package, ReceiptText, Settings } from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/admin", label: "الرئيسية", icon: LayoutDashboard },
  { href: "/admin/offices", label: "المكاتب الكبيرة", icon: Building2 },
  { href: "/admin/packages", label: "الباقات", icon: Package },
  { href: "/admin/subscriptions", label: "الاشتراكات", icon: ReceiptText },
  { href: "/admin/broadcasts", label: "التنبيهات", icon: Megaphone },
  { href: "/admin/settings", label: "إعدادات المنصة", icon: Settings },
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
