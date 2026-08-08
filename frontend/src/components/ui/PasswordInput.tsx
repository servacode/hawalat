"use client";

/** حقل كلمة مرور مركزي: أيقونة قفل + زر عين لإظهار/إخفاء القيمة — يُستخدم في كل النماذج. */

import { Eye, EyeOff, Lock } from "lucide-react";
import { useState } from "react";
import { Input, type InputProps } from "./Input";

export function PasswordInput({
  icon = Lock,
  ...props
}: Omit<InputProps, "type" | "trailing">) {
  const [show, setShow] = useState(false);
  return (
    <Input
      {...props}
      icon={icon}
      type={show ? "text" : "password"}
      trailing={
        <button
          type="button"
          tabIndex={-1}
          aria-label={show ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
          onClick={() => setShow((s) => !s)}
          className="rounded-md p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-brand"
        >
          {show ? <EyeOff className="size-4.5" /> : <Eye className="size-4.5" />}
        </button>
      }
    />
  );
}
