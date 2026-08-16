import Link from "next/link";
import { ArrowRight, type Gauge } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function PillarCard({
  title,
  status,
  statusTone,
  primary,
  helper,
  href,
  icon: Icon,
  children,
}: {
  title: string;
  status: string;
  statusTone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  primary: string;
  helper: string;
  href: string;
  icon: typeof Gauge;
  children: ReactNode;
}) {
  return (
    <Card className="h-full rounded-md">
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-brand-700" />
            <CardTitle>{title}</CardTitle>
          </div>
          <Badge tone={statusTone}>{status}</Badge>
        </div>
        <div>
          <div className="text-3xl font-semibold text-slate-950">{primary}</div>
          <p className="mt-1 text-sm text-slate-500">{helper}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {children}
        <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-brand-700">
          查看详情 <ArrowRight className="h-4 w-4" />
        </Link>
      </CardContent>
    </Card>
  );
}
