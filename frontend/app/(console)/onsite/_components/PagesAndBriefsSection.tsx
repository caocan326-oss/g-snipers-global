import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { crawlStatusLabel, type ContentBrief, type SitePage } from "@/lib/api";
import { discoverySourceLabel, labelOr, pageTypeLabel, priorityHintLabel } from "../../_labels";

type PageForm = { path: string; locale: string; title: string };

export function PagesAndBriefsSection({
  pages,
  form,
  setForm,
  create,
  briefs,
}: {
  pages: SitePage[];
  form: PageForm;
  setForm: (form: PageForm) => void;
  create: (e: FormEvent) => void;
  briefs: ContentBrief[];
}) {
  return (
    <div id="onsite-pages" className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
      <Card className="rounded-md">
        <CardHeader>
        <CardTitle>登记重点页面</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <Input placeholder="路径" value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} required />
            <Input placeholder="语言" value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })} />
            <Input placeholder="页面名称" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            <Button type="submit">加入诊断清单</Button>
          </form>
          <div className="mt-4 max-h-56 overflow-auto rounded-md border border-slate-200">
            {pages.map((p) => (
              <Link
                key={p.id}
                href={`/onsite/${p.id}`}
                className="grid gap-1 border-b border-slate-100 px-3 py-2 text-sm last:border-b-0 hover:bg-slate-50 md:grid-cols-[1fr_auto]"
              >
                <div>
                  <div className="font-medium text-brand-700">{p.path}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>{labelOr(priorityHintLabel, p.priority_hint, "常规")}</span>
                    <span>{labelOr(pageTypeLabel, p.page_type, "其他页")}</span>
                    <span>深度 {p.url_depth ?? 0}</span>
                    <span>{labelOr(discoverySourceLabel, p.discovery_source, "手工登记")}</span>
                    <span>sitemap {p.is_in_sitemap ?? "未测"}</span>
                    <span>字数 {p.word_count ?? 0}</span>
                    <span>缺 alt {p.images_missing_alt ?? 0}/{p.image_count ?? 0}</span>
                    <span>TTFB {p.ttfb_ms ?? "未测"}{p.ttfb_ms ? "ms" : ""}</span>
                    <span>跳转 {p.redirect_count ?? 0}</span>
                    <span>{p.content_type || "未知类型"}</span>
                  </div>
                </div>
                <div className="text-xs text-slate-500 md:text-right">
                  <div>{crawlStatusLabel[p.crawl_status] ?? p.crawl_status}</div>
                  {p.body_hash ? <div>hash {p.body_hash.slice(0, 8)}</div> : null}
                  <div>{p.fetched_at ? new Date(p.fetched_at).toLocaleString("zh-CN") : "尚未抓取"}</div>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>内容选题辅助</CardTitle>
          <CheckCircle2 className="h-5 w-5 text-slate-400" />
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-slate-500">这里辅助内容生产。真正的 SEO 诊断仍以抓取、收录、搜索表现和高风险整改为主。</p>
          {briefs.length === 0 ? <p className="text-sm text-slate-500">还没有提纲。站内问题优先。</p> : null}
          {briefs.slice(0, 5).map((b) => (
            <div key={b.id} className="rounded-md border border-slate-200 p-3">
              <div className="font-medium">{b.title}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                <span>{b.target_keyword}</span>
                <span>{b.locale}</span>
                <Badge tone="amber">SERP {b.serp_features}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
