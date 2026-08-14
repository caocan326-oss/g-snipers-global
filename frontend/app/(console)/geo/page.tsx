"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type GeoAsset,
  type GeoChecklistItem,
  type GeoPrompt,
  type SeoPage,
} from "@/lib/api";

const engineLabel: Record<string, string> = {
  chatgpt: "ChatGPT",
  perplexity: "Perplexity",
  gemini: "Gemini",
  claude: "Claude",
};

const obsLabel: Record<string, string> = {
  untested: "未测",
  mentioned: "出现",
  not_mentioned: "未出现",
  cited: "被引用",
};

const obsTone: Record<string, "default" | "amber" | "green" | "red" | "blue"> = {
  untested: "amber",
  mentioned: "blue",
  not_mentioned: "default",
  cited: "green",
};

export default function GeoPage() {
  const [tab, setTab] = useState<"monitor" | "assets" | "checklist">("monitor");
  const [prompts, setPrompts] = useState<GeoPrompt[]>([]);
  const [assets, setAssets] = useState<GeoAsset[]>([]);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [pageId, setPageId] = useState("");
  const [items, setItems] = useState<GeoChecklistItem[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ prompt_text: "", locale: "en-US" });
  const [confirmNote, setConfirmNote] = useState("");

  function loadPrompts() {
    api<GeoPrompt[]>("/api/geo/prompts").then(setPrompts).catch((e) => setError(e.message));
  }

  function loadAssets() {
    api<GeoAsset[]>("/api/geo/assets").then(setAssets).catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadPrompts();
    loadAssets();
    api<SeoPage[]>("/api/seo-pages").then(setPages).catch(() => undefined);
  }, []);

  async function addPrompt(e: FormEvent) {
    e.preventDefault();
    await api("/api/geo/prompts", { method: "POST", body: JSON.stringify(form) });
    setForm({ prompt_text: "", locale: "en-US" });
    loadPrompts();
  }

  async function setObs(id: string, status: string) {
    await api(`/api/geo/observations/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    loadPrompts();
  }

  async function generateLlms() {
    await api("/api/geo/assets/llms.txt/generate", { method: "POST" });
    loadAssets();
  }

  async function saveAsset(id: string, body: string) {
    await api(`/api/geo/assets/${id}`, { method: "PATCH", body: JSON.stringify({ body }) });
    loadAssets();
  }

  async function readyAsset(id: string) {
    setError("");
    try {
      await api(`/api/geo/assets/${id}/mark-ready`, {
        method: "POST",
        body: JSON.stringify({ confirmed: true, note: confirmNote }),
      });
      loadAssets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "确认失败");
    }
  }

  async function loadChecklist(id: string) {
    setPageId(id);
    const rows = await api<GeoChecklistItem[]>(`/api/geo/checklists/ensure?seo_page_id=${id}`, { method: "POST" });
    setItems(rows);
  }

  async function setCheck(id: string, status: string) {
    await api(`/api/geo/checklist-items/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    if (pageId) loadChecklist(pageId);
  }

  const llms = assets.find((a) => a.kind === "llms_txt");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">GEO 监测与资产</h1>
        <p className="mt-1 text-sm text-slate-500">
          挂在 SEO 旁边：抽查问句 + llms.txt / 可引用清单。不是「已让 ChatGPT 引用」交付，也不计算引用率。未抽查一律显示未测，不用 0% 充数。
        </p>
      </div>

      <div className="flex gap-2">
        <Button size="sm" variant={tab === "monitor" ? "default" : "outline"} onClick={() => setTab("monitor")}>
          问句监测
        </Button>
        <Button size="sm" variant={tab === "assets" ? "default" : "outline"} onClick={() => setTab("assets")}>
          llms.txt
        </Button>
        <Button size="sm" variant={tab === "checklist" ? "default" : "outline"} onClick={() => setTab("checklist")}>
          可引用清单
        </Button>
      </div>

      {tab === "monitor" ? (
        <div className="space-y-4">
          {prompts.map((p) => (
            <Card key={p.id}>
              <CardHeader>
                <CardTitle className="text-base">{p.prompt_text}</CardTitle>
                <p className="text-xs text-slate-500">{p.locale}</p>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-3">
                {p.observations.map((o) => (
                  <div key={o.id} className="rounded-md border p-3">
                    <div className="mb-2 text-xs text-slate-500">{engineLabel[o.engine] ?? o.engine}</div>
                    <Badge tone={obsTone[o.status]}>{obsLabel[o.status] ?? o.status}</Badge>
                    <div className="mt-2 flex gap-1">
                      {["untested", "mentioned", "not_mentioned", "cited"].map((s) => (
                        <Button key={s} size="sm" variant="ghost" onClick={() => setObs(o.id, s)}>
                          {obsLabel[s]}
                        </Button>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
          <Card>
            <CardHeader>
              <CardTitle>加入监测问句</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-3" onSubmit={addPrompt}>
                <Input
                  className="md:col-span-2"
                  placeholder="买家会问模型的原句"
                  value={form.prompt_text}
                  onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
                  required
                />
                <div className="flex gap-2">
                  <Input
                    value={form.locale}
                    onChange={(e) => setForm({ ...form, locale: e.target.value })}
                  />
                  <Button type="submit">添加</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "assets" ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>llms.txt 草稿</CardTitle>
              <p className="mt-1 text-sm text-slate-500">由 SEO 选题生成，需人工改稿并确认。不会自动挂到客户域名。</p>
            </div>
            <Button variant="outline" onClick={generateLlms}>
              按选题生成
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {llms ? (
              <>
                <Badge>{llms.status === "ready" ? "可交付" : "草稿"}</Badge>
                <Textarea
                  className="min-h-[280px] font-mono"
                  defaultValue={llms.body}
                  key={llms.updated_at ?? llms.id}
                  onBlur={(e) => saveAsset(llms.id, e.target.value)}
                />
                <Input
                  placeholder="确认备注"
                  value={confirmNote}
                  onChange={(e) => setConfirmNote(e.target.value)}
                />
                <Button onClick={() => readyAsset(llms.id)}>我已确认，标记可交付</Button>
              </>
            ) : (
              <p className="text-sm text-slate-500">还没有草稿。先点「按选题生成」。</p>
            )}
          </CardContent>
        </Card>
      ) : null}

      {tab === "checklist" ? (
        <Card>
          <CardHeader>
            <CardTitle>可引用清单（挂在 SEO 选题上）</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
              value={pageId}
              onChange={(e) => loadChecklist(e.target.value)}
            >
              <option value="">选择一篇 SEO 选题</option>
              {pages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            {items.map((i) => (
              <div key={i.id} className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <div className="font-medium">{i.label}</div>
                  <Badge tone={i.status === "untested" ? "amber" : i.status === "pass" ? "green" : "red"}>
                    {i.status === "untested" ? "未测" : i.status === "pass" ? "通过" : "未通过"}
                  </Badge>
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "untested")}>
                    未测
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "pass")}>
                    通过
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "fail")}>
                    未通过
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
