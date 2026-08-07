"use client";

import { LogoutButton, RoleGuard } from "@/components/auth/RoleGuard";
import { Card, CardBody } from "@/components/ui";

export default function SmallOfficeHome() {
  return (
    <RoleGuard role="small_office">
      {(session) => (
        <main className="mx-auto flex max-w-4xl flex-col gap-6 px-5 py-10">
          <header className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                {session.user.first_name || session.user.username}
              </h1>
              <p className="text-muted">
                الكود: <span className="tnum">{session.user.office_code}</span> — تابع
                لمكتب {session.user.tenant_name}
              </p>
            </div>
            <LogoutButton />
          </header>
          <Card>
            <CardBody>
              <p className="text-muted">
                إرسال الحركات والصناديق والسجل — تُبنى بدءاً من المرحلة 5.
              </p>
            </CardBody>
          </Card>
        </main>
      )}
    </RoleGuard>
  );
}
