import { cn } from "@/lib/cn";
import { Card } from "./Card";

export interface StatCardProps {
  title: string;
  value: string;
  /** دلالة الرقم: موجب (لنا) / سالب (علينا) / محايد / ربح (ذهبي) */
  tone?: "pos" | "neg" | "neutral" | "profit";
  detail?: string;
  className?: string;
}

const tones = {
  pos: "text-pos",
  neg: "text-neg",
  neutral: "text-ink",
  profit: "text-accent",
} as const;

export function StatCard({ title, value, tone = "neutral", detail, className }: StatCardProps) {
  return (
    <Card
      className={cn("px-5 py-4", tone === "profit" && "border-s-3 border-s-accent", className)}
    >
      <p className="text-sm text-muted">{title}</p>
      <p className={cn("tnum mt-1.5 text-3xl font-bold tracking-tight", tones[tone])}>
        {value}
      </p>
      {detail && <p className={cn("mt-1 text-sm", tones[tone])}>{detail}</p>}
    </Card>
  );
}
