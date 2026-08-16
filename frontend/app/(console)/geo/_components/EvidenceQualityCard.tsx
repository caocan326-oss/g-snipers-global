import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoProviderStatus, GeoSampleResult, GeoSampleRun, GeoSummary } from "@/lib/api";

import type { GeoEvidenceVerdict } from "../_helpers";

export type ProviderQualityEntry = {
  provider: GeoProviderStatus;
  providerRuns: GeoSampleRun[];
  providerResults: GeoSampleResult[];
  verified: number;
  citations: number;
  status: string;
};

export function EvidenceQualityCard({
  evidenceVerdict,
  runs,
  summary,
  providerQuality,
}: {
  evidenceVerdict: GeoEvidenceVerdict;
  runs: GeoSampleRun[];
  summary: GeoSummary | null;
  providerQuality: ProviderQualityEntry[];
}) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>证据可信度与数据源质量</CardTitle>
            <p className="mt-1 text-sm text-slate-500">报告只引用可追溯证据：测试批次、证据编号、联网来源 URL 和核验状态必须能对上。</p>
          </div>
          <Badge tone={evidenceVerdict.tone}>{evidenceVerdict.level}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-950">{evidenceVerdict.title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">{evidenceVerdict.text}</p>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-4">
            <div className="rounded-md bg-white p-3"><div className="text-xs text-slate-500">采样批次</div><div className="mt-1 font-semibold">{runs.length}</div></div>
            <div className="rounded-md bg-white p-3"><div className="text-xs text-slate-500">证据记录</div><div className="mt-1 font-semibold">{summary?.evidence_results ?? 0}</div></div>
            <div className="rounded-md bg-white p-3"><div className="text-xs text-slate-500">品牌提及</div><div className="mt-1 font-semibold">{summary?.mention_rate ?? "未测"}</div></div>
            <div className="rounded-md bg-white p-3"><div className="text-xs text-slate-500">核验引用</div><div className="mt-1 font-semibold">{summary?.verified_citation_rate ?? "未测"}</div></div>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {providerQuality.map(({ provider, providerRuns, verified, citations, status }) => (
            <div key={provider.key} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm font-medium text-slate-900">{provider.label}</span>
                <Badge tone={!provider.configured ? "amber" : verified > 0 ? "green" : citations > 0 ? "blue" : "default"}>{status}</Badge>
              </div>
              <p className="mt-2 line-clamp-2 text-xs text-slate-500">{provider.note}</p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-md bg-slate-50 p-2"><div className="font-semibold">{providerRuns.length}</div><div className="text-slate-500">批次</div></div>
                <div className="rounded-md bg-slate-50 p-2"><div className="font-semibold">{citations}</div><div className="text-slate-500">来源</div></div>
                <div className="rounded-md bg-slate-50 p-2"><div className="font-semibold">{verified}</div><div className="text-slate-500">核验</div></div>
              </div>
              <p className="mt-2 text-[11px] text-slate-400">
                {provider.web_grounded ? "联网数据源：需要来源 URL 才能进入引用率。" : "非联网数据源：只做分析、建议和文本判断。"}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
