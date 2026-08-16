"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export default function WorkOrdersRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/offsite");
  }, [router]);

  return (
    <div className="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">执行项已并入业务工作台</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        独立任务入口已下线。SEO 整改、GEO 复测和站外曝光会在各自模块内完成创建、跟进和核验。
      </p>
      <Button className="mt-4" onClick={() => router.replace("/offsite")}>
        打开站外曝光工作台
      </Button>
    </div>
  );
}
