import { BarChart3, CheckCircle2, Gauge, Globe2, Link2, ListChecks, SearchCheck } from "lucide-react";

import type { Workbench, WorkbenchSeoPerformance } from "@/lib/api";

import { MetricTile } from "./MetricTile";
import { PillarCard } from "./PillarCard";

export function PillarsOverview({
  data,
  highRisk,
  technicalTone,
  geoStatusTone,
  geoRecorded,
  workTone,
  reviewTotal,
  perf,
}: {
  data: Workbench;
  highRisk: number;
  technicalTone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  geoStatusTone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  geoRecorded: number;
  workTone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  reviewTotal: number;
  perf: WorkbenchSeoPerformance;
}) {
  return (
    <>
      <section className="grid gap-4 xl:grid-cols-3">
        <PillarCard
          title="网站 SEO 风险"
          status={highRisk > 0 ? "需整改" : data.summary.onsite_pages > 0 ? "已审计" : "未抓取"}
          statusTone={technicalTone}
          primary={`${highRisk} 个 P0/P1`}
          helper={`${data.summary.onsite_pages} 个页面，检查搜索引擎能不能抓到、看懂、收录，并判断页面质量。`}
          href="/onsite"
          icon={SearchCheck}
        >
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P0</div><div className="mt-1 font-semibold">{data.summary.onsite_open_critical}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P1</div><div className="mt-1 font-semibold">{data.summary.onsite_open_high}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P2</div><div className="mt-1 font-semibold">{data.summary.onsite_open_low}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="AI 搜索可见度"
          status={data.summary.geo_untested > 0 ? "存在未测" : geoRecorded > 0 ? "已有证据" : "未采样"}
          statusTone={geoStatusTone}
          primary={`${geoRecorded} 条记录`}
          helper={`${data.summary.geo_prompts} 个买家问题，${data.summary.geo_untested} 个未测。看 AI 回答里有没有提到客户、有没有引用客户官网。`}
          href="/geo"
          icon={Globe2}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">买家问题</div><div className="mt-1 font-semibold">{data.summary.geo_prompts}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">证据待补</div><div className="mt-1 font-semibold">{data.summary.geo_untested}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="站外曝光与整改"
          status={reviewTotal > 0 ? "待处理" : "清爽"}
          statusTone={workTone}
          primary={`${reviewTotal} 个执行项`}
          helper={`${data.summary.geo_tickets_open} 个 AI 搜索整改项，${data.summary.seo_pending_review} 个网站待复核；站外机会进入曝光工作台跟进。`}
          href="/offsite"
          icon={ListChecks}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">GEO</div><div className="mt-1 font-semibold">{data.summary.geo_tickets_open}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">人审</div><div className="mt-1 font-semibold">{data.summary.seo_pending_review}</div></div>
          </div>
        </PillarCard>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="曝光" value={perf.total_impressions} helper={`${perf.days} 天 Google/Bing 数据`} icon={BarChart3} />
        <MetricTile label="点击" value={perf.total_clicks} helper={`点击率 ${perf.avg_ctr ?? "-"}%`} icon={Gauge} />
        <MetricTile label="收录页面" value={perf.indexed_pages} helper={`待核验 ${perf.index_pending_pages}`} icon={CheckCircle2} />
        <MetricTile label="站外权威线索" value={perf.backlink_domains} helper={`${perf.authority_status}，未核验 ${perf.unverified_backlinks}`} icon={Link2} />
      </section>
    </>
  );
}
