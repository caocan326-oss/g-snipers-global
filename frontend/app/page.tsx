"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getToken() ? "/distribution" : "/login");
  }, [router]);
  return <p className="p-8 text-sm text-slate-500">正在进入工作台…</p>;
}
