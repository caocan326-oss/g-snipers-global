import { History, RotateCcw, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SiteArchive } from "@/lib/api";

export function SiteArchivesSection({
  archives,
  archiveBusyId,
  restoreArchive,
  deleteArchive,
  loadArchives,
}: {
  archives: SiteArchive[];
  archiveBusyId: string;
  restoreArchive: (item: SiteArchive) => void;
  deleteArchive: (item: SiteArchive) => void;
  loadArchives: () => void;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <History className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">历史网站 / 测试数据</h2>
            <Badge tone={archives.length ? "blue" : "default"}>{archives.length} 个历史网站</Badge>
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            当前工作台只显示当前官网的数据。保存新官网并切换网站时，旧网站的诊断上下文会进入历史数据；可恢复，也可二次确认后删除。
          </p>
        </div>
        <Button type="button" variant="outline" onClick={loadArchives}>刷新历史数据</Button>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {archives.map((item) => {
          const counts = Object.entries(item.readable_counts).slice(0, 5);
          return (
            <div key={item.id} className="rounded-md border border-slate-200 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="truncate font-semibold text-slate-950">{item.site_origin}</div>
                  <p className="mt-1 text-xs text-slate-500">
                    归档时间：{item.archived_at ? new Date(item.archived_at).toLocaleString("zh-CN") : "未知"}
                  </p>
                  {item.restored_at ? <p className="mt-1 text-xs text-slate-500">最近恢复：{new Date(item.restored_at).toLocaleString("zh-CN")}</p> : null}
                  {item.note ? <p className="mt-2 line-clamp-2 text-xs text-slate-500">{item.note}</p> : null}
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => restoreArchive(item)} disabled={archiveBusyId === item.id}>
                    <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                    恢复
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => deleteArchive(item)} disabled={archiveBusyId === item.id}>
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    删除
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {counts.length ? counts.map(([label, value]) => (
                  <Badge key={label} tone="blue">{label} {value}</Badge>
                )) : <span className="text-xs text-slate-500">该历史快照没有可展示的数据计数。</span>}
              </div>
            </div>
          );
        })}
        {archives.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500 lg:col-span-2">
            还没有历史网站。切换到新官网后，旧网站诊断数据会自动归档到这里。
          </div>
        ) : null}
      </div>
    </section>
  );
}
