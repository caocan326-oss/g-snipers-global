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
          helper={`${data.summary.onsite_pages} 个页面。只算网站问题，不含 AI 搜索和站外。`}
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
          status={(data.summary.geo_latest_sampled ?? 0) > 0 ? "已抽查" : data.summary.geo_prompts > 0 ? "还没抽查" : "尚未开始"}
          statusTone={geoStatusTone}
          primary={(data.summary.geo_latest_sampled ?? 0) > 0 ? `${data.summary.geo_latest_sampled} 条抽查` : `${geoRecorded} 条记录`}
          helper={
            (data.summary.geo_latest_sampled ?? 0) > 0
              ? `${data.summary.geo_prompts} 个买家问题。看抽查记录，不要看引擎空位。`
              : `${data.summary.geo_prompts} 个买家问题还没联网抽查。`
          }
          href="/geo"
          icon={Globe2}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">买家问题</div><div className="mt-1 font-semibold">{data.summary.geo_prompts}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">最近抽查</div><div className="mt-1 font-semibold">{data.summary.geo_latest_sampled ?? 0}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="站外曝光与跟进"
          status={reviewTotal > 0 ? "待处理" : "清爽"}
          statusTone={workTone}
          primary={`${reviewTotal} 个执行项`}
          helper={`网站 + AI 搜索 + 站外未关闭加总，和左边「紧急/优先」不是同一个数。其中 AI 搜索待处理 ${data.summary.geo_tickets_open}，网站待复查 ${data.summary.seo_pending_review}。`}
          href="/offsite"
          icon={ListChecks}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">AI 搜索</div><div className="mt-1 font-semibold">{data.summary.geo_tickets_open}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">待复查</div><div className="mt-1 font-semibold">{data.summary.seo_pending_review}</div></div>
          </div>
        </PillarCard>
      </section>
      <p className="text-xs leading-5 text-slate-500">
        三块数字口径不同：左边只算网站紧急/优先，中间是买家问题抽查，右边是三处未关闭加总。对不上不是算错。
      </p>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="曝光" value={perf.total_impressions} helper={`${perf.days} 天 Google/Bing 数据`} icon={BarChart3} />
        <MetricTile label="点击" value={perf.total_clicks} helper={`点击率 ${perf.avg_ctr ?? "-"}%`} icon={Gauge} />
        <MetricTile label="收录页面" value={perf.indexed_pages} helper={`待核验 ${perf.index_pending_pages}`} icon={CheckCircle2} />
        <MetricTile label="站外权威线索" value={perf.backlink_domains} helper={`${perf.authority_status}，未核验 ${perf.unverified_backlinks}`} icon={Link2} />
      </section>
    </>
  );
}
