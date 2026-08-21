import { Button } from "@/components/ui/button";

export function SiteSwitchBanner({
  currentOrigin,
  nextOrigin,
  busy,
  onConfirm,
  onCancel,
}: {
  currentOrigin: string;
  nextOrigin: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-4">
      <p className="text-sm font-semibold text-amber-950">更换官网会归档当前工作台</p>
      <p className="mt-1 text-sm leading-6 text-amber-900">
        检查、AI 搜索和清单都会换成新站点。现在的演示站会进历史网站，以后还能恢复。
      </p>
      <p className="mt-2 text-sm text-slate-700">当前：{currentOrigin || "未设置"}</p>
      <p className="text-sm text-slate-700">新官网：{nextOrigin}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" onClick={onConfirm} disabled={busy}>
          {busy ? "正在保存…" : "确认更换并开始抓取"}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
          先不换
        </Button>
      </div>
    </div>
  );
}
