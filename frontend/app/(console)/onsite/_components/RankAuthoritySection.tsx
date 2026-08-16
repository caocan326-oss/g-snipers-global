import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SeoPerformanceSummary } from "@/lib/api";

import { RankDistributionPanel } from "./RankDistributionPanel";

export function RankAuthoritySection({ performance }: { performance: SeoPerformanceSummary | null }) {
  return (
    <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>关键词排名分布</CardTitle>
              <p className="mt-1 text-sm text-slate-500">客户最容易理解的 SEO 表现：有多少词进入第一页、前三页、前五页。</p>
            </div>
            <Badge tone={(performance?.keyword_rank_distribution.total ?? 0) + (performance?.serp?.rank_distribution.total ?? 0) > 0 ? "green" : "amber"}>
              {(performance?.keyword_rank_distribution.total ?? 0) + (performance?.serp?.rank_distribution.total ?? 0) > 0 ? "有排名数据" : "待补数据"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3">
          <RankDistributionPanel
            title="Google/Bing 平均排名"
            distribution={performance?.keyword_rank_distribution}
            empty="授权 Google 搜索表现或导入 Google/Bing 表格后显示。"
          />
          <RankDistributionPanel
            title="目标关键词实查排名"
            distribution={performance?.serp?.rank_distribution}
            empty="运行关键词排名检查后显示前 50 名分布。"
          />
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>网站权重与站外可信度</CardTitle>
          <p className="mt-1 text-sm text-slate-500">权重需要第三方权威数据源，当前不使用没有来源的模拟分数。</p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">第三方权重</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">未接入 Semrush / Ahrefs / Moz / DataForSEO</div>
            <p className="mt-1 text-xs text-slate-500">接入后可显示 Authority Score、Domain Rating、Domain Authority 或同类指标。</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">当前可用替代指标</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">目标词排名、曝光点击、站外来源线索</div>
            <p className="mt-1 text-xs text-slate-500">这些能支撑测试和交付判断，但不能冒充第三方权重。</p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
