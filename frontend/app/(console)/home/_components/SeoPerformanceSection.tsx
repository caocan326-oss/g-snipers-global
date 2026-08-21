import { BarChart3 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { WorkbenchSeoPerformance } from "@/lib/api";

import type { seoPerformanceVerdict } from "../_helpers";
import { BucketList } from "./BucketList";
import { RankDistributionGrid } from "./RankDistributionGrid";

export function SeoPerformanceSection({
  perf,
  seoVerdict,
}: {
  perf: WorkbenchSeoPerformance;
  seoVerdict: ReturnType<typeof seoPerformanceVerdict>;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <BarChart3 className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">SEO 表现结论</h2>
            <Badge tone={seoVerdict.tone as "amber" | "green" | "red"}>{perf.days} 天</Badge>
          </div>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">{seoVerdict.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{seoVerdict.text}</p>
          {perf.serp_runs > 0 ? (
            <p className="mt-3 text-lg font-semibold text-slate-950">
              我方出现 {perf.serp_own_visible_runs} / 竞品出现 {perf.serp_competitor_visible_runs}
            </p>
          ) : null}
        </div>
        <div className="grid w-full gap-2 text-sm sm:grid-cols-3 xl:w-[520px]">
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">平均排名</div>
            <div className="mt-1 font-semibold text-slate-950">{perf.avg_position ?? "-"}</div>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">目标词 TOP10</div>
            <div className="mt-1 font-semibold text-slate-950">{perf.serp_rank_distribution.top_10}/{perf.serp_rank_distribution.total || perf.serp_runs}</div>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">最近性能</div>
            <div className="mt-1 font-semibold text-slate-950">{perf.latest_speed_score ?? "-"}</div>
          </div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <RankDistributionGrid
          title="Google/Bing 关键词排名分布"
          distribution={perf.keyword_rank_distribution}
          empty="接入 Google/Bing 后显示关键词平均排名分层。"
        />
        <RankDistributionGrid
          title="目标关键词实查分布"
          distribution={perf.serp_rank_distribution}
          empty="运行目标关键词排名检查后显示前 50 名结果。"
        />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <BucketList title="国家表现" items={perf.top_countries} empty="接入 Google/Bing 后显示目标国家曝光。" />
        <BucketList title="关键词机会" items={perf.top_keywords} empty="导入搜索表现后显示高曝光关键词。" />
        <BucketList title="页面机会" items={perf.top_pages} empty="导入页面维度数据后显示可优化页面。" />
      </div>
    </section>
  );
}
