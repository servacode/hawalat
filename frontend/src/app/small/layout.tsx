"use client";

import { ChartColumn, History, LayoutDashboard, Megaphone, Send, Wallet } from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell, type NavItem } from "@/components/layout/Shell";

const NAV: NavItem[] = [
  { href: "/small", label: "الرئيسية", icon: LayoutDashboard },
  { href: "/small/send", label: "إرسال حركة", icon: Send },
  { href: "/small/transactions", label: "سجل الحركات", icon: History },
  { href: "/small/boxes", label: "الصناديق", icon: Wallet },
  { href: "/small/reports", label: "التقارير", icon: ChartColumn },
  { href: "/small/alerts", label: "التنبيهات", icon: Megaphone },
];

export default function SmallLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="small_office">
      {(session) => (
        <Shell
          title={session.user.first_name || session.user.username}
          subtitle={session.user.office_code}
          nav={NAV}
        >
          {children}
        </Shell>
      )}
    </RoleGuard>
  );
}
