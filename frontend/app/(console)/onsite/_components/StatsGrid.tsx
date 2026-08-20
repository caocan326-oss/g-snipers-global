import { Card, CardContent } from "@/components/ui/card";
import type { OnsiteBoard } from "@/lib/api";

type Stats = {
  fetched: number;
  waitingDraft: number;
  readyToExecute: number;
  waitingRetest: number;
  untested: number;
  needsReview: number;
  solved: number;
};

export function StatsGrid({ board, stats }: { board: OnsiteBoard; stats: Stats }) {
  return (
    <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-10">
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{board.pages}</div>
          <div className="text-xs text-slate-500">已登记页面</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{stats.fetched}</div>
          <div className="text-xs text-slate-500">已查看</div>
        </CardContent>
      </Card>
      <Card className="rounded-md border-red-200">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold text-red-700">{board.counts.critical}</div>
          <div className="text-xs text-slate-500">紧急</div>
        </CardContent>
      </Card>
      <Card className="rounded-md border-amber-200">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold text-amber-700">{board.counts.high}</div>
          <div className="text-xs text-slate-500">优先</div>
        </CardContent>
      </Card>
      <Card className="rounded-md border-emerald-200">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold text-emerald-700">{board.counts.low}</div>
          <div className="text-xs text-slate-500">常规</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{stats.waitingDraft}</div>
          <div className="text-xs text-slate-500">待写改法</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{stats.needsReview}</div>
          <div className="text-xs text-slate-500">需确认</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{stats.readyToExecute}</div>
          <div className="text-xs text-slate-500">待上线</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold">{stats.waitingRetest}</div>
          <div className="text-xs text-slate-500">待复查</div>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardContent className="py-4">
          <div className="text-2xl font-semibold text-emerald-700">{stats.solved}</div>
          <div className="text-xs text-slate-500">已解决</div>
        </CardContent>
      </Card>
    </div>
  );
}
