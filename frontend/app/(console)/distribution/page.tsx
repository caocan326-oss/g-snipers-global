"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function DistributionRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/offsite?tab=dist");
  }, [router]);
  return <p className="text-sm text-slate-500">分发台已并入「外链核验与分发」…</p>;
}
