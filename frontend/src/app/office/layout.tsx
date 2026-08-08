"use client";

import { ChartColumn, History, Inbox, LayoutDashboard, Megaphone, Settings, Users, Wallet } from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/office", label: "الرئيسية", icon: LayoutDashboard },
  { href: "/office/pending", label: "الحركات الجارية", icon: Inbox },
  { href: "/office/transactions", label: "سجل الحركات", icon: History },
  { href: "/office/members", label: "الحسابات", icon: Users },
  { href: "/office/boxes", label: "الصناديق", icon: Wallet },
  { href: "/office/reports", label: "التقارير", icon: ChartColumn },
  { href: "/office/alerts", label: "التنبيهات", icon: Megaphone },
  { href: "/office/settings", label: "الإعدادات", icon: Settings },
];

export default function OfficeLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="big_office">
      {(session) => (
        <Shell
          title={session.user.tenant_name ?? "المكتب الكبير"}
          subtitle={session.user.office_code}
          nav={NAV}
        >
          {children}
        </Shell>
      )}
    </RoleGuard>
  );
}
