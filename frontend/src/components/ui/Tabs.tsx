"use client";

import { cn } from "@/lib/cn";
import { useState, type ReactNode } from "react";

export interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ tabs, defaultKey }: { tabs: Tab[]; defaultKey?: string }) {
  const [active, setActive] = useState(defaultKey ?? tabs[0]?.key);
  const current = tabs.find((t) => t.key === active);
  return (
    <div>
      <div role="tablist" className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={t.key === active}
            onClick={() => setActive(t.key)}
            className={cn(
              "-mb-px rounded-t-md px-4 py-2.5 text-base font-medium transition-colors",
              "focus-visible:outline-2 focus-visible:outline-brand",
              t.key === active
                ? "border-b-2 border-brand text-brand-700"
                : "text-muted hover:text-ink",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="pt-4">
        {current?.content}
      </div>
    </div>
  );
}
