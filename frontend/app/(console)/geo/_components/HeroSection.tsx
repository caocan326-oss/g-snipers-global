import { Activity, Database, Download, FileText, Globe2, ShieldCheck, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GeoProviderStatus, GeoProviderStatusList, GeoSummary } from "@/lib/api";

import { providerRoleLabel } from "../_helpers";

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
            <Badge tone={summary?.recorded ? "green" : "amber"}>{summary?.recorded ? "已有观测" : "待采样"}</Badge>
            <Badge tone="blue">标准买家问题集</Badge>
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-950">AI 搜索可见度诊断</h1>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
            用买家真实会问的问题测试 AI 回答里有没有提到客户、有没有引用客户官网、是不是只推荐竞品。没有联网来源的数据只作为分析参考。
          </p>
        </div>
        <div className="grid w-full gap-2 text-sm md:grid-cols-3 xl:w-[560px]">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><Activity className="h-4 w-4" />最近测试批次</div>
            <div className="mt-1 truncate font-mono text-xs font-medium text-slate-900">{summary?.latest_run_id ?? "暂无"}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><Database className="h-4 w-4" />证据数量</div>
            <div className="mt-1 font-medium text-slate-900">{summary?.evidence_results ?? 0}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500"><ShieldCheck className="h-4 w-4" />已确认引用</div>
            <div className="mt-1 font-medium text-slate-900">{summary?.verified_citation_rate ?? "未测"}</div>
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={seedPromptPanel} disabled={busyAction === "seed-prompts"}>
          <Wand2 className="mr-2 h-4 w-4" />
          {busyAction === "seed-prompts" ? "生成中…" : "生成买家问题"}
        </Button>
        <Button size="sm" variant="outline" onClick={createEvidenceRun} disabled={busyAction === "evidence-run"}>
          {busyAction === "evidence-run" ? "整理中…" : "保存当前证据"}
        </Button>
        <Button size="sm" variant="outline" onClick={draftTicketsFromEvidence} disabled={busyAction === "draft-tickets"}>
          {busyAction === "draft-tickets" ? "生成中…" : "生成整改项"}
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
          <Button size="sm" onClick={runAutoSample} disabled={busyAction === "auto-sample" || Boolean(selectedProvider && !selectedProvider.configured)}>
            <Globe2 className="mr-2 h-4 w-4" />
            {busyAction === "auto-sample" ? "采样中…" : "运行采样"}
          </Button>
        </div>
        <Button size="sm" variant="outline" onClick={downloadGeoReport}>
          <FileText className="mr-2 h-4 w-4" />
          导出 AI 搜索报告
        </Button>
        <Button size="sm" variant="outline" onClick={downloadGeoTable}>
          <Download className="mr-2 h-4 w-4" />
          导出证据表格
        </Button>
      </div>
      {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      <p className="mt-3 text-xs text-slate-500">
        当前测试来源：{selectedProvider?.label ?? sampleProvider} · {selectedProvider?.web_grounded ? "联网证据源，返回 URL 时可计入引用率" : "分析参考源，只判断品牌提及和内容方向"}
      </p>
    </section>
  );
}
