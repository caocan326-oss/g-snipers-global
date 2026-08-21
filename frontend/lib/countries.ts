export type DiagnosticCountry = {
  code: string;
  name: string;
  region: string;
  locale: string;
};

export const DIAGNOSTIC_COUNTRIES: DiagnosticCountry[] = [
  { code: "US", name: "美国", region: "北美", locale: "en-US" },
  { code: "GB", name: "英国", region: "欧洲", locale: "en-GB" },
  { code: "DE", name: "德国", region: "欧洲", locale: "de-DE" },
  { code: "JP", name: "日本", region: "亚太", locale: "ja-JP" },
  { code: "AE", name: "阿联酋", region: "中东", locale: "en-AE" },
  { code: "AU", name: "澳大利亚", region: "亚太", locale: "en-AU" },
];

export function countryByCode(code: string) {
  return DIAGNOSTIC_COUNTRIES.find((item) => item.code === (code || "").toUpperCase());
}

export function countryByLocale(locale: string) {
  const value = (locale || "").trim();
  return DIAGNOSTIC_COUNTRIES.find((item) => item.locale.toLowerCase() === value.toLowerCase());
}

export function countryLabel(codeOrLocale: string) {
  return countryByCode(codeOrLocale)?.name || countryByLocale(codeOrLocale)?.name || codeOrLocale || "未选国家";
}

export function localeForCode(code: string) {
  return countryByCode(code)?.locale || "en-US";
}
