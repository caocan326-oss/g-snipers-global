import type { Gauge } from "lucide-react";

export function MetricTile({ label, value, helper, icon: Icon }: { label: string; value: string | number | null; helper?: string; icon?: typeof Gauge }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
        {Icon ? <Icon className="h-4 w-4 text-slate-400" /> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value ?? "-"}</div>
      {helper ? <div className="mt-1 text-xs text-slate-500">{helper}</div> : null}
    </div>
  );
}
