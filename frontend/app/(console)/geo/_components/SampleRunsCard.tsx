import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoSampleRun } from "@/lib/api";

export function SampleRunsCard({ runs }: { runs: GeoSampleRun[] }) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>采样批次记录</CardTitle>
        <p className="text-sm text-slate-500">正式报告里的引用结论必须能追溯到采样批次、证据编号、配置 hash 和核验状态。</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {runs.length ? runs.map((run) => (
          <div key={run.id} className="rounded-md border border-slate-200 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-mono text-xs text-slate-500">{run.id}</div>
                <div className="mt-1 text-sm font-medium">
                  {run.protocol_version} · {run.prompt_set_id} · {run.results_count} 条证据
                </div>
              </div>
              <Badge tone={run.status === "done" ? "green" : "amber"}>{run.status}</Badge>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-4">
              <div>配置指纹：<span className="font-mono">{run.config_hash}</span></div>
              <div>提及：{run.mention_rate}</div>
              <div>自有引用：{run.cite_rate}</div>
              <div>核验引用：{run.verified_citation_rate}</div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {run.results.slice(0, 6).map((result) => (
                <Badge key={result.id} tone={result.verification_status === "passed" ? "green" : "default"}>
                  {result.evidence_id} · {result.engine_label ?? result.engine}
                </Badge>
              ))}
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">暂无采样批次。记录一条观测后，可以点击“固化当前证据”。</p>}
      </CardContent>
    </Card>
  );
}
