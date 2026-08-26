import { Copy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { OnsiteIssue } from "@/lib/api";

import { sevLabel, sevTone } from "../_helpers";

export function WeeklyFixesCard({
  issues,
  copyOne,
  copyAll,
  openIssue,
}: {
  issues: OnsiteIssue[];
  copyOne: (issue: OnsiteIssue) => void;
  copyAll: () => void;
  openIssue: (id: string) => void;
}) {
  return (
    <Card className="rounded-md border-amber-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">这周给客户改三处</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              从紧急/优先里每页只挑一条，最多三页。不是全部问题。短稿只写哪一页、请做、怎么验。我们不代改官网。
            </p>
          </div>
          {issues.length ? (
            <Button size="sm" variant="outline" onClick={copyAll}>
              <Copy className="mr-1.5 h-3.5 w-3.5" />
              复制这三处
            </Button>
          ) : null}
        </div>
        {issues.length ? (
          <div className="grid gap-3 lg:grid-cols-3">
            {issues.map((issue, index) => (
              <div key={issue.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{index + 1}</Badge>
                  <Badge tone={sevTone[issue.severity] ?? "default"}>{sevLabel[issue.severity] ?? issue.severity}</Badge>
                </div>
                <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
                  {issue.customer_note || "还没有给客户的短稿。"}
                </pre>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => copyOne(issue)}>
                    复制短稿
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => openIssue(issue.id)}>
                    打开这条
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
