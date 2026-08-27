import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoTrustMap, GeoTrustRound } from "@/lib/api";

function RoundBlock({ row }: { row: GeoTrustRound }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={row.mentioned ? "green" : "default"}>{row.mentioned ? "提到了" : "没提到"}</Badge>
        <span className="text-xs text-slate-500">{row.label}{row.owned ? " · 有官网" : ""}</span>
      </div>
      {row.hosts.length ? (
        <p className="mt-1 text-xs leading-5 text-slate-600">引用：{row.hosts.join("、")}</p>
      ) : (
        <p className="mt-1 text-xs leading-5 text-slate-500">这一轮没有引用。</p>
      )}
      {row.competitors.length ? <p className="mt-1 text-xs leading-5 text-slate-600">竞品：{row.competitors.join("、")}</p> : null}
    </div>
  );
}

const kindTone: Record<string, "green" | "amber" | "red" | "blue" | "default"> = {
  owned: "green",
  marketplace: "amber",
  competitor: "red",
  other: "blue",
};

export function TrustMapCard({ trustMap }: { trustMap?: GeoTrustMap | null }) {
  const empty = !trustMap || trustMap.empty;
  return (
    <Card className="rounded-md border-sky-200">
      <CardHeader>
        <CardTitle>信任源地图 / 竞品对照</CardTitle>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          同一批已记问句里，AI 引用了谁、提到了谁；同一问对照上一轮和这一轮。只记抽查里出现的。没有原句或还没抽就空着。不会编来源。不保证这次被提到。
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-slate-600">{trustMap?.note || "没有原句，没有信任源地图。不会编来源，不编竞品。"}</p>
        {trustMap?.compare_note ? <p className="text-sm leading-6 text-slate-600">{trustMap.compare_note}</p> : null}
        {empty ? null : (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">AI 引用的站</h3>
              {trustMap.sources.length ? (
                trustMap.sources.map((row) => (
                  <div key={row.host} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={kindTone[row.kind] || "default"}>{row.kind_label}</Badge>
                      <span className="text-xs text-slate-500">{row.hits} 次 · {row.prompt_count} 句</span>
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{row.host}</p>
                    {row.sample_prompt ? <p className="mt-1 text-xs leading-5 text-slate-500">{row.sample_prompt}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">还没有抽查引用。</p>
              )}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-950">同一问里提到的竞品</h3>
              {trustMap.competitors.length ? (
                trustMap.competitors.map((row) => (
                  <div key={row.name} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={row.registered ? "red" : "amber"}>{row.registered ? "选题已记" : "抽查出现"}</Badge>
                      <span className="text-xs text-slate-500">{row.hits} 次 · {row.prompt_count} 句</span>
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-950">{row.name}</p>
                    {row.sample_prompt ? <p className="mt-1 text-xs leading-5 text-slate-500">{row.sample_prompt}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">抽查里还没有竞品名字。</p>
              )}
            </div>
          </div>
        )}
        {trustMap?.rounds && trustMap.rounds.length > 1 ? (
          <div className="grid gap-3 md:grid-cols-2">
            {trustMap.rounds.map((row) => (
              <RoundBlock key={`${row.label}-${row.at}`} row={row} />
            ))}
          </div>
        ) : null}
        {trustMap?.prompts?.length ? (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-slate-950">按问句对照</h3>
            {trustMap.prompts.map((row) => (
              <div key={row.prompt_id} className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-medium text-slate-950">{row.prompt_text}</p>
                {row.compare ? <p className="text-xs leading-5 text-slate-600">{row.compare}</p> : null}
                <div className="grid gap-2 md:grid-cols-2">
                  {row.previous ? <RoundBlock row={row.previous} /> : null}
                  {row.latest ? <RoundBlock row={row.latest} /> : null}
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
