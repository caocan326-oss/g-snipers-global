import type { WorkbenchSeoBucket } from "@/lib/api";

export function BucketList({ title, items, empty }: { title: string; items: WorkbenchSeoBucket[]; empty: string }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <div className="text-xs font-semibold text-slate-500">{title}</div>
      <div className="mt-2 space-y-2">
        {items.slice(0, 4).map((item) => (
          <div key={item.key} className="flex items-center justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-slate-800">{item.key}</span>
            <span className="shrink-0 text-xs text-slate-500">{item.impressions} 曝光 / {item.clicks} 点击</span>
          </div>
        ))}
        {items.length === 0 ? <div className="text-sm text-slate-500">{empty}</div> : null}
      </div>
    </div>
  );
}
