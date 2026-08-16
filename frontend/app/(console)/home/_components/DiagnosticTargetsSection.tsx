import { Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ProjectTargets } from "@/lib/api";

export type TargetForm = { site_origin: string; markets: string; keywords: string; competitors: string };

export function DiagnosticTargetsSection({
  targets,
  targetForm,
  setTargetForm,
  saveTargets,
  note,
}: {
  targets: ProjectTargets | null;
  targetForm: TargetForm;
  setTargetForm: (value: TargetForm) => void;
  saveTargets: () => void;
  note: string;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Target className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">客户诊断目标</h2>
            <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "可开跑" : "待补"}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">先明确客户官网、目标国家、核心关键词和竞品，后续网站抓取、关键词排名检查和 AI 搜索买家问题都会按这些目标执行。</p>
        </div>
        <Button type="button" onClick={saveTargets}>保存诊断目标</Button>
      </div>
      <div className="mt-4 grid gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr]">
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">官网</div>
          <Input value={targetForm.site_origin} onChange={(e) => setTargetForm({ ...targetForm, site_origin: e.target.value })} placeholder="https://www.example.com" />
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">目标国家</div>
          <Textarea className="min-h-[96px]" value={targetForm.markets} onChange={(e) => setTargetForm({ ...targetForm, markets: e.target.value })} placeholder="United States | North America | US | en-US" />
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">核心品类 / 搜索词</div>
          <Textarea className="min-h-[96px]" value={targetForm.keywords} onChange={(e) => setTargetForm({ ...targetForm, keywords: e.target.value })} placeholder="industrial pump supplier, valve manufacturer" />
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">主要竞品</div>
          <Textarea className="min-h-[96px]" value={targetForm.competitors} onChange={(e) => setTargetForm({ ...targetForm, competitors: e.target.value })} placeholder="Competitor | https://competitor.com" />
        </div>
      </div>
      {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
    </section>
  );
}
