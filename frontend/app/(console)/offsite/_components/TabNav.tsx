import { Button } from "@/components/ui/button";

import type { Tab } from "../_helpers";

export function TabNav({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button size="sm" variant={tab === "opportunities" ? "default" : "outline"} onClick={() => setTab("opportunities")}>
        推荐曝光渠道
      </Button>
      <Button size="sm" variant={tab === "distribution" ? "default" : "outline"} onClick={() => setTab("distribution")}>
        执行任务
      </Button>
      <Button size="sm" variant={tab === "placements" ? "default" : "outline"} onClick={() => setTab("placements")}>
        结果核验
      </Button>
      <Button size="sm" variant={tab === "content" ? "default" : "outline"} onClick={() => setTab("content")}>
        对外材料
      </Button>
      <Button size="sm" variant={tab === "platforms" ? "default" : "outline"} onClick={() => setTab("platforms")}>
        平台主页与账号
      </Button>
    </div>
  );
}
