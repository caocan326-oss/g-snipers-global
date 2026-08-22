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

function slotGroup(
  p: GeoPrompt,
  region: string,
  title: string,
  setObs: (id: string, status: string, extra?: Record<string, string | null>) => void
) {
  const rows = p.observations.filter((o) => (o.region || "") === region);
  const opened = rows.filter((o) => o.status !== "untested");
  const closed = rows.filter((o) => o.status === "untested");
  const card = (o: (typeof rows)[number]) => (
    <div key={o.id} className="w-full rounded-md border p-3 lg:w-[calc(50%-0.375rem)]">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-xs font-medium text-slate-500">{o.engine_label || o.engine}</div>
        <Badge tone={obsTone[o.status]}>{obsLabel[o.status] ?? o.status}</Badge>
      </div>
      <div className="mb-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
        <span>{o.surface || "manual_ai_answer"}</span>
        <span>{o.sample_type || "manual"}</span>
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
          placeholder="回答摘录：粘贴 AI 答案里提到客户、竞品或官网来源的片段"
          defaultValue={o.response_excerpt || ""}
          onBlur={(e) => setObs(o.id, o.status, { response_excerpt: e.target.value })}
        />
        <Input
          placeholder="来源网址，一行或逗号分隔"
          defaultValue={o.citation_urls || ""}
          onBlur={(e) => setObs(o.id, o.status, { citation_urls: e.target.value })}
        />
        <div className="grid gap-2 md:grid-cols-2">
          <Input
            placeholder="品牌/产品提及"
            defaultValue={o.brand_mentions || ""}
            onBlur={(e) => setObs(o.id, o.status, { brand_mentions: e.target.value })}
          />
          <Input
            placeholder="竞品提及"
            defaultValue={o.competitor_mentions || ""}
            onBlur={(e) => setObs(o.id, o.status, { competitor_mentions: e.target.value })}
          />
        </div>
        <Input
          placeholder="备注：说明这条记录来自人工记下、AI 回答、搜索结果或其他来源"
          defaultValue={o.interpretation_note || o.notes || ""}
          onBlur={(e) => setObs(o.id, o.status, { interpretation_note: e.target.value, notes: e.target.value })}
        />
      </div>
    </div>
  );
  return (
    <div>
      <div className="mb-2 text-xs font-medium text-slate-500">{title}</div>
      {closed.length ? (
        <p className="mb-2 text-xs text-slate-500">
          {closed.length} 个引擎还没手工打开。这是记 ChatGPT 等回答用的空位，不是这轮联网抽查的缺口。
        </p>
      ) : null}
      {opened.length ? <div className="flex flex-wrap gap-3">{opened.map(card)}</div> : null}
      {closed.length ? (
        <details className="mt-3 rounded-md border border-dashed border-slate-200 p-3">
          <summary className="cursor-pointer text-xs text-slate-600">
            展开未打开的引擎（{closed.map((o) => o.engine_label || o.engine).join("、")}）
          </summary>
          <div className="mt-3 flex flex-wrap gap-3">{closed.map(card)}</div>
        </details>
      ) : null}
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
      {prompts.map((p) => (
        <Card key={p.id}>
          <CardHeader>
            <CardTitle className="text-base">{p.prompt_text}</CardTitle>
            <p className="text-xs text-slate-500">
              {p.sample_verdict
                ? `${countryLabel(p.locale)} · 联网抽查被提到 ${displayRate(p.mention_rate)} · 给出官网 ${displayRate(p.cite_rate)}`
                : `${countryLabel(p.locale)} · 被提到 ${displayRate(p.mention_rate)} · 给出官网 ${displayRate(p.cite_rate)} · 已核对 ${displayRate(p.verified_citation_rate)} · 竞品 ${displayRate(p.competitor_rate)}`}
            </p>
            {p.sample_verdict ? <p className="mt-1 text-xs font-medium text-slate-700">{p.sample_verdict}</p> : null}
            <p className="mt-1 text-[11px] text-slate-400">
              {p.sample_verdict
                ? "「被提到 / 给出官网」按这一轮联网记录算。下面 8 个引擎空位没手工打开的仍是尚未检查。"
                : "上面「被提到 / 给出官网 / 已核对」是 8 个引擎空位。没打开的保持尚未检查。"}
            </p>
            {p.evidence ? <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{p.evidence}</pre> : null}
            <div className="mt-2 flex items-center gap-2">
              <Button size="sm" onClick={() => aiPrompt(p.id)}>
                AI 诊断
              </Button>
              <span className="text-xs text-slate-500">判断</span>
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
          </CardHeader>
          <CardContent className="space-y-4">
            {slotGroup(p, "western", "海外 AI / 搜索引擎", setObs)}
            {slotGroup(p, "china", "中国 AI / 搜索引擎（可手工记录）", setObs)}
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardHeader>
          <CardTitle>新增买家问题</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={addPrompt}>
            <Input
              placeholder="例如：Which supplier is reliable for industrial pumps in the US?"
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
