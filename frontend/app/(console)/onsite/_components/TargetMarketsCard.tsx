import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Market, SeoPerformanceSummary } from "@/lib/api";

export function TargetMarketsCard({
  targetMarkets,
  targetKeywords,
  performance,
}: {
  targetMarkets: Market[];
  targetKeywords: { id: string; label: string; status: string }[];
  performance: SeoPerformanceSummary | null;
}) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>第二步：确认目标市场和搜索词</CardTitle>
        <p className="mt-1 text-sm text-slate-500">诊断会围绕目标国家、客户核心产品词、竞品和关键页面排序，让报告更贴近实际获客市场。</p>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">目标国家 / 市场</div>
          <div className="mt-2 space-y-2">
            {targetMarkets.length ? (
              targetMarkets.map((market) => (
                <div key={market.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-slate-800">{market.name}</span>
                  <span className="text-xs text-slate-500">{market.country_code} · {market.primary_locale}</span>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">未设置。请先在首页填写客户诊断目标。</div>
            )}
          </div>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">核心搜索词 / 选题</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {targetKeywords.length ? (
              targetKeywords.map((item) => (
                <Badge key={item.id} tone={item.status === "ready" ? "green" : "blue"}>
                  {item.label}
                </Badge>
              ))
            ) : (
              <div className="text-sm text-slate-500">未设置。先登记核心产品词、行业词和采购意图词。</div>
            )}
          </div>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">搜索表现 / 网页速度</div>
          <div className="mt-2 space-y-2 text-sm text-slate-700">
            <div className="flex items-center justify-between gap-3">
              <span>Google 搜索表现数据</span>
              <Badge tone={performance?.gsc_status === "已导入" ? "green" : "amber"}>{performance?.gsc_status ?? "读取中"}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Bing Webmaster</span>
              <Badge tone={performance?.bing_status === "已导入" ? "green" : "amber"}>{performance?.bing_status ?? "读取中"}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>网页速度测试</span>
              <Badge tone={performance?.pagespeed_status === "已测速" ? "green" : "amber"}>{performance?.pagespeed_status ?? "读取中"}</Badge>
            </div>
            <p className="text-xs text-slate-500">接入或导入数据后，报告会带上曝光、点击、点击率、排名和速度证据。</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
