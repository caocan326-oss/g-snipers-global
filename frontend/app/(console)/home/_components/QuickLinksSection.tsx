import Link from "next/link";
import { FileText, Globe2, SearchCheck } from "lucide-react";

export function QuickLinksSection() {
  return (
    <section className="grid gap-4 lg:grid-cols-3">
      <Link href="/geo" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
        <Globe2 className="h-5 w-5 text-brand-700" />
        <div className="mt-3 font-medium text-slate-950">检测 AI 搜索可见度</div>
        <p className="mt-1 text-sm text-slate-500">按品牌、品类、竞品和任务型问题分开观测，不用一个黑箱分数概括所有结果。</p>
      </Link>
      <Link href="/onsite" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
        <SearchCheck className="h-5 w-5 text-brand-700" />
        <div className="mt-3 font-medium text-slate-950">复查 SEO 高风险项</div>
        <p className="mt-1 text-sm text-slate-500">优先修 robots、noindex、JS 壳、canonical 和 Schema。</p>
      </Link>
      <Link href="/distribution" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
        <FileText className="h-5 w-5 text-brand-700" />
        <div className="mt-3 font-medium text-slate-950">生成交付报告</div>
        <p className="mt-1 text-sm text-slate-500">报告跟随总览结构，保留数据来源、抓取记录和证据索引，方便客户复核。</p>
      </Link>
    </section>
  );
}
