import { Button } from "@/components/ui/button";

import type { Tab } from "../_helpers";

export function TabNav({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant={tab === "tickets" ? "default" : "outline"} onClick={() => setTab("tickets")}>
        待处理（办事）
      </Button>
      <Button size="sm" variant={tab === "sample" ? "default" : "outline"} onClick={() => setTab("sample")}>
        买家问题
      </Button>
      <Button size="sm" variant={tab === "assets" ? "default" : "outline"} onClick={() => setTab("assets")}>
        可供引用的材料
      </Button>
    </div>
  );
}
