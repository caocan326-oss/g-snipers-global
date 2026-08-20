import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { GeoAsset, GeoChecklistItem, SeoPage } from "@/lib/api";

export function AssetsPanel({
  llms,
  cite,
  pages,
  pageId,
  items,
  generateLlms,
  saveAsset,
  aiAsset,
  readyAsset,
  loadChecklist,
  setCheck,
}: {
  llms: GeoAsset | undefined;
  cite: GeoAsset | undefined;
  pages: SeoPage[];
  pageId: string;
  items: GeoChecklistItem[];
  generateLlms: () => void;
  saveAsset: (id: string, body: string) => void;
  aiAsset: (id: string) => void;
  readyAsset: (id: string) => void;
  loadChecklist: (id: string) => void;
  setCheck: (id: string, status: string) => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>llms.txt 草稿</CardTitle>
            <p className="mt-1 text-sm text-slate-500">这是给 AI 理解网站用的材料草稿，不会自动发布到客户域名。</p>
          </div>
          <Button variant="outline" onClick={generateLlms}>
            按选题生成
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {llms ? (
            <>
              <Badge>{llms.status === "ready" ? "可交付" : "草稿"}</Badge>
              <Textarea
                className="min-h-[220px] font-mono"
                defaultValue={llms.body}
                key={llms.updated_at ?? llms.id}
                onBlur={(e) => saveAsset(llms.id, e.target.value)}
              />
              <Button variant="outline" onClick={() => aiAsset(llms.id)}>
                AI 优化草稿
              </Button>
              <Button onClick={() => readyAsset(llms.id)}>我已确认，标记可交付</Button>
            </>
          ) : (
            <p className="text-sm text-slate-500">还没有草稿。</p>
          )}
        </CardContent>
      </Card>
      {cite ? (
        <Card>
          <CardHeader>
            <CardTitle>可供引用的材料清单</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              className="min-h-[160px]"
              defaultValue={cite.body}
              key={cite.updated_at ?? cite.id}
              onBlur={(e) => saveAsset(cite.id, e.target.value)}
            />
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>内容是否便于被引用</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <select
            className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
            value={pageId}
            onChange={(e) => loadChecklist(e.target.value)}
          >
            <option value="">选择一篇选题</option>
            {pages.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          {items.map((i) => (
            <div key={i.id} className="flex items-center justify-between rounded-md border p-3">
              <div>
                <div className="font-medium">{i.label}</div>
                <Badge tone={i.status === "untested" ? "amber" : i.status === "pass" ? "green" : "red"}>
                  {i.status === "untested" ? "尚未检查" : i.status === "pass" ? "通过" : "未通过"}
                </Badge>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "untested")}>
                  尚未检查
                </Button>
                <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "pass")}>
                  通过
                </Button>
                <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "fail")}>
                  未通过
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
