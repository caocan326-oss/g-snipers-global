import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { WorkbenchItem } from "@/lib/api";

function TrendDots({ trend }: { trend: string }) {
  const rounds = (trend.split("轮：")[1] || "")
    .split("。")[0]
    .split("·")
    .map((part) => part.trim())
    .filter(Boolean);
  if (!rounds.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {rounds.map((note, index) => (
        <span
          key={`${note}-${index}`}
          className={`h-2.5 w-2.5 rounded-full ${note.includes("没提到") ? "bg-slate-300" : "bg-emerald-500"}`}
          title={note}
        />
      ))}
    </div>
  );
}

export function BuyerQuestionsSection({
  items,
  sources = [],
  competitors = [],
  trustNote = "",
}: {
  items: WorkbenchItem[];
  sources?: WorkbenchItem[];
  competitors?: WorkbenchItem[];
  trustNote?: string;
}) {
  return (
    <Card className="rounded-md border-sky-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">AI 可见度作战室</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              同一批真问句：抽查看没看到、AI 引用了谁、提到了谁。测完出英文段，发给客户，他们贴上后再测同一问。没有原句就空着。不保证这次被提到。我们不代改。
            </p>
          </div>
          <Link href="/geo">
            <Button size="sm">
              去作战室
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
        {items.length ? (
          <div className="space-y-2">
            {items.map((item) => (
              <Link
                key={item.id}
                href="/geo"
                className="block rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-500"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                  {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                </div>
                <h3 className="mt-2 text-sm font-medium text-slate-950">{item.title}</h3>
                {item.trend ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <TrendDots trend={item.trend} />
                    <p className="text-xs leading-5 text-slate-600">{item.trend}</p>
                  </div>
                ) : null}
                {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-600">{item.meta}</p> : null}
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">还没有买家原句。先从销售、询盘、展会或客户自己说的记下来。没有时间序列，也没有可引用资产。</p>
        )}
        {trustNote ? <p className="text-sm leading-6 text-slate-600">{trustNote}</p> : null}
        {sources.length || competitors.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">AI 引用的站</h3>
              {sources.length ? (
                sources.map((item) => (
                  <div key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                      {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{item.title}</p>
                    {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-500">{item.meta}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">还没有抽查引用。</p>
              )}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">同一问里提到的竞品</h3>
              {competitors.length ? (
                competitors.map((item) => (
                  <div key={item.id} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                      {item.subtitle ? <span className="text-xs text-slate-500">{item.subtitle}</span> : null}
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{item.title}</p>
                    {item.meta ? <p className="mt-1 text-xs leading-5 text-slate-500">{item.meta}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">抽查里还没有竞品名字。</p>
              )}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
