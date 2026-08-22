import { Activity, Database, Download, FileText, Globe2, ShieldCheck, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GeoProviderStatus, GeoProviderStatusList, GeoSummary } from "@/lib/api";

import { UsageTodayBar } from "../../_components/UsageTodayBar";
import { displayRate, formatCheckAt, providerRoleLabel } from "../_helpers";

export function HeroSection({
  summary,
  busyAction,
  seedPromptPanel,
  createEvidenceRun,
  draftTicketsFromEvidence,
  providers,
  sampleProvider,
  setSampleProvider,
  selectedProvider,
  runAutoSample,
  runGroundedBatch,
  retestSameQuestions,
  canRetestSame,
  downloadGeoReport,
  downloadGeoTable,
  note,
  error,
}: {
  summary: GeoSummary | null;
  busyAction: string;
  seedPromptPanel: () => void;
  createEvidenceRun: () => void;
  draftTicketsFromEvidence: () => void;
  providers: GeoProviderStatusList | null;
  sampleProvider: string;
  setSampleProvider: (value: string) => void;
  selectedProvider: GeoProviderStatus | undefined;
  runAutoSample: () => void;
  runGroundedBatch: () => void;
  retestSameQuestions: () => void;
  canRetestSame: boolean;
  downloadGeoReport: () => void;
  downloadGeoTable: () => void;
  note: string;
  error: string;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">AI 搜索可见度</Badge>
            <Badge tone={(summary?.latest_sampled || summary?.evidence_results || summary?.recorded) ? "green" : "amber"}>
              {(summary?.latest_sampled || summary?.evidence_results || summary?.recorded) ? "已有抽查" : "还没抽查"}
            </Badge>
            <Badge tone="blue">标准买家问题</Badge>
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-950">AI 搜索可见度</h1>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
            用买家会问的问题，看 AI 回答里有没有提到客户、有没有给出官网、是不是只在推荐竞品。没有联网来源的结果只作分析参考。
          </p>
          <div className="mt-2">
            <UsageTodayBar meters={["bocha", "bailian", "tavily", "llm"]} refreshToken={busyAction} />
          </div>
        </div>
        <div className="grid w-full gap-2 text-sm md:grid-cols-3 xl:w-[560px]">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><Activity className="h-4 w-4" />最近一次检查</div>
            <div className="mt-1 font-medium text-slate-900">{formatCheckAt(summary?.latest_run_at)}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><Database className="h-4 w-4" />检查记录</div>
            <div className="mt-1 font-medium text-slate-900">{summary?.evidence_results ?? 0}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><ShieldCheck className="h-4 w-4" />已核对官网来源</div>
            <div className="mt-1 font-medium text-slate-900">{displayRate(summary?.verified_citation_rate)}</div>
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={seedPromptPanel} disabled={busyAction === "seed-prompts"}>
          <Wand2 className="mr-2 h-4 w-4" />
          {busyAction === "seed-prompts" ? "生成中…" : "生成买家问题"}
        </Button>
        <Button size="sm" variant="outline" onClick={createEvidenceRun} disabled={busyAction === "evidence-run"}>
          {busyAction === "evidence-run" ? "整理中…" : "保存当前记录"}
        </Button>
        <Button size="sm" variant="outline" onClick={draftTicketsFromEvidence} disabled={busyAction === "draft-tickets"}>
          {busyAction === "draft-tickets" ? "生成中…" : "生成待处理项"}
        </Button>
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-1">
          <select
            className="h-8 min-w-[190px] rounded border border-slate-200 bg-white px-2 text-xs outline-none focus:border-emerald-500"
            value={sampleProvider}
            onChange={(e) => setSampleProvider(e.target.value)}
            aria-label="选择 AI 搜索测试数据源"
          >
            {(providers?.providers ?? [{ key: "deepseek", label: "DeepSeek", configured: true, role: "analysis", web_grounded: false }]).map((provider) => (
              <option key={provider.key} value={provider.key}>
                {provider.label} · {providerRoleLabel[provider.role] ?? provider.role}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={runAutoSample} disabled={busyAction === "auto-sample" || busyAction === "grounded-batch" || Boolean(selectedProvider && !selectedProvider.configured)}>
            <Globe2 className="mr-2 h-4 w-4" />
            {busyAction === "auto-sample" ? "检查中…" : "只测这一源"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={runGroundedBatch}
            disabled={busyAction === "auto-sample" || busyAction === "grounded-batch" || !(providers?.providers ?? []).some((provider) => provider.configured && provider.web_grounded && (provider.key === "bocha" || provider.key === "bailian" || provider.key === "tavily"))}
          >
            {busyAction === "grounded-batch" ? "抽查中…" : "已配置的联网源都测"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={retestSameQuestions}
            disabled={!canRetestSame || busyAction === "auto-sample" || busyAction === "grounded-batch" || busyAction === "retest-same"}
          >
            {busyAction === "retest-same" ? "复测中…" : "同一问再测"}
          </Button>
        </div>
        <Button size="sm" variant="outline" onClick={downloadGeoReport}>
          <FileText className="mr-2 h-4 w-4" />
          下载 AI 搜索说明（PDF）
        </Button>
        <Button size="sm" variant="outline" onClick={downloadGeoTable}>
          <Download className="mr-2 h-4 w-4" />
          下载检查记录
        </Button>
      </div>
      {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      <p className="mt-3 text-xs text-slate-500">
        一次只跑下拉里选中的源。已配置但没选的卡片会空着，不是坏了。当前：{selectedProvider?.label ?? "尚未选择"} · {selectedProvider?.web_grounded ? "联网来源：返回网址时，可算作给出了官网" : "分析参考：只判断有没有提到品牌，不算给出官网"}。
        「同一问再测」只对最近一批买家问题再抽一次，记下有没有变化，不承诺这次会提到。
      </p>
    </section>
  );
}
