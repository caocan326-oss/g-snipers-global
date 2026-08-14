"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type BacklinkGap } from "@/lib/api";

const gapLabel: Record<string, string> = {
  identified: "已识别",
  outreach: "外联中",
  replied: "有回复",
  won: "拿到",
  lost: "未果",
  skipped: "本季不做",
};

export default function OffsitePage() {
  const [gaps, setGaps] = useState<BacklinkGap[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ competitor_name: "", referring_domain: "", notes: "" });
  const [contact, setContact] = useState("");

  function load() {
    api<BacklinkGap[]>("/api/offsite/gaps").then(setGaps).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function addGap(e: FormEvent) {
    e.preventDefault();
    await api("/api/offsite/gaps", { method: "POST", body: JSON.stringify(form) });
    setForm({ competitor_name: "", referring_domain: "", notes: "" });
    load();
  }

  async function addOutreach(gapId: string) {
    if (!contact) return;
    await api(`/api/offsite/gaps/${gapId}/outreach`, {
      method: "POST",
      body: JSON.stringify({ contact, channel: "email" }),
    });
    setContact("");
    load();
  }

  async function setGapStatus(id: string, status: string) {
    await api(`/api/offsite/gaps/${id}?status=${status}`, { method: "PATCH" });
    load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">站外优化</h1>
        <p className="mt-1 text-sm text-slate-500">
          竞品外链 / 引荐域缺口 + 外联跟进。不代买外链、不群发。域名权重没有数据源时显示未测，不用 Ahrefs/Semrush 假数字。
        </p>
      </div>

      {gaps.map((g) => (
        <Card key={g.id}>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>
                {g.referring_domain}{" "}
                <span className="text-sm font-normal text-slate-400">vs {g.competitor_name}</span>
              </CardTitle>
              <p className="mt-1 text-xs text-slate-500">{g.notes}</p>
            </div>
            <div className="flex gap-2">
              <Badge>{gapLabel[g.status] ?? g.status}</Badge>
              <Badge tone="amber">权重 {g.domain_metric === "untested" ? "未测" : g.domain_metric}</Badge>
              <Badge tone="default">我方 {g.our_presence === "untested" ? "未测" : g.our_presence === "none" ? "无" : g.our_presence}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <ul className="space-y-1 text-sm">
              {g.outreach.map((o) => (
                <li key={o.id}>
                  {o.contact} · {o.channel} · {o.status === "todo" ? "待跟" : o.status === "sent_manual" ? "已手发" : o.status}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              <Input
                className="max-w-xs"
                placeholder="外联对象"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              />
              <Button size="sm" variant="outline" onClick={() => addOutreach(g.id)}>
                加跟进
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setGapStatus(g.id, "skipped")}>
                本季不做
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardHeader>
          <CardTitle>登记缺口</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={addGap}>
            <Input
              placeholder="竞品"
              value={form.competitor_name}
              onChange={(e) => setForm({ ...form, competitor_name: e.target.value })}
              required
            />
            <Input
              placeholder="引荐域"
              value={form.referring_domain}
              onChange={(e) => setForm({ ...form, referring_domain: e.target.value })}
              required
            />
            <Input placeholder="备注" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <Button type="submit">添加</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
