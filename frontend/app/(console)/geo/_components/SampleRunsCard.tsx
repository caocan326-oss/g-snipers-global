import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoSampleRun } from "@/lib/api";

export function SampleRunsCard({ runs }: { runs: GeoSampleRun[] }) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>检查批次记录</CardTitle>
        <p className="text-sm text-slate-500">正式说明里“给出了官网”的结论，必须能对上检查批次、记录编号和核对状态。</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {runs.length ? runs.map((run) => (
          <div key={run.id} className="rounded-md border border-slate-200 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-mono text-xs text-slate-500">{run.id}</div>
                <div className="mt-1 text-sm font-medium">
                  {run.protocol_version} · {run.prompt_set_id} · {run.results_count} 条记录
                </div>
                {run.results_count === 0 ? (
                  <p className="mt-1 text-xs text-amber-700">这批没有写出记录。提及写「未测」只表示这批是空的，不要拿去对说明页。</p>
                ) : null}
                {run.note ? <p className="mt-1 text-xs text-slate-500">{run.note}</p> : null}
              </div>
              <Badge tone={run.status === "done" ? "green" : "amber"}>{run.status}</Badge>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-4">
              <div>配置指纹：<span className="font-mono">{run.config_hash}</span></div>
              <div>提及：{run.mention_rate}</div>
              <div>给出了官网：{run.cite_rate}</div>
              <div>官网来源已核对：{run.verified_citation_rate}</div>
            </div>
            <div className="mt-3 space-y-3">
              {run.results.map((result) => (
                <div key={result.id} className="rounded-md bg-slate-50 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={result.mentioned ? "blue" : "default"}>{result.mentioned ? "被提到" : "未提到"}</Badge>
                    <Badge tone={result.owned_citations.length ? "green" : "default"}>
                      {result.owned_citations.length ? "有官网链接" : "没有官网链接"}
                    </Badge>
                    <span className="text-xs text-slate-500">{result.engine_label ?? result.engine}</span>
                  </div>
                  {result.answer_excerpt ? (
                    <p className="mt-2 whitespace-pre-wrap text-slate-700">{result.answer_excerpt}</p>
                  ) : (
                    <p className="mt-2 text-xs text-slate-400">这条没有回答摘录，看导出记录。</p>
                  )}
                  {result.third_party_citations.length ? (
                    <p className="mt-2 text-xs text-slate-500">外来网址：{result.third_party_citations.join("；")}</p>
                  ) : null}
                  {result.owned_citations.length ? (
                    <p className="mt-2 text-xs text-slate-500">疑似官网：{result.owned_citations.join("；")}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">还没有检查批次。记下一条回答后，可以点击“保存当前记录”。</p>}
      </CardContent>
    </Card>
  );
}
