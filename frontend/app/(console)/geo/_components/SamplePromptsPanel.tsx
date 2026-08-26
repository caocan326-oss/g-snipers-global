import { FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CountryPicker } from "@/components/CountryPicker";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { countryLabel } from "@/lib/countries";
import type { GeoPrompt } from "@/lib/api";

import { diagnosisOptions, displayRate, evidenceLabel, obsLabel, obsTone } from "../_helpers";

function openedSlots(
  p: GeoPrompt,
  region: string,
  title: string,
  setObs: (id: string, status: string, extra?: Record<string, string | null>) => void
) {
  const rows = p.observations.filter((o) => (o.region || "") === region && o.status !== "untested");
  if (!rows.length) return null;
  return (
    <div>
      <div className="mb-2 text-xs font-medium text-slate-500">{title}</div>
      <div className="flex flex-wrap gap-3">
        {rows.map((o) => (
          <div key={o.id} className="w-full rounded-md border p-3 lg:w-[calc(50%-0.375rem)]">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="text-xs font-medium text-slate-500">{o.engine_label || o.engine}</div>
              <Badge tone={obsTone[o.status]}>{obsLabel[o.status] ?? o.status}</Badge>
            </div>
            <div className="mb-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
              <span>{evidenceLabel[o.evidence_tier || "none"] || o.evidence_label}</span>
              {o.observed_at ? <span>{new Date(o.observed_at).toLocaleString("zh-CN")}</span> : null}
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {["untested", "not_mentioned", "mentioned", "cited", "verified"].map((s) => (
                <Button key={s} size="sm" variant="ghost" onClick={() => setObs(o.id, s)}>
                  {obsLabel[s]}
                </Button>
              ))}
            </div>
            <div className="mt-3 grid gap-2">
              <Textarea
                className="min-h-[72px]"
                placeholder="回答摘录"
                defaultValue={o.response_excerpt || ""}
                onBlur={(e) => setObs(o.id, o.status, { response_excerpt: e.target.value })}
              />
              <Input
                placeholder="来源网址"
                defaultValue={o.citation_urls || ""}
                onBlur={(e) => setObs(o.id, o.status, { citation_urls: e.target.value })}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SamplePromptsPanel({
  prompts,
  form,
  setForm,
  addPrompt,
  aiPrompt,
  setDiagnosis,
  setObs,
}: {
  prompts: GeoPrompt[];
  form: { prompt_text: string; country_code: string };
  setForm: (form: { prompt_text: string; country_code: string }) => void;
  addPrompt: (e: FormEvent) => void;
  aiPrompt: (id: string) => void;
  setDiagnosis: (promptId: string, diagnosis: string) => void;
  setObs: (id: string, status: string, extra?: Record<string, string | null>) => void;
}) {
  return (
    <div className="space-y-4">
      {prompts.map((p) => {
        const closedCount = p.observations.filter((o) => o.status === "untested").length;
        const western = openedSlots(p, "western", "已手工打开的海外引擎", setObs);
        const china = openedSlots(p, "china", "已手工打开的中国引擎", setObs);
        return (
          <Card key={p.id}>
            <CardHeader>
              <CardTitle className="text-base">{p.prompt_text}</CardTitle>
              <p className="text-xs text-slate-500">
                {countryLabel(p.locale)} · 联网抽查被提到 {displayRate(p.mention_rate)} · 给出官网 {displayRate(p.cite_rate)}
              </p>
              {p.sample_verdict ? <p className="mt-1 text-xs font-medium text-slate-700">{p.sample_verdict}</p> : null}
              <p className="mt-1 text-[11px] text-slate-400">
                ChatGPT / Perplexity 等还没逐个打开
                {closedCount ? `（空着 ${closedCount} 个记位，不假装有覆盖）` : ""}。上面比例只算已跑过的联网抽查。
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-slate-500">客户经理：改判断 / AI 诊断</summary>
                <div className="mt-2 flex items-center gap-2">
                  <Button size="sm" onClick={() => aiPrompt(p.id)}>
                    AI 诊断
                  </Button>
                  <select
                    className="h-8 rounded-md border border-slate-200 px-2 text-sm"
                    value={p.diagnosis}
                    onChange={(e) => setDiagnosis(p.id, e.target.value)}
                  >
                    {diagnosisOptions.map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
              </details>
            </CardHeader>
            {(western || china) && (
              <CardContent className="space-y-4">
                {western}
                {china}
              </CardContent>
            )}
          </Card>
        );
      })}
      {prompts.length === 0 ? (
        <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          还没有买家原句。不要编。可点「采用已记原句」，或在下面手写一句再抽查。只有搜索词时仍会空着。
        </p>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>新增买家问题</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={addPrompt}>
            <Input
              placeholder="例如：Which brand makes the best 100W USB-C charger for laptops?"
              value={form.prompt_text}
              onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
              required
            />
            <div>
              <div className="mb-1 text-xs text-slate-500">这个问题按哪个国家记</div>
              <CountryPicker value={form.country_code} onChange={(country_code) => setForm({ ...form, country_code })} />
            </div>
            <Button type="submit">添加</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
