import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeoProviderStatusList } from "@/lib/api";

import { providerRoleLabel } from "../_helpers";

export function ProviderStatusCard({ providers }: { providers: GeoProviderStatusList | null }) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>测试来源与可信边界</CardTitle>
        <p className="mt-1 text-sm text-slate-500">
          DeepSeek 负责分析和建议；只有联网搜索类数据源返回来源网址时，才算作给出了官网。
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {(providers?.providers ?? []).map((provider) => (
          <div key={provider.key} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="truncate text-sm font-medium text-slate-800">{provider.label}</div>
              <Badge tone={provider.configured ? "green" : "amber"}>
                {provider.configured ? "已配置" : "未配置"}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone={provider.web_grounded ? "blue" : "default"}>
                {provider.web_grounded ? "可给出联网来源" : "分析参考"}
              </Badge>
              <Badge tone={provider.role === "analysis" ? "brand" : "default"}>{providerRoleLabel[provider.role] ?? provider.role}</Badge>
            </div>
            <p className="mt-2 line-clamp-3 text-xs text-slate-500">{provider.note}</p>
            <p className="mt-2 text-[11px] text-slate-400">配置项：{provider.env_var}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
