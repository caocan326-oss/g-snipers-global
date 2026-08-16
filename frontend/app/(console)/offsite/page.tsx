"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type AiAssist, type BacklinkGap, type DistJob, type DistProvider } from "@/lib/api";

const verifyLabel: Record<string, string> = {
  unverified: "未核验",
  valid: "有效",
  dead: "失效",
  spam: "垃圾",
};

const verifyTone: Record<string, "amber" | "green" | "red" | "default"> = {
  unverified: "amber",
  valid: "green",
  dead: "red",
  spam: "default",
};

const kindLabel: Record<string, string> = {
  inbound: "我方外链",
  competitor: "竞品外链",
};

const gapLabel: Record<string, string> = {
  identified: "已识别",
  outreach: "跟进中",
  replied: "有回复",
  won: "拿到",
  lost: "未果",
  skipped: "本季不做",
};

export default function OffsitePage() {
  const [tab, setTab] = useState<"verify" | "dist">("verify");
  const [filter, setFilter] = useState<"all" | "unverified" | "valid" | "dead" | "spam">("all");
  const [gaps, setGaps] = useState<BacklinkGap[]>([]);
  const [providers, setProviders] = useState<DistProvider[]>([]);
  const [jobs, setJobs] = useState<DistJob[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    competitor_name: "",
    referring_domain: "",
    link_url: "",
    kind: "inbound",
    notes: "",
  });
  const [contact, setContact] = useState("");
  const [distForm, setDistForm] = useState({
    title: "",
    target_url: "/",
    provider_key: "directory",
    payload_summary: "",
  });

  function loadGaps() {
    api<BacklinkGap[]>("/api/offsite/gaps").then(setGaps).catch((e) => setError(e.message));
  }
  function loadDist() {
    Promise.all([api<DistProvider[]>("/api/distribution/providers"), api<DistJob[]>("/api/distribution/jobs")])
      .then(([p, j]) => {
        setProviders(p);
        setJobs(j);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("tab") === "dist") {
      setTab("dist");
    }
    loadGaps();
    loadDist();
  }, []);

  async function addGap(e: FormEvent) {
    e.preventDefault();
    await api("/api/offsite/gaps", { method: "POST", body: JSON.stringify(form) });
    setForm({ competitor_name: "", referring_domain: "", link_url: "", kind: "inbound", notes: "" });
    loadGaps();
  }

  async function aiGap(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/offsite/gaps/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "evidence" }) });
    if (res.status === "未配置") setError(res.detail);
    loadGaps();
  }

  async function setVerify(id: string, verify_status: string) {
    await api(`/api/offsite/gaps/${id}`, { method: "PATCH", body: JSON.stringify({ verify_status }) });
    loadGaps();
  }

  async function addOutreach(gapId: string) {
    if (!contact) return;
    await api(`/api/offsite/gaps/${gapId}/outreach`, {
      method: "POST",
      body: JSON.stringify({ contact, channel: "email" }),
    });
    setContact("");
    loadGaps();
  }

  async function createJob(e: FormEvent) {
    e.preventDefault();
    await api("/api/distribution/jobs", { method: "POST", body: JSON.stringify(distForm) });
    setDistForm({ ...distForm, title: "" });
    loadDist();
  }

  async function send(id: string, confirmed: boolean) {
    setError("");
    try {
      const res = await api<{ sent: boolean; provider_status: string; detail: string }>(
        `/api/distribution/jobs/${id}/send`,
        { method: "POST", body: JSON.stringify({ confirmed }) }
      );
      if (!res.sent) setError(res.detail);
      loadDist();
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">站外曝光与外链核验</h1>
        <p className="mt-1 text-sm text-slate-500">
          逐条记录第三方提及、我方外链和竞品外链，核验有效、失效或垃圾链接。这里不冒充 Ahrefs/DR 权重；分发接口未配置时不会真实发送。
        </p>
      </div>

      <div className="flex gap-2">
        <Button size="sm" variant={tab === "verify" ? "default" : "outline"} onClick={() => setTab("verify")}>
          核验清单
        </Button>
        <Button size="sm" variant={tab === "dist" ? "default" : "outline"} onClick={() => setTab("dist")}>
          内容分发
        </Button>
      </div>

      {tab === "verify" ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
              <button key={s} type="button" className="text-left" onClick={() => setFilter(filter === s ? "all" : s)}>
                <Card className={filter === s ? "border-brand-600" : ""}>
                  <CardHeader>
                    <CardTitle className="text-sm">{verifyLabel[s]}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-2xl font-semibold">
                    {gaps.filter((g) => g.verify_status === s).length}
                  </CardContent>
                </Card>
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">当前仅做链接事实核验和跟进管理，暂不提供域名权重、外链指数或 DR。</p>
          {(filter === "all" ? gaps : gaps.filter((g) => g.verify_status === filter)).map((g) => (
            <Card key={g.id}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle>
                    {g.referring_domain}{" "}
                    <span className="text-sm font-normal text-slate-400">
                      {kindLabel[g.kind] ?? g.kind}
                      {g.competitor_name && g.competitor_name !== "—" ? ` · vs ${g.competitor_name}` : ""}
                    </span>
                  </CardTitle>
                  <p className="mt-1 text-xs text-slate-500">{g.link_url || g.competitor_url || "未登记 URL"}</p>
                  <p className="mt-1 text-xs text-slate-500">{g.notes}</p>
                  {g.evidence ? <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{g.evidence}</pre> : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={verifyTone[g.verify_status]}>{verifyLabel[g.verify_status] ?? g.verify_status}</Badge>
                  <Badge>{gapLabel[g.status] ?? g.status}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-1">
                  {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
                    <Button key={s} size="sm" variant="outline" onClick={() => setVerify(g.id, s)}>
                      {verifyLabel[s]}
                    </Button>
                  ))}
                </div>
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
                    placeholder="联系人或跟进对象"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                  />
                  <Button size="sm" onClick={() => aiGap(g.id)}>
                    AI 分析价值
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => addOutreach(g.id)}>
                    添加跟进
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardHeader>
              <CardTitle>登记一条站外线索</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-3" onSubmit={addGap}>
                <select
                  className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                >
                  <option value="inbound">我方外链</option>
                  <option value="competitor">竞品外链</option>
                </select>
                <Input
                  placeholder="来源域名"
                  value={form.referring_domain}
                  onChange={(e) => setForm({ ...form, referring_domain: e.target.value })}
                  required
                />
                <Input
                  placeholder="链接 URL 或第三方页面"
                  value={form.link_url}
                  onChange={(e) => setForm({ ...form, link_url: e.target.value })}
                />
                <Input
                  placeholder="竞品（可选）"
                  value={form.competitor_name}
                  onChange={(e) => setForm({ ...form, competitor_name: e.target.value })}
                />
                <Input placeholder="备注" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                <Button type="submit">加入站外清单</Button>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="space-y-4">
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
                        仅记录，不发送
                      </Button>
                      <Button size="sm" onClick={() => send(j.id, true)}>
                        确认发送
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
              <CardTitle>新建内容分发任务</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-2" onSubmit={createJob}>
                <Input
                  placeholder="任务标题"
                  value={distForm.title}
                  onChange={(e) => setDistForm({ ...distForm, title: e.target.value })}
                  required
                />
                <Input
                  placeholder="要推广的客户 URL"
                  value={distForm.target_url}
                  onChange={(e) => setDistForm({ ...distForm, target_url: e.target.value })}
                />
                <select
                  className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                  value={distForm.provider_key}
                  onChange={(e) => setDistForm({ ...distForm, provider_key: e.target.value })}
                >
                  {providers.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <Input
                  placeholder="分发内容摘要"
                  value={distForm.payload_summary}
                  onChange={(e) => setDistForm({ ...distForm, payload_summary: e.target.value })}
                />
                <Button type="submit">加入队列</Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
