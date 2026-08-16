import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Workbench } from "@/lib/api";

import { ActionRow } from "./ActionRow";
import { EmptyState } from "./EmptyState";

export function RiskAndGeoQueueSection({ data }: { data: Workbench }) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <Card className="rounded-md">
        <CardHeader><CardTitle>SEO 风险问题</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.seo_items.length ? data.seo_items.map((item) => <ActionRow key={item.id} item={item} />) : <EmptyState text="暂无打开的高风险 SEO 问题；未抓取页面仍显示为未测。" />}
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader><CardTitle>AI 搜索待验收</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.geo_items.length ? data.geo_items.map((item) => <ActionRow key={item.id} item={item} />) : <EmptyState text="暂无打开的 AI 搜索整改项；买家问题或测试证据不足时会保持未测。" />}
        </CardContent>
      </Card>
    </section>
  );
}
