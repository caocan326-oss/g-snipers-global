import { RadioTower } from "lucide-react";

export function WorkflowStep({
  icon: Icon,
  title,
  value,
  helper,
}: {
  icon: typeof RadioTower;
  title: string;
  value: string | number;
  helper: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-brand-700" />
        <div className="text-sm font-semibold text-slate-900">{title}</div>
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-950">{value}</div>
      <p className="mt-1 text-xs leading-5 text-slate-500">{helper}</p>
    </div>
  );
}
