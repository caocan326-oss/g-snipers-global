import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { WorkbenchItem } from "@/lib/api";

export function WeeklyOnsiteSection({
  items,
  pinned,
}: {
  items: WorkbenchItem[];
  pinned: boolean;
}) {
  return (
    <Card className="rounded-md border-amber-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">这周给客户改三处</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              这三处是这周给客户看的改法。客户改不改官网不挡我们交付。钉住、发给客户、打开核对在站内。我们不代改。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/distribution">
              <Button size="sm" variant="outline">
                客户说明
              </Button>
            </Link>
            <Link href="/onsite">
              <Button size="sm">
                去站内
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </div>
        {pinned ? <Badge tone="amber">已钉住。新抓到的页不会顶掉。</Badge> : null}
        {items.length ? (
          <div className="grid gap-3 lg:grid-cols-3">
            {items.map((item, index) => (
              <Link
                key={item.id}
                href="/onsite"
                className="space-y-2 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-500"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{index + 1}</Badge>
                  {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                </div>
                <h3 className="text-sm font-medium text-slate-950">{item.title}</h3>
                <p className="text-xs text-slate-500">{item.subtitle}</p>
                {item.meta ? <p className="text-xs leading-5 text-slate-600">{item.meta}</p> : null}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">这周还没有要改的站内三处。有紧急或优先页才会出现。</p>
        )}
      </CardContent>
    </Card>
  );
}
