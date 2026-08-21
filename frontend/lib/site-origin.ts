import { api, siteOriginHost, type CrawlSession } from "@/lib/api";

export function isHostSwitch(current: string, next: string): boolean {
  const from = siteOriginHost(current);
  const to = siteOriginHost(next);
  return Boolean(from && to && from !== to);
}

export async function recrawlSavedSite(maxUrls = 50, maxDepth = 2): Promise<CrawlSession> {
  return api<CrawlSession>("/api/onsite/crawl-site", {
    method: "POST",
    body: JSON.stringify({ max_urls: maxUrls, max_depth: maxDepth }),
    timeoutMs: 180000,
  });
}

export function crawlFinishedNote(session: CrawlSession): string {
  return `已保存，这一轮抓取完成：发现 ${session.discovered} · 成功 ${session.fetched} · 失败 ${session.failed} · 新增问题 ${session.created}`;
}
