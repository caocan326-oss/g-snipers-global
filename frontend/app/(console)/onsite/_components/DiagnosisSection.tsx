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
              <CardTitle>检查是否完整</CardTitle>
              <p className="mt-1 text-sm text-slate-500">判断现在的材料够不够写给客户看，以及下一步该补什么。</p>
            </div>
            <Badge tone={diagnosisReadiness.ready ? "green" : "amber"}>{diagnosisReadiness.ready ? "可以继续" : "材料待补"}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">已查看页面</div>
            <div className="mt-1 text-xl font-semibold text-slate-950">{diagnosisReadiness.pageCoverage}%</div>
            <p className="mt-1 text-xs text-slate-500">{fetched}/{totalPages} 个已登记页面已查看</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">未完成问题</div>
            <div className="mt-1 text-xl font-semibold text-slate-950">{diagnosisReadiness.unresolved}</div>
            <p className="mt-1 text-xs text-slate-500">紧急 / 优先 / 常规尚未关闭</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">搜索数据</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">{diagnosisReadiness.hasSearchData ? "已接入" : "未接入"}</div>
            <p className="mt-1 text-xs text-slate-500">Google / Bing 导入或自动同步</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">速度 / 关键词位置</div>
            <div className="mt-1 text-sm font-semibold text-slate-950">{diagnosisReadiness.hasSpeed ? "已测速" : "未测速"} / {diagnosisReadiness.hasSerp ? "已查位置" : "未查位置"}</div>
            <p className="mt-1 text-xs text-slate-500">用来说明打开速度和搜索结果位置</p>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>给客户的结论</CardTitle>
              <p className="mt-1 text-sm text-slate-500">把搜索数据转成下一步建议，而不是只列原始数字。</p>
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
