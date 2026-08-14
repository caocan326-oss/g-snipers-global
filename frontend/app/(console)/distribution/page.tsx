"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type DistJob, type DistProvider } from "@/lib/api";

export default function DistributionPage() {
  const [providers, setProviders] = useState<DistProvider[]>([]);
  const [jobs, setJobs] = useState<DistJob[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    target_url: "/",
    provider_key: "directory",
    payload_summary: "",
  });

  function load() {
    Promise.all([api<DistProvider[]>("/api/distribution/providers"), api<DistJob[]>("/api/distribution/jobs")])
      .then(([p, j]) => {
        setProviders(p);
        setJobs(j);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/distribution/jobs", { method: "POST", body: JSON.stringify(form) });
    setForm({ ...form, title: "" });
    load();
  }

  async function send(id: string, confirmed: boolean) {
    setError("");
    try {
      const res = await api<{ sent: boolean; provider_status: string; detail: string }>(
        `/api/distribution/jobs/${id}/send`,
        { method: "POST", body: JSON.stringify({ confirmed }) }
      );
      if (!res.sent) setError(res.detail);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">外链分发台</h1>
        <p className="mt-1 text-sm text-slate-500">
          多渠道适配器已就位。Key 未配时状态为未配置，确认后也不会发起真实请求、不会刷成功次数。高风险外发必须人工确认。
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {providers.map((p) => (
          <Card key={p.key}>
            <CardHeader>
              <CardTitle>{p.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge tone={p.configured ? "green" : "amber"}>{p.status}</Badge>
              <p className="mt-2 text-xs text-slate-500">env：{p.env_var}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          {jobs.map((j) => (
            <div key={j.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{j.title}</div>
                  <div className="text-xs text-slate-500">
                    {j.target_url} · {j.provider_key}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="amber">{j.last_result}</Badge>
                  <Button size="sm" variant="outline" onClick={() => send(j.id, false)}>
                    未确认
                  </Button>
                  <Button size="sm" onClick={() => send(j.id, true)}>
                    确认尝试发送
                  </Button>
                </div>
              </div>
              {j.last_detail ? <p className="mt-2 text-sm text-slate-600">{j.last_detail}</p> : null}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>新建分发任务</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={create}>
            <Input
              placeholder="标题"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
            <Input
              placeholder="目标 URL"
              value={form.target_url}
              onChange={(e) => setForm({ ...form, target_url: e.target.value })}
            />
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={form.provider_key}
              onChange={(e) => setForm({ ...form, provider_key: e.target.value })}
            >
              {providers.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
            <Input
              placeholder="摘要"
              value={form.payload_summary}
              onChange={(e) => setForm({ ...form, payload_summary: e.target.value })}
            />
            <Button type="submit">加入队列</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
