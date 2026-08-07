"use client";

import { LogoutButton, RoleGuard } from "@/components/auth/RoleGuard";
import { Card, CardBody } from "@/components/ui";

export default function AdminHome() {
  return (
    <RoleGuard role="admin">
      {(session) => (
        <main className="mx-auto flex max-w-4xl flex-col gap-6 px-5 py-10">
          <header className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">لوحة إدارة المنصة</h1>
              <p className="text-muted">أهلاً {session.user.first_name || session.user.username} 👑</p>
            </div>
            <LogoutButton />
          </header>
          <Card>
            <CardBody>
              <p className="text-muted">
                إدارة المكاتب الكبيرة والباقات والاشتراكات — تُبنى في المرحلة 3.
              </p>
            </CardBody>
          </Card>
        </main>
      )}
    </RoleGuard>
  );
}
