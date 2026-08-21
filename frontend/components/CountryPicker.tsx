import { DIAGNOSTIC_COUNTRIES } from "@/lib/countries";
import { cn } from "@/lib/utils";

export function CountryPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (code: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {DIAGNOSTIC_COUNTRIES.map((country) => {
        const on = value === country.code;
        return (
          <button
            key={country.code}
            type="button"
            onClick={() => onChange(country.code)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-sm",
              on ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            )}
          >
            {country.name}
          </button>
        );
      })}
    </div>
  );
}
