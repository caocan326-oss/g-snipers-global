import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SeoPerformanceSummary } from "@/lib/api";

type DiagnosisReadiness = {
  pageCoverage: number;
  hasSearchData: boolean;
  hasSpeed: boolean;
  hasSerp: boolean;
  unresolved: number;
  ready: boolean;
};

type SearchVerdict = {
  title: string;
  text: string;
  tone: "default" | "amber" | "red" | "green";
};

export function DiagnosisSection({
  diagnosisReadiness,
  fetched,
  totalPages,
  searchVerdict,
  performance,
}: {
  diagnosisReadiness: DiagnosisReadiness;
  fetched: number;
  totalPages: number;
  searchVerdict: SearchVerdict;
  performance: SeoPerformanceSummary | null;
}) {
  return (
    <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>第三步：判断诊断是否完整</CardTitle>
              <p className="mt-1 text-sm text-slate-500">用于判断这份网站诊断能不能进入客户测试和报告导出。</p>
            </div>
            <Badge tone={diagnosisReadiness.ready ? "green" : "amber"}>{diagnosisReadiness.ready ? "可测试" : "证据待补"}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">页面抓取覆盖</div>
            <div className="mt-1 text-xl font-semibold text-slate-950">{diagnosisReadiness.pageCoverage}%</div>
            <p className="mt-1 text-xs text-slate-500">{fetched}/{totalPages} 个登记页面已抓取</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">待推进问题</div>
            <div className="mt-1 text-xl font-semibold text-slate-950">{diagnosisReadiness.unresolved}</div>
            <p className="mt-1 text-xs text-slate-500">P0/P1/P2 未关闭问题</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">搜索表现证据</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">{diagnosisReadiness.hasSearchData ? "已接入" : "未接入"}</div>
            <p className="mt-1 text-xs text-slate-500">Google/Bing 表格导入或自动同步</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">速度 / 关键词排名</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">{diagnosisReadiness.hasSpeed ? "已测速" : "未测速"} / {diagnosisReadiness.hasSerp ? "已查排名" : "未查排名"}</div>
            <p className="mt-1 text-xs text-slate-500">用于支撑页面体验和搜索可见度</p>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>客户能看懂的结论</CardTitle>
              <p className="mt-1 text-sm text-slate-500">把搜索数据翻译成客户能理解的下一步，而不是只展示原始字段。</p>
            </div>
            <Badge tone={searchVerdict.tone}>{performance?.gsc_status ?? "读取中"}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <h3 className="text-lg font-semibold text-slate-950">{searchVerdict.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{searchVerdict.text}</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">曝光</div>
              <div className="mt-1 font-semibold">{performance?.total_impressions ?? 0}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">点击</div>
              <div className="mt-1 font-semibold">{performance?.total_clicks ?? 0}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">平均排名</div>
              <div className="mt-1 font-semibold">{performance?.avg_position ?? "-"}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
