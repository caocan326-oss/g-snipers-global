import { Button } from "@/components/ui/button";

import type { Tab } from "../_helpers";

export function TabNav({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant={tab === "sample" ? "default" : "outline"} onClick={() => setTab("sample")}>
        问句采样
      </Button>
      <Button size="sm" variant={tab === "tickets" ? "default" : "outline"} onClick={() => setTab("tickets")}>
        整改验收
      </Button>
      <Button size="sm" variant={tab === "assets" ? "default" : "outline"} onClick={() => setTab("assets")}>
        可引用资产
      </Button>
    </div>
  );
}
