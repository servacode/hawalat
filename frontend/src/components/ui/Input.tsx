import { cn } from "@/lib/cn";
import type { LucideIcon } from "lucide-react";
import { useId, type InputHTMLAttributes, type ReactNode } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  /** أيقونة بداية الحقل (جهة اليمين في RTL) — من مكتبة الأيقونات المركزية */
  icon?: LucideIcon;
  /** عنصر نهاية الحقل (مثل زر إظهار كلمة المرور) */
  trailing?: ReactNode;
}

export function Input({
  label,
  error,
  hint,
  icon: Icon,
  trailing,
  className,
  id,
  ...props
}: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-ink">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <Icon
            className="pointer-events-none absolute start-3 top-1/2 size-4.5 -translate-y-1/2 text-muted"
            aria-hidden="true"
          />
        )}
        <input
          id={inputId}
          className={cn(
            "w-full rounded-md border border-border bg-surface px-3.5 py-2.5 text-base text-ink",
            "placeholder:text-muted transition-colors",
            "focus:border-brand focus:outline-2 focus:outline-offset-0 focus:outline-brand/30",
            "disabled:cursor-not-allowed disabled:opacity-50",
            Icon && "ps-10",
            trailing ? "pe-11" : null,
            error && "border-danger focus:border-danger focus:outline-danger/30",
            className,
          )}
          aria-invalid={error ? true : undefined}
          {...props}
        />
        {trailing && (
          <div className="absolute end-2 top-1/2 -translate-y-1/2">{trailing}</div>
        )}
      </div>
      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : hint ? (
        <p className="text-sm text-muted">{hint}</p>
      ) : null}
    </div>
  );
}
