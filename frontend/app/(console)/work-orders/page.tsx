"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type WorkOrder } from "@/lib/api";

const typeLabel: Record<string, string> = {
  insight: "洞察",
  seo_outline: "SEO 大纲",
  seo_draft: "SEO 正文",
  seo_meta: "SEO Meta",
  geo_monitor: "GEO 监测",
  geo_asset: "GEO 资产",
  onsite: "站内",
  offsite: "站外",
  distribution: "分发",
  other: "其他",
};

const statusLabel: Record<string, string> = {
  open: "待领取",
  claimed: "已领取",
  in_progress: "进行中",
  done: "完成",
  blocked: "受阻",
};

export default function WorkOrdersPage() {
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", type: "seo_outline", acceptance_criteria: "" });

  function load() {
    const q = status ? `?status=${status}` : "";
    api<WorkOrder[]>(`/api/work-orders${q}`).then(setOrders).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [status]);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/work-orders", { method: "POST", body: JSON.stringify(form) });
    setForm({ title: "", type: "seo_outline", acceptance_criteria: "" });
    load();
  }

  async function claim(id: string) {
    await api(`/api/work-orders/${id}/claim`, { method: "POST" });
    load();
  }

  async function setOrderStatus(id: string, next: string) {
    await api(`/api/work-orders/${id}/status`, { method: "POST", body: JSON.stringify({ status: next }) });
    load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">工单</h1>
        <p className="mt-1 text-sm text-slate-500">
          支撑洞察调研与 SEO 执行（大纲 / 正文 / Meta）。类型仅限工作台需要的几种。
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {["", "open", "claimed", "in_progress", "done", "blocked"].map((s) => (
          <Button key={s || "all"} size="sm" variant={status === s ? "default" : "outline"} onClick={() => setStatus(s)}>
            {s ? statusLabel[s] : "全部"}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          {orders.map((o) => (
            <div key={o.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3">
              <div>
                <div className="font-medium">{o.title}</div>
                <div className="mt-1 flex gap-2 text-xs">
                  <Badge>{typeLabel[o.type] ?? o.type}</Badge>
                  <Badge tone="amber">{statusLabel[o.status] ?? o.status}</Badge>
                </div>
                {o.acceptance_criteria ? (
                  <p className="mt-1 text-xs text-slate-500">验收：{o.acceptance_criteria}</p>
                ) : null}
              </div>
              <div className="flex gap-2">
                {o.status === "open" ? (
                  <Button size="sm" onClick={() => claim(o.id)}>
                    领取
                  </Button>
                ) : null}
                {o.status === "claimed" ? (
                  <Button size="sm" variant="outline" onClick={() => setOrderStatus(o.id, "in_progress")}>
                    开始
                  </Button>
                ) : null}
                {o.status === "in_progress" ? (
                  <Button size="sm" variant="outline" onClick={() => setOrderStatus(o.id, "done")}>
                    完成
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>新建工单</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <Input
              placeholder="标题"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              {Object.entries(typeLabel).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <Input
              placeholder="验收标准"
              value={form.acceptance_criteria}
              onChange={(e) => setForm({ ...form, acceptance_criteria: e.target.value })}
            />
            <Button type="submit">创建</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
