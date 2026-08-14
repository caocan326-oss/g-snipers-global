"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Market } from "@/lib/api";

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
  const [form, setForm] = useState({
    name: "",
    region: "亚太",
    country_code: "",
    primary_locale: "en-US",
  });

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
      await api("/api/markets", { method: "POST", body: JSON.stringify({ ...form, status: "watching" }) });
      setForm({ ...form, name: "", country_code: "" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">洞察投喂</h1>
        <p className="mt-1 text-sm text-slate-500">
          选市场、记信号，再开到三条链：站内改页 / GEO 工单 / 外链跟进。不做机会分或 Share of Voice 看板。
        </p>
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
                    {m.region} · {m.primary_locale}
                  </p>
                </div>
                <Badge tone={statusTone[m.status] ?? "default"}>{statusLabel[m.status] ?? m.status}</Badge>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600">
                  信号 {m.demand_count} · 竞品 {m.competitor_count}
                </p>
                <p className="mt-2 text-xs text-slate-500">点进去把信号投喂到交付链。</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>新增目标市场</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-5" onSubmit={onCreate}>
            <div>
              <Label>名称</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <Label>大区</Label>
              <Input value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
            </div>
            <div>
              <Label>国家码</Label>
              <Input
                value={form.country_code}
                onChange={(e) => setForm({ ...form, country_code: e.target.value.toUpperCase() })}
                required
              />
            </div>
            <div>
              <Label>主语言</Label>
              <Input
                value={form.primary_locale}
                onChange={(e) => setForm({ ...form, primary_locale: e.target.value })}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit">添加</Button>
            </div>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
