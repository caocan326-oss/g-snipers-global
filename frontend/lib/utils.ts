import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export async function copyText(text: string) {
  const value = (text || "").trim();
  if (!value) return false;
  await navigator.clipboard.writeText(value);
  return true;
}
