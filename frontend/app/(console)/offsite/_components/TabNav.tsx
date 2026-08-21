import { Button } from "@/components/ui/button";

import type { Tab } from "../_helpers";

export function TabNav({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  const items: { key: Tab; label: string }[] = [
    { key: "channels", label: "渠道卡片" },
    { key: "content", label: "对外稿" },
    { key: "distribution", label: "执行记录" },
    { key: "placements", label: "发出去了没有" },
    { key: "platforms", label: "账号和接口" },
    { key: "opportunities", label: "线索" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Button key={item.key} size="sm" variant={tab === item.key ? "default" : "outline"} onClick={() => setTab(item.key)}>
          {item.label}
        </Button>
      ))}
    </div>
  );
}
