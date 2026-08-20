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
          title="网站检查"
          status={highRisk > 0 ? "待处理" : data.summary.onsite_pages > 0 ? "已查看" : "未查看"}
          statusTone={technicalTone}
          primary={`${highRisk} 个紧急/优先`}
          helper={`${data.summary.onsite_pages} 个页面。看能不能打开、搜索有没有收录、标题和说明清不清楚。`}
          href="/onsite"
          icon={SearchCheck}
        >
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">紧急</div><div className="mt-1 font-semibold">{data.summary.onsite_open_critical}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">优先</div><div className="mt-1 font-semibold">{data.summary.onsite_open_high}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">常规</div><div className="mt-1 font-semibold">{data.summary.onsite_open_low}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="AI 搜索可见度"
          status={data.summary.geo_untested > 0 ? "尚未检查" : geoRecorded > 0 ? "已有记录" : "尚未开始"}
          statusTone={geoStatusTone}
          primary={`${geoRecorded} 条记录`}
          helper={`${data.summary.geo_prompts} 个买家问题，${data.summary.geo_untested} 条尚未检查。看 AI 回答里有没有提到客户、有没有给出官网。`}
          href="/geo"
          icon={Globe2}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">买家问题</div><div className="mt-1 font-semibold">{data.summary.geo_prompts}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">证据待补</div><div className="mt-1 font-semibold">{data.summary.geo_untested}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="站外曝光与跟进"
          status={reviewTotal > 0 ? "待处理" : "清爽"}
          statusTone={workTone}
          primary={`${reviewTotal} 个执行项`}
          helper={`${data.summary.geo_tickets_open} 个 AI 搜索待处理项，${data.summary.seo_pending_review} 个网站待复查；站外线索进曝光台跟进。`}
          href="/offsite"
          icon={ListChecks}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">AI 搜索</div><div className="mt-1 font-semibold">{data.summary.geo_tickets_open}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">待复查</div><div className="mt-1 font-semibold">{data.summary.seo_pending_review}</div></div>
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
