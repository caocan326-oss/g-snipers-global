"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type UsageBoard, type UsageMeter, type UsageTenant, type User } from "@/lib/api";

function tone(meter: UsageMeter): "green" | "amber" | "red" {
  if (meter.limit <= 0 || meter.remaining <= 0) return "red";
  if (meter.used / Math.max(meter.limit, 1) >= 0.8) return "amber";
  return "green";
}

export default function UsagePage() {
  const [user, setUser] = useState<User | null>(null);
  const [board, setBoard] = useState<UsageBoard | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");

  function draftKey(tenantId: string, meter: string) {
    return `${tenantId}:${meter}`;
  }

  function load() {
    api<UsageBoard>("/api/usage/board")
      .then((next) => {
        setBoard(next);
        const seed: Record<string, string> = {};
        for (const tenant of next.tenants) {
          for (const meter of tenant.meters) {
            seed[draftKey(tenant.tenant_id, meter.key)] = String(meter.limit);
          }
        }
        setDrafts(seed);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "读不了用量"));
  }

  useEffect(() => {
    api<User>("/api/auth/me")
      .then((next) => {
        setUser(next);
        if (next.role !== "admin") {
          setError("只有管理员能改各家客户的每天次数。");
          return;
        }
        load();
      })
      .catch((e) => setError(e instanceof Error ? e.message : "未登录"));
  }, []);

  async function save(tenant: UsageTenant, meter: UsageMeter) {
    const key = draftKey(tenant.tenant_id, meter.key);
    const dailyLimit = Number(drafts[key]);
    if (!Number.isFinite(dailyLimit) || dailyLimit < 0) {
      setError("上限必须是 0 或正整数。");
      return;
    }
    setBusy(key);
    setError("");
    setNote("");
    try {
      await api("/api/usage/quota", {
        method: "PATCH",
        body: JSON.stringify({ tenant_id: tenant.tenant_id, meter: meter.key, daily_limit: dailyLimit }),
      });
      setNote(`${tenant.tenant_name} 的「${meter.label}」每天改成 ${dailyLimit} 次。今天已用的次数不动。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy("");
    }
  }

  if (user && user.role !== "admin") {
    return <p className="text-sm text-red-600">只有管理员能看这一页。</p>;
  }
  if (error && !board) return <p className="text-sm text-red-600">{error}</p>;
  if (!board) return <p className="text-sm text-slate-500">读取各家客户今天的用量…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">管理员</Badge>
          <Badge>今天 {board.day}（北京时间）</Badge>
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-950">每家客户每天能打几次外部接口</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
          数的是调用次数，不是金额。用完就拦下，避免连点或账号被盗把账单打爆。改上限只影响「今天还能不能再打」，已用次数不会清零。
        </p>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      {board.tenants.map((tenant) => (
        <Card key={tenant.tenant_id} className="rounded-md">
          <CardHeader>
            <CardTitle>{tenant.tenant_name}</CardTitle>
            <p className="text-sm text-slate-500">{tenant.site_origin || "尚未登记官网"}</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {tenant.meters.map((meter) => {
              const key = draftKey(tenant.tenant_id, meter.key);
              const width = meter.limit > 0 ? Math.min(100, Math.round((meter.used / meter.limit) * 100)) : 100;
              return (
                <div key={meter.key} className="rounded-md border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900">{meter.label}</div>
                      <div className="text-xs text-slate-500">{meter.vendor} · {meter.hint}</div>
                    </div>
                    <Badge tone={tone(meter)}>还剩 {meter.remaining}</Badge>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded bg-slate-100">
                    <div className="h-full bg-brand-600" style={{ width: `${width}%` }} />
                  </div>
                  <div className="mt-2 flex flex-wrap items-end gap-2 text-sm">
                    <div className="text-slate-600">今天已用 {meter.used}</div>
                    <label className="ml-auto flex items-center gap-2 text-slate-600">
                      每天上限
                      <Input
                        className="h-9 w-24"
                        value={drafts[key] ?? String(meter.limit)}
                        onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                      />
                    </label>
                    <Button size="sm" variant="outline" disabled={busy === key} onClick={() => save(tenant, meter)}>
                      {busy === key ? "保存中…" : "保存"}
                    </Button>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
