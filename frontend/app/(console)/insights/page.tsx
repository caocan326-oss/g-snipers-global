"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CountryPicker } from "@/components/CountryPicker";
import { api, type Market } from "@/lib/api";
import { countryByCode, countryLabel } from "@/lib/countries";

const statusTone: Record<string, "green" | "amber" | "default"> = {
  priority: "green",
  watching: "amber",
  paused: "default",
};

const statusLabel: Record<string, string> = {
  priority: "优先",
  watching: "观察",
  paused: "暂停",
};

export default function InsightsPage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [error, setError] = useState("");
  const [countryCode, setCountryCode] = useState("US");

  function load() {
    api<Market[]>("/api/markets").then(setMarkets).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const country = countryByCode(countryCode);
      if (!country) return setError("请先点选一个国家。");
      await api("/api/markets", {
        method: "POST",
        body: JSON.stringify({
          name: country.name,
          region: country.region,
          country_code: country.code,
          primary_locale: country.locale,
          status: "watching",
        }),
      });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">市场机会入口</h1>
            <p className="mt-1 text-sm text-slate-500">
              记录目标市场、买家需求和竞品线索，再转成 SEO 诊断任务、GEO 整改项或站外跟进。
            </p>
          </div>
          <Button asChild>
            <Link href="/insights/new">新建市场</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {markets.map((m) => (
          <Link key={m.id} href={`/insights/${m.id}`}>
            <Card className="h-full hover:border-brand-600">
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle>
                    {m.name}{" "}
                    <span className="text-xs font-normal text-slate-400">{m.country_code}</span>
                  </CardTitle>
                  <p className="mt-1 text-xs text-slate-500">
                    {m.region} · {countryLabel(m.country_code || m.primary_locale)}
                  </p>
                </div>
                <Badge tone={statusTone[m.status] ?? "default"}>{statusLabel[m.status] ?? m.status}</Badge>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600">
                  信号 {m.demand_count} · 竞品 {m.competitor_count}
                </p>
                <p className="mt-2 text-xs text-slate-500">进入后可把需求线索转成具体交付任务。</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>新增客户目标市场</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onCreate}>
            <CountryPicker value={countryCode} onChange={setCountryCode} />
            <Button type="submit">添加市场</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
