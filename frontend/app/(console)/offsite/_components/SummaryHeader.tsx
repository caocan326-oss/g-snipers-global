import { Badge } from "@/components/ui/badge";

import { StatTile } from "./StatTile";

type Stats = {
  activeOpportunities: number;
  validPlacements: number;
  needsReview: number;
  openJobs: number;
  approvedAssets: number;
};

export function SummaryHeader({
  stats,
  platformsCount,
}: {
  stats: Stats;
  platformStats?: unknown;
  platformsCount: number;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">站外分发</Badge>
            <Badge tone="amber">半自动 · 人确认再发</Badge>
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-950">想发哪个渠道，点哪张卡片</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            一张卡片就是一个新媒体或目录。AI 写稿；发出去要打开官方页，由客户自己登号或用自己的接口。我们不代发、不代登。内置浏览器还没做。
          </p>
        </div>
        <div className="grid w-full gap-2 sm:grid-cols-3 xl:w-[480px]">
          <StatTile label="渠道" value={platformsCount} helper="一张卡一个渠道" />
          <StatTile label="现成的稿" value={stats.approvedAssets} helper="人看过才能发出" />
          <StatTile label="记下要发" value={stats.openJobs} helper="还没回填结果链接" />
        </div>
      </div>
    </section>
  );
}
