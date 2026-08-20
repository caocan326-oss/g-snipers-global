import { ClipboardList, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { CrawlSession } from "@/lib/api";

export function SiteSetupCard({
  origin,
  setOrigin,
  saveOrigin,
  setupSnipersTest,
  maxUrls,
  setMaxUrls,
  maxDepth,
  setMaxDepth,
  fetchSite,
  crawlSite,
  busyId,
  sessions,
}: {
  origin: string;
  setOrigin: (value: string) => void;
  saveOrigin: () => void;
  setupSnipersTest: () => void;
  maxUrls: number;
  setMaxUrls: (value: number) => void;
  maxDepth: number;
  setMaxDepth: (value: number) => void;
  fetchSite: () => void;
  crawlSite: () => void;
  busyId: string;
  sessions: CrawlSession[];
}) {
  return (
    <Card id="onsite-site-setup" className="rounded-md">
      <CardHeader>
        <CardTitle>登记要检查的网站</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
          <Input
            placeholder="https://www.customer.com"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
          />
          <Button type="button" variant="outline" onClick={saveOrigin}>
            保存网站
          </Button>
          <Button type="button" variant="outline" onClick={setupSnipersTest}>
            使用演示网站
          </Button>
        </div>
        <div className="grid gap-3 lg:grid-cols-[120px_120px_auto_auto_1fr]">
          <Input
            type="number"
            min={1}
            max={300}
            value={maxUrls}
            onChange={(e) => setMaxUrls(Number(e.target.value))}
            aria-label="最大 URL"
          />
          <Input
            type="number"
            min={0}
            max={5}
            value={maxDepth}
            onChange={(e) => setMaxDepth(Number(e.target.value))}
            aria-label="最大深度"
          />
          <Button type="button" onClick={fetchSite} variant="outline">
            <RefreshCcw className="mr-2 h-4 w-4" />
            查看已登记页面
          </Button>
          <Button type="button" onClick={crawlSite} disabled={busyId === "crawl-site"}>
            <ClipboardList className="mr-2 h-4 w-4" />
            扩大页面范围
          </Button>
          <div className="text-xs text-slate-500">
            当前：{origin || "未设置"} · 最多 {maxUrls} 页 · 深度 {maxDepth}
          </div>
        </div>
        {sessions[0] ? (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            最近一次查看：发现 {sessions[0].discovered} · 成功 {sessions[0].fetched} · 失败 {sessions[0].failed} · 新增问题 {sessions[0].created} · 需浏览器渲染 {sessions[0].needs_js}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
