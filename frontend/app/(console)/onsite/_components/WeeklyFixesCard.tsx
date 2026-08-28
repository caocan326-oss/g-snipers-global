import { Copy, Pin } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { OnsiteIssue } from "@/lib/api";

import { sevLabel, sevTone } from "../_helpers";

export function WeeklyFixesCard({
  issues,
  pinned,
  copyOne,
  copyAll,
  openIssue,
  markTemplateLimit,
  markSent,
  clearSent,
  pinWeek,
  unpinWeek,
  rotateWeek,
  recheckIssue,
  recordVerdict,
  restoreDropped,
  canRestore,
  busyId,
}: {
  issues: OnsiteIssue[];
  pinned: boolean;
  copyOne: (issue: OnsiteIssue) => void;
  copyAll: () => void;
  openIssue: (id: string) => void;
  markTemplateLimit: (issue: OnsiteIssue) => void;
  markSent: (issue: OnsiteIssue) => void;
  clearSent: (issue: OnsiteIssue) => void;
  pinWeek: () => void;
  unpinWeek: () => void;
  rotateWeek: () => void;
  recheckIssue: (issue: OnsiteIssue) => void;
  recordVerdict: (issue: OnsiteIssue, passed: boolean) => void;
  restoreDropped: () => void;
  canRestore: boolean;
  busyId: string;
}) {
  const allPassed = issues.length > 0 && issues.every((issue) => (issue.retest_result || "").includes("这一条现在对得上"));
  return (
    <Card className="rounded-md border-amber-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">这周给客户改三处</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              从紧急/优先里每页只挑一条，最多三页。同一紧急程度先挑列表页，不优先 article_id 深页。钉住后新抓到的紧急页不会顶掉。「打开核对」只打开现网并记下看过。看完再点「记过」或「记不过」。不会自己勾完、也不会拿掉。已发给客户不是官网已改。我们不代改。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {issues.length ? (
              <Button size="sm" variant="outline" onClick={copyAll}>
                <Copy className="mr-1.5 h-3.5 w-3.5" />
                复制这三处
              </Button>
            ) : null}
            {allPassed ? (
              <Button size="sm" onClick={rotateWeek} disabled={busyId === "weekly-next"}>
                换下一组
              </Button>
            ) : null}
            {issues.length && pinned ? (
              <Button size="sm" variant="outline" onClick={unpinWeek} disabled={busyId === "weekly-pin"}>
                取消钉住
              </Button>
            ) : issues.length ? (
              <Button size="sm" variant="outline" onClick={pinWeek} disabled={busyId === "weekly-pin"}>
                <Pin className="mr-1.5 h-3.5 w-3.5" />
                钉住这三处
              </Button>
            ) : null}
            {canRestore ? (
              <Button size="sm" variant="outline" onClick={restoreDropped} disabled={busyId === "weekly-restore"}>
                放回刚拿掉的一页
              </Button>
            ) : null}
          </div>
        </div>
        {pinned ? <Badge tone="amber">已钉住。新抓到的页不会顶掉。</Badge> : null}
        {allPassed ? (
          <p className="text-sm leading-6 text-emerald-700">
            这三处都核对过。换下一组按紧急/优先另挑。上一组还在问题板，不是已解决。我们不代改。
          </p>
        ) : null}
        {!allPassed && issues.some((issue) => !issue.sent_to_customer) ? (
          <p className="text-sm leading-6 text-amber-800">
            还有没发给客户的。复制短稿发给客户，再点已发给客户。不是官网已改。我们不代发。
          </p>
        ) : null}
        {issues.length ? (
          <div className="grid gap-3 lg:grid-cols-3">
            {issues.map((issue, index) => (
              <div key={issue.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{index + 1}</Badge>
                  <Badge tone={sevTone[issue.severity] ?? "default"}>{sevLabel[issue.severity] ?? issue.severity}</Badge>
                  {issue.sent_to_customer ? <Badge tone="blue">已发给客户</Badge> : null}
                </div>
                <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
                  {issue.customer_note || "还没有给客户的短稿。"}
                </pre>
                {issue.retest_result ? <p className="text-xs leading-5 text-slate-600">{issue.retest_result}</p> : null}
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => copyOne(issue)}>
                    复制短稿
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => openIssue(issue.id)}>
                    打开这条
                  </Button>
                  {issue.sent_to_customer ? (
                    <Button size="sm" variant="outline" onClick={() => clearSent(issue)} disabled={busyId === issue.id}>
                      取消已发
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => markSent(issue)} disabled={busyId === issue.id}>
                      已发给客户
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => recheckIssue(issue)} disabled={busyId === issue.id}>
                    打开核对
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => recordVerdict(issue, true)} disabled={busyId === issue.id}>
                    记过
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => recordVerdict(issue, false)} disabled={busyId === issue.id}>
                    记不过
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => markTemplateLimit(issue)} disabled={busyId === issue.id}>
                    记受模板限制
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm leading-6 text-slate-500">还没有紧急或优先项能写成给客户的短稿。先查看网页，再从问题板挑。</p>
        )}
      </CardContent>
    </Card>
  );
}
