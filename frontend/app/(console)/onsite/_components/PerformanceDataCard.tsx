import { BarChart3, Gauge, RefreshCcw, Search, Upload, Wrench } from "lucide-react";
import { ChangeEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type {
  BingStatus,
  DataSyncStatus,
  GscStatus,
  IndexNowStatus,
  IntegrationSettings,
  SeoPerformanceSummary,
} from "@/lib/api";

type IntegrationForm = {
  gsc_oauth_client_id: string;
  gsc_oauth_client_secret: string;
  gsc_oauth_redirect_uri: string;
  pagespeed_api_key: string;
  brightdata_dataset_api_key: string;
  brightdata_serp_dataset_id: string;
  brightdata_serp_endpoint: string;
};

export function PerformanceDataCard({
  gsc,
  integrations,
  bing,
  indexNow,
  syncStatus,
  performance,
  showGscSetup,
  setShowGscSetup,
  integrationForm,
  setIntegrationForm,
  authorizeGsc,
  saveIntegrationSettings,
  syncGsc,
  busyId,
  performanceSource,
  setPerformanceSource,
  importPerformanceFile,
  runPageSpeed,
  runSerp,
  submitIndexNow,
  runDueSync,
}: {
  gsc: GscStatus | null;
  integrations: IntegrationSettings | null;
  bing: BingStatus | null;
  indexNow: IndexNowStatus | null;
  syncStatus: DataSyncStatus | null;
  performance: SeoPerformanceSummary | null;
  showGscSetup: boolean;
  setShowGscSetup: (updater: (value: boolean) => boolean) => void;
  integrationForm: IntegrationForm;
  setIntegrationForm: (form: IntegrationForm) => void;
  authorizeGsc: () => void;
  saveIntegrationSettings: () => void;
  syncGsc: () => void;
  busyId: string;
  performanceSource: "gsc_csv" | "bing_csv";
  setPerformanceSource: (value: "gsc_csv" | "bing_csv") => void;
  importPerformanceFile: (event: ChangeEvent<HTMLInputElement>) => void;
  runPageSpeed: () => void;
  runSerp: () => void;
  submitIndexNow: () => void;
  runDueSync: () => void;
}) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>第四步：补齐搜索表现数据</CardTitle>
        <p className="mt-1 text-sm text-slate-500">优先使用免费且可信的数据源：Google/Bing 记录真实搜索表现，网页速度测试记录访问体验，关键词排名检查记录目标词在 Google 的可见度。</p>
      </CardHeader>
      <CardContent className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-md border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <Search className="h-4 w-4" />
            Google 搜索表现自动同步
          </div>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <div className="flex items-center justify-between gap-3">
              <span>OAuth 配置</span>
              <Badge tone={gsc?.configured ? "green" : "amber"}>{gsc?.configured ? "已配置" : "未配置"}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>客户授权</span>
              <Badge tone={gsc?.connected ? "green" : "amber"}>{gsc?.connected ? "已连接" : "未连接"}</Badge>
            </div>
            <div className="truncate text-xs text-slate-500">{gsc?.site_url || gsc?.note || "读取中"}</div>
            {gsc?.last_sync_at ? <div className="text-xs text-slate-500">最近同步 {new Date(gsc.last_sync_at).toLocaleString("zh-CN")}</div> : null}
            {gsc?.last_error ? <div className="text-xs text-red-600">{gsc.last_error}</div> : null}
          </div>
          <div className="mt-3 grid gap-2">
            {gsc?.configured ? (
              <Button type="button" variant="outline" onClick={authorizeGsc}>
                {gsc.connected ? "重新授权 Google 数据" : "打开 Google 授权页"}
              </Button>
            ) : (
              <Button type="button" variant="outline" onClick={() => setShowGscSetup((value) => !value)}>
                查看配置要求
              </Button>
            )}
            <Button type="button" onClick={syncGsc} disabled={!gsc?.connected || busyId === "gsc-sync"}>
              {busyId === "gsc-sync" ? "同步中…" : "同步 28 天数据"}
            </Button>
          </div>
          {showGscSetup || !gsc?.configured ? (
            <div className="mt-3 rounded-md bg-amber-50 p-3 text-xs leading-5 text-amber-900">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-medium">配置数据源</div>
                <Badge tone={integrations?.gsc_configured ? "green" : "amber"}>
                  {integrations?.gsc_configured ? "Google 数据已配置" : "Google 数据待配置"}
                </Badge>
              </div>
              <p className="mt-1">
                Google 授权页需要先保存授权 Client ID / Secret。密钥只提交到后端保存，前端不会回显完整值。
              </p>
              <div className="mt-3 grid gap-2">
                <Input
                  placeholder="Google OAuth Client ID"
                  value={integrationForm.gsc_oauth_client_id}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, gsc_oauth_client_id: e.target.value })}
                />
                <Input
                  placeholder="Google OAuth Client Secret"
                  type="password"
                  value={integrationForm.gsc_oauth_client_secret}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, gsc_oauth_client_secret: e.target.value })}
                />
                <Input
                  placeholder={`Redirect URI，默认 ${gsc?.redirect_uri || "前端 /onsite"}`}
                  value={integrationForm.gsc_oauth_redirect_uri}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, gsc_oauth_redirect_uri: e.target.value })}
                />
              </div>
              <div className="mt-3 grid gap-2 border-t border-amber-200 pt-3">
                <Input
                  placeholder="Bright Data Dataset API Key"
                  type="password"
                  value={integrationForm.brightdata_dataset_api_key}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, brightdata_dataset_api_key: e.target.value })}
                />
                <Input
                  placeholder="Bright Data SERP Dataset ID，默认 gd_mfz5x93lmsjjjylob"
                  value={integrationForm.brightdata_serp_dataset_id}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, brightdata_serp_dataset_id: e.target.value })}
                />
                <Input
                  placeholder="网页速度测试 API Key（可选，不填也可免费测速）"
                  type="password"
                  value={integrationForm.pagespeed_api_key}
                  onChange={(e) => setIntegrationForm({ ...integrationForm, pagespeed_api_key: e.target.value })}
                />
              </div>
              {integrations?.fields.some((field) => field.configured) ? (
                <div className="mt-3 grid gap-1">
                  {integrations.fields.filter((field) => field.configured).map((field) => (
                    <div key={field.key} className="flex items-center justify-between gap-2 rounded border border-amber-200 bg-white px-2 py-1">
                      <span className="truncate">{field.label}</span>
                      <span className="shrink-0 font-mono text-[11px]">{field.masked_value} · {field.source === "env" ? ".env" : "前台保存"}</span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button type="button" size="sm" onClick={saveIntegrationSettings} disabled={busyId === "integrations"}>
                  <Wrench className="mr-2 h-3.5 w-3.5" />
                  {busyId === "integrations" ? "保存中…" : "保存配置"}
                </Button>
                {integrations?.gsc_configured ? (
                  <Button type="button" size="sm" variant="outline" onClick={authorizeGsc}>
                    打开授权页
                  </Button>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
        <div className="rounded-md border border-slate-200 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                <Upload className="h-4 w-4" />
                导入搜索表现 CSV
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                适合客户暂时不能授权 Google 数据时使用。支持 Google/Bing 导出的关键词、页面、国家、设备、点击、曝光、点击率、平均排名字段。
              </p>
            </div>
            <Badge tone={(performance?.imports.length ?? 0) > 0 ? "green" : "amber"}>
              已导入 {performance?.imports.length ?? 0} 批
            </Badge>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-[160px_minmax(0,1fr)]">
            <select
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-500"
              value={performanceSource}
              onChange={(e) => setPerformanceSource(e.target.value as "gsc_csv" | "bing_csv")}
            >
              <option value="gsc_csv">GSC CSV</option>
              <option value="bing_csv">Bing CSV</option>
            </select>
            <Input
              className="min-w-0"
              type="file"
              accept=".csv,text/csv"
              onChange={importPerformanceFile}
              disabled={busyId === "performance-import"}
            />
          </div>
        </div>
        <div className="rounded-md border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <Gauge className="h-4 w-4" />
            免费测速
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.speed_latest.length ?? 0}</div>
              <div className="text-[11px] text-slate-500">测速记录</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.speed_latest[0]?.performance_score ?? "-"}</div>
              <div className="text-[11px] text-slate-500">最近性能</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.speed_latest[0]?.seo_score ?? "-"}</div>
              <div className="text-[11px] text-slate-500">最近 SEO</div>
            </div>
          </div>
          <Button type="button" onClick={runPageSpeed} disabled={busyId === "pagespeed"} className="mt-3 w-full">
            <Gauge className="mr-2 h-4 w-4" />
            {busyId === "pagespeed" ? "测速中…" : "测首页和核心页"}
          </Button>
        </div>
        <div className="rounded-md border border-slate-200 p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <Search className="h-4 w-4" />
            Google 关键词排名检查
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.serp?.total_runs ?? 0}</div>
              <div className="text-[11px] text-slate-500">查询轮次</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.serp?.own_visible_runs ?? 0}</div>
              <div className="text-[11px] text-slate-500">我方出现</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.serp?.competitor_visible_runs ?? 0}</div>
              <div className="text-[11px] text-slate-500">竞品出现</div>
            </div>
          </div>
          <Button type="button" onClick={runSerp} disabled={busyId === "serp"} className="mt-3 w-full">
            <Search className="mr-2 h-4 w-4" />
            {busyId === "serp" ? "查询中…" : "查询目标关键词排名"}
          </Button>
          <p className="mt-2 text-xs text-slate-500">
            {performance?.serp?.configured ? "按目标国家和核心搜索词查询 Google 前 50，作为市场可见度证据。" : "服务器尚未配置排名检查数据源，关键词排名保持未测。"}
          </p>
        </div>
        <div className="rounded-md border border-slate-200 p-4 xl:col-span-2">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <BarChart3 className="h-4 w-4" />
            搜索表现摘要
          </div>
          <div className="mt-3 grid gap-2 text-center sm:grid-cols-3">
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.total_impressions ?? 0}</div>
              <div className="text-[11px] text-slate-500">曝光</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.total_clicks ?? 0}</div>
              <div className="text-[11px] text-slate-500">点击</div>
            </div>
            <div className="rounded-md bg-slate-50 p-2">
              <div className="text-lg font-semibold">{performance?.avg_ctr ?? "-"}</div>
              <div className="text-[11px] text-slate-500">CTR%</div>
            </div>
          </div>
          <div className="mt-3 space-y-1 text-xs text-slate-600">
            {(performance?.by_query ?? []).slice(0, 3).map((item) => (
              <div key={item.key} className="flex items-center justify-between gap-2">
                <span className="truncate">{item.key}</span>
                <span className="shrink-0 text-slate-500">{item.impressions} / {item.clicks}</span>
              </div>
            ))}
            {performance?.by_query.length ? null : <div className="text-slate-500">导入 GSC/Bing CSV 后显示关键词表现。</div>}
          </div>
        </div>
      </CardContent>
      {performance?.serp?.latest_runs?.length ? (
        <CardContent className="border-t border-slate-100 pt-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-sm font-medium text-slate-800">最近关键词排名查询</div>
            <Badge tone="blue">排名证据</Badge>
          </div>
          <div className="grid gap-2 lg:grid-cols-2">
            {performance.serp.latest_runs.slice(0, 4).map((run) => (
              <div key={run.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate font-medium text-slate-800">{run.keyword}</span>
                  <Badge tone={run.status === "ok" ? "green" : "red"}>{run.status}</Badge>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600">
                  <span>{run.country}/{run.device}</span>
                  <span>我方 {run.own_best_position ?? "未出现"}</span>
                  <span>竞品 {run.competitor_best_position ?? "未出现"}</span>
                </div>
                {run.error ? <p className="mt-2 text-xs text-red-600">{run.error}</p> : null}
              </div>
            ))}
          </div>
        </CardContent>
      ) : null}
      <CardContent className="grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-3">
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-sm font-medium text-slate-800">Bing Webmaster</div>
          <div className="mt-2 flex items-center justify-between gap-3 text-sm">
            <span>API Key</span>
            <Badge tone={bing?.configured ? "green" : "amber"}>{bing?.configured ? "已配置" : "未配置"}</Badge>
          </div>
          <p className="mt-2 text-xs text-slate-500">{bing?.note || "读取中"}</p>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-sm font-medium text-slate-800">IndexNow</div>
          <div className="mt-2 flex items-center justify-between gap-3 text-sm">
            <span>{indexNow?.host || "未设置官网"}</span>
            <Badge tone={indexNow?.configured ? "green" : "amber"}>{indexNow?.configured ? "可提交" : "未配置"}</Badge>
          </div>
          <p className="mt-2 truncate text-xs text-slate-500">{indexNow?.key_location || indexNow?.note || "读取中"}</p>
          {indexNow?.last_submitted_at ? <p className="mt-1 text-xs text-slate-500">最近提交 {new Date(indexNow.last_submitted_at).toLocaleString("zh-CN")}</p> : null}
          <Button type="button" variant="outline" onClick={submitIndexNow} disabled={!indexNow?.configured || busyId === "indexnow"} className="mt-3 w-full">
            {busyId === "indexnow" ? "提交中…" : "提交已抓取 URL"}
          </Button>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-medium text-slate-800">同步历史</div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={runDueSync}
              disabled={!gsc?.connected || busyId === "run-due-sync"}
            >
              {busyId === "run-due-sync" ? "检查中…" : "运行到期同步"}
            </Button>
          </div>
          <div className="mt-2 space-y-2">
            {(syncStatus?.runs ?? []).slice(0, 3).map((run) => (
              <div key={run.id} className="flex items-center justify-between gap-3 text-xs text-slate-600">
                <span>{run.source} · {run.mode} · {run.status}</span>
                <span>{run.rows_imported ? `${run.rows_imported} 行` : run.submitted ? `${run.submitted} URL` : "-"}</span>
              </div>
            ))}
            {syncStatus?.runs.length ? null : <p className="text-xs text-slate-500">暂无同步记录。</p>}
          </div>
          <p className="mt-2 text-xs text-slate-500">服务器定时任务也可以调用同一个入口，避免依赖浏览器常开。</p>
        </div>
      </CardContent>
    </Card>
  );
}
