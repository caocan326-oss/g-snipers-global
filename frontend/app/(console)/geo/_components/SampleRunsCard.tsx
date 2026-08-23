import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoSampleResult, GeoSampleRun } from "@/lib/api";

function otherCitations(result: GeoSampleResult) {
  const shops = result.marketplace_citations ?? [];
  return result.third_party_citations.filter((url) => !shops.includes(url));
}

function verificationLabel(status: string) {
  if (status === "passed") return "官网已核对";
  if (status === "failed") return "官网核对未通过";
  if (status === "pending") return "疑似官网，待打开核对";
  return "没有可核官网";
}

export function SampleRunsCard({
  runs,
  busyId,
  verifyOwnedCitation,
}: {
  runs: GeoSampleRun[];
  busyId?: string;
  verifyOwnedCitation?: (resultId: string, checkedUrl: string, passed: boolean) => void;
}) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>检查批次记录</CardTitle>
        <p className="text-sm text-slate-500">
          正式说明里“给出了官网”的结论，必须能对上检查批次、记录编号，并且是人对着客户官网链接打开核对过的。购物页不能勾通过。
        </p>
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
              {run.results.map((result) => {
                const shops = result.marketplace_citations ?? [];
                const other = otherCitations(result);
                const pendingOwned = result.owned_citations.length > 0 && result.verification_status !== "passed";
                return (
                <div key={result.id} className="rounded-md bg-slate-50 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={result.mentioned ? "blue" : "default"}>{result.mentioned ? "被提到" : "未提到"}</Badge>
                    <Badge tone={result.owned_citations.length ? "green" : "default"}>
                      {result.owned_citations.length ? "有官网链接" : "没有官网链接"}
                    </Badge>
                    <Badge
                      tone={
                        result.verification_status === "passed"
                          ? "green"
                          : result.verification_status === "failed"
                            ? "red"
                            : pendingOwned
                              ? "amber"
                              : "default"
                      }
                    >
                      {verificationLabel(result.verification_status)}
                    </Badge>
                    {shops.length ? <Badge tone="default">有购物页，不算官网</Badge> : null}
                    <span className="text-xs text-slate-500">{result.engine_label ?? result.engine}</span>
                  </div>
                  {result.mentioned && !result.owned_citations.length ? (
                    <p className="mt-2 text-xs text-amber-700">
                      正文提到了品牌，但链接里没有客户官网，所以没有「核对通过」。上线地址栏填的页不算抽查给出了官网。
                    </p>
                  ) : null}
                  {result.answer_excerpt ? (
                    <p className="mt-2 whitespace-pre-wrap text-slate-700">{result.answer_excerpt}</p>
                  ) : (
                    <p className="mt-2 text-xs text-slate-400">这条没有回答摘录，看导出记录。</p>
                  )}
                  {result.owned_citations.length ? (
                    <div className="mt-2 space-y-2">
                      <p className="text-xs text-slate-500">疑似官网（只有这些能核成「给出了官网」）：</p>
                      {result.owned_citations.map((url) => (
                        <div key={url} className="flex flex-wrap items-center gap-2 text-xs">
                          <a className="break-all text-brand-700 underline" href={url} target="_blank" rel="noreferrer">
                            {url}
                          </a>
                          {verifyOwnedCitation && result.verification_status !== "passed" ? (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={busyId === result.id}
                                onClick={() => verifyOwnedCitation(result.id, url, true)}
                              >
                                {busyId === result.id ? "核对中…" : "打开过，核对通过"}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={busyId === result.id}
                                onClick={() => verifyOwnedCitation(result.id, url, false)}
                              >
                                打不开 / 不是客户页
                              </Button>
                            </>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {result.verification_note ? (
                    <p className="mt-2 text-xs text-slate-500">核对备注：{result.verification_note}</p>
                  ) : null}
                  {shops.length ? (
                    <p className="mt-2 text-xs text-slate-500">购物页（不算官网）：{shops.join("；")}</p>
                  ) : null}
                  {other.length ? (
                    <p className="mt-2 text-xs text-slate-500">其它外来网址：{other.join("；")}</p>
                  ) : null}
                </div>
                );
              })}
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">还没有检查批次。记下一条回答后，可以点击“保存当前记录”。</p>}
      </CardContent>
    </Card>
  );
}
