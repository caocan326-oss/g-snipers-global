import { CheckCircle2, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BacklinkGap } from "@/lib/api";

import { verifyLabel, verifyTone } from "../_helpers";

type VerifyFilter = "all" | "unverified" | "valid" | "dead" | "spam";

export function PlacementsTab({
  gaps,
  filter,
  setFilter,
  visibleGaps,
  setVerify,
}: {
  gaps: BacklinkGap[];
  filter: VerifyFilter;
  setFilter: (filter: VerifyFilter) => void;
  visibleGaps: BacklinkGap[];
  setVerify: (id: string, verifyStatus: string) => void;
}) {
  return (
    <section className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
          <button key={s} type="button" className="text-left" onClick={() => setFilter(filter === s ? "all" : s)}>
            <Card className={filter === s ? "rounded-md border-brand-600" : "rounded-md"}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  {s === "valid" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <ShieldCheck className="h-4 w-4 text-slate-400" />}
                  {verifyLabel[s]}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">
                {gaps.filter((g) => g.verify_status === s).length}
              </CardContent>
            </Card>
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {visibleGaps.map((g) => (
          <div key={g.id} className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="font-semibold text-slate-950">{g.referring_domain}</div>
                  <Badge tone={verifyTone[g.verify_status]}>{verifyLabel[g.verify_status] ?? g.verify_status}</Badge>
                </div>
                <p className="mt-1 break-all font-mono text-xs text-slate-400">{g.link_url || g.competitor_url || "未登记 URL"}</p>
                <p className="mt-2 text-sm text-slate-500">{g.notes || "暂无备注"}</p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-1">
                {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
                  <Button key={s} size="sm" variant="outline" onClick={() => setVerify(g.id, s)}>
                    {verifyLabel[s]}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
