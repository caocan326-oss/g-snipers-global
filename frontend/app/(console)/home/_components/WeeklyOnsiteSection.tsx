import Link from "next/link";
import { useState } from "react";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { WorkbenchItem } from "@/lib/api";
import { copyText } from "@/lib/utils";

function liveUrl(origin: string, path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  const root = origin.replace(/\/$/, "");
  if (!root || !path) return "";
  return `${root}${path.startsWith("/") ? path : `/${path}`}`;
}

export function WeeklyOnsiteSection({
  items,
  pinned,
  siteOrigin,
  busyId,
  canRestore,
  note,
  error,
  recheckIssue,
  recordVerdict,
  restoreDropped,
  markSent,
  clearSent,
  markClaimed,
  clearClaimed,
  rotateWeek,
}: {
  items: WorkbenchItem[];
  pinned: boolean;
  siteOrigin: string;
  busyId: string;
  canRestore: boolean;
  note?: string;
  error?: string;
  recheckIssue: (item: WorkbenchItem) => void;
  recordVerdict: (item: WorkbenchItem, passed: boolean) => void;
  restoreDropped: () => void;
  markSent: (item: WorkbenchItem) => void;
  clearSent: (item: WorkbenchItem) => void;
  markClaimed: (item: WorkbenchItem) => void;
  clearClaimed: (item: WorkbenchItem) => void;
  rotateWeek: () => void;
}) {
  const [copiedId, setCopiedId] = useState("");
  const allPassed = items.length > 0 && items.every((item) => item.status === "核对过");
  const unsentCount = items.filter((item) => item.status === "待发给客户").length;
  const failCount = items.filter((item) => item.status === "核对不过").length;

  async function copyNote(item: WorkbenchItem) {
    const text = (item.meta || "").trim();
    if (!text) return;
    const ok = await copyText(text);
    if (ok) {
      setCopiedId(item.id);
      window.setTimeout(() => setCopiedId((cur) => (cur === item.id ? "" : cur)), 2000);
    }
  }

  return (
    <Card className="rounded-md border-amber-200">
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">这周给客户改三处</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              这三处是这周给客户看的改法。客户改不改官网不挡我们交付。「打开核对」只打开现网并记下看过。看完再点「记过」或「记不过」。复制短稿后再点记下已发。客户说改完了还要再打开核对。已发给客户不是官网已改。不会自己勾完。我们不代改。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/distribution">
              <Button size="sm" variant="outline">
                客户说明
              </Button>
            </Link>
            {allPassed ? (
              <Button size="sm" onClick={rotateWeek} disabled={busyId === "weekly-next"}>
                换下一组
              </Button>
            ) : null}
            {canRestore ? (
              <Button size="sm" variant="outline" onClick={restoreDropped} disabled={busyId === "weekly-restore"}>
                放回刚拿掉的一页
              </Button>
            ) : null}
            <Link href="/onsite">
              <Button size="sm">
                去站内
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </div>
        {pinned ? <Badge tone="amber">已钉住。新抓到的页不会顶掉。</Badge> : null}
        {allPassed ? (
          <p className="text-sm leading-6 text-emerald-700">
            这三处都核对过。换下一组按紧急/优先另挑。上一组还在问题板，不是已解决。我们不代改。
          </p>
        ) : null}
        {unsentCount ? (
          <p className="text-sm leading-6 text-amber-800">
            {unsentCount} 处还没发给客户。复制短稿发给客户，再点记下已发。不是官网已改。我们不代发。
          </p>
        ) : null}
        {failCount ? (
          <p className="text-sm leading-6 text-amber-800">
            {failCount} 处核对不过。等客户再改完再打开核对。不是官网已改。我们不代改。
          </p>
        ) : null}
        {error ? <p className="text-sm leading-6 text-red-600">{error}</p> : null}
        {note ? <p className="text-sm leading-6 text-emerald-700">{note}</p> : null}
        {items.length ? (
          <div className="grid gap-3 lg:grid-cols-3">
            {items.map((item, index) => {
              const url = liveUrl(siteOrigin, item.subtitle);
              return (
                <div key={item.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{index + 1}</Badge>
                    {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
                    {item.sent ? <Badge tone="blue">已发给客户</Badge> : null}
                    {item.claimed ? <Badge tone="amber">客户说改完了</Badge> : null}
                  </div>
                  <h3 className="text-sm font-medium text-slate-950">{item.title}</h3>
                  {url ? (
                    <a href={url} target="_blank" rel="noreferrer" className="block text-xs text-brand-700 underline">
                      {item.subtitle}
                    </a>
                  ) : (
                    <p className="text-xs text-slate-500">{item.subtitle}</p>
                  )}
                  {item.meta ? <p className="text-xs leading-5 text-slate-600">{item.meta}</p> : null}
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => recheckIssue(item)} disabled={busyId === `recheck:${item.id}`}>
                      打开核对
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => recordVerdict(item, true)} disabled={busyId === `verdict:${item.id}`}>
                      记过
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => recordVerdict(item, false)} disabled={busyId === `verdict:${item.id}`}>
                      记不过
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void copyNote(item)}
                      disabled={!item.meta.trim()}
                    >
                      {copiedId === item.id ? "已复制" : "复制给客户"}
                    </Button>
                    {item.sent ? (
                      <Button size="sm" variant="outline" onClick={() => clearSent(item)} disabled={busyId === `sent:${item.id}`}>
                        取消已发
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => markSent(item)} disabled={busyId === `sent:${item.id}`}>
                        记下已发
                      </Button>
                    )}
                    {item.sent && item.status !== "核对过" ? (
                      item.claimed ? (
                        <Button size="sm" variant="outline" onClick={() => clearClaimed(item)} disabled={busyId === `claimed:${item.id}`}>
                          取消客户说改完
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => markClaimed(item)} disabled={busyId === `claimed:${item.id}`}>
                          客户说改完了
                        </Button>
                      )
                    ) : null}
                    <Link href="/onsite">
                      <Button size="sm" variant="ghost">
                        去站内
                      </Button>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-500">这周还没有要改的站内三处。有紧急或优先页才会出现。</p>
        )}
      </CardContent>
    </Card>
  );
}
