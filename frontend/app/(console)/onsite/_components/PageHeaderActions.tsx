import { Bot, ClipboardList, Download } from "lucide-react";

import { Button } from "@/components/ui/button";

export function PageHeaderActions({
  crawlOrSeed,
  analyze,
  busyId,
  downloadReport,
  downloadReportTable,
}: {
  crawlOrSeed: () => void;
  analyze: () => void;
  busyId: string;
  downloadReport: () => void;
  downloadReportTable: () => void;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold">网站 SEO 诊断与整改</h1>
        <p className="mt-1 text-sm text-slate-500">
          按步骤检查客户官网：先设置网站，再抓取页面，找出高风险问题，接入搜索表现，最后导出客户报告并复测。
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button onClick={crawlOrSeed} variant="outline">
          <ClipboardList className="mr-2 h-4 w-4" />
          从内链扩清单
        </Button>
        <Button onClick={analyze} disabled={busyId === "ai-batch"}>
          <Bot className="mr-2 h-4 w-4" />
          {busyId === "ai-batch" ? "生成中…" : "批量生成整改建议"}
        </Button>
        <Button onClick={downloadReport} variant="outline">
          <Download className="mr-2 h-4 w-4" />
          导出客户报告（PDF）
        </Button>
        <Button onClick={downloadReportTable} variant="outline">
          <Download className="mr-2 h-4 w-4" />
          导出执行表格
        </Button>
      </div>
    </div>
  );
}
