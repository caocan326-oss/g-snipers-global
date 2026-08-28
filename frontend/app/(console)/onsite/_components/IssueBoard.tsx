import { Bot, Copy, RefreshCcw, Search, Wrench, XCircle } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { OnsiteIssue } from "@/lib/api";
import { cn } from "@/lib/utils";

import {
  catLabel,
  filters,
  isTemplateLimited,
  plainIssueTitle,
  type FilterKey,
  nextStep,
  priorityLabel,
  sevLabel,
  sevTone,
  statusLabel,
  statusTone,
} from "../_helpers";

export function IssueBoard({
  visibleIssues,
  totalCount,
  filter,
  setFilter,
  query,
  setQuery,
  expandedId,
  setExpandedId,
  drafts,
  setDrafts,
  busyId,
  aiIssue,
  saveDraft,
  copyDraft,
  retestIssue,
  apply,
  ignoreIssue,
  markTemplateLimit,
  clearTemplateLimit,
}: {
  visibleIssues: OnsiteIssue[];
  totalCount: number;
  filter: FilterKey;
  setFilter: (filter: FilterKey) => void;
  query: string;
  setQuery: (query: string) => void;
  expandedId: string;
  setExpandedId: (id: string) => void;
  drafts: Record<string, string>;
  setDrafts: (drafts: Record<string, string>) => void;
  busyId: string;
  aiIssue: (id: string) => void;
  saveDraft: (issue: OnsiteIssue) => void;
  copyDraft: (issue: OnsiteIssue) => void;
  retestIssue: (issue: OnsiteIssue) => void;
  apply: (issue: OnsiteIssue) => void;
  ignoreIssue: (issue: OnsiteIssue) => void;
  markTemplateLimit: (issue: OnsiteIssue) => void;
  clearTemplateLimit: (issue: OnsiteIssue) => void;
}) {
  return (
    <Card id="onsite-issues" className="rounded-md">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
        <CardTitle>需要处理的问题</CardTitle>
            <p className="mt-1 text-sm text-slate-500">按紧急程度和进度排列。这里是检查记录，不是这周要做完。这周给客户看的三处在上面。点开一条即可查看依据、改法和复查方式。</p>
          </div>
          <Badge tone="amber">{visibleIssues.length} / {totalCount} 条</Badge>
        </div>
        <div className="grid gap-3 xl:grid-cols-[1fr_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              className="pl-9"
              placeholder="搜索网址、页面名、问题类型或改法"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {filters.map((item) => (
              <Button
                key={item.key}
                size="sm"
                variant={filter === item.key ? "default" : "outline"}
                onClick={() => setFilter(item.key)}
              >
                {item.label}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {visibleIssues.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-200 p-5 text-sm text-slate-500">
            当前筛选下没有待处理项。
          </div>
        ) : null}
        {visibleIssues.map((issue) => {
          const expanded = expandedId === issue.id;
          const severityTone = sevTone[issue.severity as keyof typeof sevTone] ?? "green";
          return (
            <div key={issue.id} className={cn("rounded-md border", expanded ? "border-brand-600" : "border-slate-200")}>
              <button
                type="button"
                className="grid w-full gap-3 p-4 text-left lg:grid-cols-[72px_1fr_180px_150px_110px]"
                onClick={() => setExpandedId(expanded ? "" : issue.id)}
              >
                <div>
                  <Badge tone={severityTone}>{priorityLabel(issue)}</Badge>
                  <div className="mt-2 text-xs text-slate-500">{sevLabel[issue.severity] ?? issue.severity}</div>
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{plainIssueTitle(issue.title)}</span>
                    <Badge>{catLabel[issue.category] ?? issue.category}</Badge>
                    <Badge tone="amber">{issue.metric_status === "untested" ? "尚未检查" : issue.metric_status}</Badge>
                    {isTemplateLimited(issue) ? <Badge tone="red">受模板限制</Badge> : null}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span className="text-brand-700">{issue.page_title || issue.page_path}</span>
                    <span>{issue.page_path}</span>
                  </div>
                </div>
                <div>
                  <Badge tone={statusTone[issue.status] ?? "default"}>{statusLabel[issue.status] ?? issue.status}</Badge>
                  <div className="mt-2 truncate text-xs text-slate-500">{issue.owner_hint || (issue.risk === "high" ? "需人工确认" : "可交给执行")}</div>
                </div>
                <div className="text-sm text-slate-600">{nextStep(issue)}</div>
                <div className="text-right text-xs font-medium text-brand-700">{expanded ? "收起" : "查看详情"}</div>
              </button>

              {expanded ? (
                <div className="border-t border-slate-100 bg-slate-50/60 p-4">
                  <div className="mb-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="text-xs font-medium text-slate-500">负责人</div>
                      <p className="mt-1 text-sm text-slate-800">{issue.owner_hint || "待分配"}</p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="text-xs font-medium text-slate-500">验收标准</div>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-800">{issue.acceptance_criteria || "按改法修改后，重新打开页面，确认问题不再出现。"}</p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="text-xs font-medium text-slate-500">复查方式</div>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-800">{issue.retest_method || "重新打开页面，对照修改前后的内容。"}</p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="text-xs font-medium text-slate-500">复查结果</div>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-800">{issue.retest_result || "尚未复查"}</p>
                    </div>
                  </div>
                  <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-slate-500">查看依据</div>
                      {plainIssueTitle(issue.title) !== issue.title && !/GEO-[A-Z]+-\d+|schema|JSON-LD/i.test(issue.title) ? (
                        <p className="text-xs text-slate-500">内部名称：{issue.title}</p>
                      ) : null}
                      <p className="text-sm text-slate-700">{issue.detail || "暂无详情。"}</p>
                      {issue.evidence ? (
                        <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-md bg-white p-3 text-xs text-slate-500">
                          {issue.evidence}
                        </pre>
                      ) : null}
                      {issue.ai_review ? <p className="text-xs text-slate-600">AI 初审：{issue.ai_review}</p> : null}
                      <div className="grid gap-2 pt-2 md:grid-cols-2">
                        <div className="rounded-md border border-slate-200 bg-white p-3">
                          <div className="text-xs font-medium text-slate-500">影响</div>
                          <p className="mt-1 text-sm text-slate-700">{issue.impact || "影响页面是否容易被理解和复查。"}</p>
                        </div>
                        <div className="rounded-md border border-slate-200 bg-white p-3">
                          <div className="text-xs font-medium text-slate-500">执行角色</div>
                          <p className="mt-1 text-sm text-slate-700">{issue.owner_hint || "客户经理 / 执行人"}</p>
                        </div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {issue.blocked_reason ? (
                        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{issue.blocked_reason}</p>
                      ) : null}
                      {issue.customer_note ? (
                        <div className="rounded-md border border-amber-200 bg-amber-50/70 p-3">
                          <div className="text-xs font-medium text-slate-500">给客户的短稿</div>
                          <pre className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{issue.customer_note}</pre>
                        </div>
                      ) : null}
                      <div className="text-xs font-medium text-slate-500">改法</div>
                      <div className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700">
                        <div className="text-xs font-medium text-slate-500">建议动作</div>
                        <p className="mt-1">{issue.recommended_action || "根据查看依据补充改法，人工确认后再修改网站。"}</p>
                        <div className="mt-3 text-xs font-medium text-slate-500">复查方法</div>
                        <p className="mt-1">{issue.retest_method || "修改后重新打开页面，对照是否已经纠正。"}</p>
                      </div>
                      <Textarea
                        className="min-h-[120px] bg-white"
                        placeholder="填写给网站执行人员的改法。系统不会自动改网站。"
                        value={drafts[issue.id] ?? issue.proposed_change}
                        onChange={(e) => setDrafts({ ...drafts, [issue.id]: e.target.value })}
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/onsite/${issue.page_id}`}>查看该页</Link>
                        </Button>
                        <Button size="sm" onClick={() => aiIssue(issue.id)} disabled={busyId === issue.id}>
                          <Bot className="mr-1.5 h-3.5 w-3.5" />
                          {busyId === issue.id ? "生成中…" : "生成改法"}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => saveDraft(issue)} disabled={busyId === issue.id}>
                          保存改法
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => copyDraft(issue)}>
                          <Copy className="mr-1.5 h-3.5 w-3.5" />
                          复制短稿
                        </Button>
                        {issue.status === "confirmed" || issue.status === "draft_applied" ? (
                          <Button size="sm" variant="outline" onClick={() => retestIssue(issue)} disabled={busyId === issue.id}>
                            <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
                            复查本条
                          </Button>
                        ) : issue.severity === "low" && issue.risk === "low" ? (
                          <Button size="sm" variant="outline" onClick={() => apply(issue)} disabled={busyId === issue.id}>
                            交给执行
                          </Button>
                        ) : (
                          <Button size="sm" onClick={() => apply(issue)} disabled={busyId === issue.id}>
                            <Wrench className="mr-1.5 h-3.5 w-3.5" />
                            标记已修改
                          </Button>
                        )}
                        {isTemplateLimited(issue) ? (
                          <Button size="sm" variant="outline" onClick={() => clearTemplateLimit(issue)} disabled={busyId === issue.id}>
                            取消受模板限制
                          </Button>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => markTemplateLimit(issue)} disabled={busyId === issue.id}>
                            记受模板限制
                          </Button>
                        )}
                        <Button size="sm" variant="outline" onClick={() => ignoreIssue(issue)} disabled={busyId === issue.id}>
                          <XCircle className="mr-1.5 h-3.5 w-3.5" />
                          本轮不改
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
